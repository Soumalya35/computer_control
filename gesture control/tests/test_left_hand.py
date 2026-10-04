"""
Unit Tests for Left Hand Recognition & Secondary Classification
Verifies that left hands are classified into true gestures (Open Palm, Fist, Pointing, Pinch, Peace)
without being suppressed or ignored.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gestures.classifier import GestureClassifier
from gestures.registry import GestureRegistry
from kinematics.features import KinematicFeatures


def make_features_for_fingers(fingers, pinch_ratio=0.75):
    return KinematicFeatures(
        fingers=fingers,
        clarities=(1.0, 1.0, 1.0, 1.0, 1.0),
        palm_scale=0.30,
        pinch_ratio=pinch_ratio,
        is_pinch_enter=(pinch_ratio <= 0.38),
        is_pinch_exit=(pinch_ratio > 0.52),
        index_pos_norm=(0.3, 0.5),
        thumb_pos_norm=(0.28, 0.52),
        mid_pos_norm=(0.29, 0.51),
        velocity=0.0
    )


class TestLeftHandRecognition(unittest.TestCase):

    def setUp(self):
        self.classifier = GestureClassifier()

    def test_left_hand_pinch_bimanual_select(self):
        feat = make_features_for_fingers((0, 0, 0, 0, 0), pinch_ratio=0.22)
        cand = self.classifier.classify(feat, hand_role="SECONDARY", confidence=0.85)
        self.assertEqual(cand.action, "BIMANUAL_SELECT")
        self.assertEqual(cand.role, "SECONDARY")

    def test_left_hand_peace_next_tab(self):
        feat = make_features_for_fingers((0, 1, 1, 0, 0), pinch_ratio=0.75)
        cand = self.classifier.classify(feat, hand_role="SECONDARY", confidence=0.85)
        self.assertEqual(cand.action, "NEXT_TAB")
        self.assertEqual(cand.role, "SECONDARY")

    def test_left_hand_three_fingers_prev_tab(self):
        feat = make_features_for_fingers((0, 1, 1, 1, 0), pinch_ratio=0.75)
        cand = self.classifier.classify(feat, hand_role="SECONDARY", confidence=0.85)
        self.assertEqual(cand.action, "PREVIOUS_TAB")

    def test_left_hand_open_palm_identified(self):
        feat = make_features_for_fingers((1, 1, 1, 1, 1), pinch_ratio=0.85)
        cand = self.classifier.classify(feat, hand_role="SECONDARY", confidence=0.90)
        # Either RESUME (role ANY) or LEFT_OPEN_PALM
        self.assertIn(cand.name, ("RESUME", "LEFT_OPEN_PALM"))

    def test_left_hand_fist_pause(self):
        feat = make_features_for_fingers((0, 0, 0, 0, 0), pinch_ratio=0.85)
        cand = self.classifier.classify(feat, hand_role="SECONDARY", confidence=0.90)
        self.assertEqual(cand.action, "PAUSE")


if __name__ == "__main__":
    unittest.main()
