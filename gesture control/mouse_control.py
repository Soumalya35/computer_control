"""
Mouse Control Module
Provides relative (trackpad-style) and absolute cursor motion without unwanted repositioning/snapping,
velocity-adaptive Exponential Moving Average (EMA) cursor smoothing,
zero-jump pinch anchor stabilization for precise clicking and text selection,
and ultra-fast direct Windows cursor positioning via Win32 user32 SetCursorPos.
"""

import sys
import math
import ctypes
import numpy as np
import pyautogui

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    FRAME_WIDTH, FRAME_HEIGHT,
    INTERACTION_MARGIN_X, INTERACTION_MARGIN_Y,
    SMOOTH_FAST, SMOOTH_SLOW, SMOOTH_VEL_THRESH,
    SMOOTHENING, WHEEL_DELTA,
    CLICK_STABILIZE_FRAMES, CLICK_STABILIZE_RADIUS,
    CURSOR_MODE, MOUSE_SENSITIVITY_X, MOUSE_SENSITIVITY_Y,
    MOUSE_DEADZONE
)

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Win32 Mouse Event Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
IS_WINDOWS = sys.platform == "win32"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MouseController:
    """Controls OS cursor with relative/absolute modes, click stabilization, and zero-snap tracking."""

    def __init__(self, smoothening=SMOOTHENING, cursor_mode=CURSOR_MODE):
        self.screen_w = SCREEN_WIDTH
        self.screen_h = SCREEN_HEIGHT
        self.smoothening = smoothening
        self.cursor_mode = cursor_mode

        # Initialize to current actual OS cursor location (prevents initial snap to center)
        init_x, init_y = self.get_os_cursor_pos()
        self.prev_x = float(init_x)
        self.prev_y = float(init_y)
        self.curr_x = self.prev_x
        self.curr_y = self.prev_y

        # Camera coordinate tracking for Relative Mode
        self.prev_cam_x = None
        self.prev_cam_y = None

        self.is_dragging = False
        self.scroll_accumulator = 0.0

        # Pinch click & selection stabilization
        self.was_pinching_prev = False
        self.pinch_freeze_frames = 0
        self.pinch_anchor_x = self.curr_x
        self.pinch_anchor_y = self.curr_y

    def get_os_cursor_pos(self):
        """Returns the current true OS cursor position (x, y) from Windows user32."""
        if IS_WINDOWS:
            try:
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                return pt.x, pt.y
            except Exception:
                pass
        try:
            pos = pyautogui.position()
            return pos.x, pos.y
        except Exception:
            return self.screen_w // 2, self.screen_h // 2

    def map_coordinates(self, cam_x, cam_y):
        """
        Maps camera coordinates within expanded interaction margins to full screen coordinates.
        Used when cursor_mode is 'ABSOLUTE'.
        """
        x_min = INTERACTION_MARGIN_X
        x_max = FRAME_WIDTH - INTERACTION_MARGIN_X
        y_min = INTERACTION_MARGIN_Y
        y_max = FRAME_HEIGHT - INTERACTION_MARGIN_Y

        screen_x = np.interp(cam_x, (x_min, x_max), (0, self.screen_w))
        screen_y = np.interp(cam_y, (y_min, y_max), (0, self.screen_h))

        screen_x = max(0.0, min(float(self.screen_w - 1), float(screen_x)))
        screen_y = max(0.0, min(float(self.screen_h - 1), float(screen_y)))

        return screen_x, screen_y

    def reset_tracking(self):
        """Called when hand leaves the frame or stops pointing, resetting relative delta history."""
        self.prev_cam_x = None
        self.prev_cam_y = None

    def move(self, cam_x, cam_y, is_pinch_mode=False):
        """
        Moves cursor without unwanted repositioning/snapping:
        - RELATIVE MODE: Glides cursor from its CURRENT OS position by (dx, dy).
          Lifting or raising your hand never snaps the cursor across the screen.
        - ABSOLUTE MODE: Maps camera frame coordinates directly to screen resolution.
        - PINCH STABILIZATION: Locks cursor during initial pinch frames to eliminate click drift.
        """
        if self.cursor_mode == "RELATIVE":
            # ------------------------------------------------
            # RELATIVE TRACKPAD-STYLE MOTION (NO REPOSITIONING)
            # ------------------------------------------------
            if self.prev_cam_x is None or self.prev_cam_y is None:
                # First frame of active pointing: latch onto current OS position without moving
                cur_os_x, cur_os_y = self.get_os_cursor_pos()
                self.curr_x = float(cur_os_x)
                self.curr_y = float(cur_os_y)
                self.prev_x = self.curr_x
                self.prev_y = self.curr_y
                self.prev_cam_x = cam_x
                self.prev_cam_y = cam_y
                return int(round(self.curr_x)), int(round(self.curr_y))

            raw_dx = (cam_x - self.prev_cam_x) * MOUSE_SENSITIVITY_X
            raw_dy = (cam_y - self.prev_cam_y) * MOUSE_SENSITIVITY_Y
            self.prev_cam_x = cam_x
            self.prev_cam_y = cam_y

            # Micro-motion deadzone suppression
            if math.hypot(raw_dx, raw_dy) < MOUSE_DEADZONE:
                raw_dx = 0.0
                raw_dy = 0.0

            target_x = max(0.0, min(float(self.screen_w - 1), self.curr_x + raw_dx))
            target_y = max(0.0, min(float(self.screen_h - 1), self.curr_y + raw_dy))

        else:
            # ------------------------------------------------
            # ABSOLUTE FULLSCREEN MAPPING
            # ------------------------------------------------
            target_x, target_y = self.map_coordinates(cam_x, cam_y)

        # ----------------------------------------------------
        # Pinch Contact Stabilization (Eliminates Click Drift)
        # ----------------------------------------------------
        if is_pinch_mode and not self.was_pinching_prev:
            self.pinch_freeze_frames = CLICK_STABILIZE_FRAMES
            self.pinch_anchor_x = self.curr_x
            self.pinch_anchor_y = self.curr_y
            self.was_pinching_prev = True

        elif not is_pinch_mode:
            self.was_pinching_prev = False
            self.pinch_freeze_frames = 0

        # If in early pinch stabilization phase
        if is_pinch_mode and self.pinch_freeze_frames > 0:
            dist_from_anchor = math.hypot(target_x - self.pinch_anchor_x, target_y - self.pinch_anchor_y)
            if dist_from_anchor < CLICK_STABILIZE_RADIUS:
                # Hold cursor stationary on the intended target
                self.pinch_freeze_frames -= 1
                return int(round(self.curr_x)), int(round(self.curr_y))
            else:
                # User is deliberately dragging or selecting across the screen
                self.pinch_freeze_frames = 0

        # Calculate target displacement from current position
        dist = math.hypot(target_x - self.prev_x, target_y - self.prev_y)

        # Dynamic adaptive smoothing interpolation
        speed_ratio = min(1.0, dist / float(SMOOTH_VEL_THRESH))
        dynamic_smooth = SMOOTH_SLOW - (speed_ratio * (SMOOTH_SLOW - SMOOTH_FAST))
        dynamic_smooth = max(1.4, dynamic_smooth)

        # Adaptive EMA formula
        self.curr_x = self.prev_x + (target_x - self.prev_x) / dynamic_smooth
        self.curr_y = self.prev_y + (target_y - self.prev_y) / dynamic_smooth

        ix = int(round(self.curr_x))
        iy = int(round(self.curr_y))

        # Direct native Windows cursor placement (instantaneous, 0ms latency)
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.SetCursorPos(ix, iy)
            except Exception:
                try:
                    pyautogui.moveTo(ix, iy)
                except Exception:
                    pass
        else:
            try:
                pyautogui.moveTo(ix, iy)
            except Exception:
                pass

        self.prev_x = self.curr_x
        self.prev_y = self.curr_y

        return ix, iy

    def click(self):
        """Executes primary left mouse click."""
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                return
            except Exception:
                pass
        try:
            pyautogui.click()
        except Exception:
            pass

    def right_click(self):
        """Executes secondary right mouse click."""
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                return
            except Exception:
                pass
        try:
            pyautogui.rightClick()
        except Exception:
            pass

    def double_click(self):
        """Executes double left click."""
        self.click()
        self.click()

    def start_drag(self):
        """Presses and holds the left mouse button for text selection and dragging."""
        if not self.is_dragging:
            if IS_WINDOWS:
                try:
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    self.is_dragging = True
                    return
                except Exception:
                    pass
            try:
                pyautogui.mouseDown()
                self.is_dragging = True
            except Exception:
                pass

    def end_drag(self):
        """Releases the left mouse button after text selection or dragging."""
        if self.is_dragging:
            if IS_WINDOWS:
                try:
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.is_dragging = False
                    return
                except Exception:
                    pass
            try:
                pyautogui.mouseUp()
                self.is_dragging = False
            except Exception:
                pass

    def scroll_continuous(self, velocity_units):
        """
        Dispatches continuous fluid scrolling using a fractional accumulator.
        Avoids discrete stepped jumps by accumulating smooth fractional velocities.
        """
        self.scroll_accumulator += velocity_units

        # Check if enough velocity has accumulated for one or more wheel clicks
        if abs(self.scroll_accumulator) >= 1.0:
            notches = int(self.scroll_accumulator)
            self.scroll_accumulator -= notches

            if IS_WINDOWS:
                try:
                    delta_dw = int(notches * WHEEL_DELTA)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta_dw, 0)
                    return
                except Exception:
                    pass

            try:
                pyautogui.scroll(int(notches * 120))
            except Exception:
                pass

    def scroll(self, notches):
        """Backwards-compatible alias for discrete or continuous scrolling."""
        self.scroll_continuous(notches)

    def reset_scroll(self):
        """Resets the scroll accumulator."""
        self.scroll_accumulator = 0.0
