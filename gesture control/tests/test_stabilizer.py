"""
Unit Tests for Temporal Stabilizer
Tests sliding-window majority voting, confidence gating, and per-action cooldown intervals.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gestures import TemporalStabilizer, ClassifiedGesture


def make_candidate(action, mode="CONTINUOUS", confidence=0.85, cooldown=0.5):
    return ClassifiedGesture(
        name=action,
        action=action,
        role="PRIMARY",
        category="test",
        mode=mode,
        cooldown=cooldown,
        confidence=confidence,
        description=f"Test {action}",
        is_pinch=False,
        features=None
    )


class TestStabilizer(unittest.TestCase):

    def setUp(self):
        # 5-frame window, 3 votes required
        self.stabilizer = TemporalStabilizer(window_size=5, min_votes=3, confidence_threshold=0.65)

    def test_voting_requirement(self):
        cand = make_candidate("MOVE_MOUSE", mode="CONTINUOUS")

        # Frame 1: 1 vote -> None
        self.assertIsNone(self.stabilizer.update(cand))
        # Frame 2: 2 votes -> None
        self.assertIsNone(self.stabilizer.update(cand))
        # Frame 3: 3 votes >= min_votes -> Accepted!
        res = self.stabilizer.update(cand)
        self.assertIsNotNone(res)
        self.assertEqual(res.action, "MOVE_MOUSE")

    def test_low_confidence_rejection(self):
        cand_low = make_candidate("MOVE_MOUSE", confidence=0.50)  # Below 0.65 threshold
        self.assertIsNone(self.stabilizer.update(cand_low))
        self.assertEqual(len(self.stabilizer.history), 0, "Low confidence must not enter history")

    def test_discrete_action_cooldown(self):
        cand_discrete = make_candidate("ALT_TAB", mode="DISCRETE", cooldown=0.5)

        # Feed 3 votes
        self.stabilizer.update(cand_discrete)
        self.stabilizer.update(cand_discrete)
        res1 = self.stabilizer.update(cand_discrete)
        self.assertIsNotNone(res1, "Should fire discrete action on threshold")

        # Holding the same gesture immediately should NOT fire again
        res2 = self.stabilizer.update(cand_discrete)
        self.assertIsNone(res2, "Should block repeated fire while held")

    def test_pause_resume(self):
        cand_pause = make_candidate("PAUSE", mode="DISCRETE")
        cand_resume = make_candidate("RESUME", mode="DISCRETE")
        cand_point = make_candidate("MOVE_MOUSE", mode="CONTINUOUS")

        for _ in range(3):
            self.stabilizer.update(cand_pause)
        self.assertTrue(self.stabilizer.is_paused)

        # Other actions must be blocked while paused
        for _ in range(3):
            res_blocked = self.stabilizer.update(cand_point)
        self.assertIsNone(res_blocked)

        # Resume action unblocks
        for _ in range(3):
            res_resumed = self.stabilizer.update(cand_resume)
        self.assertFalse(self.stabilizer.is_paused)


if __name__ == "__main__":
    unittest.main()
