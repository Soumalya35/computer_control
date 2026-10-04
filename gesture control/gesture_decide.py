"""
Gesture Decision Module
Analyzes 21 hand landmarks, evaluates finger state configurations (extended vs folded),
computes stabilized kinematic confidence scores without erratic fluctuations, measures
depth-adaptive thumb-to-index pinch proximity with entry/exit hysteresis, supports dual-hand gestures,
and provides robust detection for Volume Down (Pinky & Thumb Down).
"""

import math
from config import (
    MIN_GESTURE_CONFIDENCE, CONFIDENCE_SMOOTH_FACTOR
)
from gesture_database import gesture_map, UNKNOWN_GESTURE

# Global history dictionary for per-hand confidence smoothing
_CONFIDENCE_HISTORY = {}


def _dist_2d(p1, p2):
    """Euclidean distance in 2D normalized space."""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def evaluate_finger(tip, pip, mcp, wrist):
    """
    Evaluates whether a finger is extended using distance-to-wrist ratio,
    vertical position, and joint vector collinearity.
    Returns (is_extended: int, clarity: float).
    """
    d_tip_wrist = _dist_2d(tip, wrist)
    d_pip_wrist = _dist_2d(pip, wrist)

    ratio = d_tip_wrist / max(1e-4, d_pip_wrist)
    is_vertically_higher = tip.y < pip.y

    v1_x, v1_y = (pip.x - mcp.x), (pip.y - mcp.y)
    v2_x, v2_y = (tip.x - pip.x), (tip.y - pip.y)
    mag1 = math.hypot(v1_x, v1_y)
    mag2 = math.hypot(v2_x, v2_y)

    cos_angle = 1.0
    if mag1 > 1e-4 and mag2 > 1e-4:
        cos_angle = (v1_x * v2_x + v1_y * v2_y) / (mag1 * mag2)

    extension_score = 0.0
    if ratio > 1.25 and is_vertically_higher:
        extension_score += 0.55
    elif ratio > 1.12:
        extension_score += 0.35

    if cos_angle > 0.55:
        extension_score += 0.45
    elif cos_angle > 0.2:
        extension_score += 0.20

    is_extended = 1 if extension_score >= 0.50 else 0
    dist_from_thresh = abs(extension_score - 0.50)
    clarity = min(1.0, max(0.55, 0.55 + dist_from_thresh * 1.5))

    return is_extended, clarity


def evaluate_thumb(lms, hand_label="Right"):
    """
    Evaluates thumb extension using rotation-invariant distance to pinky knuckle
    and vertical extension.
    Returns (is_extended: int, clarity: float).
    """
    tip = lms[4]
    ip = lms[3]
    mcp = lms[2]
    pinky_mcp = lms[17]

    dist_tip_to_pinky = _dist_2d(tip, pinky_mcp)
    dist_ip_to_pinky = _dist_2d(ip, pinky_mcp)

    is_vertically_up = (tip.y < ip.y) and (ip.y < mcp.y)
    dist_ratio = dist_tip_to_pinky / max(1e-4, dist_ip_to_pinky)
    is_laterally_extended = dist_ratio > 1.12

    is_extended = 1 if (is_laterally_extended or is_vertically_up) else 0
    clarity = min(1.0, max(0.55, 0.55 + abs(dist_ratio - 1.12) * 1.8))

    return is_extended, clarity


def smooth_confidence(hand_key, raw_conf):
    """Smooths confidence over time using Exponential Moving Average to prevent flicker."""
    prev_conf = _CONFIDENCE_HISTORY.get(hand_key, raw_conf)
    smoothed = (prev_conf * CONFIDENCE_SMOOTH_FACTOR) + (raw_conf * (1.0 - CONFIDENCE_SMOOTH_FACTOR))
    _CONFIDENCE_HISTORY[hand_key] = smoothed
    return smoothed


