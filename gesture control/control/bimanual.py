"""
Bimanual Control Module
Coordinates two-handed desktop interaction:
- Right Hand: Steers mouse pointer with silky smooth trajectory.
- Left Hand:  Performs high-reliability selection and clicking operations:
  * Left Pinch Tap (< 350ms): Instant Left Click (Selection) at pointer
  * Left Pinch Hold (>= 350ms or displacement > 15px): Engages Left Mouse Down (Drag-Select Text / Files)
  * Left Two-Finger Tap: Instant Right Click (Context Menu) at pointer
  * Left Double-Pinch: Instant Double Click
  * Visual ripple telemetry for real-time click feedback
"""

import time
import math
from dataclasses import dataclass
from typing import Optional, Tuple
from system.win32_input import InputBackend
from control.drag import DragController
from config.loader import config


@dataclass
class BimanualState:
    action_name: str                  # "IDLE", "PINCH_DWELL", "SELECT_CLICK", "RIGHT_CLICK", "DRAGGING", "RELEASE"
    is_selecting: bool                # True if left mouse button is currently held down
    pinch_active: bool                # True if left hand is pinching
    pinch_frames: int
    description: str
    click_event: Optional[str] = None # "LEFT_CLICK", "RIGHT_CLICK", "DOUBLE_CLICK", or None
    click_pos: Optional[Tuple[int, int]] = None


