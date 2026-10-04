"""
Configuration Loader Module
Loads, validates, and centralizes all settings from YAML configuration files.
Provides fallback defaults and loads personalized user calibration profiles.
"""

import os
import json
import yaml


CONFIG_DIR = os.path.dirname(__file__)
TRACKING_YAML = os.path.join(CONFIG_DIR, "tracking.yaml")
GESTURES_YAML = os.path.join(CONFIG_DIR, "gestures.yaml")
SYSTEM_YAML = os.path.join(CONFIG_DIR, "system.yaml")
CALIBRATION_JSON = os.path.join(CONFIG_DIR, "calibration.json")
CALIBRATION_BACKUP_JSON = os.path.join(CONFIG_DIR, "calibration_backup.json")


def _load_yaml(filepath, default_dict):
    """Safely loads a YAML file, falling back to default_dict on failure."""
    if not os.path.exists(filepath):
        return default_dict
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else default_dict
    except Exception as e:
        print(f"[Config Warning] Failed to load {filepath}: {e}. Using defaults.")
        return default_dict


class ConfigManager:
    """Centralized configuration manager providing validated runtime parameters."""

    def __init__(self):
        self.tracking = _load_yaml(TRACKING_YAML, {})
        self.gestures = _load_yaml(GESTURES_YAML, {})
        self.system = _load_yaml(SYSTEM_YAML, {})
        self.calibration = self._load_calibration()

    def _load_calibration(self):
        """Loads optional user calibration data with multi-session history support."""
        if os.path.exists(CALIBRATION_JSON):
            try:
                if os.path.getsize(CALIBRATION_JSON) == 0:
                    return {}
                with open(CALIBRATION_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        return {}
                    # If already structured with sessions and active_profile
                    if "sessions" in data and "active_profile" in data:
                        return data
                    # Legacy flat format migration: preserve old record as session 1
                    if data:
                        legacy_record = dict(data)
                        legacy_record["session_id"] = 1
                        return {
                            "active_profile": dict(data),
                            "sessions": [legacy_record]
                        }
            except Exception as e:
                print(f"[Config Warning] Failed to load {CALIBRATION_JSON}: {e}")
        return {}

    def save_calibration(self, new_session_data):
        """
        Saves user calibration data cumulatively and atomically without overwriting previous sessions.
        Maintains complete history, per-gesture profiles, and automatically writes a backup copy.
        """
        try:
            current = self._load_calibration()
            sessions = list(current.get("sessions", []))
            
            new_session_data["session_id"] = len(sessions) + 1
            sessions.append(new_session_data)

            # Compute aggregated active profile from history (weighted towards latest)
            # Latest session weight: 0.60, prior history average: 0.40
            if len(sessions) == 1:
                active_profile = dict(new_session_data)
            else:
                prev_palms = [s.get("palm_scale", 0.30) for s in sessions[:-1] if "palm_scale" in s]
                prev_enter = [s.get("pinch_enter_ratio", 0.38) for s in sessions[:-1] if "pinch_enter_ratio" in s]
                prev_exit = [s.get("pinch_exit_ratio", 0.52) for s in sessions[:-1] if "pinch_exit_ratio" in s]
                prev_noise = [s.get("tremor_noise_px", 2.0) for s in sessions[:-1] if "tremor_noise_px" in s]

                avg_palm = sum(prev_palms) / max(1, len(prev_palms))
                avg_enter = sum(prev_enter) / max(1, len(prev_enter))
                avg_exit = sum(prev_exit) / max(1, len(prev_exit))
                avg_noise = sum(prev_noise) / max(1, len(prev_noise))

                active_profile = {
                    "palm_scale": round(0.40 * avg_palm + 0.60 * new_session_data.get("palm_scale", avg_palm), 4),
                    "pinch_enter_ratio": round(0.40 * avg_enter + 0.60 * new_session_data.get("pinch_enter_ratio", avg_enter), 3),
                    "pinch_exit_ratio": round(0.40 * avg_exit + 0.60 * new_session_data.get("pinch_exit_ratio", avg_exit), 3),
                    "tremor_noise_px": round(0.40 * avg_noise + 0.60 * new_session_data.get("tremor_noise_px", avg_noise), 3),
                    "left_pinch_enter_ratio": new_session_data.get("left_pinch_enter_ratio", 0.36),
                    "left_pinch_exit_ratio": new_session_data.get("left_pinch_exit_ratio", 0.50),
                    "finger_extension_ratio": new_session_data.get("finger_extension_ratio", 1.25),
                    "finger_straightness_cosine": new_session_data.get("finger_straightness_cosine", 0.60),
                    "two_finger_separation_ratio": new_session_data.get("two_finger_separation_ratio", 0.38),
                    "total_sessions": len(sessions),
                    "last_calibrated_at": new_session_data.get("calibrated_at", "")
                }

                # Preserve full per-gesture calibrated profiles
                if "gestures" in new_session_data:
                    active_profile["gestures"] = new_session_data["gestures"]

            full_payload = {
                "active_profile": active_profile,
                "sessions": sessions
            }

            # Atomic save: write to temporary file first, then replace
            temp_file = CALIBRATION_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(full_payload, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, CALIBRATION_JSON)

            # Automated backup creation
            try:
                with open(CALIBRATION_BACKUP_JSON, "w", encoding="utf-8") as f_bak:
                    json.dump(full_payload, f_bak, indent=2, ensure_ascii=False)
            except Exception as e_bak:
                print(f"[Config Warning] Could not write calibration backup: {e_bak}")

            self.calibration = full_payload
            print(f"[CALIBRATION] Cumulative profile saved atomically. Total history sessions: {len(sessions)}")
            return True
        except Exception as e:
            print(f"[Config Error] Failed to save cumulative calibration: {e}")
            return False

    # Convenience properties
    @property
    def camera_width(self):
        return self.tracking.get("camera", {}).get("capture_width", 1280)

    @property
    def camera_height(self):
        return self.tracking.get("camera", {}).get("capture_height", 720)

    @property
    def camera_fps(self):
        return self.tracking.get("camera", {}).get("camera_fps", 60)

    @property
    def inference_fps(self):
        return self.tracking.get("camera", {}).get("inference_fps", 30)

    @property
    def pinch_enter_ratio(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "pinch_enter_ratio" in active:
            return active["pinch_enter_ratio"]
        return self.tracking.get("kinematics", {}).get("pinch_enter_ratio", 0.38)

    @property
    def pinch_exit_ratio(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "pinch_exit_ratio" in active:
            return active["pinch_exit_ratio"]
        return self.tracking.get("kinematics", {}).get("pinch_exit_ratio", 0.52)

    @property
    def left_pinch_enter_ratio(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "left_pinch_enter_ratio" in active:
            return active["left_pinch_enter_ratio"]
        return 0.36

    @property
    def left_pinch_exit_ratio(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "left_pinch_exit_ratio" in active:
            return active["left_pinch_exit_ratio"]
        return 0.50

    @property
    def gestures_profile(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "gestures" in active:
            return active["gestures"]
        return {}

    @property
    def palm_scale(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "palm_scale" in active:
            return active["palm_scale"]
        return 0.30

    @property
    def tremor_noise_px(self):
        active = self.calibration.get("active_profile", self.calibration)
        if isinstance(active, dict) and "tremor_noise_px" in active:
            return active["tremor_noise_px"]
        return 2.0

    @property
    def temporal_window(self):
        return self.gestures.get("stabilization", {}).get("temporal_window", 5)

    @property
    def temporal_votes(self):
        return self.gestures.get("stabilization", {}).get("temporal_votes", 3)

    @property
    def confidence_threshold(self):
        return self.gestures.get("stabilization", {}).get("confidence_threshold", 0.65)


# Global singleton instance
config = ConfigManager()