def recognize_gesture(
    hand_landmarks,
    hand_label="Right",
    frame_width=1280,
    frame_height=720,
    detection_score=0.90,
    is_currently_pinching=False,
    is_secondary=False
):
    """
    Analyzes landmark coordinates and returns classified gesture dictionary
    with stabilized confidence, depth-adaptive pinch hysteresis, robust Volume Down detection,
    and two-hand role recognition.
    """
    lms = hand_landmarks.landmark
    wrist = lms[0]

    # 1. Evaluate Thumb
    thumb_state, thumb_clarity = evaluate_thumb(lms, hand_label)

    # 2. Evaluate other 4 fingers: Index (8), Middle (12), Ring (16), Pinky (20)
    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]
    finger_mcps = [5, 9, 13, 17]

    fingers = [thumb_state]
    clarities = [thumb_clarity]

    for tip_idx, pip_idx, mcp_idx in zip(finger_tips, finger_pips, finger_mcps):
        f_state, f_clarity = evaluate_finger(lms[tip_idx], lms[pip_idx], lms[mcp_idx], wrist)
        fingers.append(f_state)
        clarities.append(f_clarity)

    avg_clarity = sum(clarities) / len(clarities)

    # 3. Calculate Biometric Palm Scale for Depth-Adaptive Pinch Normalization
    x_wrist = int(wrist.x * frame_width)
    y_wrist = int(wrist.y * frame_height)
    x_mcp_mid = int(lms[9].x * frame_width)
    y_mcp_mid = int(lms[9].y * frame_height)
    palm_len_px = math.hypot(x_mcp_mid - x_wrist, y_mcp_mid - y_wrist)

    dynamic_pinch_enter = max(32, min(80, int(palm_len_px * 0.38)))
    dynamic_pinch_exit = max(50, int(dynamic_pinch_enter * 1.38))

    # 4. Calculate Coordinates
    x_thumb = int(lms[4].x * frame_width)
    y_thumb = int(lms[4].y * frame_height)
    x_index = int(lms[8].x * frame_width)
    y_index = int(lms[8].y * frame_height)

    mid_x = (x_thumb + x_index) // 2
    mid_y = (y_thumb + y_index) // 2

    pinch_distance = math.hypot(x_index - x_thumb, y_index - y_thumb)
    effective_pinch_thresh = dynamic_pinch_exit if is_currently_pinching else dynamic_pinch_enter
    is_pinch = pinch_distance < effective_pinch_thresh

    not_open_palm = (fingers[3] == 0 or fingers[4] == 0 or fingers[2] == 0)
    finger_tuple = tuple(fingers)
    hand_key = f"{hand_label}_{'sec' if is_secondary else 'pri'}"

    # ----------------------------------------------------
    # Special Detection: Volume Down (Pinky or Thumb Down)
    # ----------------------------------------------------
    thumb_tip = lms[4]
    thumb_ip = lms[3]
    thumb_mcp = lms[2]
    is_thumb_down = (thumb_tip.y > thumb_ip.y) and (thumb_ip.y > thumb_mcp.y)
    other_4_folded = (fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0)

    # Thumb Down Gesture (👎)
    if is_thumb_down and other_4_folded and not is_secondary:
        conf = smooth_confidence(hand_key, 0.90)
        return {
            "description": "Thumb Down (Volume Down)",
            "action": "VOLUME_DOWN",
            "category": "media",
            "continuous": False,
            "cooldown": 0.20,
            "finger_tuple": (1, 0, 0, 0, 0),
            "is_pinch": False,
            "pinch_distance": pinch_distance,
            "pinch_threshold": dynamic_pinch_enter,
            "index_pos": (x_index, y_index),
            "thumb_pos": (x_thumb, y_thumb),
            "mid_pos": (mid_x, mid_y),
            "hand_label": hand_label,
            "is_secondary": is_secondary,
            "confidence": round(conf, 3)
        }

    # Pinky Only Gesture: Disambiguate from Shaka
    pinky_extended = (fingers[4] == 1)
    other_3_folded = (fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 0)
    if pinky_extended and other_3_folded and not is_secondary:
        dist_thumb_index_knuckle = _dist_2d(lms[4], lms[5])
        # If thumb is not sticking far out, it is definitely Pinky Only (Volume Down)
        if dist_thumb_index_knuckle < 0.16 or thumb_state == 0:
            conf = smooth_confidence(hand_key, 0.88)
            return {
                "description": "Pinky Only (Volume Down)",
                "action": "VOLUME_DOWN",
                "category": "media",
                "continuous": False,
                "cooldown": 0.20,
                "finger_tuple": (0, 0, 0, 0, 1),
                "is_pinch": False,
                "pinch_distance": pinch_distance,
                "pinch_threshold": dynamic_pinch_enter,
                "index_pos": (x_index, y_index),
                "thumb_pos": (x_thumb, y_thumb),
                "mid_pos": (mid_x, mid_y),
                "hand_label": hand_label,
                "is_secondary": is_secondary,
                "confidence": round(conf, 3)
            }

    # ----------------------------------------------------
    # Handle Pinch Action (Primary & Secondary)
    # ----------------------------------------------------
    if is_pinch and not_open_palm:
        pinch_proximity_score = max(0.0, min(1.0, 1.0 - (pinch_distance / dynamic_pinch_exit)))
        raw_conf = min(0.99, 0.40 * detection_score + 0.35 * avg_clarity + 0.25 * pinch_proximity_score + 0.12)
        conf = smooth_confidence(hand_key, raw_conf)

        gesture_data = dict(gesture_map["PINCH"])
        if is_secondary:
            gesture_data["action"] = "SEC_PINCH_SELECT"
            gesture_data["description"] = "Secondary Pinch (Select/Click)"

        gesture_data["finger_tuple"] = finger_tuple
        gesture_data["is_pinch"] = True
        gesture_data["pinch_distance"] = pinch_distance
        gesture_data["pinch_threshold"] = dynamic_pinch_enter
        gesture_data["index_pos"] = (x_index, y_index)
        gesture_data["thumb_pos"] = (x_thumb, y_thumb)
        gesture_data["mid_pos"] = (mid_x, mid_y)
        gesture_data["hand_label"] = hand_label
        gesture_data["is_secondary"] = is_secondary
        gesture_data["confidence"] = round(conf, 3)
        return gesture_data

    # ----------------------------------------------------
    # Handle Secondary Hand Specific Gestures
    # ----------------------------------------------------
    if is_secondary:
        # Peace sign on secondary hand -> NEXT_TAB
        if finger_tuple in [(0, 1, 1, 0, 0), (1, 1, 1, 0, 0)]:
            raw_conf = 0.45 * detection_score + 0.45 * avg_clarity + 0.1
            conf = smooth_confidence(hand_key, raw_conf)
            return {
                "description": "Secondary Peace (Next Tab)",
                "action": "NEXT_TAB",
                "category": "keyboard",
                "continuous": False,
                "cooldown": 0.45,
                "finger_tuple": finger_tuple,
                "is_pinch": False,
                "pinch_distance": pinch_distance,
                "index_pos": (x_index, y_index),
                "thumb_pos": (x_thumb, y_thumb),
                "mid_pos": (mid_x, mid_y),
                "hand_label": hand_label,
                "is_secondary": True,
                "confidence": round(conf, 3)
            }

        # Three fingers on secondary hand -> PREV_TAB
        if finger_tuple in [(0, 1, 1, 1, 0), (1, 1, 1, 1, 0)]:
            raw_conf = 0.45 * detection_score + 0.45 * avg_clarity + 0.1
            conf = smooth_confidence(hand_key, raw_conf)
            return {
                "description": "Secondary 3-Fingers (Prev Tab)",
                "action": "PREV_TAB",
                "category": "keyboard",
                "continuous": False,
                "cooldown": 0.45,
                "finger_tuple": finger_tuple,
                "is_pinch": False,
                "pinch_distance": pinch_distance,
                "index_pos": (x_index, y_index),
                "thumb_pos": (x_thumb, y_thumb),
                "mid_pos": (mid_x, mid_y),
                "hand_label": hand_label,
                "is_secondary": True,
                "confidence": round(conf, 3)
            }

        # Secondary Fist -> Instant Left Click / Drag Hold
        if finger_tuple == (0, 0, 0, 0, 0):
            raw_conf = 0.45 * detection_score + 0.45 * avg_clarity + 0.1
            conf = smooth_confidence(hand_key, raw_conf)
            return {
                "description": "Secondary Fist (Select Hold)",
                "action": "SEC_FIST_SELECT",
                "category": "mouse",
                "continuous": True,
                "cooldown": 0.0,
                "finger_tuple": finger_tuple,
                "is_pinch": False,
                "pinch_distance": pinch_distance,
                "index_pos": (x_index, y_index),
                "thumb_pos": (x_thumb, y_thumb),
                "mid_pos": (mid_x, mid_y),
                "hand_label": hand_label,
                "is_secondary": True,
                "confidence": round(conf, 3)
            }

    # ----------------------------------------------------
    # Standard Tuple lookup for Primary Hand
    # ----------------------------------------------------
    base_data = gesture_map.get(finger_tuple, UNKNOWN_GESTURE)

    match_bonus = 0.14 if base_data["action"] != "NO_ACTION" else -0.08
    raw_confidence = max(0.25, min(0.99, 0.45 * detection_score + 0.45 * avg_clarity + match_bonus))
    conf = smooth_confidence(hand_key, raw_confidence)

    gesture_data = dict(base_data)
    gesture_data["finger_tuple"] = finger_tuple
    gesture_data["is_pinch"] = False
    gesture_data["pinch_distance"] = pinch_distance
    gesture_data["pinch_threshold"] = dynamic_pinch_enter
    gesture_data["index_pos"] = (x_index, y_index)
    gesture_data["thumb_pos"] = (x_thumb, y_thumb)
    gesture_data["mid_pos"] = (mid_x, mid_y)
    gesture_data["hand_label"] = hand_label
    gesture_data["is_secondary"] = is_secondary
    gesture_data["confidence"] = round(conf, 3)

    return gesture_data