"""
Cursor Control Module
Maps normalized camera interaction box coordinates to OS display resolution and applies
continuous adaptive filtering (velocity-adaptive EMA with continuous non-linear tremor suppression)
to provide a silky smooth, jitter-free, and responsive mouse experience.
"""

import math
import numpy as np
from typing import Tuple


class CursorController:
    """
    Controls cursor coordinates with invariant anchor tracking and continuous adaptive smoothing.
    Combines velocity-dependent cutoff with smooth sub-pixel tremor attenuation:
    - Low speed / resting: high smoothing, continuous damping eliminates physiological tremor with zero stair-stepping.
    - High speed: instant responsiveness, tracking ballistic hand movements with near-zero latency.
    """

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin_x: int = 60,
        margin_y: int = 45,
        cam_width: int = 1280,
        cam_height: int = 720,
        alpha_slow: float = 0.15,
        alpha_fast: float = 0.72,
        v_slow: float = 3.0,
        v_fast: float = 24.0
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.norm_x_min = margin_x / float(cam_width)
        self.norm_x_max = 1.0 - (margin_x / float(cam_width))
        self.norm_y_min = margin_y / float(cam_height)
        self.norm_y_max = 1.0 - (margin_y / float(cam_height))

        self.alpha_slow = alpha_slow
        self.alpha_fast = alpha_fast
        self.v_slow = v_slow
        self.v_fast = v_fast

        # Filter internal state (high precision float)
        self.filtered_x = float(screen_width // 2)
        self.filtered_y = float(screen_height // 2)
        self.prev_target_x = self.filtered_x
        self.prev_target_y = self.filtered_y
        self.current_velocity = 0.0
        self.is_first_point = True

    def map_to_screen(self, norm_x: float, norm_y: float) -> Tuple[float, float]:
        """Linearly interpolates normalized coordinates within interaction margin to display bounds."""
        target_x = np.interp(norm_x, (self.norm_x_min, self.norm_x_max), (0.0, float(self.screen_width)))
        target_y = np.interp(norm_y, (self.norm_y_min, self.norm_y_max), (0.0, float(self.screen_height)))

        target_x = max(0.0, min(float(self.screen_width - 1), float(target_x)))
        target_y = max(0.0, min(float(self.screen_height - 1), float(target_y)))
        return float(target_x), float(target_y)

    def update(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        Calculates screen target and applies continuous adaptive filtering.
        Returns integer screen coordinates (x, y).
        """
        target_x, target_y = self.map_to_screen(norm_x, norm_y)

        # Initial point lock: directly align to hand position on entry
        if self.is_first_point:
            self.filtered_x = target_x
            self.filtered_y = target_y
            self.prev_target_x = target_x
            self.prev_target_y = target_y
            self.is_first_point = False
            return int(round(self.filtered_x)), int(round(self.filtered_y))

        # Target displacement in screen pixels this frame
        delta_x = target_x - self.prev_target_x
        delta_y = target_y - self.prev_target_y
        step_dist = math.hypot(delta_x, delta_y)

        # Filtered tracking distance
        dist_to_filtered = math.hypot(target_x - self.filtered_x, target_y - self.filtered_y)

        # Estimate instantaneous velocity with smooth blending
        self.current_velocity = 0.70 * self.current_velocity + 0.30 * step_dist

        # Continuous smooth non-linear damping:
        # Instead of a binary deadzone cutoff (which causes stair-stepping and stickiness),
        # apply a continuous power gain that gently suppresses sub-pixel physiological tremor (< 3px)
        # while smoothly transitioning to full speed as velocity increases.
        tremor_scale = 3.2
        if dist_to_filtered < tremor_scale:
            # Smooth Hermite-like / quadratic damping factor in [0.10, 1.0]
            gain = (dist_to_filtered / tremor_scale) ** 1.6
            damped_target_x = self.filtered_x + (target_x - self.filtered_x) * max(0.12, gain)
            damped_target_y = self.filtered_y + (target_y - self.filtered_y) * max(0.12, gain)
        else:
            damped_target_x = target_x
            damped_target_y = target_y

        # Velocity-adaptive interpolation weight alpha
        alpha = float(np.interp(
            self.current_velocity,
            [self.v_slow, self.v_fast],
            [self.alpha_slow, self.alpha_fast]
        ))

        # Continuous Exponential Moving Average
        self.filtered_x = (1.0 - alpha) * self.filtered_x + alpha * damped_target_x
        self.filtered_y = (1.0 - alpha) * self.filtered_y + alpha * damped_target_y

        self.prev_target_x = target_x
        self.prev_target_y = target_y

        # Clamp to display bounds
        final_x = max(0, min(self.screen_width - 1, int(round(self.filtered_x))))
        final_y = max(0, min(self.screen_height - 1, int(round(self.filtered_y))))

        return final_x, final_y

    def reset(self, center: bool = False):
        """Resets the cursor filter."""
        self.is_first_point = True
        if center:
            self.filtered_x = float(self.screen_width // 2)
            self.filtered_y = float(self.screen_height // 2)
            self.prev_target_x = self.filtered_x
            self.prev_target_y = self.filtered_y
        self.current_velocity = 0.0
