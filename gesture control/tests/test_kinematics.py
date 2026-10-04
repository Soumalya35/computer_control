"""
Unit Tests for Kinematics Package
Tests pure mathematical functions: distances, palm scale, joint cosines, feature extraction, and confidence breakdown.
"""

import os
import sys
import unittest
from types import SimpleNamespace

# Ensure gesture control is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kinematics import (
    euclidean_distance_2d,
    get_palm_scale,
    get_pinch_distance,
    get_normalized_pinch_ratio,
    joint_cosine_alignment,
    extract_features,
    ConfidenceEngine
)


class MockPoint:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def create_mock_hand(finger_extended=(False, False, False, False, False)):
    """
    Creates a synthetic 21-landmark hand with specified finger extension states.
    finger_extended = (Thumb, Index, Middle, Ring, Pinky)
    """
    landmarks = [MockPoint(0.5, 0.8) for _ in range(21)]  # Wrist at (0.5, 0.8)

    # Landmark 0: Wrist
    landmarks[0] = MockPoint(0.5, 0.8)
    # Landmark 9: Middle MCP
    landmarks[9] = MockPoint(0.5, 0.5)  # Palm scale = 0.3

    # Thumb: 1, 2, 3, 4
    if finger_extended[0]:
        landmarks[1] = MockPoint(0.45, 0.7)
        landmarks[2] = MockPoint(0.40, 0.6)
        landmarks[3] = MockPoint(0.35, 0.5)
        landmarks[4] = MockPoint(0.30, 0.4)  # Extended outwards
    else:
        landmarks[1] = MockPoint(0.48, 0.7)
        landmarks[2] = MockPoint(0.47, 0.65)
        landmarks[3] = MockPoint(0.46, 0.62)
        landmarks[4] = MockPoint(0.48, 0.60)  # Folded against palm

    # Index: 5, 6, 7, 8
    landmarks[5] = MockPoint(0.42, 0.52)
    if finger_extended[1]:
        landmarks[6] = MockPoint(0.42, 0.40)
        landmarks[7] = MockPoint(0.42, 0.30)
        landmarks[8] = MockPoint(0.42, 0.20)  # Extended up
    else:
        landmarks[6] = MockPoint(0.42, 0.55)
        landmarks[7] = MockPoint(0.42, 0.62)
        landmarks[8] = MockPoint(0.42, 0.65)  # Curled down

    # Middle: 9, 10, 11, 12
    if finger_extended[2]:
        landmarks[10] = MockPoint(0.50, 0.38)
        landmarks[11] = MockPoint(0.50, 0.28)
        landmarks[12] = MockPoint(0.50, 0.18)
    else:
        landmarks[10] = MockPoint(0.50, 0.55)
        landmarks[11] = MockPoint(0.50, 0.62)
        landmarks[12] = MockPoint(0.50, 0.66)

    # Ring: 13, 14, 15, 16
    landmarks[13] = MockPoint(0.58, 0.52)
    if finger_extended[3]:
        landmarks[14] = MockPoint(0.58, 0.40)
        landmarks[15] = MockPoint(0.58, 0.30)
        landmarks[16] = MockPoint(0.58, 0.20)
    else:
        landmarks[14] = MockPoint(0.58, 0.55)
        landmarks[15] = MockPoint(0.58, 0.62)
        landmarks[16] = MockPoint(0.58, 0.65)

    # Pinky: 17, 18, 19, 20
    landmarks[17] = MockPoint(0.65, 0.55)
    if finger_extended[4]:
        landmarks[18] = MockPoint(0.65, 0.45)
        landmarks[19] = MockPoint(0.65, 0.35)
        landmarks[20] = MockPoint(0.65, 0.25)
    else:
        landmarks[18] = MockPoint(0.65, 0.58)
        landmarks[19] = MockPoint(0.65, 0.63)
        landmarks[20] = MockPoint(0.65, 0.67)

    return landmarks


class TestKinematics(unittest.TestCase):

    def test_euclidean_distance(self):
        p1 = MockPoint(0.0, 0.0)
        p2 = MockPoint(3.0, 4.0)
        self.assertAlmostEqual(euclidean_distance_2d(p1, p2), 5.0)

    def test_palm_scale(self):
        hand = create_mock_hand()
        scale = get_palm_scale(hand)
        self.assertAlmostEqual(scale, 0.3, places=2)

    def test_joint_cosine_straight_vs_bent(self):
        # Straight line: (0,0) -> (0,1) -> (0,2)
        p_prev = MockPoint(0.0, 0.0)
        p_joint = MockPoint(0.0, 1.0)
        p_next = MockPoint(0.0, 2.0)
        cos_straight = joint_cosine_alignment(p_prev, p_joint, p_next)
        self.assertAlmostEqual(cos_straight, 1.0)

        # 90-degree bend: (0,0) -> (0,1) -> (1,1)
        p_bent = MockPoint(1.0, 1.0)
        cos_bent = joint_cosine_alignment(p_prev, p_joint, p_bent)
        self.assertAlmostEqual(cos_bent, 0.0)

    def test_feature_extraction_pointing(self):
        # Only index extended
        hand = create_mock_hand(finger_extended=(False, True, False, False, False))
        features = extract_features(hand)
        self.assertEqual(features.fingers[1], 1, "Index must be extended (1)")
        self.assertEqual(features.fingers[2], 0, "Middle must be folded (0)")
        self.assertEqual(features.fingers[3], 0, "Ring must be folded (0)")
        self.assertEqual(features.fingers[4], 0, "Pinky must be folded (0)")

    def test_pinch_ratio(self):
        # Hand with thumb tip close to index tip
        hand = create_mock_hand()
        hand[4] = MockPoint(0.42, 0.22)
        hand[8] = MockPoint(0.42, 0.20)
        ratio = get_normalized_pinch_ratio(hand)
        self.assertLess(ratio, 0.20, "Pinch ratio should be well below enter threshold")

    def test_confidence_engine(self):
        engine = ConfidenceEngine()
        mock_features = SimpleNamespace(
            palm_scale=0.25,
            clarities=(0.9, 0.95, 0.9, 0.85, 0.9)
        )
        conf = engine.compute(detection_score=0.95, features=mock_features, temporal_agreement=1.0)
        self.assertTrue(conf.is_actionable)
        self.assertGreaterEqual(conf.total, 0.80)
        self.assertGreater(conf.c_detection, 0.90)


if __name__ == "__main__":
    unittest.main()
