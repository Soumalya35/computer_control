"""
Confidence Scoring Module
Computes inspectable multi-factor confidence metrics:
C = w1*C_detection + w2*C_geometry + w3*C_pose + w4*C_temporal + w5*C_visibility
"""

from dataclasses import dataclass


@dataclass
class ConfidenceBreakdown:
    """Detailed components of the multi-factor confidence score."""
    c_detection: float
    c_geometry: float
    c_pose: float
    c_temporal: float
    c_visibility: float
    total: float
    is_candidate: bool
    is_actionable: bool


class ConfidenceEngine:
    """Calculates and breaks down multi-factor confidence scores for gesture candidates."""

    def __init__(
        self,
        w1=0.35,  # Detection
        w2=0.20,  # Geometry
        w3=0.25,  # Pose clarity
        w4=0.10,  # Temporal agreement
        w5=0.10,  # Visibility
        candidate_thresh=0.60,
        action_thresh=0.65
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4
        self.w5 = w5
        self.candidate_thresh = candidate_thresh
        self.action_thresh = action_thresh

    def compute(
        self,
        detection_score: float,
        features,
        temporal_agreement: float = 1.0,
        missing_landmarks: int = 0
    ) -> ConfidenceBreakdown:
        """
        Computes composite confidence and returns a full inspectable breakdown.
        """
        # 1. Detection quality (from MediaPipe palm/landmark detector)
        c_det = max(0.0, min(1.0, float(detection_score)))

        # 2. Geometry quality (valid palm scale and reasonable aspect ratios)
        # Normal palm scale in normalized coords is between 0.08 and 0.55
        c_geom = 1.0
        if features.palm_scale < 0.06 or features.palm_scale > 0.65:
            c_geom = 0.50
        elif features.palm_scale < 0.09:
            c_geom = 0.80

        # 3. Pose quality (average clarity across all 5 fingers)
        c_pose = sum(features.clarities) / max(1, len(features.clarities))

        # 4. Temporal quality (recent frame agreement)
        c_temp = max(0.0, min(1.0, float(temporal_agreement)))

        # 5. Visibility quality (penalty for out-of-frame or low-presence landmarks)
        c_vis = max(0.0, 1.0 - (missing_landmarks * 0.15))

        # Weighted total
        total = (
            self.w1 * c_det +
            self.w2 * c_geom +
            self.w3 * c_pose +
            self.w4 * c_temp +
            self.w5 * c_vis
        )
        total = max(0.0, min(1.0, round(total, 3)))

        return ConfidenceBreakdown(
            c_detection=round(c_det, 3),
            c_geometry=round(c_geom, 3),
            c_pose=round(c_pose, 3),
            c_temporal=round(c_temp, 3),
            c_visibility=round(c_vis, 3),
            total=total,
            is_candidate=total >= self.candidate_thresh,
            is_actionable=total >= self.action_thresh
        )
