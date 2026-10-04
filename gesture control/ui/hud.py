"""
Heads-Up Display (HUD) Module
Renders diagnostic overlays, independent Right & Left hand action telemetry,
mode selection buttons (Operation vs Calibration), bimanual interaction status,
confidence gauges, active interaction zones, animated click ripple effects,
and 12-stage calibration guidance with skip/redo hints.
"""

import time
import cv2
from typing import Optional, List, Tuple


class ClickRipple:
    """Animated click feedback ring expanding from click coordinates."""

    def __init__(self, x: int, y: int, click_type: str = "LEFT_CLICK"):
        self.x = int(x)
        self.y = int(y)
        self.click_type = click_type
        self.radius = 6.0
        self.max_radius = 42.0
        self.alpha = 1.0
        self.active = True

    def update(self):
        self.radius += 5.5
        self.alpha = max(0.0, 1.0 - (self.radius / self.max_radius))
        if self.radius >= self.max_radius:
            self.active = False

    def draw(self, frame):
        if not self.active:
            return
        h, w, _ = frame.shape
        if not (0 <= self.x < w and 0 <= self.y < h):
            return

        if self.click_type == "LEFT_CLICK":
            color = (0, 255, 120)       # Bright Green
        elif self.click_type == "RIGHT_CLICK":
            color = (255, 180, 0)       # Amber/Cyan
        else:
            color = (0, 220, 255)       # Yellow/Gold

        overlay = frame.copy()
        cv2.circle(overlay, (self.x, self.y), int(self.radius), color, 3)
        cv2.circle(overlay, (self.x, self.y), 4, color, cv2.FILLED)
        cv2.addWeighted(overlay, self.alpha, frame, 1.0 - self.alpha, 0, frame)


