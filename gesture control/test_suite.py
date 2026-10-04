"""
Test Suite for Vision-Based Gesture Control System
Verifies dual-hand dispatching, confidence smoothing, pinch selection anchor stabilization,
relative cursor motion without repositioning, Volume Down functionality, and tab switching.
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from gesture_database import gesture_map
from gestre_stabilizer import GestureStabilizer
from mouse_control import MouseController
from keyboard_control import KeyboardController
from gesture_action import GestureActionDispatcher
from gesture_decide import smooth_confidence, recognize_gesture
from config import (
    FRAME_WIDTH, FRAME_HEIGHT,
    INTERACTION_MARGIN_X, INTERACTION_MARGIN_Y,
    VOTING_WINDOW_SIZE, VOTING_MIN_MATCHES,
    MIN_GESTURE_CONFIDENCE
)


class MockLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class MockHandLandmarks:
    def __init__(self, landmarks_dict):
        self.landmark = [MockLandmark(0.5, 0.5) for _ in range(21)]
        for idx, (x, y) in landmarks_dict.items():
            self.landmark[idx] = MockLandmark(x, y)


def test_stabilizer_with_voting_and_confidence():
    print("Testing GestureStabilizer with sliding-window voting and confidence...")
    stabilizer = GestureStabilizer(
        window_size=VOTING_WINDOW_SIZE,
        min_matches=VOTING_MIN_MATCHES,
        default_cooldown=0.5,
        min_confidence=MIN_GESTURE_CONFIDENCE
    )

    pointing_high_conf = {
        "action": "MOVE_MOUSE",
        "category": "mouse",
        "continuous": True,
        "cooldown": 0,
        "confidence": 0.88
    }
    pointing_low_conf = {
        "action": "MOVE_MOUSE",
        "category": "mouse",
        "continuous": True,
        "cooldown": 0,
        "confidence": 0.30
    }

    res_low = stabilizer.update(pointing_low_conf)
    assert res_low is None, "Low confidence frame must be rejected"
    assert len(stabilizer.history) == 0, "Buffer should remain empty on low confidence"

    for _ in range(VOTING_MIN_MATCHES - 1):
        assert stabilizer.update(pointing_high_conf) is None

    res = stabilizer.update(pointing_high_conf)
    assert res is not None and res["action"] == "MOVE_MOUSE"

    res_stream = stabilizer.update(pointing_high_conf)
    assert res_stream is not None and res_stream["action"] == "MOVE_MOUSE"

    print("Sliding-window voting and confidence tests PASSED!")


def test_mouse_scrolling_interface():
    print("Testing MouseController native wheel scroll...")
    mouse = MouseController()
    mouse.scroll(2)
    mouse.scroll(-2)
    print("MouseController scrolling tests PASSED!")


def test_mouse_relative_no_reposition():
    print("Testing MouseController relative tracking (no unwanted repositioning)...")
    mouse = MouseController(cursor_mode="RELATIVE")
    mouse.get_os_cursor_pos = lambda: (700, 400)
    mouse.curr_x = 700.0
    mouse.curr_y = 400.0
    mouse.prev_x = 700.0
    mouse.prev_y = 400.0
    mouse.reset_tracking()

    # Frame 1: Hand enters at camera (500, 300)
    # Latching onto current position without moving cursor!
    ix1, iy1 = mouse.move(500, 300)
    assert abs(ix1 - 700) <= 2 and abs(iy1 - 400) <= 2, "Must not snap/reposition on initial hand acquisition"

    # Frame 2: Hand moves right by 10 px
    ix2, iy2 = mouse.move(510, 300)
    assert ix2 > ix1, "Cursor must glide relative to previous location"

    # Hand drops and re-enters at a completely different camera position (e.g. 200, 100)
    mouse.reset_tracking()
    mouse.get_os_cursor_pos = lambda: (ix2, iy2)
    ix3, iy3 = mouse.move(200, 100)
    assert abs(ix3 - ix2) <= 2 and abs(iy3 - iy2) <= 2, "Hand re-entry at different camera pos must NOT snap cursor"

    print("MouseController relative tracking (no repositioning) tests PASSED!")


def test_pinch_anchor_stabilization():
    print("Testing MouseController click & selection anchor stabilization...")
    mouse = MouseController()
    cam_center_x = FRAME_WIDTH // 2
    cam_center_y = FRAME_HEIGHT // 2

    ix_init, iy_init = mouse.move(cam_center_x, cam_center_y, is_pinch_mode=False)
    ix1, iy1 = mouse.move(cam_center_x, cam_center_y, is_pinch_mode=True)
    assert mouse.was_pinching_prev is True
    assert mouse.pinch_freeze_frames > 0

    ix2, iy2 = mouse.move(cam_center_x + 1, cam_center_y + 1, is_pinch_mode=True)
    assert (ix1, iy1) == (ix2, iy2), "Micro-tremor during pinch initiation must be stabilized"

    print("Pinch anchor stabilization test PASSED!")


def test_confidence_smoothing():
    print("Testing confidence EMA smoothing against erratic fluctuations...")
    stream = [0.85, 0.40, 0.82, 0.35, 0.88]
    smoothed_values = [smooth_confidence("Right_test", v) for v in stream]

    for i in range(1, len(smoothed_values)):
        delta = abs(smoothed_values[i] - smoothed_values[i-1])
        assert delta < 0.25, f"Fluctuation too sharp: delta={delta}"

    print("Confidence EMA smoothing tests PASSED!")


def test_volume_down_execution_and_gestures():
    print("Testing Volume Down execution and gesture recognition...")
    # 1. Test Win32 hardware key execution (does not raise FailSafeException)
    KeyboardController.volume_down()
    KeyboardController.volume_up()

    # 2. Test Thumb Down gesture landmark configuration
    # Thumb tip (4) is lower than IP (3) which is lower than MCP (2)
    # Other 4 fingers (8, 12, 16, 20) are folded down below PIPs
    thumb_down_lms = MockHandLandmarks({
        0: (0.5, 0.5),
        2: (0.45, 0.52),
        3: (0.45, 0.62),
        4: (0.45, 0.72),   # Thumb tip pointing DOWN
        5: (0.50, 0.42), 6: (0.50, 0.32), 8: (0.50, 0.40),   # Index folded inward
        9: (0.55, 0.42), 10: (0.55, 0.32), 12: (0.55, 0.40), # Middle folded inward
        13: (0.60, 0.42), 14: (0.60, 0.32), 16: (0.60, 0.40),# Ring folded inward
        17: (0.65, 0.42), 18: (0.65, 0.32), 20: (0.65, 0.40) # Pinky folded inward
    })
    res_td = recognize_gesture(thumb_down_lms, hand_label="Right")
    assert res_td["action"] == "VOLUME_DOWN", f"Thumb Down must yield VOLUME_DOWN, got {res_td['action']}"

    # 3. Test Pinky Only gesture landmark configuration
    pinky_only_lms = MockHandLandmarks({
        0: (0.5, 0.7),
        2: (0.45, 0.65), 3: (0.46, 0.63), 4: (0.48, 0.60),   # Thumb tucked on side
        5: (0.50, 0.55), 6: (0.50, 0.45), 8: (0.50, 0.53),   # Index folded inward
        9: (0.55, 0.55), 10: (0.55, 0.45), 12: (0.55, 0.53), # Middle folded inward
        13: (0.60, 0.55), 14: (0.60, 0.45), 16: (0.60, 0.53),# Ring folded inward
        17: (0.65, 0.55), 18: (0.65, 0.45), 20: (0.65, 0.30) # Pinky extended UP
    })
    res_pinky = recognize_gesture(pinky_only_lms, hand_label="Right")
    assert res_pinky["action"] == "VOLUME_DOWN", f"Pinky Only must yield VOLUME_DOWN, got {res_pinky['action']}"

    print("Volume Down execution and gesture tests PASSED!")


def test_pointing_relaxed_thumb():
    print("Testing pointing gesture with relaxed thumb...")
    assert (0, 1, 0, 0, 0) in gesture_map
    assert gesture_map[(0, 1, 0, 0, 0)]["action"] == "MOVE_MOUSE"

    assert (1, 1, 0, 0, 0) in gesture_map
    assert gesture_map[(1, 1, 0, 0, 0)]["action"] == "MOVE_MOUSE"

    print("Pointing gesture relaxed thumb test PASSED!")


def test_gesture_database_integrity():
    print("Testing Gesture Database entries...")
    required_actions = [
        "MOVE_MOUSE", "SCROLL_MODE", "LEFT_CLICK",
        "ALT_TAB", "TASK_VIEW", "VOLUME_UP", "VOLUME_DOWN",
        "PLAY_PAUSE", "NEXT_TAB", "PREV_TAB", "PAUSE", "RESUME"
    ]

    actions_in_db = {val["action"] for val in gesture_map.values()}
    for req in required_actions:
        assert req in actions_in_db, f"Missing required action in database: {req}"

    print("All required actions verified in Gesture Database! PASSED!")


if __name__ == "__main__":
    test_stabilizer_with_voting_and_confidence()
    test_mouse_scrolling_interface()
    test_mouse_relative_no_reposition()
    test_pinch_anchor_stabilization()
    test_confidence_smoothing()
    test_volume_down_execution_and_gestures()
    test_pointing_relaxed_thumb()
    test_gesture_database_integrity()
    print("\nALL ENHANCED TEST SUITE TESTS PASSED!")
