"""
Kinematic Feature Extraction Module
Extracts normalized finger extension booleans, thumb abduction, pinch ratios, and motion velocity.
"""

from dataclasses import dataclass
from typing import Tuple

from .distances import (
    euclidean_distance_2d,
    get_palm_scale,
    get_normalized_pinch_ratio,
    get_thumb_to_pinky_ratio
)
from .angles import joint_cosine_alignment


@dataclass
class KinematicFeatures:
    """Structured kinematic feature set extracted from 21 MediaPipe hand landmarks."""
    fingers: Tuple[int, int, int, int, int]
    clarities: Tuple[float, float, float, float, float]
    palm_scale: float
    pinch_ratio: float
    is_pinch_enter: bool
    is_pinch_exit: bool
    index_pos_norm: Tuple[float, float]
    thumb_pos_norm: Tuple[float, float]
    mid_pos_norm: Tuple[float, float]
    velocity: float


def evaluate_single_finger(landmarks, tip_idx, pip_idx, mcp_idx, wrist_idx=0):
    """
    Evaluates finger extension state using radial distance-to-wrist ratio and joint collinearity.
    Returns: (is_extended: int, clarity: float)
    """
    tip = landmarks[tip_idx]
    pip = landmarks[pip_idx]
    mcp = landmarks[mcp_idx]
    wrist = landmarks[wrist_idx]

    d_tip_wrist = euclidean_distance_2d(tip, wrist)
    d_pip_wrist = max(1e-4, euclidean_distance_2d(pip, wrist))
    ratio_wrist = d_tip_wrist / d_pip_wrist

    cos_val = joint_cosine_alignment(mcp, pip, tip)

    # If tip is curled towards palm/wrist, finger is folded
    if ratio_wrist < 1.12:
        return 0, min(1.0, (1.12 - ratio_wrist) * 2.0)

    # Finger is extended outward from palm and aligned
    if ratio_wrist > 1.22 and cos_val > 0.35:
        return 1, min(1.0, (ratio_wrist - 1.22) * 2.0 + cos_val * 0.5)
    elif ratio_wrist > 1.15 and cos_val > 0.60:
        return 1, 0.6
    else:
        return 0, 0.5


def evaluate_thumb(landmarks):
    """
    Evaluates thumb extension using invariant ratio to pinky knuckle and vertical check.
    Returns: (is_extended: int, clarity: float)
    """
    ratio = get_thumb_to_pinky_ratio(landmarks)
    tip = landmarks[4]
    ip = landmarks[3]
    mcp = landmarks[2]

    is_vertically_up = (tip.y < ip.y) and (ip.y < mcp.y)
    is_laterally_extended = ratio > 1.14

    is_extended = 1 if (is_laterally_extended or is_vertically_up) else 0
    clarity = min(1.0, max(0.5, abs(ratio - 1.14) * 3.0))
    return is_extended, clarity


def extract_features(
    landmarks,
    pinch_enter_ratio=0.38,
    pinch_exit_ratio=0.52,
    prev_index_pos=None
) -> KinematicFeatures:
    """Extracts complete normalized kinematic features from a set of 21 landmarks."""
    # 1. Evaluate Thumb (4)
    thumb_state, thumb_clarity = evaluate_thumb(landmarks)

    # 2. Evaluate 4 Fingers: Index (8), Middle (12), Ring (16), Pinky (20)
    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]
    finger_mcps = [5, 9, 13, 17]

    fingers = [thumb_state]
    clarities = [thumb_clarity]

    for tip_idx, pip_idx, mcp_idx in zip(finger_tips, finger_pips, finger_mcps):
        f_state, f_clarity = evaluate_single_finger(landmarks, tip_idx, pip_idx, mcp_idx)
        fingers.append(f_state)
        clarities.append(f_clarity)

    # 3. Palm scale and normalized pinch
    palm_scale = get_palm_scale(landmarks)
    pinch_ratio = get_normalized_pinch_ratio(landmarks)
    is_pinch_enter = pinch_ratio < pinch_enter_ratio
    is_pinch_exit = pinch_ratio > pinch_exit_ratio

    # 4. Positions
    index_pos = (landmarks[8].x, landmarks[8].y)
    thumb_pos = (landmarks[4].x, landmarks[4].y)
    mid_pos = ((index_pos[0] + thumb_pos[0]) / 2.0, (index_pos[1] + thumb_pos[1]) / 2.0)

    # 5. Velocity
    velocity = 0.0
    if prev_index_pos is not None:
        dx = index_pos[0] - prev_index_pos[0]
        dy = index_pos[1] - prev_index_pos[1]
        velocity = euclidean_distance_2d(landmarks[8], type('Point', (), {'x': prev_index_pos[0], 'y': prev_index_pos[1]}))

    return KinematicFeatures(
        fingers=tuple(fingers),
        clarities=tuple(clarities),
        palm_scale=palm_scale,
        pinch_ratio=pinch_ratio,
        is_pinch_enter=is_pinch_enter,
        is_pinch_exit=is_pinch_exit,
        index_pos_norm=index_pos,
        thumb_pos_norm=thumb_pos,
        mid_pos_norm=mid_pos,
        velocity=velocity
    )
