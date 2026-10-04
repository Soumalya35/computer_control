"""
Telemetry Profiler Module
Measures stage-by-stage execution latency, frame rate, CPU load, and memory usage.
"""

import time
import os
from collections import deque
from typing import Dict

try:
    import psutil
    _PROCESS = psutil.Process(os.getpid())
except Exception:
    _PROCESS = None


class SystemProfiler:
    """Accurately benchmarks latency across the 6-stage gesture control pipeline."""

    def __init__(self, history_len: int = 30):
        self.history_len = history_len

        # Stage latency buffers (ms)
        self.capture_times = deque(maxlen=history_len)
        self.inference_times = deque(maxlen=history_len)
        self.feature_times = deque(maxlen=history_len)
        self.classifier_times = deque(maxlen=history_len)
        self.stabilizer_times = deque(maxlen=history_len)
        self.dispatch_times = deque(maxlen=history_len)
        self.total_times = deque(maxlen=history_len)

        self.last_frame_start = time.perf_counter()
        self.frame_intervals = deque(maxlen=history_len)

        # Temporary timing holders for current frame
        self._current_timings = {}

    def start_frame(self):
        """Marks beginning of frame pipeline."""
        now = time.perf_counter()
        interval = now - self.last_frame_start
        if interval > 0:
            self.frame_intervals.append(interval)
        self.last_frame_start = now
        self._current_timings = {}

    def record_stage(self, stage_name: str, duration_ms: float):
        """Records the latency in milliseconds for an individual processing stage."""
        self._current_timings[stage_name] = duration_ms

    def end_frame(self):
        """Finalizes per-frame metrics and records to history buffers."""
        t_cap = self._current_timings.get("capture", 0.0)
        t_inf = self._current_timings.get("inference", 0.0)
        t_feat = self._current_timings.get("features", 0.0)
        t_cls = self._current_timings.get("classifier", 0.0)
        t_stab = self._current_timings.get("stabilizer", 0.0)
        t_disp = self._current_timings.get("dispatch", 0.0)

        total = t_cap + t_inf + t_feat + t_cls + t_stab + t_disp

        self.capture_times.append(t_cap)
        self.inference_times.append(t_inf)
        self.feature_times.append(t_feat)
        self.classifier_times.append(t_cls)
        self.stabilizer_times.append(t_stab)
        self.dispatch_times.append(t_disp)
        self.total_times.append(total)

    def _mean(self, buffer: deque) -> float:
        return sum(buffer) / len(buffer) if buffer else 0.0

    def get_metrics(self) -> Dict[str, float]:
        """Returns averaged latency metrics across recent frames."""
        avg_fps = (
            len(self.frame_intervals) / sum(self.frame_intervals)
            if self.frame_intervals and sum(self.frame_intervals) > 0 else 0.0
        )

        cpu_pct = 0.0
        memory_mb = 0.0
        if _PROCESS:
            try:
                cpu_pct = _PROCESS.cpu_percent()
                memory_mb = _PROCESS.memory_info().rss / (1024.0 * 1024.0)
            except Exception:
                pass

        return {
            "fps": round(avg_fps, 1),
            "capture_ms": round(self._mean(self.capture_times), 2),
            "inference_ms": round(self._mean(self.inference_times), 2),
            "features_ms": round(self._mean(self.feature_times), 2),
            "classifier_ms": round(self._mean(self.classifier_times), 2),
            "stabilizer_ms": round(self._mean(self.stabilizer_times), 2),
            "dispatch_ms": round(self._mean(self.dispatch_times), 2),
            "total_ms": round(self._mean(self.total_times), 2),
            "cpu_pct": round(cpu_pct, 1),
            "memory_mb": round(memory_mb, 1)
        }

    def format_summary(self) -> str:
        """
        Formats metrics into the exact report specification from the manual.
        """
        m = self.get_metrics()
        return (
            f"FPS:        {m['fps']}\n"
            f"Capture:    {m['capture_ms']} ms\n"
            f"Inference:  {m['inference_ms']} ms\n"
            f"Features:   {m['features_ms']} ms\n"
            f"Classifier: {m['classifier_ms']} ms\n"
            f"Stabilizer: {m['stabilizer_ms']} ms\n"
            f"Dispatch:   {m['dispatch_ms']} ms\n"
            f"Total:      {m['total_ms']} ms\n"
            f"CPU:        {m['cpu_pct']}%\n"
            f"Memory:     {m['memory_mb']} MB"
        )
