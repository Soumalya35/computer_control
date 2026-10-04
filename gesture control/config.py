"""
Configuration Module for Vision-Based Gesture Control System
Defines all tunable parameters for camera capture, dual-hand tracking, gesture recognition,
relative/absolute cursor motion, selection stabilization, tab switching, and HUD display.
"""

import pyautogui

# -----------------------------
# CAMERA SETTINGS
# -----------------------------
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# -----------------------------
# SCREEN RESOLUTION
# -----------------------------
try:
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

# -----------------------------
# MEDIAPIPE SETTINGS (DUAL HAND SUPPORT)
# -----------------------------
MAX_HANDS = 2
MODEL_COMPLEXITY = 1
MIN_DETECTION_CONFIDENCE = 0.65
MIN_TRACKING_CONFIDENCE = 0.65

# Minimum gesture confidence required to accept a detection (0.0 to 1.0)
MIN_GESTURE_CONFIDENCE = 0.50
# Exponential Moving Average factor to stabilize confidence readout (prevents HUD flicker)
CONFIDENCE_SMOOTH_FACTOR = 0.75

# -----------------------------
# CURSOR TRACKING MODE (ELIMINATES UNWANTED REPOSITIONING)
# -----------------------------
# "RELATIVE" (Recommended): Trackpad-like relative motion from current cursor location.
# Cursor stays wherever you left it and never jumps or snaps when hand is raised/dropped.
# "ABSOLUTE": Maps camera frame directly to screen dimensions.
CURSOR_MODE = "RELATIVE"

# Sensitivity multipliers for relative cursor motion
MOUSE_SENSITIVITY_X = 1.80
MOUSE_SENSITIVITY_Y = 1.80
# Sub-pixel motion deadzone to eliminate microscopic camera sensor jitter
MOUSE_DEADZONE = 1.2

# -----------------------------
# INTERACTION & MOUSE SETTINGS (EXPANDED INPUT AREA)
# -----------------------------
# Margins inside camera frame for absolute mapping (>90% active camera area)
INTERACTION_MARGIN_X = 65
INTERACTION_MARGIN_Y = 45

# Adaptive smoothing bounds (Lower = responsive at high speeds; Higher = stable at low speeds)
SMOOTH_FAST = 1.8      # Smoothing factor when moving quickly (near-zero latency)
SMOOTH_SLOW = 4.5      # Smoothing factor when moving slowly or hovering (zero tremor)
SMOOTH_VEL_THRESH = 20 # Pixel velocity threshold to switch between slow/fast smoothing

SMOOTHENING = 3.5      # Baseline smoothing fallback
SAFE_MARGIN = 60

# -----------------------------
# PINCH, CLICK & SELECTION STABILITY SETTINGS
# -----------------------------
# Dynamic depth-adaptive pinch ratio (fraction of biometric palm length)
PINCH_PALM_RATIO = 0.38
# Fallback pixel distance thresholds if palm scale unavailable
PINCH_ENTER_DIST = 42
PINCH_EXIT_DIST = 62
PINCH_DIST_THRESHOLD = 42

# Frames of contact where cursor is held stationary so clicking small buttons/text does not drift
CLICK_STABILIZE_FRAMES = 4
CLICK_STABILIZE_RADIUS = 16

# Consecutive pinch frames required to transition into active Drag & Drop text selection
PINCH_HOLD_DRAG_FRAMES = 3
# Number of grace frames allowed if pinch distance briefly spikes during an active drag
DRAG_RELEASE_GRACE_FRAMES = 3

# -----------------------------
# DUAL-HAND INTERACTION SETTINGS
# -----------------------------
TWO_HAND_MODE_ENABLED = True
# If True, secondary hand pinch/fist triggers click/drag at primary cursor position (zero tremor)
TWO_HAND_AUX_CLICK_ENABLED = True

# -----------------------------
# TAB CHANGING CONFIGURATION
# -----------------------------
TAB_HOTKEY_NEXT = ('ctrl', 'tab')          # Next tab (Browser / VS Code / Editors)
TAB_HOTKEY_PREV = ('ctrl', 'shift', 'tab')  # Previous tab
TAB_WINDOW_HOTKEY = ('alt', 'tab')         # Window switch fallback (Alt + Tab)
TAB_SWITCH_COOLDOWN = 0.45                 # Cooldown between tab switches (seconds)
TAB_TWO_HAND_ENABLED = True                # Allow secondary hand to switch tabs

# -----------------------------
# FLUID MOMENTUM SCROLL SETTINGS
# -----------------------------
# Scroll velocity gain multiplier (converts smoothed hand velocity to wheel notches)
SCROLL_VELOCITY_GAIN = 0.22
# Exponential smoothing factor for scroll velocity (0.0 to 1.0)
SCROLL_SMOOTH_FACTOR = 0.65
# Momentum decay factor per frame when hand motion slows down (smooth glide)
SCROLL_INERTIA_DECAY = 0.75
# Minimum velocity threshold to maintain inertia
SCROLL_MIN_VELOCITY = 0.6
# Native Windows wheel unit per notch
WHEEL_DELTA = 120

# -----------------------------
# GESTURE STABILIZATION & VOTING
# -----------------------------
# Size of the sliding temporal window (number of recent frames)
VOTING_WINDOW_SIZE = 5
# Minimum votes in the sliding window required to accept a gesture
VOTING_MIN_MATCHES = 3

STABLE_FRAMES = 3
ACTION_COOLDOWN = 0.5

# -----------------------------
# DRAWING & HUD STYLING
# -----------------------------
LANDMARK_RADIUS = 4
LANDMARK_COLOR = (255, 0, 255)
LANDMARK_TEXT_COLOR = (0, 255, 0)

BOUNDING_BOX_COLOR = (0, 255, 0)
BOUNDING_BOX_SECONDARY_COLOR = (255, 180, 0)
BOUNDING_BOX_THICKNESS = 2
BOUNDING_BOX_PADDING = 18

# Interaction Zone Box Styling
BOX_COLOR = (255, 200, 0)          # Cyan/Amber active border
BOX_ACTIVE_COLOR = (0, 255, 0)     # Green when hand is inside
BOX_THICKNESS = 2

# HUD Text Styling
FONT_SCALE = 0.8
FONT_THICKNESS = 2

# -----------------------------
# DEBUG & DISPLAY FLAGS
# -----------------------------
SHOW_FPS = True
SHOW_LANDMARK_NUMBERS = False
SHOW_BOUNDING_BOX = True
SHOW_HAND_LABEL = True
SHOW_ACTION_TEXT = True
SHOW_DESCRIPTION_TEXT = True
SHOW_INTERACTION_BOX = True
SHOW_PINCH_LINE = True
SHOW_CONTROL_PANEL = True
SHOW_CONFIDENCE_METER = True