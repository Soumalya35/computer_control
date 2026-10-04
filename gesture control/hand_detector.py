"""
Hand Detector Module
Wraps MediaPipe Hands API with OpenCV to perform real-time dual-hand detection, 21-landmark extraction,
distance measurement, expanded interaction zone rendering, and an optimized Control Panel / HUD overlay.
"""

import cv2
import math
import numpy as np
from mediapipe.python.solutions import hands
from mediapipe.python.solutions import drawing_utils

from config import (
    CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT,
    MAX_HANDS, MODEL_COMPLEXITY,
    MIN_DETECTION_CONFIDENCE, MIN_TRACKING_CONFIDENCE,
    LANDMARK_RADIUS, LANDMARK_COLOR, LANDMARK_TEXT_COLOR,
    BOUNDING_BOX_COLOR, BOUNDING_BOX_SECONDARY_COLOR,
    BOUNDING_BOX_THICKNESS, BOUNDING_BOX_PADDING,
    INTERACTION_MARGIN_X, INTERACTION_MARGIN_Y,
    BOX_COLOR, BOX_ACTIVE_COLOR, BOX_THICKNESS,
    SHOW_BOUNDING_BOX, SHOW_HAND_LABEL, SHOW_FPS,
    SHOW_ACTION_TEXT, SHOW_DESCRIPTION_TEXT,
    SHOW_LANDMARK_NUMBERS, SHOW_INTERACTION_BOX, SHOW_PINCH_LINE,
    SHOW_CONTROL_PANEL, SHOW_CONFIDENCE_METER
)


