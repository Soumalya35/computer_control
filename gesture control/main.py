"""
Main Orchestration Module for Vision-Based Gesture Control System
Orchestrates Camera, Multi-Hand Tracking, Bimanual Coordination, Kinematics,
State Machine, Win32 Automation, Multi-Session Calibration, and Interactive In-Window Mode Control.
"""

import time
import cv2

from config import config
from vision.camera import CameraManager
from vision.hand_tracker import HandTracker
from vision.hand_association import HandAssociationTracker
from kinematics.features import extract_features
from kinematics.confidence import ConfidenceEngine
from gestures.classifier import GestureClassifier
from gestures.stabilizer import TemporalStabilizer
from gestures.state_machine import GestureStateMachine
from system.win32_input import Win32InputBackend
from system.safety import SafetyManager
from system.hotkeys import HotkeyManager
from control.cursor import CursorController
from control.scrolling import ScrollController
from control.drag import DragController
from control.dispatcher import CommandDispatcher
from control.bimanual import BimanualController
from calibration.calibrator import Calibrator
from telemetry.profiler import SystemProfiler
from ui.hud import HUDManager


def main():
    print("==========================================================")
    print("  Vision-Based Gesture Control for Computer Interaction   ")
    print("==========================================================")
    print("  Orchestration: Refactored Decoupled Pipeline")
    print("  Modes:         [O] Operation Mode | [C] Calibration Mode")
    print("  Bimanual:      Right Hand Steers Cursor | Left Hand Selects")
    print("                 - Left Pinch Tap:  Click to Select")
    print("                 - Left Pinch Hold: Drag / Text Selection")
    print("  Secondary:     Left 2-Fin: Next Tab | Left 3-Fin: Prev Tab")
    print("  Safety:        Closed Fist: Pause | Open Palm: Resume")
    print("  Hotkeys:       'o'=Operation | 'c'=Calibrate | ' '=Pause | ESC/q=Exit")
    print("==========================================================")

    # 1. Initialize Subsystems
    camera = CameraManager(
        device_index=config.tracking.get("camera", {}).get("device_index", 0),
        width=config.camera_width,
        height=config.camera_height,
        camera_fps=config.camera_fps,
        inference_fps=config.inference_fps
    )

    tracker = HandTracker(
        max_num_hands=config.tracking.get("mediapipe", {}).get("max_num_hands", 2),
        model_complexity=config.tracking.get("mediapipe", {}).get("model_complexity", 1),
        min_detection_confidence=config.tracking.get("mediapipe", {}).get("min_detection_confidence", 0.55),
        min_tracking_confidence=config.tracking.get("mediapipe", {}).get("min_tracking_confidence", 0.55)
    )

    association = HandAssociationTracker(
        primary_hand_preference="Right",
        lost_timeout_sec=0.60
    )

    confidence_engine = ConfidenceEngine(
        candidate_thresh=config.gestures.get("stabilization", {}).get("candidate_threshold", 0.60),
        action_thresh=config.confidence_threshold
    )

    classifier = GestureClassifier()

    primary_stabilizer = TemporalStabilizer(
        window_size=config.temporal_window,
        min_votes=config.temporal_votes,
        confidence_threshold=config.confidence_threshold
    )

    secondary_stabilizer = TemporalStabilizer(
        window_size=config.temporal_window,
        min_votes=config.temporal_votes,
        confidence_threshold=config.confidence_threshold
    )

    state_machine = GestureStateMachine(
        drag_hold_frames=config.tracking.get("kinematics", {}).get("drag_hold_frames", 7),
        drag_grace_frames=config.tracking.get("kinematics", {}).get("drag_grace_frames", 3)
    )

    # 2. Input & Control Subsystems
    backend = Win32InputBackend()
    safety = SafetyManager(backend, hand_loss_timeout_sec=config.system.get("safety", {}).get("hand_loss_timeout_sec", 1.0))
    hotkeys = HotkeyManager(backend)

    cursor = CursorController(
        screen_width=config.system.get("system", {}).get("screen_fallback_width", 1920),
        screen_height=config.system.get("system", {}).get("screen_fallback_height", 1080),
        margin_x=config.system.get("interaction_box", {}).get("margin_x", 60),
        margin_y=config.system.get("interaction_box", {}).get("margin_y", 45),
        cam_width=config.camera_width,
        cam_height=config.camera_height,
        alpha_slow=config.system.get("adaptive_ema", {}).get("alpha_slow", 0.20),
        alpha_fast=config.system.get("adaptive_ema", {}).get("alpha_fast", 0.65),
        v_slow=config.system.get("adaptive_ema", {}).get("v_slow", 5.0),
        v_fast=config.system.get("adaptive_ema", {}).get("v_fast", 25.0)
    )

    scroll = ScrollController(
        cam_height=config.camera_height,
        scroll_gain=config.system.get("scrolling", {}).get("scroll_gain", 0.22),
        smooth_factor=config.system.get("scrolling", {}).get("smooth_factor", 0.65),
        inertia_decay=config.system.get("scrolling", {}).get("inertia_decay", 0.75),
        min_velocity=config.system.get("scrolling", {}).get("min_velocity", 0.60)
    )

    drag = DragController(backend)
    dispatcher = CommandDispatcher(backend, cursor, scroll, drag, hotkeys)
    bimanual = BimanualController(
        backend=backend,
        drag=drag,
        drag_hold_frames=config.tracking.get("kinematics", {}).get("bimanual_tap_hold_frames", 15),
        displacement_threshold=config.tracking.get("kinematics", {}).get("bimanual_drag_displacement", 0.035),
        pinch_enter_ratio=config.left_pinch_enter_ratio,
        pinch_exit_ratio=config.left_pinch_exit_ratio
    )

    # 3. Telemetry, UI & Calibration
    profiler = SystemProfiler(history_len=30)
    hud = HUDManager()
    calibrator = Calibrator()

    # Application Mode: "OPERATION" vs "CALIBRATION"
    app_mode = "OPERATION"

    # Mouse Click Callback for Mode Buttons
    def on_window_mouse(event, x, y, flags, param):
        nonlocal app_mode
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked_mode = hud.handle_mouse_click(x, y)
            if clicked_mode == "OPERATION":
                app_mode = "OPERATION"
                calibrator.stop()
                print("[MODE] Switched to LIVE OPERATION MODE")
            elif clicked_mode == "CALIBRATION":
                app_mode = "CALIBRATION"
                calibrator.start()
                print("[MODE] Switched to BIOMETRIC CALIBRATION MODE")

    window_name = "Vision-Based Gesture Control"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_window_mouse)

    if not camera.open():
        print("[ERROR] Could not open camera device. Please check connection.")
        return

    print("[SUCCESS] Pipeline initialized. Starting video loop...")

    try:
        while True:
            profiler.start_frame()

            # Stage 1: Camera Read & Mirrored Frame Grab
            success, frame, cap_ms = camera.read()
            profiler.record_stage("capture", cap_ms)
            if not success or frame is None:
                break

            # Stage 2: Hand Detection & Persistent Association
            parsed_hands, inf_ms = tracker.process(frame)
            profiler.record_stage("inference", inf_ms)

            active_tracks = association.update(parsed_hands)

            # Draw Hand Skeletons
            for track in active_tracks:
                tracker.draw_hand(frame, track.raw_landmarks)

            # Identify Right and Left Hands explicitly by anatomical handedness
            right_track = next((t for t in active_tracks if t.handedness == "Right"), None)
            left_track = next((t for t in active_tracks if t.handedness == "Left"), None)

            # Fallback: if single hand is in view and it's Left, allow cursor steering
            primary_track = right_track if right_track is not None else left_track
            secondary_track = left_track if right_track is not None else None

            right_action_str = "NONE"
            right_conf_val = 0.0
            left_action_str = "NONE"
            left_conf_val = 0.0
            is_inside_box = False

            # Stage 3: Feature Extraction
            t_feat0 = time.perf_counter()
            primary_features = None
            if primary_track is not None:
                safety.notify_hand_seen()
                primary_features = extract_features(
                    primary_track.landmarks,
                    pinch_enter_ratio=config.pinch_enter_ratio,
                    pinch_exit_ratio=config.pinch_exit_ratio
                )

                # Check if inside active interaction zone
                nx, ny = primary_features.index_pos_norm
                is_inside_box = (
                    cursor.norm_x_min <= nx <= cursor.norm_x_max and
                    cursor.norm_y_min <= ny <= cursor.norm_y_max
                )

                # Right Hand Pinch Feedback
                if primary_track.handedness == "Right":
                    hud.draw_pinch_feedback(
                        frame,
                        primary_features.thumb_pos_norm,
                        primary_features.index_pos_norm,
                        primary_features.is_pinch_enter,
                        primary_features.pinch_ratio,
                        label="Right Pinch"
                    )

            left_features = None
            if left_track is not None:
                left_features = extract_features(
                    left_track.landmarks,
                    pinch_enter_ratio=config.left_pinch_enter_ratio,
                    pinch_exit_ratio=config.left_pinch_exit_ratio
                )
                # Left Hand Pinch Feedback
                hud.draw_pinch_feedback(
                    frame,
                    left_features.thumb_pos_norm,
                    left_features.index_pos_norm,
                    left_features.is_pinch_enter,
                    left_features.pinch_ratio,
                    label="Left Pinch"
                )

            # Calibration Mode Execution: Route appropriate hand based on stage
            if app_mode == "CALIBRATION" and calibrator.is_active:
                calib_stage = calibrator.get_current_stage()
                if calib_stage == "BIMANUAL_SELECT":
                    calib_target = left_track if left_track is not None else (primary_track if primary_track and primary_track.handedness == "Left" else None)
                    calib_lbl = "Left"
                else:
                    calib_target = right_track if right_track is not None else (primary_track if primary_track and primary_track.handedness == "Right" else primary_track)
                    calib_lbl = "Right"

                if calib_target is not None:
                    done = calibrator.process_frame(calib_target.landmarks, calib_target.detection_confidence, hand_label=calib_lbl)
                    if done:
                        app_mode = "OPERATION"
                        print("[CALIBRATION] 12-gesture calibration complete! Switched to OPERATION MODE.")

            profiler.record_stage("features", (time.perf_counter() - t_feat0) * 1000.0)

            # Stage 4: Confidence Scoring & Gesture Classification
            t_cls0 = time.perf_counter()
            primary_candidate = None
            if primary_features is not None and primary_track is not None:
                conf_breakdown = confidence_engine.compute(
                    detection_score=primary_track.detection_confidence,
                    features=primary_features,
                    temporal_agreement=primary_stabilizer.get_voting_agreement()
                )
                p_conf = conf_breakdown.total
                if primary_track.handedness == "Right":
                    right_conf_val = p_conf
                else:
                    left_conf_val = p_conf

                primary_candidate = classifier.classify(
                    features=primary_features,
                    hand_role="PRIMARY" if primary_track.handedness == "Right" else "SECONDARY",
                    confidence=p_conf,
                    is_currently_pinching=state_machine.is_in_pinch_state()
                )

            secondary_candidate = None
            if secondary_track is not None and left_features is not None:
                sec_conf = confidence_engine.compute(secondary_track.detection_confidence, left_features).total
                left_conf_val = sec_conf
                secondary_candidate = classifier.classify(left_features, hand_role="SECONDARY", confidence=sec_conf)

            profiler.record_stage("classifier", (time.perf_counter() - t_cls0) * 1000.0)

            # Stage 5: Temporal Stabilization & State Machine
            t_stab0 = time.perf_counter()
            stable_primary = primary_stabilizer.update(primary_candidate)
            stable_secondary = secondary_stabilizer.update(secondary_candidate)

            state_out = state_machine.update(
                stabilized_gesture=stable_primary,
                features=primary_features,
                hand_present=(primary_track is not None)
            )
            profiler.record_stage("stabilizer", (time.perf_counter() - t_stab0) * 1000.0)

            # Stage 6: Bimanual Selection & Command Dispatching
            t_disp0 = time.perf_counter()
            cur_norm = primary_features.index_pos_norm if primary_features is not None else (0.5, 0.5)
            bimanual_state = bimanual.update(
                left_features=left_features,
                left_track_present=(left_track is not None),
                right_track_present=(right_track is not None),
                current_cursor_pos=(cursor.filtered_x, cursor.filtered_y),
                current_norm_pos=cur_norm
            )

            # Trigger visual ripple on HUD if a click event occurred
            if bimanual_state.click_event:
                h_f, w_f, _ = frame.shape
                ripple_x = int(cur_norm[0] * w_f)
                ripple_y = int(cur_norm[1] * h_f)
                hud.trigger_click_ripple(ripple_x, ripple_y, bimanual_state.click_event)

            # Dispatch OS commands ONLY in OPERATION mode
            telemetry_dragging = False
            telemetry_paused = state_machine.is_paused
            if app_mode == "OPERATION":
                telemetry = dispatcher.dispatch(state_out)
                telemetry_dragging = telemetry.is_dragging or bimanual_state.is_selecting
                telemetry_paused = telemetry.is_paused

                # Secondary hand discrete hotkeys (e.g. Next Tab / Prev Tab)
                if stable_secondary and stable_secondary.action in ("NEXT_TAB", "PREVIOUS_TAB"):
                    hotkeys.dispatch(stable_secondary.action)
            else:
                # In CALIBRATION mode, suppress cursor moves
                pass

            profiler.record_stage("dispatch", (time.perf_counter() - t_disp0) * 1000.0)

            # Check Safety Timeout
            safety.check_hand_loss_timeout()

            # Finalize Profiler Metrics
            profiler.end_frame()
            metrics = profiler.get_metrics()

            # Update Action Display Labels
            if right_track is not None:
                if stable_primary and primary_track == right_track:
                    right_action_str = stable_primary.action
                elif primary_candidate and primary_track == right_track:
                    right_action_str = primary_candidate.name

            if left_track is not None:
                if bimanual_state.action_name != "IDLE":
                    left_action_str = bimanual_state.action_name
                elif stable_secondary:
                    left_action_str = stable_secondary.action
                elif secondary_candidate:
                    left_action_str = secondary_candidate.name
                elif primary_track == left_track and stable_primary:
                    left_action_str = stable_primary.action

            # UI Overlays
            hud.draw_interaction_box(
                frame,
                margin_x=config.system.get("interaction_box", {}).get("margin_x", 60),
                margin_y=config.system.get("interaction_box", {}).get("margin_y", 45),
                is_inside=is_inside_box
            )

            calib_fraction, _, _ = calibrator.get_stage_progress() if app_mode == "CALIBRATION" else (0.0, 0, 0)
            hud.draw_hud(
                frame=frame,
                mode=app_mode,
                right_hand_action=right_action_str,
                right_confidence=right_conf_val,
                left_hand_action=left_action_str,
                left_confidence=left_conf_val,
                bimanual_status=bimanual_state.action_name,
                is_paused=telemetry_paused,
                is_dragging=telemetry_dragging,
                metrics=metrics,
                calibrating_text=calibrator.get_instructions() if app_mode == "CALIBRATION" else None,
                calib_progress=calib_fraction
            )

            cv2.imshow(window_name, frame)

            # Keyboard commands
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):  # ESC or q
                safety.trigger_emergency_stop()
                break
            elif key in (ord('c'), ord('C')):
                app_mode = "CALIBRATION"
                calibrator.start()
                print("[MODE] Switched to CALIBRATION MODE ('c' pressed)")
            elif key in (ord('o'), ord('O')):
                app_mode = "OPERATION"
                calibrator.stop()
                print("[MODE] Switched to OPERATION MODE ('o' pressed)")
            elif key in (ord('n'), ord('N')):
                if app_mode == "CALIBRATION":
                    calibrator.next_stage()
                    print(f"[CALIBRATION] Advanced to next stage: {calibrator.get_current_stage()} ('n' pressed)")
            elif key in (ord('b'), ord('B')):
                if app_mode == "CALIBRATION":
                    calibrator.prev_stage()
                    print(f"[CALIBRATION] Reverted to previous stage: {calibrator.get_current_stage()} ('b' pressed)")
            elif key == ord(' '):  # Spacebar to pause / resume
                state_machine.is_paused = not state_machine.is_paused
                print(f"[SYSTEM] System Paused: {state_machine.is_paused}")

    finally:
        safety.cleanup_on_exit()
        camera.release()
        print("\n" + "="*50)
        print("  Final Runtime Telemetry Benchmark Summary:")
        print("="*50)
        print(profiler.format_summary())
        print("="*50)


if __name__ == "__main__":
    main()