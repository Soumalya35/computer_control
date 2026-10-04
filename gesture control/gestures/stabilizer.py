"""
Temporal Stabilizer Module
Enforces sliding-window temporal majority voting, confidence gating, and per-action cooldown timers.
"""

import time
from collections import deque, Counter
from typing import Optional

from .classifier import ClassifiedGesture


class TemporalStabilizer:
    """Stabilizes candidate classifications using sliding-window voting and per-action cooldowns."""

    def __init__(
        self,
        window_size: int = 5,
        min_votes: int = 3,
        confidence_threshold: float = 0.65,
        default_cooldown: float = 0.60
    ):
        self.window_size = window_size
        self.min_votes = min_votes
        self.confidence_threshold = confidence_threshold
        self.default_cooldown = default_cooldown

        self.history = deque(maxlen=self.window_size)
        self.last_execution = {}
        self.current_stable_action = None
        self.executed_for_current_hold = False
        self.is_paused = False

    def update(self, candidate: Optional[ClassifiedGesture]) -> Optional[ClassifiedGesture]:
        """
        Updates sliding-window voting history and returns stabilized gesture if criteria are met.
        Does not flush history on a single dropped frame, ensuring smooth and stable transitions.
        """
        if candidate is None:
            self.history.append("NO_ACTION")
            if Counter(self.history).get("NO_ACTION", 0) >= self.window_size:
                self.history.clear()
                self.current_stable_action = None
                self.executed_for_current_hold = False
            return None

        # 1. Confidence Gating
        if candidate.confidence < self.confidence_threshold:
            return None

        # 2. Add candidate action to sliding window
        self.history.append(candidate.action)

        # 3. Majority Voting
        counts = Counter(self.history)
        most_common_action, votes = counts.most_common(1)[0]

        if votes < self.min_votes:
            return None

        stabilized_action = most_common_action

        # Detect action transitions
        if stabilized_action != self.current_stable_action:
            self.current_stable_action = stabilized_action
            self.executed_for_current_hold = False

        now = time.time()
        cooldown = candidate.cooldown if candidate.cooldown > 0 else self.default_cooldown

        # 4. Global System PAUSE / RESUME Handling
        if stabilized_action == "PAUSE":
            if not self.executed_for_current_hold and (now - self.last_execution.get("PAUSE", 0) >= cooldown):
                self.is_paused = True
                self.last_execution["PAUSE"] = now
                self.executed_for_current_hold = True
                return candidate
            return None

        if stabilized_action == "RESUME":
            if not self.executed_for_current_hold and (now - self.last_execution.get("RESUME", 0) >= cooldown):
                self.is_paused = False
                self.last_execution["RESUME"] = now
                self.executed_for_current_hold = True
                return candidate
            return None

        if self.is_paused:
            return None

        # 5. Continuous / State Machine Actions
        if candidate.mode in ("CONTINUOUS", "STATE_MACHINE"):
            return candidate

        # 6. Discrete Actions (Single trigger per physical hold + cooldown)
        if not self.executed_for_current_hold:
            if now - self.last_execution.get(stabilized_action, 0) >= cooldown:
                self.last_execution[stabilized_action] = now
                self.executed_for_current_hold = True
                return candidate

        return None

    def get_voting_agreement(self) -> float:
        """Returns agreement ratio in current window [0.0 - 1.0]."""
        if not self.history:
            return 0.0
        counts = Counter(self.history)
        _, top_votes = counts.most_common(1)[0]
        return min(1.0, top_votes / float(self.min_votes))

    def reset(self):
        """Resets voting history and state."""
        self.history.clear()
        self.current_stable_action = None
        self.executed_for_current_hold = False
