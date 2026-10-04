"""
Gesture Database Module
Defines the mapping between finger state configurations (Thumb, Index, Middle, Ring, Pinky)
and corresponding system operations, including action categories, cooldowns, and tab navigation.

Finger tuple: (Thumb, Index, Middle, Ring, Pinky)
1 = Finger Up / Extended
0 = Finger Down / Folded
"""

gesture_map = {

    # ==========================
    # SYSTEM STATE CONTROL
    # ==========================
    (0, 0, 0, 0, 0): {
        "description": "Closed Fist",
        "action": "PAUSE",
        "category": "system",
        "continuous": False,
        "cooldown": 0.8
    },

    (1, 1, 1, 1, 1): {
        "description": "Open Palm",
        "action": "RESUME",
        "category": "system",
        "continuous": False,
        "cooldown": 0.8
    },

    # ==========================
    # MOUSE CONTROL
    # ==========================
    # 👆 Index finger pointing -> Move mouse cursor (Tucked Thumb)
    (0, 1, 0, 0, 0): {
        "description": "Pointing Finger",
        "action": "MOVE_MOUSE",
        "category": "mouse",
        "continuous": True,
        "cooldown": 0.0
    },

    # 👆 Index finger pointing -> Move mouse cursor (Relaxed / Extended Thumb)
    (1, 1, 0, 0, 0): {
        "description": "Pointing (Relaxed Thumb)",
        "action": "MOVE_MOUSE",
        "category": "mouse",
        "continuous": True,
        "cooldown": 0.0
    },

    # 🤏 Pinch gesture -> Left click / Drag and drop
    "PINCH": {
        "description": "Pinch (Thumb + Index)",
        "action": "LEFT_CLICK",
        "category": "mouse",
        "continuous": False,
        "cooldown": 0.30
    },

    # ==========================
    # SCROLL CONTROL
    # ==========================
    # ✌️ Two fingers (Index + Middle) -> Vertical Scroll mode
    # Mapped for both tight thumb (0,1,1,0,0) and relaxed thumb (1,1,1,0,0)
    (0, 1, 1, 0, 0): {
        "description": "Two Fingers (Scroll)",
        "action": "SCROLL_MODE",
        "category": "scroll",
        "continuous": True,
        "cooldown": 0.0
    },
    (1, 1, 1, 0, 0): {
        "description": "Two Fingers (Scroll)",
        "action": "SCROLL_MODE",
        "category": "scroll",
        "continuous": True,
        "cooldown": 0.0
    },

    # ==========================
    # WINDOW & TAB NAVIGATION
    # ==========================
    # Three fingers (Index + Middle + Ring) -> Alt + Tab
    (0, 1, 1, 1, 0): {
        "description": "Three Fingers",
        "action": "ALT_TAB",
        "category": "keyboard",
        "continuous": False,
        "cooldown": 0.65
    },
    (1, 1, 1, 1, 0): {
        "description": "Three Fingers (Relaxed Thumb)",
        "action": "ALT_TAB",
        "category": "keyboard",
        "continuous": False,
        "cooldown": 0.65
    },

    # Four fingers (Index + Middle + Ring + Pinky) -> Task View (Win + Tab)
    (0, 1, 1, 1, 1): {
        "description": "Four Fingers",
        "action": "TASK_VIEW",
        "category": "keyboard",
        "continuous": False,
        "cooldown": 0.8
    },

    # 🤘 Rock gesture (Index + Pinky) -> Next Tab (Ctrl + Tab)
    (0, 1, 0, 0, 1): {
        "description": "Rock (Next Tab)",
        "action": "NEXT_TAB",
        "category": "keyboard",
        "continuous": False,
        "cooldown": 0.45
    },

    # Rock with Thumb extended (Thumb + Index + Pinky) -> Previous Tab (Ctrl + Shift + Tab)
    (1, 1, 0, 0, 1): {
        "description": "Rock+Thumb (Prev Tab)",
        "action": "PREV_TAB",
        "category": "keyboard",
        "continuous": False,
        "cooldown": 0.45
    },

    # ==========================
    # MEDIA & VOLUME CONTROL
    # ==========================
    # 👍 Thumb Up -> Volume Up
    (1, 0, 0, 0, 0): {
        "description": "Thumb Up",
        "action": "VOLUME_UP",
        "category": "media",
        "continuous": False,
        "cooldown": 0.20
    },

    # Pinky finger only -> Volume Down
    (0, 0, 0, 0, 1): {
        "description": "Pinky Only",
        "action": "VOLUME_DOWN",
        "category": "media",
        "continuous": False,
        "cooldown": 0.20
    },

    # 🤙 Thumb + Pinky (Call/Shaka) -> Play / Pause media
    (1, 0, 0, 0, 1): {
        "description": "Call Gesture (Shaka)",
        "action": "PLAY_PAUSE",
        "category": "media",
        "continuous": False,
        "cooldown": 0.6
    }
}

UNKNOWN_GESTURE = {
    "description": "Unknown Gesture",
    "action": "NO_ACTION",
    "category": "none",
    "continuous": False,
    "cooldown": 0.0
}