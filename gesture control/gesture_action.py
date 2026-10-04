"""
Gesture Action Dispatcher Module
Coordinates primary & dual-hand gesture stabilization, relative & absolute cursor manipulation,
zero-tremor click/drag selection (single-hand and two-hand), tab switching, and fluid scrolling.
"""

import math
from gestre_stabilizer import GestureStabilizer
from mouse_control import MouseController
from keyboard_control import KeyboardController
from config import (
    PINCH_HOLD_DRAG_FRAMES, DRAG_RELEASE_GRACE_FRAMES,
    SCROLL_VELOCITY_GAIN, SCROLL_SMOOTH_FACTOR,
    SCROLL_INERTIA_DECAY, SCROLL_MIN_VELOCITY,
    TWO_HAND_MODE_ENABLED, TWO_HAND_AUX_CLICK_ENABLED,
    TAB_SWITCH_COOLDOWN
)


class GestureActionDispatcher:
    """Dispatches recognized gestures with dual-hand coordination, selection stability, and tab navigation."""

    def __init__(self):
        self.stabilizer = GestureStabilizer()
        self.secondary_stabilizer = GestureStabilizer(
            window_size=4,
            min_matches=2,
            default_cooldown=TAB_SWITCH_COOLDOWN,
            min_confidence=0.45
        )
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

        # Primary Hand Pinch / Drag State Machine
        self.pinch_counter = 0
        self.was_pinching = False
        self.drag_grace_counter = 0
        self.pinch_start_pos = None

        # Secondary Hand Aux Selection State Machine
        self.sec_pinch_counter = 0
        self.sec_was_pinching = False

        # Fluid Momentum Scrolling State Machine
        self.prev_scroll_y = None
        self.scroll_velocity = 0.0
        self.last_scroll_dir = None

    def dispatch(self, primary_data, hand_landmarks=None, secondary_data=None):
        """
        Processes primary and optional secondary gesture data, coordinates dual-hand interactions,
        handles text selection/dragging, and executes OS commands without unwanted cursor repositioning.
        """
        stable_primary = self.stabilizer.update(primary_data)
        stable_secondary = self.secondary_stabilizer.update(secondary_data) if secondary_data else None

        is_paused = self.stabilizer.is_paused

        raw_action = primary_data.get("action", "NO_ACTION") if primary_data else "NO_ACTION"
        confidence = primary_data.get("confidence", 0.0) if primary_data else 0.0
        is_pinch = primary_data.get("is_pinch", False) if primary_data else False
        index_pos = primary_data.get("index_pos", None) if primary_data else None

        action_to_show = stable_primary["action"] if stable_primary else raw_action
        desc_to_show = stable_primary["description"] if stable_primary else (primary_data.get("description", "") if primary_data else "")

        cursor_screen_pos = (self.mouse.curr_x, self.mouse.curr_y)

        # ----------------------------------------------------
        # System Paused State Check
        # ----------------------------------------------------
        if is_paused and (not stable_primary or stable_primary["action"] != "RESUME"):
            if self.mouse.is_dragging:
                self.mouse.end_drag()
            self.mouse.reset_tracking()
            self.prev_scroll_y = None
            self.scroll_velocity = 0.0
            return {
                "action": "PAUSE",
                "description": "System Paused (Fist). Show Open Palm to Resume",
                "is_paused": True,
                "is_dragging": False,
                "cursor_pos": cursor_screen_pos,
                "is_pinched": False,
                "confidence": confidence,
                "progress": self.stabilizer.get_stabilization_progress(),
                "scroll_dir": None,
                "scroll_vel": 0.0,
                "two_hand_active": False
            }

        # ----------------------------------------------------
        # 1. DUAL-HAND SECONDARY INTERACTIONS (SELECTION & TABS)
        # ----------------------------------------------------
        two_hand_active = False

        if TWO_HAND_MODE_ENABLED and secondary_data:
            two_hand_active = True
            sec_action = secondary_data.get("action", "NO_ACTION")
            sec_is_pinch = secondary_data.get("is_pinch", False) or (sec_action == "SEC_FIST_SELECT")

            # A. Secondary Hand Aux Selection & Dragging (Zero Cursor Wobble)
            if TWO_HAND_AUX_CLICK_ENABLED:
                if sec_is_pinch:
                    self.sec_pinch_counter += 1
                    self.sec_was_pinching = True

                    if not self.mouse.is_dragging:
                        self.mouse.start_drag()
                    action_to_show = "DRAG (2-Hand)"
                    desc_to_show = "Secondary Hand Holding Selection"

                elif self.sec_was_pinching:
                    if self.mouse.is_dragging:
                        self.mouse.end_drag()
                        action_to_show = "DROP (2-Hand)"
                        desc_to_show = "Selection Released"
                    else:
                        self.mouse.click()
                        action_to_show = "CLICK (2-Hand)"
                        desc_to_show = "Secondary Hand Clicked"

                    self.sec_pinch_counter = 0
                    self.sec_was_pinching = False

            # B. Secondary Hand Tab Switching
            if stable_secondary:
                s_act = stable_secondary["action"]
                if s_act == "NEXT_TAB":
                    self.keyboard.next_tab()
                    action_to_show = "NEXT TAB (2-Hand)"
                    desc_to_show = "Switched to Next Tab"
                elif s_act == "PREV_TAB":
                    self.keyboard.previous_tab()
                    action_to_show = "PREV TAB (2-Hand)"
                    desc_to_show = "Switched to Previous Tab"

        # ----------------------------------------------------
        # 2. PRIMARY HAND PINCH / DRAG SELECTION
        # ----------------------------------------------------
        # Consistently use index_pos to prevent coordinate jump when initiating pinch
        drag_anchor = index_pos

        if is_pinch and drag_anchor:
            self.drag_grace_counter = 0
            self.pinch_counter += 1
            self.was_pinching = True

            # Track initial position of pinch contact
            if self.pinch_counter == 1:
                self.pinch_start_pos = (self.mouse.curr_x, self.mouse.curr_y)

            # Move cursor with pinch stabilization enabled (prevents drift on click)
            cursor_screen_pos = self.mouse.move(drag_anchor[0], drag_anchor[1], is_pinch_mode=True)

            displacement = 0.0
            if self.pinch_start_pos:
                displacement = math.hypot(
                    cursor_screen_pos[0] - self.pinch_start_pos[0],
                    cursor_screen_pos[1] - self.pinch_start_pos[1]
                )

            # Instant drag-selection engagement
            if displacement > 8 or self.pinch_counter >= PINCH_HOLD_DRAG_FRAMES:
                if not self.mouse.is_dragging:
                    self.mouse.start_drag()
                action_to_show = "DRAGGING"
                desc_to_show = "Selecting Text / Dragging"
            else:
                action_to_show = "PINCH"
                desc_to_show = "Pinch (Tap to Click, Move to Select)"

        elif self.mouse.is_dragging and drag_anchor and self.drag_grace_counter < DRAG_RELEASE_GRACE_FRAMES:
            # Grace frames during drag prevents accidental drop on temporary landmark flutter
            self.drag_grace_counter += 1
            cursor_screen_pos = self.mouse.move(drag_anchor[0], drag_anchor[1], is_pinch_mode=True)
            action_to_show = "DRAGGING"
            desc_to_show = f"Holding Selection (grace {self.drag_grace_counter})"

        else:
            # Primary pinch released
            if self.was_pinching:
                if self.mouse.is_dragging:
                    self.mouse.end_drag()
                    action_to_show = "DROP"
                    desc_to_show = "Released Selection"
                else:
                    self.mouse.click()
                    action_to_show = "LEFT_CLICK"
                    desc_to_show = "Pinch Tap: Left Click"

                self.pinch_counter = 0
                self.was_pinching = False
                self.drag_grace_counter = 0
                self.pinch_start_pos = None

        # ----------------------------------------------------
        # 3. CONTINUOUS MOUSE MOVEMENT
        # ----------------------------------------------------
        active_action = stable_primary["action"] if stable_primary else raw_action

        if active_action == "MOVE_MOUSE" and not is_pinch and not self.mouse.is_dragging and index_pos:
            cursor_screen_pos = self.mouse.move(index_pos[0], index_pos[1], is_pinch_mode=False)
            self.prev_scroll_y = None
            self.scroll_velocity = 0.0
            self.last_scroll_dir = None

        # ----------------------------------------------------
        # 4. FLUID MOMENTUM SCROLLING ENGINE
        # ----------------------------------------------------
        elif active_action == "SCROLL_MODE" and index_pos:
            self.mouse.reset_tracking()
            curr_y = index_pos[1]

            if self.prev_scroll_y is not None:
                raw_dy = float(self.prev_scroll_y - curr_y)
                self.scroll_velocity = (self.scroll_velocity * (1.0 - SCROLL_SMOOTH_FACTOR)) + (raw_dy * SCROLL_SMOOTH_FACTOR)

                scaled_velocity = self.scroll_velocity * SCROLL_VELOCITY_GAIN
                self.mouse.scroll_continuous(scaled_velocity)

                if abs(self.scroll_velocity) > 0.4:
                    self.last_scroll_dir = "UP" if self.scroll_velocity > 0 else "DOWN"
                    action_to_show = f"SCROLL {self.last_scroll_dir}"
                    desc_to_show = f"Fluid Scrolling {self.last_scroll_dir}"

            self.prev_scroll_y = curr_y

        else:
            # Non-mouse gesture or hand inactive: reset relative camera delta history
            self.mouse.reset_tracking()

            # Inertia momentum decay
            if abs(self.scroll_velocity) > SCROLL_MIN_VELOCITY:
                self.scroll_velocity *= SCROLL_INERTIA_DECAY
                self.mouse.scroll_continuous(self.scroll_velocity * SCROLL_VELOCITY_GAIN)
            else:
                self.scroll_velocity = 0.0
                self.mouse.reset_scroll()
                self.prev_scroll_y = None
                self.last_scroll_dir = None

        # ----------------------------------------------------
        # 5. DISCRETE KEYBOARD & SYSTEM ACTIONS
        # ----------------------------------------------------
        if stable_primary:
            act = stable_primary["action"]

            if act == "ALT_TAB":
                self.keyboard.alt_tab()
            elif act == "TASK_VIEW":
                self.keyboard.task_view()
            elif act == "NEXT_TAB":
                self.keyboard.next_tab()
            elif act == "PREV_TAB":
                self.keyboard.previous_tab()
            elif act == "VOLUME_UP":
                self.keyboard.volume_up()
            elif act == "VOLUME_DOWN":
                self.keyboard.volume_down()
            elif act == "PLAY_PAUSE":
                self.keyboard.play_pause()
            elif act == "PAUSE":
                pass
            elif act == "RESUME":
                pass

        return {
            "action": action_to_show,
            "description": desc_to_show,
            "is_paused": is_paused,
            "is_dragging": self.mouse.is_dragging,
            "cursor_pos": cursor_screen_pos,
            "is_pinched": is_pinch,
            "confidence": confidence,
            "progress": self.stabilizer.get_stabilization_progress(),
            "scroll_dir": self.last_scroll_dir,
            "scroll_vel": round(self.scroll_velocity, 2),
            "two_hand_active": two_hand_active
        }
