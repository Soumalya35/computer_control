"""
Command Dispatcher Module
Translates StateMachine events and kinematic trajectories into InputBackend actions
and coordinates cursor filtering, scrolling, drag lifecycle, and hotkey invocation.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from system.win32_input import InputBackend
from system.hotkeys import HotkeyManager
from .cursor import CursorController
from .scrolling import ScrollController
from .drag import DragController
from gestures.state_machine import StateOutput, State


@dataclass
class DispatchTelemetry:
    """Telemetry data generated during event dispatch."""
    state_name: str
    action_name: str
    description: str
    cursor_screen_pos: Tuple[int, int]
    is_dragging: bool
    is_paused: bool
    scroll_direction: Optional[str]
    scroll_velocity: float


class CommandDispatcher:
    """Central action execution coordinator driving OS input backends."""

    def __init__(
        self,
        backend: InputBackend,
        cursor: CursorController,
        scroll: ScrollController,
        drag: DragController,
        hotkeys: HotkeyManager
    ):
        self.backend = backend
        self.cursor = cursor
        self.scroll = scroll
        self.drag = drag
        self.hotkeys = hotkeys

        self.last_screen_pos = (cursor.screen_width // 2, cursor.screen_height // 2)

    def dispatch(self, state_out: StateOutput) -> DispatchTelemetry:
        """
        Executes OS commands corresponding to state_out and returns execution telemetry.
        """
        event = state_out.event
        target_pos = state_out.target_pos or (0.5, 0.5)

        scroll_dir = None
        scroll_vel = 0.0

        # ----------------------------------------------------
        # 1. CURSOR MOVEMENT & DRAG POSITIONING
        # ----------------------------------------------------
        if event in ("MOVE", "DRAGGING", "DRAG_START"):
            sx, sy = self.cursor.update(target_pos[0], target_pos[1])
            self.backend.move_mouse(sx, sy)
            self.last_screen_pos = (sx, sy)

        # ----------------------------------------------------
        # 2. CLICK & DRAG STATE MACHINE HOOKS
        # ----------------------------------------------------
        if event == "CLICK":
            self.drag.click()
        elif event == "DRAG_START":
            self.drag.start_drag()
        elif event == "DRAG_END":
            self.drag.end_drag()

        # ----------------------------------------------------
        # 3. SCROLLING DISPATCH (CONTINUOUS + INERTIA)
        # ----------------------------------------------------
        if event == "SCROLL":
            notches, scroll_dir, scroll_vel = self.scroll.update(target_pos[1])
            if notches != 0:
                self.backend.wheel(notches)
        else:
            # Apply momentum inertia decay when not actively scrolling
            notches, scroll_dir, scroll_vel = self.scroll.decay()
            if notches != 0:
                self.backend.wheel(notches)

        # ----------------------------------------------------
        # 4. DISCRETE HOTKEY / MEDIA DISPATCH
        # ----------------------------------------------------
        if event == "HOTKEY":
            self.hotkeys.dispatch(state_out.action_name)

        # Reset controllers when appropriate
        if state_out.state in (State.LOST_HAND, State.PAUSED):
            self.drag.reset()
            self.scroll.reset()

        return DispatchTelemetry(
            state_name=state_out.state.name,
            action_name=state_out.action_name,
            description=state_out.description,
            cursor_screen_pos=self.last_screen_pos,
            is_dragging=self.drag.is_dragging,
            is_paused=state_out.is_paused,
            scroll_direction=scroll_dir,
            scroll_velocity=scroll_vel
        )