class HandDetector:
    """Detects up to 2 hands, extracts landmarks, and renders an interactive HUD control panel."""

    def __init__(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        self.mp_hands = hands
        self.mp_draw = drawing_utils

        self.hand_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MAX_HANDS,
            model_complexity=MODEL_COMPLEXITY,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE
        )

    def get_frame(self):
        """Captures a webcam frame, mirrors horizontally, and extracts MediaPipe hands."""
        success, frame = self.cap.read()
        if not success or frame is None:
            return False, None, None

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hand_detector.process(rgb)

        return success, frame, results

    def get_landmark_pixels(self, frame, hand_landmarks):
        """Converts normalized landmarks into integer pixel coordinates (cx, cy)."""
        h, w, _ = frame.shape
        lm_pixels = {}
        for idx, lm in enumerate(hand_landmarks.landmark):
            cx = int(lm.x * w)
            cy = int(lm.y * h)
            lm_pixels[idx] = (cx, cy)
        return lm_pixels

    @staticmethod
    def find_distance(p1, p2):
        """Calculates Euclidean distance and midpoint between two (x, y) pixel coordinates."""
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2
        return dist, (mid_x, mid_y)

    def draw_hand(self, frame, hand_landmarks):
        """Renders hand skeleton landmarks and connection lines."""
        self.mp_draw.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS
        )

        h, w, _ = frame.shape
        for idx, lm in enumerate(hand_landmarks.landmark):
            cx = int(lm.x * w)
            cy = int(lm.y * h)

            cv2.circle(frame, (cx, cy), LANDMARK_RADIUS, LANDMARK_COLOR, cv2.FILLED)

            if SHOW_LANDMARK_NUMBERS:
                cv2.putText(
                    frame,
                    str(idx),
                    (cx, cy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    LANDMARK_TEXT_COLOR,
                    1
                )

    def draw_interaction_box(self, frame, hand_inside=False):
        """Draws the expanded active interaction zone with corner accents."""
        if not SHOW_INTERACTION_BOX:
            return

        h, w, _ = frame.shape
        x1 = INTERACTION_MARGIN_X
        y1 = INTERACTION_MARGIN_Y
        x2 = w - INTERACTION_MARGIN_X
        y2 = h - INTERACTION_MARGIN_Y

        box_clr = BOX_ACTIVE_COLOR if hand_inside else BOX_COLOR

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_clr, BOX_THICKNESS)

        # Corner accents for a sleek HUD look
        c_len = 24
        c_th = 4
        # Top-left
        cv2.line(frame, (x1, y1), (x1 + c_len, y1), box_clr, c_th)
        cv2.line(frame, (x1, y1), (x1, y1 + c_len), box_clr, c_th)
        # Top-right
        cv2.line(frame, (x2, y1), (x2 - c_len, y1), box_clr, c_th)
        cv2.line(frame, (x2, y1), (x2, y1 + c_len), box_clr, c_th)
        # Bottom-left
        cv2.line(frame, (x1, y2), (x1 + c_len, y2), box_clr, c_th)
        cv2.line(frame, (x1, y2), (x1, y2 - c_len), box_clr, c_th)
        # Bottom-right
        cv2.line(frame, (x2, y2), (x2 - c_len, y2), box_clr, c_th)
        cv2.line(frame, (x2, y2), (x2, y2 - c_len), box_clr, c_th)

        cv2.putText(
            frame,
            "WIDE ACTIVE ZONE (>90% AREA)",
            (x1 + 10, y1 + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            box_clr,
            1
        )

    def draw_pinch_indicator(self, frame, thumb_pt, index_pt, is_pinched, pinch_dist):
        """Renders visual feedback line and midpoint circle between thumb and index tips."""
        if not SHOW_PINCH_LINE:
            return

        line_color = (0, 255, 0) if is_pinched else (0, 215, 255)
        cv2.line(frame, thumb_pt, index_pt, line_color, 2)

        mid_x = (thumb_pt[0] + index_pt[0]) // 2
        mid_y = (thumb_pt[1] + index_pt[1]) // 2

        radius = 8 if is_pinched else 5
        cv2.circle(frame, (mid_x, mid_y), radius, line_color, cv2.FILLED)

        tag = f"PINCH: {int(pinch_dist)}px" if is_pinched else f"{int(pinch_dist)}px"
        cv2.putText(
            frame,
            tag,
            (mid_x + 12, mid_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            line_color,
            1
        )

    def draw_bounding_box(self, frame, hand_landmarks, hand_label="Hand", is_secondary=False):
        """Draws bounding box around hand with primary/secondary distinction."""
        if not SHOW_BOUNDING_BOX:
            return

        h, w, _ = frame.shape
        x_list = [int(lm.x * w) for lm in hand_landmarks.landmark]
        y_list = [int(lm.y * h) for lm in hand_landmarks.landmark]

        xmin = max(0, min(x_list) - BOUNDING_BOX_PADDING)
        ymin = max(0, min(y_list) - BOUNDING_BOX_PADDING)
        xmax = min(w, max(x_list) + BOUNDING_BOX_PADDING)
        ymax = min(h, max(y_list) + BOUNDING_BOX_PADDING)

        box_color = BOUNDING_BOX_SECONDARY_COLOR if is_secondary else BOUNDING_BOX_COLOR
        tag = f"{hand_label} (Shortcuts/Select)" if is_secondary else f"{hand_label} (Mouse)"

        cv2.rectangle(
            frame,
            (xmin, ymin),
            (xmax, ymax),
            box_color,
            BOUNDING_BOX_THICKNESS
        )

        if SHOW_HAND_LABEL:
            cv2.putText(
                frame,
                tag,
                (xmin, max(20, ymin - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                box_color,
                2
            )

    def draw_hud(
        self,
        frame,
        action_name,
        description,
        is_paused=False,
        confidence=0.0,
        fps=0.0,
        scroll_dir=None,
        is_dragging=False,
        scroll_vel=0.0,
        two_hand_active=False
    ):
        """
        Renders an optimized, high-tech Control Panel dashboard banner:
        1. Top Bar: Status Pill, Action Badge, Confidence Gauge, FPS, 2-Hand Indicator.
        2. Scroll / Drag feedback indicators with fluid velocity meters.
        3. Bottom Bar: Complete Gesture Quick-Reference Cheat Sheet.
        """
        if not SHOW_CONTROL_PANEL:
            return

        h, w, _ = frame.shape

        # ----------------------------------------------------
        # 1. TOP CONTROL PANEL HEADER BAR
        # ----------------------------------------------------
        top_bar_h = 68
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, top_bar_h), (18, 22, 28), cv2.FILLED)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
        cv2.line(frame, (0, top_bar_h), (w, top_bar_h), (45, 55, 72), 1)

        # Status Pill [● ACTIVE] or [■ PAUSED]
        pill_x = 20
        pill_y = 16
        pill_w = 115
        pill_h = 36
        status_bg = (0, 140, 60) if not is_paused else (0, 30, 180)
        status_txt = "ACTIVE" if not is_paused else "PAUSED"
        cv2.rectangle(frame, (pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h), status_bg, cv2.FILLED)
        cv2.rectangle(frame, (pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h), (255, 255, 255), 1)
        cv2.putText(
            frame,
            status_txt,
            (pill_x + 18, pill_y + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            2
        )

        # 2-Hand Badge if both hands are active
        action_x = 150
        if two_hand_active:
            th_w = 120
            cv2.rectangle(frame, (145, pill_y), (145 + th_w, pill_y + pill_h), (180, 100, 20), cv2.FILLED)
            cv2.rectangle(frame, (145, pill_y), (145 + th_w, pill_y + pill_h), (255, 200, 100), 1)
            cv2.putText(
                frame,
                "2-HANDS",
                (155, pill_y + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )
            action_x = 280

        # Action Display Badge
        action_color = (0, 255, 120) if not is_paused else (100, 100, 255)
        if is_dragging or "DRAG" in action_name:
            action_color = (0, 165, 255)  # Orange for drag
        elif "SCROLL" in action_name:
            action_color = (255, 215, 0)  # Cyan for scroll
        elif "TAB" in action_name:
            action_color = (255, 105, 180) # Magenta for tabs

        cv2.putText(
            frame,
            f"ACTION: {action_name}",
            (action_x, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.70,
            action_color,
            2
        )
        if description:
            cv2.putText(
                frame,
                description,
                (action_x, 56),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 210, 220),
                1
            )

        # Real-time Stabilized Confidence Gauge
        if SHOW_CONFIDENCE_METER:
            conf_pct = int(round(confidence * 100))
            gauge_x = w - 340
            gauge_y = 22
            gauge_w = 110
            gauge_h = 16

            if conf_pct >= 70:
                bar_color = (0, 230, 80)
            elif conf_pct >= 50:
                bar_color = (0, 200, 255)
            else:
                bar_color = (50, 50, 255)

            cv2.putText(
                frame,
                f"CONF: {conf_pct}%",
                (gauge_x, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                bar_color,
                2
            )

            bar_start_x = gauge_x + 105
            cv2.rectangle(frame, (bar_start_x, gauge_y), (bar_start_x + gauge_w, gauge_y + gauge_h), (50, 60, 75), cv2.FILLED)
            fill_w = int(gauge_w * max(0.0, min(1.0, confidence)))
            if fill_w > 0:
                cv2.rectangle(frame, (bar_start_x, gauge_y), (bar_start_x + fill_w, gauge_y + gauge_h), bar_color, cv2.FILLED)
            cv2.rectangle(frame, (bar_start_x, gauge_y), (bar_start_x + gauge_w, gauge_y + gauge_h), (120, 130, 150), 1)

        # FPS Badge
        if SHOW_FPS:
            cv2.putText(
                frame,
                f"FPS: {int(fps)}",
                (w - 95, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (0, 255, 255),
                2
            )

        # ----------------------------------------------------
        # 2. ACTIVE SCROLL / DRAG ONSCREEN CALLOUTS
        # ----------------------------------------------------
        if is_dragging:
            drag_callout_y = 110
            cv2.putText(
                frame,
                "[ SELECTION DRAG ACTIVE ]",
                (w // 2 - 160, drag_callout_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 165, 255),
                2
            )
        elif scroll_dir:
            scroll_callout_y = 110
            arrow = "^" if scroll_dir == "UP" else "v"
            scroll_txt = f"{arrow} FLUID SCROLLING {scroll_dir} ({abs(scroll_vel):.1f} px/f) {arrow}"
            cv2.putText(
                frame,
                scroll_txt,
                (w // 2 - 200, scroll_callout_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 220, 0),
                2
            )

        # ----------------------------------------------------
        # 3. BOTTOM CONTROL PANEL QUICK REFERENCE CHEAT-SHEET
        # ----------------------------------------------------
        bot_bar_h = 32
        bot_y1 = h - bot_bar_h
        bot_overlay = frame.copy()
        cv2.rectangle(bot_overlay, (0, bot_y1), (w, h), (12, 16, 20), cv2.FILLED)
        cv2.addWeighted(bot_overlay, 0.85, frame, 0.15, 0, frame)
        cv2.line(frame, (0, bot_y1), (w, bot_y1), (45, 55, 72), 1)

        help_text = (
            "Point: Move | Pinch: Click/Drag | 2-Hand: Offhand Pinch/Fist=Select, Offhand Peace=NextTab, Offhand 3Fin=PrevTab | "
            "Rock: NextTab | Rock+Thumb: PrevTab"
        )
        cv2.putText(
            frame,
            help_text,
            (15, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (210, 220, 230),
            1
        )

    def release(self):
        """Releases camera resource and closes OpenCV windows."""
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()