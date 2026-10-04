"""
Unit Tests for Gestures Package
Tests GestureRegistry, GestureClassifier (Primary & Secondary roles, Priority rules, Conflict resolution).
"""

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gestures import GestureRegistry, GestureClassifier, DEFAULT_GESTURES
from kinematics.features import KinematicFeatures


def make_features(fingers, is_pinch_enter=False, is_pinch_exit=False, pinch_ratio=0.5):
    return KinematicFeatures(
        fingers=fingers,
        clarities=(1.0, 1.0, 1.0, 1.0, 1.0),
        palm_scale=0.3,
        pinch_ratio=pinch_ratio,
        is_pinch_enter=is_pinch_enter,
        is_pinch_exit=is_pinch_exit,
        index_pos_norm=(0.5, 0.5),
        thumb_pos_norm=(0.5, 0.5),
        mid_pos_norm=(0.5, 0.5),
        velocity=0.0
    )


class TestGestures(unittest.TestCase):

    def setUp(self):
        self.registry = GestureRegistry()
        self.classifier = GestureClassifier(self.registry)

    def test_registry_priority_sorting(self):
        all_gestures = self.registry.get_all()
        # Ensure gestures are sorted in descending order of priority
        priorities = [g.priority for g in all_gestures]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_primary_pointing_classification(self):
        features = make_features(fingers=(0, 1, 0, 0, 0))
        res = self.classifier.classify(features, hand_role="PRIMARY")
        self.assertEqual(res.action, "MOVE_MOUSE")
        self.assertEqual(res.role, "PRIMARY")

    def test_primary_fist_priority(self):
        features = make_features(fingers=(0, 0, 0, 0, 0))
        res = self.classifier.classify(features, hand_role="PRIMARY")
        self.assertEqual(res.action, "PAUSE")

    def test_secondary_hand_peace(self):
        # Two fingers on secondary hand must map to NEXT_TAB, not SCROLL_MODE
        features = make_features(fingers=(0, 1, 1, 0, 0))
        res_sec = self.classifier.classify(features, hand_role="SECONDARY")
        self.assertEqual(res_sec.action, "NEXT_TAB")
        self.assertEqual(res_sec.role, "SECONDARY")

        # Two fingers on primary hand must map to SCROLL_MODE
        res_pri = self.classifier.classify(features, hand_role="PRIMARY")
        self.assertEqual(res_pri.action, "SCROLL_MODE")
        self.assertEqual(res_pri.role, "PRIMARY")

    def test_pinch_classification(self):
        features = make_features(fingers=(0, 1, 0, 0, 0), is_pinch_enter=True, pinch_ratio=0.2)
        res = self.classifier.classify(features, hand_role="PRIMARY")
        self.assertEqual(res.action, "LEFT_CLICK")
        self.assertTrue(res.is_pinch)


if __name__ == "__main__":
    unittest.main()
