"""
Camera Manager Module
Manages camera capture lifecycle, horizontal frame mirroring, hardware timestamping,
and decoupled inference rate scheduling.
"""

import time
import cv2
from typing import Tuple, Optional


class CameraManager:
    """Manages OpenCV webcam video capture, frame timestamps, and inference scheduling."""

    def __init__(
        self,
        device_index: int = 0,
        width: int = 1280,
        height: int = 720,
        camera_fps: int = 60,
        inference_fps: int = 30,
        mirror_horizontal: bool = True
    ):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.camera_fps = camera_fps
        self.inference_fps = inference_fps
        self.mirror_horizontal = mirror_horizontal

        self.cap: Optional[cv2.VideoCapture] = None
        self.last_inference_time = 0.0
        self.inference_interval = 1.0 / max(1, inference_fps)

        self.last_capture_duration_ms = 0.0
        self.frame_timestamp = 0.0

    def open(self) -> bool:
        """Opens camera once with requested resolution."""
        if self.cap is not None and self.cap.isOpened():
            return True

        self.cap = cv2.VideoCapture(self.device_index)
        # Request MJPG format to bypass USB 2.0 uncompressed bandwidth limits
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.camera_fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        success, _ = self.cap.read()
        return success

    def read(self) -> Tuple[bool, Optional[any], float]:
        """
        Reads a frame from the camera, mirrors horizontally, and records timing.
        Returns: (success: bool, frame: np.ndarray, capture_ms: float)
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None, 0.0

        t0 = time.perf_counter()
        success, frame = self.cap.read()
        t1 = time.perf_counter()

        self.last_capture_duration_ms = (t1 - t0) * 1000.0
        self.frame_timestamp = time.time()

        if not success or frame is None:
            return False, None, self.last_capture_duration_ms

        if self.mirror_horizontal:
            frame = cv2.flip(frame, 1)

        return True, frame, self.last_capture_duration_ms

    def should_run_inference(self) -> bool:
        """
        Decouples camera capture rate from inference rate.
        Returns True if enough time has passed since last MediaPipe inference run.
        """
        now = time.time()
        if (now - self.last_inference_time) >= self.inference_interval:
            self.last_inference_time = now
            return True
        return False

    def release(self):
        """Cleanly releases camera device."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
