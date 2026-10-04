"""
Landmarks Data Structure Module
Defines normalized and pixel landmark representations extracted from MediaPipe Hands.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LandmarkPoint:
    x: float
    y: float
    z: float = 0.0
    px: int = 0
    py: int = 0


class HandLandmarksSet:
    """Set of 21 hand landmarks supporting indexation and geometric calculations."""

    def __init__(self, raw_landmarks, frame_width: int = 1280, frame_height: int = 720):
        self.points: List[LandmarkPoint] = []
        for lm in raw_landmarks:
            px = int(lm.x * frame_width)
            py = int(lm.y * frame_height)
            z = getattr(lm, "z", 0.0)
            self.points.append(LandmarkPoint(x=lm.x, y=lm.y, z=z, px=px, py=py))

    def __getitem__(self, idx: int) -> LandmarkPoint:
        return self.points[idx]

    def __len__(self) -> int:
        return len(self.points)

    def get_palm_center_norm(self) -> Tuple[float, float]:
        """Calculates normalized center of palm between wrist (0) and middle MCP (9)."""
        w = self.points[0]
        m = self.points[9]
        return ((w.x + m.x) / 2.0, (w.y + m.y) / 2.0)

    def get_palm_center_px(self) -> Tuple[int, int]:
        """Calculates pixel center of palm."""
        w = self.points[0]
        m = self.points[9]
        return ((w.px + m.px) // 2, (w.py + m.py) // 2)
