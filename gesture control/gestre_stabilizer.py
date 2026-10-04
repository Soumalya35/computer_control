"""
Gesture Stabilizer Module
Prevents jitter and accidental triggers through sliding-window temporal majority voting,
enforces per-action cooldown intervals, evaluates confidence thresholds, and manages
system PAUSE/RESUME state.
"""

import time
from collections import deque, Counter
from config import (
    VOTING_WINDOW_SIZE, VOTING_MIN_MATCHES,
    ACTION_COOLDOWN, MIN_GESTURE_CONFIDENCE
)


class GestureStabilizer:
    """Stabilizes raw gesture classifications with temporal voting and confidence gating."""

    def __init__(
        self,
        window_size=VOTING_WINDOW_SIZE,
        min_matches=VOTING_MIN_MATCHES,
        default_cooldown=ACTION_COOLDOWN,
        min_confidence=MIN_GESTURE_CONFIDENCE
    ):
        self.window_size = window_size
        self.min_matches = min_matches
        self.default_cooldown = default_cooldown
        self.min_confidence = min_confidence

        # Sliding window buffer of recent detected actions
        self.history = deque(maxlen=self.window_size)
        self.confidence_history = deque(maxlen=self.window_size)

        self.current_stabilized_action = None
        self.last_execution = {}
        self.executed_for_current_hold = False
        self.is_paused = False

    def update(self, gesture_data):
        """
        Processes raw gesture frame data and returns the stabilized action payload
        only if it satisfies temporal voting and confidence criteria.
        """
        if not gesture_data:
            self.history.clear()
            self.confidence_history.clear()
            self.current_stabilized_action = None
            self.executed_for_current_hold = False
            return None

        raw_action = gesture_data.get("action", "NO_ACTION")
        confidence = gesture_data.get("confidence", 0.0)

        # ----------------------------------------------------
        # 1. Confidence Threshold Gating
        # ----------------------------------------------------
        # Reject low-confidence or ambiguous frames from corrupting voting history
        if confidence < self.min_confidence:
            return None

        self.history.append(raw_action)
        self.confidence_history.append(confidence)

        # ----------------------------------------------------
        # 2. Sliding Window Majority Voting
        # ----------------------------------------------------
        counts = Counter(self.history)
        most_common_action, count = counts.most_common(1)[0]

        # Require minimum consensus in window
        if count < self.min_matches:
            return None

        stabilized_action = most_common_action
        is_continuous = gesture_data.get("continuous", False)
        cooldown = gesture_data.get("cooldown", self.default_cooldown)

        # Handle gesture transition
        if stabilized_action != self.current_stabilized_action:
            self.current_stabilized_action = stabilized_action
            self.executed_for_current_hold = False

        now = time.time()

        # ----------------------------------------------------
        # 3. System Pause / Resume State Control
        # ----------------------------------------------------
        if stabilized_action == "PAUSE":
            if now - self.last_execution.get("PAUSE", 0) >= cooldown:
                self.is_paused = True
                self.last_execution["PAUSE"] = now
                self.executed_for_current_hold = True
                return gesture_data
            return None

        if stabilized_action == "RESUME":
            if now - self.last_execution.get("RESUME", 0) >= cooldown:
                self.is_paused = False
                self.last_execution["RESUME"] = now
                self.executed_for_current_hold = True
                return gesture_data
            return None

        # Discard all actions if system is currently paused
        if self.is_paused:
            return None

        # ----------------------------------------------------
        # 4. Continuous vs Discrete Dispatching
        # ----------------------------------------------------
        if is_continuous:
            # Continuous streams (e.g., MOVE_MOUSE, SCROLL_MODE)
            return gesture_data

        # Discrete actions (e.g. ALT_TAB, VOLUME_UP, NEXT_TAB)
        if not self.executed_for_current_hold:
            if now - self.last_execution.get(stabilized_action, 0) >= cooldown:
                self.last_execution[stabilized_action] = now
                self.executed_for_current_hold = True
                return gesture_data

        return None

    def get_stabilization_progress(self):
        """Returns the proportion of agreement in the sliding window [0.0 - 1.0]."""
        if not self.history:
            return 0.0
        counts = Counter(self.history)
        _, top_count = counts.most_common(1)[0]
        return min(1.0, top_count / float(self.min_matches))

    def get_smoothed_confidence(self):
        """Returns average confidence across recent valid frames."""
        if not self.confidence_history:
            return 0.0
        return sum(self.confidence_history) / len(self.confidence_history)

    def reset(self):
        """Resets the history buffer and state."""
        self.history.clear()
        self.confidence_history.clear()
        self.current_stabilized_action = None
        self.executed_for_current_hold = False