"""
Unit Tests for Bimanual Controller Module
Tests bimanual coordination: right-hand pointer steering with left-hand pinch selection,
hold-to-drag, release, and fail-safe recovery on hand loss.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from control.bimanual import BimanualController
from control.drag import DragController
from system.win32_input import MockInputBackend
from kinematics.features import KinematicFeatures


def make_dummy_features(pinch_ratio=0.70):
    return KinematicFeatures(
        fingers=(0, 1, 0, 0, 0),
        clarities=(1.0, 1.0, 1.0, 1.0, 1.0),
        palm_scale=0.30,
        pinch_ratio=pinch_ratio,
        is_pinch_enter=(pinch_ratio <= 0.38),
        is_pinch_exit=(pinch_ratio > 0.52),
        index_pos_norm=(0.5, 0.5),
        thumb_pos_norm=(0.48, 0.52),
        mid_pos_norm=(0.49, 0.51),
        velocity=0.0
    )


class TestBimanualController(unittest.TestCase):

    def setUp(self):
        self.mock_backend = MockInputBackend()
        self.drag = DragController(self.mock_backend)
        self.bimanual = BimanualController(self.mock_backend, self.drag, drag_hold_frames=3)

    def test_idle_when_no_pinch(self):
        feat = make_dummy_features(pinch_ratio=0.80)
        state = self.bimanual.update(feat, left_track_present=True, right_track_present=True)
        self.assertEqual(state.action_name, "IDLE")
        self.assertFalse(state.is_selecting)
        self.assertFalse(self.drag.is_dragging)

    def test_quick_pinch_tap_triggers_click(self):
        # 1. Start pinch (dwell)
        feat_pinch = make_dummy_features(pinch_ratio=0.25)
        state1 = self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        self.assertEqual(state1.action_name, "PINCH_DWELL")
        self.assertFalse(self.drag.is_dragging)

        # 2. Release pinch quickly before hold threshold (3 frames)
        feat_open = make_dummy_features(pinch_ratio=0.75)
        state2 = self.bimanual.update(feat_open, left_track_present=True, right_track_present=True)
        self.assertEqual(state2.action_name, "SELECT_CLICK")
        # Assert that click was called on mock backend
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("click", call_names)

    def test_pinch_hold_triggers_drag_select(self):
        feat_pinch = make_dummy_features(pinch_ratio=0.25)
        # Frame 1: Dwell
        self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        # Frame 2: Dwell
        self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        # Frame 3: Drag threshold reached
        state3 = self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        self.assertEqual(state3.action_name, "DRAGGING")
        self.assertTrue(state3.is_selecting)
        self.assertTrue(self.drag.is_dragging)
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("left_down", call_names)

        # Release pinch
        feat_open = make_dummy_features(pinch_ratio=0.75)
        state_rel = self.bimanual.update(feat_open, left_track_present=True, right_track_present=True)
        self.assertEqual(state_rel.action_name, "RELEASE")
        self.assertFalse(self.drag.is_dragging)
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("left_up", call_names)

    def test_hand_loss_safety_release(self):
        feat_pinch = make_dummy_features(pinch_ratio=0.25)
        for _ in range(4):
            self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        self.assertTrue(self.drag.is_dragging)

        # Hand lost abruptly
        state_lost = self.bimanual.update(None, left_track_present=False, right_track_present=True)
        self.assertEqual(state_lost.action_name, "RELEASE")
        self.assertFalse(self.drag.is_dragging)
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("left_up", call_names)

    def test_two_finger_tap_triggers_right_click(self):
        # Two fingers extended (Index + Middle), Ring & Pinky curled
        feat_two = KinematicFeatures(
            fingers=(0, 1, 1, 0, 0),
            clarities=(1.0, 1.0, 1.0, 1.0, 1.0),
            palm_scale=0.30,
            pinch_ratio=0.85,
            is_pinch_enter=False,
            is_pinch_exit=True,
            index_pos_norm=(0.5, 0.5),
            thumb_pos_norm=(0.4, 0.5),
            mid_pos_norm=(0.52, 0.5),
            velocity=0.0
        )
        # Frame 1-3: Dwell with two fingers
        for _ in range(3):
            self.bimanual.update(feat_two, left_track_present=True, right_track_present=True)

        # Tap release: fingers fold or open
        feat_rel = make_dummy_features(pinch_ratio=0.85)
        state_rc = self.bimanual.update(feat_rel, left_track_present=True, right_track_present=True)
        self.assertEqual(state_rc.action_name, "RIGHT_CLICK")
        self.assertEqual(state_rc.click_event, "RIGHT_CLICK")
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("right_click", call_names)

    def test_double_click_cadence(self):
        # Tap 1
        feat_pinch = make_dummy_features(pinch_ratio=0.25)
        self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        feat_open = make_dummy_features(pinch_ratio=0.75)
        state1 = self.bimanual.update(feat_open, left_track_present=True, right_track_present=True)
        self.assertEqual(state1.click_event, "LEFT_CLICK")

        # Tap 2 within 380ms interval
        self.bimanual.update(feat_pinch, left_track_present=True, right_track_present=True)
        state2 = self.bimanual.update(feat_open, left_track_present=True, right_track_present=True)
        self.assertEqual(state2.click_event, "DOUBLE_CLICK")
        call_names = [c[0] for c in self.mock_backend.calls]
        self.assertIn("double_click", call_names)

    def test_intentional_displacement_triggers_drag_early(self):
        # Configure with longer hold window (15 frames)
        bm_long = BimanualController(self.mock_backend, self.drag, drag_hold_frames=15, displacement_threshold=0.035)
        feat_pinch = make_dummy_features(pinch_ratio=0.25)

        # Frame 1 at pos (0.50, 0.50)
        bm_long.update(feat_pinch, left_track_present=True, right_track_present=True, current_norm_pos=(0.50, 0.50))
        # Frame 2 with large intentional displacement (moved to 0.58, 0.50 -> dist = 0.08 > 0.035)
        state2 = bm_long.update(feat_pinch, left_track_present=True, right_track_present=True, current_norm_pos=(0.58, 0.50))
        self.assertEqual(state2.action_name, "DRAGGING")
        self.assertTrue(state2.is_selecting)
        self.assertTrue(self.drag.is_dragging)


if __name__ == "__main__":
    unittest.main()
