"""
Gesture Classifier Module
Classifies kinematic features against registered gestures using hand-role context,
priority evaluation, and conflict resolution.
"""

from dataclasses import dataclass
from typing import Optional

from .registry import GestureRegistry, GestureDefinition, DEFAULT_GESTURES
from kinematics.features import KinematicFeatures


@dataclass
class ClassifiedGesture:
    """Represents a classified gesture candidate with confidence and action metadata."""
    name: str
    action: str
    role: str
    category: str
    mode: str
    cooldown: float
    confidence: float
    description: str
    is_pinch: bool
    features: KinematicFeatures


UNKNOWN_GESTURE = ClassifiedGesture(
    name="UNKNOWN",
    action="NO_ACTION",
    role="NONE",
    category="none",
    mode="DISCRETE",
    cooldown=0.0,
    confidence=0.0,
    description="Unknown Gesture",
    is_pinch=False,
    features=None
)


class GestureClassifier:
    """Classifies hand pose into discrete or continuous actions using role and priority rules."""

    def __init__(self, registry: Optional[GestureRegistry] = None):
        self.registry = registry or GestureRegistry()

    def classify(
        self,
        features: KinematicFeatures,
        hand_role: str = "PRIMARY",
        confidence: float = 1.0,
        is_currently_pinching: bool = False
    ) -> ClassifiedGesture:
        """
        Evaluates features and returns the highest-priority, highest-confidence matching gesture.
        """
        matches = []

        # Check pinch condition with hysteresis
        pinch_active = (
            (features.is_pinch_exit is False if is_currently_pinching else features.is_pinch_enter)
            and features.fingers[3] == 0   # Ring folded
            and features.fingers[4] == 0   # Pinky folded
        )

        for g in self.registry.get_all():
            # Filter by hand role: PRIMARY vs SECONDARY
            if g.role != "ANY" and g.role != hand_role:
                continue

            # 1. Match pinch-based gestures
            if g.pinch_required:
                if pinch_active:
                    matches.append(g)
                continue

            # 2. Match finger tuple gestures
            if g.fingers is not None:
                # Do not trigger standard finger gestures if pinch is actively engaged
                if pinch_active and g.action != "SCROLL_MODE":
                    continue
                if g.fingers == features.fingers:
                    matches.append(g)

        if not matches:
            unknown = ClassifiedGesture(
                name="UNKNOWN",
                action="NO_ACTION",
                role=hand_role,
                category="none",
                mode="DISCRETE",
                cooldown=0.0,
                confidence=confidence,
                description="Unknown Pose",
                is_pinch=pinch_active,
                features=features
            )
            return unknown

        # Matches are already sorted by priority descending
        best_match = matches[0]

        return ClassifiedGesture(
            name=best_match.name,
            action=best_match.action,
            role=best_match.role,
            category=best_match.category,
            mode=best_match.mode,
            cooldown=best_match.cooldown,
            confidence=confidence,
            description=best_match.description,
            is_pinch=pinch_active,
            features=features
        )
