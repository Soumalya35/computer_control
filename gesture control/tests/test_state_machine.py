"""
Unit Tests for Gesture State Machine
Tests state transitions: IDLE, POINTING, PINCH_PENDING, CLICK, DRAGGING, grace frames, and hand-loss safety.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gestures import GestureStateMachine, State, ClassifiedGesture
from kinematics.features import KinematicFeatures


def make_gesture(action="MOVE_MOUSE", is_pinch=False):
    return ClassifiedGesture(
        name=action,
        action=action,
        role="PRIMARY",
        category="test",
        mode="CONTINUOUS",
        cooldown=0.0,
        confidence=0.90,
        description=action,
        is_pinch=is_pinch,
        features=None
    )


def make_feat(mid_x=0.5, mid_y=0.5):
    return KinematicFeatures(
        fingers=(0, 1, 0, 0, 0),
        clarities=(1.0, 1.0, 1.0, 1.0, 1.0),
        palm_scale=0.3,
        pinch_ratio=0.2,
        is_pinch_enter=True,
        is_pinch_exit=False,
        index_pos_norm=(mid_x, mid_y),
        thumb_pos_norm=(mid_x, mid_y),
        mid_pos_norm=(mid_x, mid_y),
        velocity=0.0
    )


class TestStateMachine(unittest.TestCase):

    def setUp(self):
        # 5 hold frames for drag, 2 grace frames
        self.sm = GestureStateMachine(drag_hold_frames=5, drag_grace_frames=2)

    def test_idle_to_pointing(self):
        g = make_gesture("MOVE_MOUSE")
        out = self.sm.update(g, make_feat(), hand_present=True)
        self.assertEqual(out.state, State.POINTING)
        self.assertEqual(out.event, "MOVE")

    def test_pinch_tap_click(self):
        g_point = make_gesture("MOVE_MOUSE", is_pinch=False)
        g_pinch = make_gesture("LEFT_CLICK", is_pinch=True)

        self.sm.update(g_point, make_feat(), hand_present=True)

        # Pinch for 2 frames (less than drag_hold_frames = 5)
        out1 = self.sm.update(g_pinch, make_feat(), hand_present=True)
        self.assertEqual(out1.state, State.PINCH_PENDING)

        out2 = self.sm.update(g_pinch, make_feat(), hand_present=True)
        self.assertEqual(out2.state, State.PINCH_PENDING)

        # Release pinch
        out_rel = self.sm.update(g_point, make_feat(), hand_present=True)
        self.assertEqual(out_rel.state, State.CLICK)
        self.assertEqual(out_rel.event, "CLICK")

    def test_pinch_hold_to_drag(self):
        g_pinch = make_gesture("LEFT_CLICK", is_pinch=True)
        # Hold pinch for 5 frames
        for _ in range(4):
            out = self.sm.update(g_pinch, make_feat(), hand_present=True)
            self.assertEqual(out.state, State.PINCH_PENDING)

        # 5th frame -> DRAG_START!
        out_drag = self.sm.update(g_pinch, make_feat(), hand_present=True)
        self.assertEqual(out_drag.state, State.DRAGGING)
        self.assertEqual(out_drag.event, "DRAG_START")
        self.assertTrue(out_drag.is_dragging)

    def test_drag_grace_frames(self):
        g_pinch = make_gesture("LEFT_CLICK", is_pinch=True)
        g_open = make_gesture("MOVE_MOUSE", is_pinch=False)

        # Engage drag
        for _ in range(5):
            self.sm.update(g_pinch, make_feat(), hand_present=True)
        self.assertEqual(self.sm.current_state, State.DRAGGING)

        # 1 frame without pinch (Grace frame 1) -> Still DRAGGING
        out_g1 = self.sm.update(g_open, make_feat(), hand_present=True)
        self.assertEqual(out_g1.state, State.DRAGGING)
        self.assertTrue(out_g1.is_dragging)

        # 2nd frame without pinch (Grace frame 2) -> Still DRAGGING
        out_g2 = self.sm.update(g_open, make_feat(), hand_present=True)
        self.assertEqual(out_g2.state, State.DRAGGING)
        self.assertTrue(out_g2.is_dragging)

        # 3rd frame without pinch -> Grace expired -> DRAG_END
        out_drop = self.sm.update(g_open, make_feat(), hand_present=True)
        self.assertEqual(out_drop.state, State.IDLE)
        self.assertEqual(out_drop.event, "DRAG_END")
        self.assertFalse(out_drop.is_dragging)

    def test_hand_loss_safety(self):
        g_pinch = make_gesture("LEFT_CLICK", is_pinch=True)
        # Engage drag
        for _ in range(5):
            self.sm.update(g_pinch, make_feat(), hand_present=True)
        self.assertEqual(self.sm.current_state, State.DRAGGING)

        # Hand suddenly disappears
        out_lost = self.sm.update(None, None, hand_present=False)
        self.assertEqual(out_lost.state, State.LOST_HAND)
        self.assertEqual(out_lost.event, "DRAG_END")
        self.assertFalse(out_lost.is_dragging)


if __name__ == "__main__":
    unittest.main()
