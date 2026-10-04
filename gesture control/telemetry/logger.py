"""
Telemetry Logger Module
Provides structured diagnostic logging for gesture transitions, safety events, and dropped frames.
"""

import time
import logging


def get_telemetry_logger(name: str = "GestureControl") -> logging.Logger:
    """Configures and returns a structured diagnostics logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s %(asctime)s] %(message)s", datefmt="%H:%M:%S")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger
