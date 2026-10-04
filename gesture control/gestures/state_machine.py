"""
Gesture State Machine Module
Implements explicit finite state machine governing interactions:
IDLE, POINTING, SCROLLING, PINCH_PENDING, CLICK, DRAGGING, LOST_HAND, and PAUSED.
"""

import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple


class State(Enum):
    IDLE = auto()
    POINTING = auto()
    SCROLLING = auto()
    PINCH_PENDING = auto()
    CLICK = auto()
    DRAGGING = auto()
    LOST_HAND = auto()
    PAUSED = auto()


@dataclass
class StateOutput:
    state: State
    event: str                  # "NONE", "MOVE", "CLICK", "DRAG_START", "DRAGGING", "DRAG_END", "SCROLL", "HOTKEY"
    target_pos: Optional[Tuple[float, float]] = None
    action_name: str = "IDLE"
    description: str = ""
    is_paused: bool = False
    is_dragging: bool = False


class GestureStateMachine:
    """Manages predictable state transitions, click-on-release, drag lock-in, and hand-loss safety."""

    def __init__(self, drag_hold_frames: int = 7, drag_grace_frames: int = 3):
        self.drag_hold_frames = drag_hold_frames
        self.drag_grace_frames = drag_grace_frames

        self.current_state = State.IDLE
        self.pinch_frame_count = 0
        self.grace_count = 0
        self.pointing_grace_count = 0
        self.scroll_grace_count = 0
        self.pinch_start_pos = (0.5, 0.5)
        self.is_paused = False

    def is_in_pinch_state(self) -> bool:
        """Returns True if state machine is actively in PINCH_PENDING or DRAGGING."""
        return self.current_state in (State.PINCH_PENDING, State.DRAGGING)

    def transition(self, state: State):
        self.current_state = state

    def update(
        self,
        stabilized_gesture,
        features,
        hand_present: bool = True
    ) -> StateOutput:
        """
        Updates the state machine based on the current stabilized gesture and kinematic features.
        """
        # ----------------------------------------------------
        # 1. Hand Loss Safety Transition
        # ----------------------------------------------------
        if not hand_present:
            was_dragging = (self.current_state == State.DRAGGING)
            self.current_state = State.LOST_HAND
            self.pinch_frame_count = 0
            self.grace_count = 0

            event = "DRAG_END" if was_dragging else "NONE"
            output = StateOutput(
                state=State.LOST_HAND,
                event=event,
                action_name="LOST_HAND",
                description="Hand Lost: Safety Release",
                is_paused=self.is_paused,
                is_dragging=False
            )
            # Instantly recover to IDLE for next frame
            self.current_state = State.IDLE
            return output

        action = stabilized_gesture.action if stabilized_gesture else "NO_ACTION"
        gesture_name = stabilized_gesture.name if stabilized_gesture else "IDLE"

        # Determine pinch state: priority to stabilized_gesture, fallback to features
        if stabilized_gesture is not None:
            is_pinch = getattr(stabilized_gesture, "is_pinch", False)
        elif features is not None:
            active_hys = (not features.is_pinch_exit) if self.is_in_pinch_state() else features.is_pinch_enter
            is_pinch = bool(active_hys and features.fingers[3] == 0 and features.fingers[4] == 0)
        else:
            is_pinch = False

        index_pos = features.index_pos_norm if features else (0.5, 0.5)
        mid_pos = features.mid_pos_norm if features else index_pos

        # ----------------------------------------------------
        # 2. System PAUSE / RESUME State Control
        # ----------------------------------------------------
        if action == "PAUSE" or (self.is_paused and gesture_name == "CLOSED_FIST"):
            was_dragging = (self.current_state == State.DRAGGING)
            self.is_paused = True
            self.current_state = State.PAUSED
            return StateOutput(
                state=State.PAUSED,
                event="DRAG_END" if was_dragging else "NONE",
                action_name="PAUSED",
                description="System Paused (Fist). Show Open Palm to Resume",
                is_paused=True,
                is_dragging=False
            )

        if self.is_paused:
            if action == "RESUME":
                self.is_paused = False
                self.current_state = State.IDLE
                return StateOutput(
                    state=State.IDLE,
                    event="NONE",
                    action_name="RESUME",
                    description="System Resumed",
                    is_paused=False,
                    is_dragging=False
                )
            return StateOutput(
                state=State.PAUSED,
                event="NONE",
                action_name="PAUSED",
                description="System Paused (Fist). Show Open Palm to Resume",
                is_paused=True,
                is_dragging=False
            )

        # ----------------------------------------------------
        # 3. Active State Evaluations
        # ----------------------------------------------------

        # --- STATE: DRAGGING ---
        if self.current_state == State.DRAGGING:
            if is_pinch:
                self.grace_count = 0
                return StateOutput(
                    state=State.DRAGGING,
                    event="DRAGGING",
                    target_pos=mid_pos,
                    action_name="DRAGGING",
                    description="Holding Pinch: Dragging",
                    is_dragging=True
                )
            else:
                # Pinch temporarily lost: consult grace frames
                self.grace_count += 1
                if self.grace_count <= self.drag_grace_frames:
                    return StateOutput(
                        state=State.DRAGGING,
                        event="DRAGGING",
                        target_pos=mid_pos,
                        action_name="DRAGGING",
                        description=f"Dragging (Grace {self.grace_count})",
                        is_dragging=True
                    )
                else:
                    # Grace expired: release drag
                    self.current_state = State.IDLE
                    self.grace_count = 0
                    self.pinch_frame_count = 0
                    return StateOutput(
                        state=State.IDLE,
                        event="DRAG_END",
                        target_pos=mid_pos,
                        action_name="DROP",
                        description="Released Drag",
                        is_dragging=False
                    )

        # --- STATE: PINCH_PENDING ---
        if self.current_state == State.PINCH_PENDING:
            if is_pinch:
                self.pinch_frame_count += 1
                disp = math.hypot(index_pos[0] - self.pinch_start_pos[0], index_pos[1] - self.pinch_start_pos[1])
                # Transition to drag if held or displaced beyond micro-threshold (0.025)
                if self.pinch_frame_count >= self.drag_hold_frames or disp > 0.025:
                    self.current_state = State.DRAGGING
                    self.grace_count = 0
                    return StateOutput(
                        state=State.DRAGGING,
                        event="DRAG_START",
                        target_pos=mid_pos,
                        action_name="DRAGGING",
                        description="Drag Locked",
                        is_dragging=True
                    )
                # Dwell before drag: lock cursor to initial pinch start position to eliminate click drift!
                return StateOutput(
                    state=State.PINCH_PENDING,
                    event="MOVE",
                    target_pos=self.pinch_start_pos,
                    action_name="PINCH_PENDING",
                    description="Pinch Dwell...",
                    is_dragging=False
                )
            else:
                # Pinch released quickly before drag threshold -> CLICK at locked start position!
                self.current_state = State.IDLE
                self.pinch_frame_count = 0
                return StateOutput(
                    state=State.CLICK,
                    event="CLICK",
                    target_pos=self.pinch_start_pos,
                    action_name="LEFT_CLICK",
                    description="Pinch Tap: Left Click",
                    is_dragging=False
                )

        # --- STATE: IDLE, POINTING, SCROLLING ---
        if is_pinch:
            self.current_state = State.PINCH_PENDING
            self.pinch_frame_count = 1
            self.pinch_start_pos = index_pos
            return StateOutput(
                state=State.PINCH_PENDING,
                event="MOVE",
                target_pos=index_pos,
                action_name="PINCH_PENDING",
                description="Pinch Started",
                is_dragging=False
            )

        if action == "MOVE_MOUSE":
            self.current_state = State.POINTING
            self.pointing_grace_count = 0
            return StateOutput(
                state=State.POINTING,
                event="MOVE",
                target_pos=index_pos,
                action_name="MOVE_MOUSE",
                description="Pointing: Move Cursor",
                is_dragging=False
            )

        if self.current_state == State.POINTING and not is_pinch and action not in ("SCROLL_MODE", "PAUSE"):
            if self.pointing_grace_count < 2:
                self.pointing_grace_count += 1
                return StateOutput(
                    state=State.POINTING,
                    event="MOVE",
                    target_pos=index_pos,
                    action_name="MOVE_MOUSE",
                    description="Pointing (Grace)",
                    is_dragging=False
                )
            self.pointing_grace_count = 0

        if action == "SCROLL_MODE":
            self.current_state = State.SCROLLING
            self.scroll_grace_count = 0
            return StateOutput(
                state=State.SCROLLING,
                event="SCROLL",
                target_pos=index_pos,
                action_name="SCROLL_MODE",
                description="Two Fingers: Scroll Mode",
                is_dragging=False
            )

        if self.current_state == State.SCROLLING and not is_pinch and action != "PAUSE":
            if self.scroll_grace_count < 2:
                self.scroll_grace_count += 1
                return StateOutput(
                    state=State.SCROLLING,
                    event="SCROLL",
                    target_pos=index_pos,
                    action_name="SCROLL_MODE",
                    description="Scrolling (Grace)",
                    is_dragging=False
                )
            self.scroll_grace_count = 0

        # Discrete hotkeys (Alt+Tab, Task View, Volume, Tab switches)
        if stabilized_gesture and stabilized_gesture.mode == "DISCRETE" and action not in ("NO_ACTION", "UNKNOWN"):
            self.current_state = State.IDLE
            return StateOutput(
                state=State.IDLE,
                event="HOTKEY",
                action_name=action,
                description=stabilized_gesture.description,
                is_dragging=False
            )

        self.current_state = State.IDLE
        disp_name = gesture_name if gesture_name not in ("UNKNOWN", "NO_ACTION") else "IDLE"
        return StateOutput(
            state=State.IDLE,
            event="NONE",
            target_pos=index_pos,
            action_name=disp_name,
            description=stabilized_gesture.description if stabilized_gesture else "Waiting for gesture",
            is_dragging=False
        )
