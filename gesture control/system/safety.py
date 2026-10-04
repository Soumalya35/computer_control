"""
Safety & Recovery Module
Monitors hand presence timeouts, handles ESC emergency stop, and releases held inputs upon application exit.
"""

import time
from typing import Optional
from .win32_input import InputBackend


class SafetyManager:
    """Guarantees failsafe execution, emergency stopping, and automatic release on hand-loss."""

    def __init__(self, backend: InputBackend, hand_loss_timeout_sec: float = 1.0):
        self.backend = backend
        self.hand_loss_timeout_sec = hand_loss_timeout_sec

        self.last_hand_seen_time = time.time()
        self.emergency_stop_triggered = False

    def notify_hand_seen(self):
        """Notifies safety manager that a valid hand is present in the current frame."""
        self.last_hand_seen_time = time.time()

    def check_hand_loss_timeout(self) -> bool:
        """
        Checks if hand has been missing longer than timeout duration.
        If so, automatically releases all buttons and keys.
        """
        if time.time() - self.last_hand_seen_time > self.hand_loss_timeout_sec:
            self.backend.release_all()
            return True
        return False

    def trigger_emergency_stop(self):
        """Immediately halts all actions, releases mouse buttons, and flags shutdown."""
        self.emergency_stop_triggered = True
        self.backend.release_all()
        print("[SAFETY] Emergency Stop Triggered! Released all virtual inputs.")

    def cleanup_on_exit(self):
        """Ensures all held mouse buttons and modifier keys are released when terminating."""
        self.backend.release_all()
        print("[SAFETY] Clean shutdown complete: all inputs released.")
