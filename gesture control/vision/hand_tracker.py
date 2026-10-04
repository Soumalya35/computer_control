"""
Hand Tracker Module
Wraps MediaPipe Hands to detect up to 2 hands, measuring exact inference latency and extracting landmarks.
"""

import time
import cv2
from typing import List, Tuple, Optional
from mediapipe.python.solutions import hands, drawing_utils

from .landmarks import HandLandmarksSet


class HandTracker:
    """Manages MediaPipe Hands detection and landmark parsing."""

    def __init__(
        self,
        max_num_hands: int = 2,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.70,
        min_tracking_confidence: float = 0.70
    ):
        self.mp_hands = hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_draw = drawing_utils
        self.last_inference_ms = 0.0

    def process(self, frame_bgr) -> Tuple[List[Tuple[HandLandmarksSet, str, float, any]], float]:
        """
        Processes BGR frame through MediaPipe and measures exact inference latency.
        Returns: (parsed_hands: [(landmarks, handedness, score, raw_landmarks)], inference_ms)
        """
        h, w, _ = frame_bgr.shape
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        t0 = time.perf_counter()
        results = self.mp_hands.process(rgb)
        t1 = time.perf_counter()
        self.last_inference_ms = (t1 - t0) * 1000.0

        parsed_hands = []
        if results.multi_hand_landmarks and results.multi_handedness:
            for raw_lms, raw_handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                handedness_label = raw_handedness.classification[0].label
                detection_score = getattr(raw_handedness.classification[0], "score", 0.90)

                lm_set = HandLandmarksSet(raw_lms.landmark, frame_width=w, frame_height=h)
                parsed_hands.append((lm_set, handedness_label, detection_score, raw_lms))

        return parsed_hands, self.last_inference_ms

    def draw_hand(self, frame, raw_landmarks):
        """Draws standard MediaPipe landmarks and connection bones."""
        self.mp_draw.draw_landmarks(
            frame,
            raw_landmarks,
            hands.HAND_CONNECTIONS
        )
