"""
Gesture Registry Module
Defines the GestureDefinition schema and builds the authoritative registry of recognized gestures,
hand roles (PRIMARY vs SECONDARY), execution modes, and dispatch priorities.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class GestureDefinition:
    name: str
    role: str                       # "PRIMARY", "SECONDARY", "ANY"
    action: str                     # "MOVE_MOUSE", "LEFT_CLICK", "SCROLL_MODE", etc.
    category: str                   # "mouse", "scroll", "keyboard", "media", "system"
    mode: str                       # "CONTINUOUS", "DISCRETE", "STATE_MACHINE"
    cooldown: float                 # Seconds before this action can re-fire
    priority: int                   # Higher integer = higher priority
    fingers: Optional[Tuple[int, int, int, int, int]] = None
    pinch_required: bool = False
    description: str = ""


# Default gesture catalog matching implementation manual specifications
DEFAULT_GESTURES: List[GestureDefinition] = [
    # --- SAFETY / SYSTEM STATE (Priority 50) ---
    GestureDefinition(
        name="PAUSE",
        role="ANY",
        action="PAUSE",
        category="system",
        mode="DISCRETE",
        cooldown=0.80,
        priority=50,
        fingers=(0, 0, 0, 0, 0),
        description="Closed Fist: Pause System"
    ),
    GestureDefinition(
        name="RESUME",
        role="ANY",
        action="RESUME",
        category="system",
        mode="DISCRETE",
        cooldown=0.80,
        priority=50,
        fingers=(1, 1, 1, 1, 1),
        description="Open Palm: Resume System"
    ),

    # --- SECONDARY HAND BIMANUAL SELECTION (Priority 35) ---
    GestureDefinition(
        name="BIMANUAL_SELECT",
        role="SECONDARY",
        action="BIMANUAL_SELECT",
        category="mouse",
        mode="STATE_MACHINE",
        cooldown=0.30,
        priority=35,
        pinch_required=True,
        description="Left Hand Pinch: Select / Click / Drag at Cursor"
    ),

    # --- PRIMARY DISCRETE ACTIONS (Priority 30) ---
    GestureDefinition(
        name="ALT_TAB",
        role="PRIMARY",
        action="ALT_TAB",
        category="keyboard",
        mode="DISCRETE",
        cooldown=0.80,
        priority=30,
        fingers=(0, 1, 1, 1, 0),
        description="Three Fingers: Switch Window (Alt+Tab)"
    ),
    GestureDefinition(
        name="ALT_TAB_RELAXED",
        role="PRIMARY",
        action="ALT_TAB",
        category="keyboard",
        mode="DISCRETE",
        cooldown=0.80,
        priority=30,
        fingers=(1, 1, 1, 1, 0),
        description="Three Fingers (Relaxed Thumb): Switch Window (Alt+Tab)"
    ),
    GestureDefinition(
        name="TASK_VIEW",
        role="PRIMARY",
        action="TASK_VIEW",
        category="keyboard",
        mode="DISCRETE",
        cooldown=0.80,
        priority=30,
        fingers=(0, 1, 1, 1, 1),
        description="Four Fingers: Task View (Win+Tab)"
    ),
    GestureDefinition(
        name="VOLUME_UP",
        role="PRIMARY",
        action="VOLUME_UP",
        category="media",
        mode="DISCRETE",
        cooldown=0.20,
        priority=30,
        fingers=(1, 0, 0, 0, 0),
        description="Thumb Up: Volume Up"
    ),
    GestureDefinition(
        name="VOLUME_DOWN",
        role="PRIMARY",
        action="VOLUME_DOWN",
        category="media",
        mode="DISCRETE",
        cooldown=0.20,
        priority=30,
        fingers=(0, 0, 0, 0, 1),
        description="Pinky Only: Volume Down"
    ),
    GestureDefinition(
        name="PLAY_PAUSE",
        role="PRIMARY",
        action="PLAY_PAUSE",
        category="media",
        mode="DISCRETE",
        cooldown=0.60,
        priority=30,
        fingers=(1, 0, 0, 0, 1),
        description="Call/Shaka Sign: Play / Pause"
    ),

    # --- SECONDARY HAND ACTIONS (Priority 25) ---
    GestureDefinition(
        name="NEXT_TAB",
        role="SECONDARY",
        action="NEXT_TAB",
        category="keyboard",
        mode="DISCRETE",
        cooldown=0.60,
        priority=25,
        fingers=(0, 1, 1, 0, 0),
        description="Secondary Peace: Next Tab (Ctrl+Tab)"
    ),
    GestureDefinition(
        name="PREVIOUS_TAB",
        role="SECONDARY",
        action="PREVIOUS_TAB",
        category="keyboard",
        mode="DISCRETE",
        cooldown=0.60,
        priority=25,
        fingers=(0, 1, 1, 1, 0),
        description="Secondary Three Fingers: Prev Tab (Ctrl+Shift+Tab)"
    ),
    GestureDefinition(
        name="LEFT_OPEN_PALM",
        role="SECONDARY",
        action="NO_ACTION",
        category="system",
        mode="DISCRETE",
        cooldown=0.0,
        priority=12,
        fingers=(1, 1, 1, 1, 1),
        description="Left Hand: Open Palm"
    ),
    GestureDefinition(
        name="LEFT_POINTING",
        role="SECONDARY",
        action="NO_ACTION",
        category="mouse",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=12,
        fingers=(0, 1, 0, 0, 0),
        description="Left Hand: Pointing"
    ),
    GestureDefinition(
        name="LEFT_POINTING_RELAXED",
        role="SECONDARY",
        action="NO_ACTION",
        category="mouse",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=12,
        fingers=(1, 1, 0, 0, 0),
        description="Left Hand: Pointing"
    ),

    # --- PRIMARY PINCH & DRAG (Priority 20) ---
    GestureDefinition(
        name="PINCH",
        role="PRIMARY",
        action="LEFT_CLICK",
        category="mouse",
        mode="STATE_MACHINE",
        cooldown=0.35,
        priority=20,
        pinch_required=True,
        description="Thumb-Index Pinch: Left Click / Hold to Drag"
    ),

    # --- PRIMARY CONTINUOUS SCROLL (Priority 15) ---
    GestureDefinition(
        name="SCROLL_TIGHT",
        role="PRIMARY",
        action="SCROLL_MODE",
        category="scroll",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=15,
        fingers=(0, 1, 1, 0, 0),
        description="Two Fingers (Tight Thumb): Scroll Mode"
    ),
    GestureDefinition(
        name="SCROLL_RELAXED",
        role="PRIMARY",
        action="SCROLL_MODE",
        category="scroll",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=15,
        fingers=(1, 1, 1, 0, 0),
        description="Two Fingers (Relaxed Thumb): Scroll Mode"
    ),

    # --- PRIMARY CONTINUOUS MOTION (Priority 10) ---
    GestureDefinition(
        name="MOVE_MOUSE",
        role="PRIMARY",
        action="MOVE_MOUSE",
        category="mouse",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=10,
        fingers=(0, 1, 0, 0, 0),
        description="Index Pointing: Move Mouse Cursor"
    ),
    GestureDefinition(
        name="POINTING_RELAXED",
        role="PRIMARY",
        action="MOVE_MOUSE",
        category="mouse",
        mode="CONTINUOUS",
        cooldown=0.0,
        priority=10,
        fingers=(1, 1, 0, 0, 0),
        description="Index Pointing (Relaxed Thumb): Move Mouse Cursor"
    )
]


class GestureRegistry:
    """Registry managing queryable gesture definitions with priority sorting."""

    def __init__(self, gestures: Optional[List[GestureDefinition]] = None):
        self._gestures = gestures or list(DEFAULT_GESTURES)
        # Sort by priority descending (higher priority evaluated first)
        self._gestures.sort(key=lambda g: g.priority, reverse=True)

    def get_all(self) -> List[GestureDefinition]:
        return self._gestures

    def find_by_name(self, name: str) -> Optional[GestureDefinition]:
        for g in self._gestures:
            if g.name == name:
                return g
        return None
