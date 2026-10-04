"""
Scroll Control Module
Performs continuous vertical displacement accumulation and momentum inertia scrolling.
"""

from typing import Optional, Tuple


class ScrollController:
    """Manages vertical displacement accumulation and momentum wheel emissions."""

    def __init__(
        self,
        cam_height: int = 720,
        scroll_gain: float = 0.22,
        smooth_factor: float = 0.65,
        inertia_decay: float = 0.75,
        min_velocity: float = 0.60
    ):
        self.cam_height = cam_height
        self.scroll_gain = scroll_gain
        self.smooth_factor = smooth_factor
        self.inertia_decay = inertia_decay
        self.min_velocity = min_velocity

        self.prev_y = None
        self.smoothed_velocity = 0.0
        self.accumulator = 0.0
        self.last_direction = None

    def update(self, curr_norm_y: float) -> Tuple[int, Optional[str], float]:
        """
        Updates scroll state given current normalized vertical coordinate.
        Returns: (notches_to_emit: int, direction_str: Optional[str], current_velocity: float)
        """
        curr_px_y = curr_norm_y * float(self.cam_height)

        if self.prev_y is None:
            self.prev_y = curr_px_y
            return 0, None, 0.0

        # Hand movement UP in camera (curr < prev) -> positive delta -> Scroll UP
        raw_dy = float(self.prev_y - curr_px_y)
        self.prev_y = curr_px_y

        # Micro-deadzone: Suppress jitter when holding two fingers stationary
        if abs(raw_dy) < 1.5:
            raw_dy = 0.0

        # Exponential smoothing on velocity
        self.smoothed_velocity = (
            (1.0 - self.smooth_factor) * self.smoothed_velocity +
            self.smooth_factor * raw_dy
        )

        # Accumulate fractional velocity
        self.accumulator += self.smoothed_velocity * self.scroll_gain

        notches = 0
        if abs(self.accumulator) >= 1.0:
            notches = int(self.accumulator)
            self.accumulator -= notches

        if abs(self.smoothed_velocity) > 0.4:
            self.last_direction = "UP" if self.smoothed_velocity > 0 else "DOWN"
        else:
            self.last_direction = None

        return notches, self.last_direction, round(self.smoothed_velocity, 2)

    def decay(self) -> Tuple[int, Optional[str], float]:
        """Applies momentum inertia decay when active hand movement ceases."""
        if abs(self.smoothed_velocity) > self.min_velocity:
            self.smoothed_velocity *= self.inertia_decay
            self.accumulator += self.smoothed_velocity * self.scroll_gain

            notches = 0
            if abs(self.accumulator) >= 1.0:
                notches = int(self.accumulator)
                self.accumulator -= notches

            direction = "UP" if self.smoothed_velocity > 0 else "DOWN"
            return notches, direction, round(self.smoothed_velocity, 2)
        else:
            self.smoothed_velocity = 0.0
            self.accumulator = 0.0
            self.prev_y = None
            self.last_direction = None
            return 0, None, 0.0

    def reset(self):
        """Resets scroll state and accumulator."""
        self.prev_y = None
        self.smoothed_velocity = 0.0
        self.accumulator = 0.0
        self.last_direction = None
