"""
Calibrator Module
Provides a comprehensive 12-stage biometric calibration routine that calibrates
EVERY gesture recognized in the catalog (Open Palm, Pointing, Pinch, 2-Finger Scroll,
3-Finger Alt+Tab, 4-Finger Task View, Thumb Up, Pinky Only, Call Shaka, Closed Fist,
Left Hand Selection, and Relaxed Rest) with interactive navigation ([N] Next / [B] Back)
and cumulative atomic persistence.
"""

import time
import math
import numpy as np
from typing import Optional, Dict, Any, List, Tuple

from kinematics.distances import (
    euclidean_distance_2d,
    get_palm_scale,
    get_normalized_pinch_ratio,
    get_thumb_to_pinky_ratio
)
from kinematics.angles import joint_cosine_alignment
from config.loader import config


class Calibrator:
    """Guided biometric calibration state machine covering all catalog gestures."""

    STAGES = [
        "OPEN_PALM",          # 1. Resume System / Palm Scale & Finger Lengths
        "POINTING",           # 2. Move Mouse / Index Collinearity & Tremor
        "PINCH",              # 3. Left Click / Drag (Right Hand)
        "TWO_FINGERS",        # 4. Scroll Mode / Peace Sign (Index + Middle)
        "THREE_FINGERS",      # 5. Alt+Tab Window Switch (Index + Middle + Ring)
        "FOUR_FINGERS",       # 6. Task View (Index + Middle + Ring + Pinky)
        "THUMB_UP",           # 7. Volume Up (Thumb extended, 4 fingers folded)
        "PINKY_UP",           # 8. Volume Down (Pinky extended, others folded)
        "CALL_SHAKA",         # 9. Play / Pause (Thumb + Pinky extended)
        "CLOSED_FIST",        # 10. Pause System (All 5 fingers curled)
        "BIMANUAL_SELECT",    # 11. Left Hand Selection / Click Trigger
        "RELAX",              # 12. Resting Open Hand (Exit Threshold Baseline)
        "COMPLETE"
    ]

    def __init__(self, samples_per_stage: int = 75, prep_countdown_sec: float = 2.0):
        self.samples_per_stage = samples_per_stage
        self.prep_countdown_sec = prep_countdown_sec
        self.stage_idx = 0
        self.samples: List[Any] = []
        self.stage_prep_start = 0.0
        self.is_prepping = False

        # Active biometric parameters
        self.calibrated_palm_scale = 0.30
        self.calibrated_pinch_enter = 0.38
        self.calibrated_pinch_exit = 0.52
        self.calibrated_left_pinch_enter = 0.36
        self.calibrated_left_pinch_exit = 0.50
        self.calibrated_tremor_noise = 2.0
        self.calibrated_finger_ext_ratio = 1.25
        self.calibrated_finger_straight_cos = 0.60
        self.calibrated_two_finger_diff = 0.38

        # Dictionary storing individual profile metrics for each gesture
        self.gestures_data: Dict[str, Any] = {}

        self.is_active = False

    def start(self):
        """Starts or restarts the full guided calibration routine."""
        self.stage_idx = 0
        self.samples = []
        self.gestures_data = {}
        self.is_active = True
        self._start_stage_prep()

    def stop(self):
        """Cancels calibration and returns to normal operation."""
        self.is_active = False
        self.stage_idx = 0
        self.samples = []
        self.is_prepping = False

    def next_stage(self):
        """Manually advances to the next calibration stage (Skip feature)."""
        if self.stage_idx < len(self.STAGES) - 2:
            self.stage_idx += 1
            self._start_stage_prep()
        elif self.stage_idx == len(self.STAGES) - 2:
            self.stage_idx += 1
            self.is_active = False
            self._save_profile()

    def prev_stage(self):
        """Goes back to the previous calibration stage to re-record."""
        if self.stage_idx > 0:
            self.stage_idx -= 1
            self._start_stage_prep()

    def _start_stage_prep(self):
        """Starts settling countdown before actively recording samples for the current stage."""
        self.stage_prep_start = time.time()
        self.is_prepping = True
        self.samples = []

    def get_current_stage(self) -> str:
        if self.stage_idx < len(self.STAGES):
            return self.STAGES[self.stage_idx]
        return "COMPLETE"

    def get_stage_progress(self) -> Tuple[float, int, int]:
        """Returns: (fraction: float 0..1, current_samples: int, total_samples: int)"""
        if self.is_prepping:
            elapsed = time.time() - self.stage_prep_start
            return min(1.0, elapsed / max(0.1, self.prep_countdown_sec)), 0, self.samples_per_stage
        curr = len(self.samples)
        return min(1.0, curr / float(self.samples_per_stage)), curr, self.samples_per_stage

    def get_instructions(self) -> str:
        """Returns user-facing prompt text with countdowns or remaining sample counts."""
        stage = self.get_current_stage()
        if stage == "COMPLETE":
            return "Calibration Complete! All 12 gesture profiles saved."

        total_steps = len(self.STAGES) - 1
        step_num = self.stage_idx + 1

        stage_titles = {
            "OPEN_PALM": "OPEN PALM (All 5 fingers extended)",
            "POINTING": "POINTING (Index extended, others curled)",
            "PINCH": "PINCH (Thumb & Index tips touching firmly)",
            "TWO_FINGERS": "TWO FINGERS / PEACE (Index & Middle extended)",
            "THREE_FINGERS": "THREE FINGERS (Index, Middle & Ring extended)",
            "FOUR_FINGERS": "FOUR FINGERS (Index, Middle, Ring & Pinky)",
            "THUMB_UP": "THUMB UP (Thumb extended up, fingers curled)",
            "PINKY_UP": "PINKY ONLY (Pinky extended, others curled)",
            "CALL_SHAKA": "CALL / SHAKA (Thumb & Pinky extended)",
            "CLOSED_FIST": "CLOSED FIST (All fingers folded tightly)",
            "BIMANUAL_SELECT": "LEFT HAND PINCH (Thumb & Index on Left Hand)",
            "RELAX": "RELAXED HAND (Resting open hand naturally)"
        }

        target_desc = stage_titles.get(stage, stage)

        if self.is_prepping:
            rem_prep = max(0.0, self.prep_countdown_sec - (time.time() - self.stage_prep_start))
            return f"[{step_num}/{total_steps}] GET READY: {target_desc} in {rem_prep:.1f}s... ([N] Next | [B] Back)"

        remaining = max(0, self.samples_per_stage - len(self.samples))
        pct = int((len(self.samples) / float(self.samples_per_stage)) * 100)
        return f"[{step_num}/{total_steps}] HOLD {target_desc} ({pct}% | {remaining} frames) - [N] Skip | [B] Back"

    def process_frame(self, landmarks, confidence: float, hand_label: str = "Right") -> bool:
        """
        Gathers calibration sample from current frame if confidence is high.
        Supports both Right and Left hand calibration.
        Returns True if entire calibration is complete.
        """
        if not self.is_active or self.stage_idx >= len(self.STAGES) - 1:
            return True

        # Check preparation countdown
        if self.is_prepping:
            if (time.time() - self.stage_prep_start) >= self.prep_countdown_sec:
                self.is_prepping = False
                self.samples = []
            else:
                return False

        if confidence < 0.60:
            return False

        stage = self.get_current_stage()
        wrist = landmarks[0]
        palm = get_palm_scale(landmarks)

        # ----------------------------------------------------
        # 1. OPEN_PALM: Reference Palm Scale & All Finger Lengths
        # ----------------------------------------------------
        if stage == "OPEN_PALM":
            idx_ratio = euclidean_distance_2d(landmarks[8], wrist) / max(1e-4, euclidean_distance_2d(landmarks[6], wrist))
            mid_ratio = euclidean_distance_2d(landmarks[12], wrist) / max(1e-4, euclidean_distance_2d(landmarks[10], wrist))
            cos_idx = joint_cosine_alignment(landmarks[5], landmarks[6], landmarks[8])

            self.samples.append((palm, idx_ratio, mid_ratio, cos_idx))
            if len(self.samples) >= self.samples_per_stage:
                palms = [s[0] for s in self.samples]
                idx_ratios = [s[1] for s in self.samples]
                cosines = [s[3] for s in self.samples]

                self.calibrated_palm_scale = float(np.median(palms))
                self.calibrated_finger_ext_ratio = round(float(np.percentile(idx_ratios, 25)) * 0.90, 2)
                self.calibrated_finger_straight_cos = round(float(np.percentile(cosines, 25)) * 0.85, 2)

                self.gestures_data["OPEN_PALM"] = {
                    "palm_scale": self.calibrated_palm_scale,
                    "index_ratio": round(float(np.median(idx_ratios)), 3),
                    "finger_straightness_cosine": self.calibrated_finger_straight_cos
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 2. POINTING: Index Collinearity & Resting Tremor
        # ----------------------------------------------------
        elif stage == "POINTING":
            self.samples.append((landmarks[8].x, landmarks[8].y))
            if len(self.samples) >= self.samples_per_stage:
                xs = [p[0] for p in self.samples]
                diffs = np.diff(xs)
                self.calibrated_tremor_noise = round(float(np.std(diffs) * 1280.0), 3)

                idx_ratio = euclidean_distance_2d(landmarks[8], wrist) / max(1e-4, euclidean_distance_2d(landmarks[6], wrist))
                cos_idx = joint_cosine_alignment(landmarks[5], landmarks[6], landmarks[8])

                self.gestures_data["POINTING"] = {
                    "tremor_noise_px": self.calibrated_tremor_noise,
                    "index_ratio": round(idx_ratio, 3),
                    "index_collinearity": round(cos_idx, 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 3. PINCH: Primary Hand Contact Ratio
        # ----------------------------------------------------
        elif stage == "PINCH":
            p_ratio = get_normalized_pinch_ratio(landmarks)
            self.samples.append(p_ratio)
            if len(self.samples) >= self.samples_per_stage:
                median_pinch = float(np.median(self.samples))
                self.calibrated_pinch_enter = round(max(0.20, median_pinch * 1.25), 3)
                self.calibrated_pinch_exit = round(max(0.35, self.calibrated_pinch_enter * 1.35), 3)

                self.gestures_data["PINCH"] = {
                    "contact_ratio": round(median_pinch, 3),
                    "enter_ratio": self.calibrated_pinch_enter,
                    "exit_ratio": self.calibrated_pinch_exit
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 4. TWO_FINGERS: Middle Extension & Finger Separation
        # ----------------------------------------------------
        elif stage == "TWO_FINGERS":
            dist_idx_mid = euclidean_distance_2d(landmarks[8], landmarks[12]) / max(1e-4, palm)
            mid_ratio = euclidean_distance_2d(landmarks[12], wrist) / max(1e-4, euclidean_distance_2d(landmarks[10], wrist))
            self.samples.append((dist_idx_mid, mid_ratio))
            if len(self.samples) >= self.samples_per_stage:
                dists = [s[0] for s in self.samples]
                self.calibrated_two_finger_diff = round(float(np.median(dists)), 3)

                self.gestures_data["TWO_FINGERS"] = {
                    "separation_ratio": self.calibrated_two_finger_diff,
                    "middle_ratio": round(float(np.median([s[1] for s in self.samples])), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 5. THREE_FINGERS: Ring Extension & 3-Finger Bundle
        # ----------------------------------------------------
        elif stage == "THREE_FINGERS":
            ring_ratio = euclidean_distance_2d(landmarks[16], wrist) / max(1e-4, euclidean_distance_2d(landmarks[14], wrist))
            cos_ring = joint_cosine_alignment(landmarks[13], landmarks[14], landmarks[16])
            self.samples.append((ring_ratio, cos_ring))
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["THREE_FINGERS"] = {
                    "ring_ratio": round(float(np.median([s[0] for s in self.samples])), 3),
                    "ring_collinearity": round(float(np.median([s[1] for s in self.samples])), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 6. FOUR_FINGERS: Pinky Extension in Cluster
        # ----------------------------------------------------
        elif stage == "FOUR_FINGERS":
            pinky_ratio = euclidean_distance_2d(landmarks[20], wrist) / max(1e-4, euclidean_distance_2d(landmarks[18], wrist))
            span = euclidean_distance_2d(landmarks[8], landmarks[20]) / max(1e-4, palm)
            self.samples.append((pinky_ratio, span))
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["FOUR_FINGERS"] = {
                    "pinky_ratio": round(float(np.median([s[0] for s in self.samples])), 3),
                    "cluster_span_ratio": round(float(np.median([s[1] for s in self.samples])), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 7. THUMB_UP: Thumb Abduction & Vertical Alignment
        # ----------------------------------------------------
        elif stage == "THUMB_UP":
            thumb_ratio = get_thumb_to_pinky_ratio(landmarks)
            self.samples.append(thumb_ratio)
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["THUMB_UP"] = {
                    "thumb_extension_ratio": round(float(np.median(self.samples)), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 8. PINKY_UP: Isolated Pinky Extension
        # ----------------------------------------------------
        elif stage == "PINKY_UP":
            pinky_ratio = euclidean_distance_2d(landmarks[20], wrist) / max(1e-4, euclidean_distance_2d(landmarks[18], wrist))
            ring_tip = euclidean_distance_2d(landmarks[16], wrist) / max(1e-4, palm)
            self.samples.append((pinky_ratio, ring_tip))
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["PINKY_UP"] = {
                    "pinky_ratio": round(float(np.median([s[0] for s in self.samples])), 3),
                    "ring_folded_ratio": round(float(np.median([s[1] for s in self.samples])), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 9. CALL_SHAKA: Thumb & Pinky Span
        # ----------------------------------------------------
        elif stage == "CALL_SHAKA":
            shaka_span = euclidean_distance_2d(landmarks[4], landmarks[20]) / max(1e-4, palm)
            mid_fold = euclidean_distance_2d(landmarks[12], wrist) / max(1e-4, palm)
            self.samples.append((shaka_span, mid_fold))
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["CALL_SHAKA"] = {
                    "thumb_pinky_span": round(float(np.median([s[0] for s in self.samples])), 3),
                    "middle_fold_ratio": round(float(np.median([s[1] for s in self.samples])), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 10. CLOSED_FIST: All Folded Ratios
        # ----------------------------------------------------
        elif stage == "CLOSED_FIST":
            f_ratio = euclidean_distance_2d(landmarks[8], wrist) / max(1e-4, palm)
            self.samples.append(f_ratio)
            if len(self.samples) >= self.samples_per_stage:
                self.gestures_data["CLOSED_FIST"] = {
                    "folded_finger_ratio": round(float(np.median(self.samples)), 3)
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 11. BIMANUAL_SELECT: Left Hand Selection Pinch
        # ----------------------------------------------------
        elif stage == "BIMANUAL_SELECT":
            p_ratio = get_normalized_pinch_ratio(landmarks)
            self.samples.append(p_ratio)
            if len(self.samples) >= self.samples_per_stage:
                median_left = float(np.median(self.samples))
                self.calibrated_left_pinch_enter = round(max(0.20, median_left * 1.25), 3)
                self.calibrated_left_pinch_exit = round(max(0.35, self.calibrated_left_pinch_enter * 1.35), 3)

                self.gestures_data["BIMANUAL_SELECT"] = {
                    "left_contact_ratio": round(median_left, 3),
                    "left_pinch_enter": self.calibrated_left_pinch_enter,
                    "left_pinch_exit": self.calibrated_left_pinch_exit
                }
                self.stage_idx += 1
                self._start_stage_prep()

        # ----------------------------------------------------
        # 12. RELAX: Natural Resting Hand Aperture
        # ----------------------------------------------------
        elif stage == "RELAX":
            p_relax = get_normalized_pinch_ratio(landmarks)
            self.samples.append(p_relax)
            if len(self.samples) >= self.samples_per_stage:
                median_relax = float(np.median(self.samples))
                if median_relax > self.calibrated_pinch_exit:
                    self.calibrated_pinch_exit = round(min(median_relax * 0.85, self.calibrated_pinch_exit + 0.05), 3)

                self.gestures_data["RELAX"] = {
                    "relaxed_pinch_ratio": round(median_relax, 3)
                }
                self.stage_idx += 1
                self.is_active = False
                self._save_profile()
                return True

        return False

    def _save_profile(self):
        """Persists learned parameters cumulatively and atomically to calibration.json."""
        calib_data = {
            "palm_scale": self.calibrated_palm_scale,
            "pinch_enter_ratio": self.calibrated_pinch_enter,
            "pinch_exit_ratio": self.calibrated_pinch_exit,
            "left_pinch_enter_ratio": self.calibrated_left_pinch_enter,
            "left_pinch_exit_ratio": self.calibrated_left_pinch_exit,
            "tremor_noise_px": self.calibrated_tremor_noise,
            "finger_extension_ratio": self.calibrated_finger_ext_ratio,
            "finger_straightness_cosine": self.calibrated_finger_straight_cos,
            "two_finger_separation_ratio": self.calibrated_two_finger_diff,
            "samples_per_stage": self.samples_per_stage,
            "calibrated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gestures": self.gestures_data
        }
        config.save_calibration(calib_data)
        print("[CALIBRATION] Successfully recorded full 12-gesture cumulative profile:", calib_data)