class HUDManager:
    """Manages real-time on-screen graphical telemetry, mode switching buttons, guidance, and ripples."""

    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        # Clickable button bounding boxes (x1, y1, x2, y2)
        self.btn_operation_rect = (16, 14, 150, 48)
        self.btn_calibration_rect = (158, 14, 305, 48)

        # Active click ripples
        self.ripples: List[ClickRipple] = []
        self.last_click_event = None
        self.last_click_time = 0.0

    def trigger_click_ripple(self, x: int, y: int, click_type: str = "LEFT_CLICK"):
        """Triggers visual click ripple at specified screen/frame coordinates."""
        self.ripples.append(ClickRipple(x, y, click_type))
        self.last_click_event = click_type
        self.last_click_time = time.time()

    def draw_interaction_box(
        self,
        frame,
        margin_x: int = 60,
        margin_y: int = 45,
        is_inside: bool = False
    ):
        """Renders the active cursor control zone with sleek corner brackets."""
        h, w, _ = frame.shape
        x1 = margin_x
        y1 = margin_y
        x2 = w - margin_x
        y2 = h - margin_y

        color = (0, 255, 0) if is_inside else (255, 200, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        # Corner accents
        c_len = 22
        c_th = 3
        # Top-left
        cv2.line(frame, (x1, y1), (x1 + c_len, y1), color, c_th)
        cv2.line(frame, (x1, y1), (x1, y1 + c_len), color, c_th)
        # Top-right
        cv2.line(frame, (x2, y1), (x2 - c_len, y1), color, c_th)
        cv2.line(frame, (x2, y1), (x2, y1 + c_len), color, c_th)
        # Bottom-left
        cv2.line(frame, (x1, y2), (x1 + c_len, y2), color, c_th)
        cv2.line(frame, (x1, y2), (x1, y2 - c_len), color, c_th)
        # Bottom-right
        cv2.line(frame, (x2, y2), (x2 - c_len, y2), color, c_th)
        cv2.line(frame, (x2, y2), (x2, y2 - c_len), color, c_th)

        cv2.putText(frame, "EXPANDED ACTIVE ZONE", (x1 + 8, y1 + 18), self.font, 0.42, color, 1)

    def draw_pinch_feedback(
        self,
        frame,
        thumb_norm: Tuple[float, float],
        index_norm: Tuple[float, float],
        is_pinch: bool,
        pinch_ratio: float,
        label: str = "Pinch"
    ):
        """Draws visual feedback line and midpoint circle between thumb and index tips."""
        h, w, _ = frame.shape
        pt1 = (int(thumb_norm[0] * w), int(thumb_norm[1] * h))
        pt2 = (int(index_norm[0] * w), int(index_norm[1] * h))

        line_color = (0, 255, 0) if is_pinch else (0, 215, 255)
        cv2.line(frame, pt1, pt2, line_color, 2)

        mid_x = (pt1[0] + pt2[0]) // 2
        mid_y = (pt1[1] + pt2[1]) // 2

        radius = 7 if is_pinch else 4
        cv2.circle(frame, (mid_x, mid_y), radius, line_color, cv2.FILLED)

        cv2.putText(
            frame,
            f"{label}: {pinch_ratio:.2f}",
            (mid_x + 8, mid_y),
            self.font,
            0.42,
            line_color,
            1
        )

    def draw_hud(
        self,
        frame,
        mode: str = "OPERATION",           # "OPERATION" vs "CALIBRATION"
        right_hand_action: str = "NONE",
        right_confidence: float = 0.0,
        left_hand_action: str = "NONE",
        left_confidence: float = 0.0,
        bimanual_status: str = "IDLE",
        is_paused: bool = False,
        is_dragging: bool = False,
        metrics: Optional[dict] = None,
        calibrating_text: Optional[str] = None,
        calib_progress: float = 0.0
    ):
        """
        Renders the comprehensive HUD:
        - Mode buttons: [O: OPERATION] and [C: CALIBRATION]
        - True independent Right Hand & Left Hand action monitors
        - Click event pill indicator
        - Real-time animated click ripples
        - Detailed calibration instructions with [N] Next and [B] Back navigation
        """
        h, w, _ = frame.shape
        now = time.time()

        # Update and draw active ripples
        for ripple in list(self.ripples):
            ripple.update()
            ripple.draw(frame)
        self.ripples = [r for r in self.ripples if r.active]

        # 1. TOP HEADER BAR
        bar_h = 82
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, bar_h), (16, 20, 26), cv2.FILLED)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.line(frame, (0, bar_h), (w, bar_h), (45, 55, 70), 1)

        # Mode Buttons in Window (Clickable & Keybound)
        # Button 1: [O: OPERATION]
        op_active = (mode == "OPERATION")
        op_bg = (0, 140, 60) if op_active else (35, 42, 52)
        op_border = (0, 255, 120) if op_active else (80, 90, 105)
        cv2.rectangle(frame, (self.btn_operation_rect[0], self.btn_operation_rect[1]),
                      (self.btn_operation_rect[2], self.btn_operation_rect[3]), op_bg, cv2.FILLED)
        cv2.rectangle(frame, (self.btn_operation_rect[0], self.btn_operation_rect[1]),
                      (self.btn_operation_rect[2], self.btn_operation_rect[3]), op_border, 1)
        cv2.putText(frame, "[O] OPERATION", (self.btn_operation_rect[0] + 10, 36), self.font, 0.48, (255, 255, 255), 1)

        # Button 2: [C: CALIBRATION]
        cal_active = (mode == "CALIBRATION")
        cal_bg = (180, 100, 0) if cal_active else (35, 42, 52)
        cal_border = (255, 160, 0) if cal_active else (80, 90, 105)
        cv2.rectangle(frame, (self.btn_calibration_rect[0], self.btn_calibration_rect[1]),
                      (self.btn_calibration_rect[2], self.btn_calibration_rect[3]), cal_bg, cv2.FILLED)
        cv2.rectangle(frame, (self.btn_calibration_rect[0], self.btn_calibration_rect[1]),
                      (self.btn_calibration_rect[2], self.btn_calibration_rect[3]), cal_border, 1)
        cv2.putText(frame, "[C] CALIBRATION", (self.btn_calibration_rect[0] + 8, 36), self.font, 0.48, (255, 255, 255), 1)

        # System Status Pill
        if is_paused:
            cv2.rectangle(frame, (16, 54), (110, 74), (0, 30, 180), cv2.FILLED)
            cv2.putText(frame, "PAUSED", (24, 69), self.font, 0.42, (255, 255, 255), 1)
        else:
            cv2.rectangle(frame, (16, 54), (110, 74), (0, 110, 50), cv2.FILLED)
            cv2.putText(frame, "RUNNING", (22, 69), self.font, 0.42, (255, 255, 255), 1)

        # Bimanual Status Pill / Click Burst
        if (now - self.last_click_time) < 0.45:
            # Flashing Click Indicator
            c_text = f"CLICK: {self.last_click_event}!"
            cv2.rectangle(frame, (116, 54), (305, 74), (0, 180, 80), cv2.FILLED)
            cv2.putText(frame, c_text, (122, 69), self.font, 0.42, (255, 255, 255), 1)
        else:
            bm_color = (0, 165, 255) if is_dragging else ((0, 200, 100) if "SELECT" in bimanual_status else (70, 80, 95))
            cv2.rectangle(frame, (116, 54), (305, 74), (25, 32, 42), cv2.FILLED)
            cv2.rectangle(frame, (116, 54), (305, 74), bm_color, 1)
            cv2.putText(frame, f"Bimanual: {bimanual_status}", (122, 69), self.font, 0.40, bm_color, 1)

        # 2. INDEPENDENT HAND PANELS
        panel_x = 320
        # Right Hand (Pointer / Spatial)
        r_col = (0, 255, 120) if right_hand_action not in ("NONE", "UNKNOWN") else (150, 160, 170)
        cv2.putText(frame, f"Right Hand: {right_hand_action}", (panel_x, 32), self.font, 0.60, r_col, 2)
        cv2.putText(frame, f"Conf: {right_confidence:.2f}", (panel_x + 280, 32), self.font, 0.45, (180, 190, 200), 1)

        # Left Hand (Selection / Hotkeys)
        l_col = (255, 200, 0) if left_hand_action not in ("NONE", "UNKNOWN") else (150, 160, 170)
        cv2.putText(frame, f"Left Hand:  {left_hand_action}", (panel_x, 62), self.font, 0.52, l_col, 2)
        cv2.putText(frame, f"Conf: {left_confidence:.2f}", (panel_x + 280, 62), self.font, 0.45, (180, 190, 200), 1)

        # 3. FPS & LATENCY TELEMETRY
        fps = metrics.get("fps", 0.0) if metrics else 0.0
        lat = metrics.get("total_ms", 0.0) if metrics else 0.0
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 130, 32), self.font, 0.55, (0, 255, 255), 2)
        cv2.putText(frame, f"Lat: {lat:.1f}ms", (w - 130, 62), self.font, 0.48, (200, 210, 220), 1)

        # 4. CALIBRATION BANNER & PROGRESS BAR
        if calibrating_text:
            banner_h = 58
            cv2.rectangle(frame, (0, bar_h + 1), (w, bar_h + 1 + banner_h), (12, 45, 90), cv2.FILLED)
            cv2.line(frame, (0, bar_h + 1 + banner_h), (w, bar_h + 1 + banner_h), (0, 140, 255), 2)
            cv2.putText(frame, f"[CALIBRATION MODE] {calibrating_text}", (18, bar_h + 26), self.font, 0.52, (255, 255, 255), 2)

            # Progress bar
            p_bar_w = w - 40
            p_bar_h = 8
            p_x = 20
            p_y = bar_h + 38
            cv2.rectangle(frame, (p_x, p_y), (p_x + p_bar_w, p_y + p_bar_h), (40, 60, 85), cv2.FILLED)
            fill_w = int(p_bar_w * max(0.0, min(1.0, calib_progress)))
            if fill_w > 0:
                cv2.rectangle(frame, (p_x, p_y), (p_x + fill_w, p_y + p_bar_h), (0, 220, 120), cv2.FILLED)
            cv2.rectangle(frame, (p_x, p_y), (p_x + p_bar_w, p_y + p_bar_h), (100, 140, 180), 1)

        # 5. BOTTOM GUIDANCE CHEAT-SHEET
        bot_h = 32
        bot_y = h - bot_h
        cv2.rectangle(frame, (0, bot_y), (w, h), (12, 16, 22), cv2.FILLED)
        cv2.line(frame, (0, bot_y), (w, bot_y), (45, 55, 70), 1)
        help_text = (
            "Modes: Click [O] or [C] | Space: Pause | Esc/Q: Exit | "
            "Bimanual: Right Hand Points | Left Pinch Tap: Left Click | Left Pinch Hold: Drag-Select | Left 2-Fin Tap: Right Click | "
            "Calib Nav: [N] Next/Skip | [B] Back"
        )
        cv2.putText(frame, help_text, (10, h - 10), self.font, 0.35, (210, 220, 230), 1)

    def handle_mouse_click(self, x: int, y: int) -> Optional[str]:
        """
        Checks if mouse click coordinates match on-screen mode buttons.
        Returns: "OPERATION", "CALIBRATION", or None
        """
        if (self.btn_operation_rect[0] <= x <= self.btn_operation_rect[2] and
                self.btn_operation_rect[1] <= y <= self.btn_operation_rect[3]):
            return "OPERATION"
        elif (self.btn_calibration_rect[0] <= x <= self.btn_calibration_rect[2] and
              self.btn_calibration_rect[1] <= y <= self.btn_calibration_rect[3]):
            return "CALIBRATION"
        return None
