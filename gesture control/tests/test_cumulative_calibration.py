"""
Unit Tests for Cumulative Calibration Persistence
Verifies that multiple calibration sessions append data without deleting previous history,
computes refined active profiles, and supports legacy file structures.
"""

import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.loader import ConfigManager
import config.loader as loader_module


class TestCumulativeCalibration(unittest.TestCase):

    def setUp(self):
        # Create a temporary JSON file for testing calibration persistence
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        self.backup_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.backup_file.close()
        self.original_path = loader_module.CALIBRATION_JSON
        self.original_backup_path = loader_module.CALIBRATION_BACKUP_JSON
        loader_module.CALIBRATION_JSON = self.temp_file.name
        loader_module.CALIBRATION_BACKUP_JSON = self.backup_file.name

    def tearDown(self):
        loader_module.CALIBRATION_JSON = self.original_path
        loader_module.CALIBRATION_BACKUP_JSON = self.original_backup_path
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
        if os.path.exists(self.backup_file.name):
            os.remove(self.backup_file.name)

    def test_multi_session_append_no_data_loss(self):
        cfg = ConfigManager()

        # Session 1
        session1 = {
            "palm_scale": 0.28,
            "pinch_enter_ratio": 0.36,
            "pinch_exit_ratio": 0.50,
            "tremor_noise_px": 2.2,
            "calibrated_at": "2026-09-22 10:00:00"
        }
        cfg.save_calibration(session1)

        with open(self.temp_file.name, "r", encoding="utf-8") as f:
            data1 = json.load(f)

        self.assertEqual(len(data1["sessions"]), 1)
        self.assertEqual(data1["sessions"][0]["session_id"], 1)
        self.assertEqual(data1["active_profile"]["palm_scale"], 0.28)

        # Session 2
        session2 = {
            "palm_scale": 0.32,
            "pinch_enter_ratio": 0.40,
            "pinch_exit_ratio": 0.54,
            "tremor_noise_px": 1.8,
            "calibrated_at": "2026-09-22 15:00:00"
        }
        cfg.save_calibration(session2)

        with open(self.temp_file.name, "r", encoding="utf-8") as f:
            data2 = json.load(f)

        # Ensure BOTH sessions are preserved
        self.assertEqual(len(data2["sessions"]), 2)
        self.assertEqual(data2["sessions"][0]["session_id"], 1)
        self.assertEqual(data2["sessions"][0]["palm_scale"], 0.28)
        self.assertEqual(data2["sessions"][1]["session_id"], 2)
        self.assertEqual(data2["sessions"][1]["palm_scale"], 0.32)

        # Verify active profile is a weighted combination of session 1 and session 2
        # 0.4 * 0.28 + 0.6 * 0.32 = 0.112 + 0.192 = 0.304
        self.assertAlmostEqual(data2["active_profile"]["palm_scale"], 0.304, places=3)
        self.assertEqual(data2["active_profile"]["total_sessions"], 2)

    def test_legacy_flat_json_migration(self):
        # Write flat legacy json
        legacy_data = {
            "palm_scale": 0.26,
            "pinch_enter_ratio": 0.35,
            "pinch_exit_ratio": 0.48,
            "tremor_noise_px": 2.0,
            "calibrated_at": "2026-09-20 12:00:00"
        }
        with open(self.temp_file.name, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        cfg = ConfigManager()
        loaded = cfg.calibration
        self.assertIn("active_profile", loaded)
        self.assertIn("sessions", loaded)
        self.assertEqual(len(loaded["sessions"]), 1)
        self.assertEqual(loaded["sessions"][0]["palm_scale"], 0.26)

    def test_per_gesture_profile_persistence(self):
        cfg = ConfigManager()
        gesture_data = {
            "OPEN_PALM": {"palm_scale": 0.31, "finger_straightness_cosine": 0.88},
            "POINTING": {"pointing_index_wrist_ratio": 1.45},
            "PINCH": {"contact_pinch_ratio": 0.22, "calibrated_pinch_enter": 0.32},
            "TWO_FINGERS": {"two_finger_separation_ratio": 0.35},
            "BIMANUAL_SELECT": {"left_contact_ratio": 0.25, "left_pinch_enter": 0.34}
        }
        session_data = {
            "palm_scale": 0.31,
            "pinch_enter_ratio": 0.32,
            "pinch_exit_ratio": 0.46,
            "left_pinch_enter_ratio": 0.34,
            "left_pinch_exit_ratio": 0.48,
            "gestures": gesture_data,
            "calibrated_at": "2026-09-27 12:00:00"
        }
        cfg.save_calibration(session_data)

        self.assertIn("gestures", cfg.calibration["active_profile"])
        self.assertEqual(cfg.gestures_profile["PINCH"]["contact_pinch_ratio"], 0.22)
        self.assertEqual(cfg.left_pinch_enter_ratio, 0.34)
        self.assertEqual(cfg.left_pinch_exit_ratio, 0.48)

    def test_backup_file_created(self):
        cfg = ConfigManager()
        session_data = {
            "palm_scale": 0.29,
            "pinch_enter_ratio": 0.35,
            "pinch_exit_ratio": 0.49,
            "calibrated_at": "2026-09-27 12:00:00"
        }
        cfg.save_calibration(session_data)

        # Assert backup file exists and matches data
        self.assertTrue(os.path.exists(self.backup_file.name))
        with open(self.backup_file.name, "r", encoding="utf-8") as f_bak:
            backup_data = json.load(f_bak)
        self.assertEqual(len(backup_data["sessions"]), 1)
        self.assertEqual(backup_data["active_profile"]["palm_scale"], 0.29)


if __name__ == "__main__":
    unittest.main()
