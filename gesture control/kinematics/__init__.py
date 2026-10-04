"""Kinematics package initialization."""
from .distances import (
    euclidean_distance_2d,
    euclidean_distance_3d,
    get_palm_scale,
    get_pinch_distance,
    get_normalized_pinch_ratio,
    get_thumb_to_pinky_ratio
)
from .angles import joint_cosine_alignment
from .features import KinematicFeatures, extract_features
from .confidence import ConfidenceEngine, ConfidenceBreakdown

__all__ = [
    "euclidean_distance_2d",
    "euclidean_distance_3d",
    "get_palm_scale",
    "get_pinch_distance",
    "get_normalized_pinch_ratio",
    "get_thumb_to_pinky_ratio",
    "joint_cosine_alignment",
    "KinematicFeatures",
    "extract_features",
    "ConfidenceEngine",
    "ConfidenceBreakdown"
]
