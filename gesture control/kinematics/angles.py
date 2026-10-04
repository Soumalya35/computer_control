"""
Kinematic Angles & Joint Alignment Module
Computes joint vector directions, dot products, and collinearity cosines to verify finger extension.
"""

import math


def vector_2d(p_from, p_to):
    """Calculates directional vector from p_from to p_to."""
    return (p_to.x - p_from.x, p_to.y - p_from.y)


def vector_magnitude(v):
    """Calculates vector magnitude."""
    return math.hypot(v[0], v[1])


def vector_dot_product(v1, v2):
    """Calculates 2D vector dot product."""
    return v1[0] * v2[0] + v1[1] * v2[1]


def joint_cosine_alignment(p_prev, p_joint, p_next):
    """
    Calculates the cosine of the angle between incoming segment (p_prev -> p_joint)
    and outgoing segment (p_joint -> p_next).
    cos(theta) = (v1 . v2) / (|v1| * |v2|)
    Returns 1.0 for a perfectly straight finger, 0.0 for a 90-degree bend, negative for folded back.
    """
    v1 = vector_2d(p_prev, p_joint)
    v2 = vector_2d(p_joint, p_next)

    mag1 = vector_magnitude(v1)
    mag2 = vector_magnitude(v2)

    if mag1 < 1e-6 or mag2 < 1e-6:
        return 1.0

    dot = vector_dot_product(v1, v2)
    cos_val = dot / (mag1 * mag2)
    # Clamp to valid [-1.0, 1.0] range
    return max(-1.0, min(1.0, cos_val))
