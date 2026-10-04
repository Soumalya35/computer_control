"""
Kinematic Distances Module
Provides normalized, dimensionless geometric distance measurements based on MediaPipe hand landmarks.
"""

import math


def euclidean_distance_2d(p1, p2):
    """Calculates 2D Euclidean distance between two points with .x and .y attributes."""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def euclidean_distance_3d(p1, p2):
    """Calculates 3D Euclidean distance between two points with .x, .y, and .z attributes."""
    dz = getattr(p1, 'z', 0.0) - getattr(p2, 'z', 0.0)
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + dz ** 2)


def get_palm_scale(landmarks):
    """
    Computes invariant palm scale: distance from Landmark 0 (Wrist) to Landmark 9 (Middle MCP).
    Serves as the reference biometric length to normalize all finger distances against hand depth.
    """
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    return max(1e-4, euclidean_distance_2d(wrist, middle_mcp))


def get_pinch_distance(landmarks):
    """Calculates distance between Landmark 4 (Thumb tip) and Landmark 8 (Index tip)."""
    return euclidean_distance_2d(landmarks[4], landmarks[8])


def get_normalized_pinch_ratio(landmarks):
    """
    Calculates dimensionless pinch ratio: distance(LM4, LM8) / palm_scale.
    This value is scale-invariant and invariant to camera distance.
    """
    palm = get_palm_scale(landmarks)
    pinch = get_pinch_distance(landmarks)
    return pinch / palm


def get_thumb_to_pinky_ratio(landmarks):
    """
    Computes rotation-invariant thumb extension ratio:
    distance(Thumb Tip 4, Pinky MCP 17) / distance(Thumb IP 3, Pinky MCP 17).
    """
    tip = landmarks[4]
    ip = landmarks[3]
    pinky_mcp = landmarks[17]

    d_tip = euclidean_distance_2d(tip, pinky_mcp)
    d_ip = max(1e-4, euclidean_distance_2d(ip, pinky_mcp))
    return d_tip / d_ip