class BimanualController:
    """
    Coordinates bimanual mouse operation:
    Right Hand = Spatial Trajectory
    Left Hand  = Selection / Clicking / Drag-and-Drop
    """

    def __init__(
        self,
        backend: InputBackend,
        drag: DragController,
        drag_hold_frames: int = 15,    # ~350ms at 45 FPS (generous human reaction tap window)
        displacement_threshold: float = 0.035, # Normalized movement threshold to trigger intentional drag
        pinch_enter_ratio: Optional[float] = None,
        pinch_exit_ratio: Optional[float] = None
    ):
        self.backend = backend
        self.drag = drag
        self.drag_hold_frames = drag_hold_frames
        self.displacement_threshold = displacement_threshold
        self.pinch_enter_ratio = pinch_enter_ratio
        self.pinch_exit_ratio = pinch_exit_ratio

        # Pinch Tracking State
        self.is_pinching = False
        self.pinch_frames = 0
        self.is_dragging = False
        self.pinch_start_pos = (0.5, 0.5)

        # Right-Click (Two-Finger Tap) Tracking State
        self.is_two_finger_dwell = False
        self.two_finger_frames = 0

        # Double-Click History Tracking
        self.last_left_click_time = 0.0
        self.double_click_interval_sec = 0.38

    def update(
        self,
        left_features,
        left_track_present: bool = True,
        right_track_present: bool = True,
        current_cursor_pos: Optional[Tuple[int, int]] = None,
        current_norm_pos: Optional[Tuple[float, float]] = None
    ) -> BimanualState:
        """
        Evaluates left hand gestures to trigger selection, clicks, and drag operations
        at the current cursor position steered by the right hand.
        """
        now = time.time()
        norm_pos = current_norm_pos or (0.5, 0.5)
        cur_pos = current_cursor_pos or (960, 540)

        # Safety reset if Left Hand is lost or occluded
        if not left_track_present or left_features is None:
            if self.is_dragging:
                self.drag.end_drag()
                self.is_dragging = False
                self.is_pinching = False
                self.pinch_frames = 0
                return BimanualState(
                    action_name="RELEASE",
                    is_selecting=False,
                    pinch_active=False,
                    pinch_frames=0,
                    description="Bimanual: Hand Lost - Released Selection"
                )
            self.is_pinching = False
            self.pinch_frames = 0
            self.is_two_finger_dwell = False
            self.two_finger_frames = 0
            return BimanualState("IDLE", False, False, 0, "Bimanual: Inactive")

        # ----------------------------------------------------
        # 1. EVALUATE LEFT HAND PINCH (PRIMARY SELECTION)
        # ----------------------------------------------------
        enter_thresh = self.pinch_enter_ratio if self.pinch_enter_ratio is not None else config.pinch_enter_ratio
        exit_thresh = self.pinch_exit_ratio if self.pinch_exit_ratio is not None else config.pinch_exit_ratio
        r_pinch = left_features.pinch_ratio

        if self.is_pinching:
            # Hysteresis: stay pinching until exceeding pinch_exit
            left_pinch_active = (r_pinch <= exit_thresh) or (not getattr(left_features, "is_pinch_exit", False))
        else:
            # Enter pinch when below pinch_enter or feature flag is True
            left_pinch_active = (r_pinch <= enter_thresh) or getattr(left_features, "is_pinch_enter", False)

        if left_pinch_active:
            if not self.is_pinching:
                # First frame of pinch engagement
                self.is_pinching = True
                self.pinch_frames = 1
                self.pinch_start_pos = norm_pos
            else:
                self.pinch_frames += 1

            # Check intentional pointer displacement while pinched
            disp = math.hypot(norm_pos[0] - self.pinch_start_pos[0], norm_pos[1] - self.pinch_start_pos[1])

            # Transition to DRAGGING if held beyond tap window OR moved intentionally
            if self.pinch_frames >= self.drag_hold_frames or disp > self.displacement_threshold:
                if not self.is_dragging:
                    self.drag.start_drag()
                    self.is_dragging = True
                return BimanualState(
                    action_name="DRAGGING",
                    is_selecting=True,
                    pinch_active=True,
                    pinch_frames=self.pinch_frames,
                    description="Bimanual Drag-Select: Holding Selection (Move with Right Hand)"
                )
            else:
                # Pinch dwelling within tap-click window (< 350ms)
                return BimanualState(
                    action_name="PINCH_DWELL",
                    is_selecting=False,
                    pinch_active=True,
                    pinch_frames=self.pinch_frames,
                    description="Bimanual Pinch Dwell (Release to Click, Hold/Move to Drag)..."
                )
        else:
            # Pinch released this frame
            if self.is_pinching:
                was_dwelling = (self.pinch_frames < self.drag_hold_frames)
                was_dragging = self.is_dragging

                self.is_pinching = False
                self.pinch_frames = 0

                if was_dragging:
                    # Released after active drag hold -> clean drop
                    self.drag.end_drag()
                    self.is_dragging = False
                    return BimanualState(
                        action_name="RELEASE",
                        is_selecting=False,
                        pinch_active=False,
                        pinch_frames=0,
                        description="Bimanual Drag-Select: Released"
                    )
                elif was_dwelling:
                    # Quick pinch-and-release -> Execute Click!
                    # Check for double-click cadence
                    if (now - self.last_left_click_time) < self.double_click_interval_sec:
                        self.drag.double_click()
                        self.last_left_click_time = 0.0
                        return BimanualState(
                            action_name="SELECT_CLICK",
                            is_selecting=False,
                            pinch_active=False,
                            pinch_frames=0,
                            description="Bimanual Select: Double Click",
                            click_event="DOUBLE_CLICK",
                            click_pos=cur_pos
                        )
                    else:
                        self.drag.click()
                        self.last_left_click_time = now
                        return BimanualState(
                            action_name="SELECT_CLICK",
                            is_selecting=False,
                            pinch_active=False,
                            pinch_frames=0,
                            description="Bimanual Select: Left Click at Pointer",
                            click_event="LEFT_CLICK",
                            click_pos=cur_pos
                        )

        # ----------------------------------------------------
        # 2. EVALUATE LEFT HAND TWO-FINGER TAP (RIGHT CLICK)
        # ----------------------------------------------------
        # Two fingers extended (Index + Middle), Ring & Pinky folded
        is_two_fingers = (
            left_features.fingers[1] == 1 and
            left_features.fingers[2] == 1 and
            left_features.fingers[3] == 0 and
            left_features.fingers[4] == 0
        )

        if is_two_fingers and not self.is_pinching:
            if not self.is_two_finger_dwell:
                self.is_two_finger_dwell = True
                self.two_finger_frames = 1
            else:
                self.two_finger_frames += 1
        else:
            if self.is_two_finger_dwell:
                # Two fingers tapped and released within short tap window (< 10 frames, ~200ms)
                if self.two_finger_frames <= 10:
                    self.drag.right_click()
                    self.is_two_finger_dwell = False
                    self.two_finger_frames = 0
                    return BimanualState(
                        action_name="RIGHT_CLICK",
                        is_selecting=False,
                        pinch_active=False,
                        pinch_frames=0,
                        description="Bimanual Context Menu: Right Click at Pointer",
                        click_event="RIGHT_CLICK",
                        click_pos=cur_pos
                    )
                self.is_two_finger_dwell = False
                self.two_finger_frames = 0

        return BimanualState(
            action_name="IDLE",
            is_selecting=False,
            pinch_active=False,
            pinch_frames=0,
            description="Bimanual Ready (Left Pinch: Select | Left 2-Fin Tap: Right Click)"
        )

    def reset(self):
        """Emergency failsafe release."""
        if self.is_dragging:
            self.drag.end_drag()
        self.is_dragging = False
        self.is_pinching = False
        self.pinch_frames = 0
        self.is_two_finger_dwell = False
        self.two_finger_frames = 0
