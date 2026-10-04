"""
Hand Association & Multi-Hand Tracking Module
Tracks up to 2 hands, preserves persistent left/right identities across frames,
maps primary/secondary action roles, and prevents accidental identity swaps.
"""

import time
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from .landmarks import HandLandmarksSet


@dataclass
class HandTrack:
    """Persistent tracking state for an individual hand."""
    track_id: int
    role: str                       # "PRIMARY" (pointer/drag/scroll) vs "SECONDARY" (auxiliary/hotkeys)
    handedness: str                 # "Right" or "Left"
    landmarks: HandLandmarksSet
    raw_landmarks: any
    detection_confidence: float
    center: Tuple[float, float]
    velocity: float
    last_seen: float
    active: bool


class HandAssociationTracker:
    """
    Associates raw frame detections with persistent HandTrack identities.
    Prevents role swapping when hands cross and recovers gracefully from temporary occlusions.
    """

    def __init__(self, primary_hand_preference: str = "Right", lost_timeout_sec: float = 0.60):
        self.primary_hand_preference = primary_hand_preference
        self.lost_timeout_sec = lost_timeout_sec

        self.tracks: Dict[int, HandTrack] = {}
        self.next_track_id = 1

    def update(
        self,
        detected_hands: List[Tuple[HandLandmarksSet, str, float, any]]
    ) -> List[HandTrack]:
        """
        Matches detected hands with persistent tracks using handedness, spatial proximity, and velocity.
        Assigns PRIMARY role to the primary hand (default: Right) and SECONDARY to the other.
        """
        now = time.time()
        active_tracks: List[HandTrack] = []

        # If no hands detected in this frame, provide short coasting grace period (120ms)
        if not detected_hands:
            coasting_tracks = []
            for track in list(self.tracks.values()):
                if track.active and (now - track.last_seen <= 0.12):
                    coasting_tracks.append(track)
                elif now - track.last_seen > self.lost_timeout_sec:
                    track.active = False
            # Prune stale tracks older than 5 seconds
            self.tracks = {tid: t for tid, t in self.tracks.items() if (now - t.last_seen) <= 5.0}
            if coasting_tracks:
                if len(coasting_tracks) == 1:
                    coasting_tracks[0].role = "PRIMARY"
                return coasting_tracks
            return []

        # Prune stale tracks older than 5 seconds
        self.tracks = {tid: t for tid, t in self.tracks.items() if (now - t.last_seen) <= 5.0}

        # Match detections to existing tracks
        unmatched_detections = list(detected_hands)
        matched_track_ids = set()

        for track_id, track in self.tracks.items():
            if not track.active and (now - track.last_seen > self.lost_timeout_sec):
                continue

            best_match_idx = -1
            min_dist = 0.35  # Max normalized distance threshold for association

            for idx, (lm_set, handedness, score, raw_lms) in enumerate(unmatched_detections):
                center = lm_set.get_palm_center_norm()
                dist = math.hypot(center[0] - track.center[0], center[1] - track.center[1])

                # Heavy penalty if handedness doesn't match
                if handedness != track.handedness:
                    dist += 0.20

                if dist < min_dist:
                    min_dist = dist
                    best_match_idx = idx

            if best_match_idx >= 0:
                # Update existing track
                lm_set, handedness, score, raw_lms = unmatched_detections.pop(best_match_idx)
                center = lm_set.get_palm_center_norm()
                velocity = math.hypot(center[0] - track.center[0], center[1] - track.center[1])

                # Adaptive landmark smoothing: dampens webcam noise while preserving fast movements
                if track.landmarks is not None and len(track.landmarks) == len(lm_set):
                    beta = max(0.40, min(0.85, 0.40 + velocity * 8.0))
                    for i in range(len(lm_set.points)):
                        p_new = lm_set.points[i]
                        p_old = track.landmarks.points[i]
                        p_new.x = (1.0 - beta) * p_old.x + beta * p_new.x
                        p_new.y = (1.0 - beta) * p_old.y + beta * p_new.y
                        p_new.z = (1.0 - beta) * p_old.z + beta * p_new.z
                        p_new.px = int(round((1.0 - beta) * p_old.px + beta * p_new.px))
                        p_new.py = int(round((1.0 - beta) * p_old.py + beta * p_new.py))

                track.landmarks = lm_set
                track.raw_landmarks = raw_lms
                track.detection_confidence = score
                track.center = center
                track.velocity = velocity
                track.last_seen = now
                track.active = True

                matched_track_ids.add(track_id)
                active_tracks.append(track)

        # Create new tracks for remaining unmatched detections
        for lm_set, handedness, score, raw_lms in unmatched_detections:
            center = lm_set.get_palm_center_norm()
            role = "PRIMARY" if handedness == self.primary_hand_preference else "SECONDARY"

            new_track = HandTrack(
                track_id=self.next_track_id,
                role=role,
                handedness=handedness,
                landmarks=lm_set,
                raw_landmarks=raw_lms,
                detection_confidence=score,
                center=center,
                velocity=0.0,
                last_seen=now,
                active=True
            )
            self.tracks[self.next_track_id] = new_track
            self.next_track_id += 1
            active_tracks.append(new_track)

        # Ensure single PRIMARY role assignment if both hands are detected
        primary_tracks = [t for t in active_tracks if t.role == "PRIMARY"]
        if len(primary_tracks) > 1:
            # Demote track that doesn't match primary_hand_preference
            for t in primary_tracks:
                if t.handedness != self.primary_hand_preference:
                    t.role = "SECONDARY"

        # If only 1 hand is present and it is Left, grant PRIMARY role so single-handed user can control cursor
        if len(active_tracks) == 1:
            active_tracks[0].role = "PRIMARY"

        return active_tracks
