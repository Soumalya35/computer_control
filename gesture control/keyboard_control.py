"""
Keyboard Control Module
Executes OS hotkeys and multimedia keys for window navigation, tab switching, and media control.
Uses native Win32 hardware event injection for zero-latency volume control without FailSafe exceptions.
"""

import sys
import ctypes
import pyautogui
from config import TAB_HOTKEY_NEXT, TAB_HOTKEY_PREV, TAB_WINDOW_HOTKEY

# Ensure no artificial delays and disable corner fail-safe triggers
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

IS_WINDOWS = sys.platform == "win32"

# Win32 Virtual Key Constants for Media Control
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


class KeyboardController:
    """Dispatches keyboard shortcuts and media keys using OS automation."""

    @staticmethod
    def alt_tab():
        """Switches active application window (Alt + Tab)."""
        try:
            pyautogui.hotkey(*TAB_WINDOW_HOTKEY)
        except Exception:
            pass

    @staticmethod
    def task_view():
        """Opens Windows Task View (Win + Tab)."""
        try:
            pyautogui.hotkey('win', 'tab')
        except Exception:
            pass

    @staticmethod
    def next_tab():
        """Switches to the next browser or editor tab (configurable, default Ctrl + Tab)."""
        try:
            pyautogui.hotkey(*TAB_HOTKEY_NEXT)
        except Exception:
            pass

    @staticmethod
    def previous_tab():
        """Switches to the previous browser or editor tab (configurable, default Ctrl + Shift + Tab)."""
        try:
            pyautogui.hotkey(*TAB_HOTKEY_PREV)
        except Exception:
            pass

    @staticmethod
    def prev_tab():
        """Alias for previous_tab."""
        KeyboardController.previous_tab()

    @staticmethod
    def switch_tab(direction="next"):
        """Switches tabs in specified direction ('next' or 'prev')."""
        if direction == "prev":
            KeyboardController.previous_tab()
        else:
            KeyboardController.next_tab()

    @staticmethod
    def volume_up():
        """Increases system master volume using native Win32 keybd_event."""
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                return
            except Exception:
                pass
        try:
            pyautogui.press('volumeup')
        except Exception:
            pass

    @staticmethod
    def volume_down():
        """Decreases system master volume using native Win32 keybd_event."""
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                return
            except Exception:
                pass
        try:
            pyautogui.press('volumedown')
        except Exception:
            pass

    @staticmethod
    def play_pause():
        """Toggles media playback (Play / Pause) using native Win32 keybd_event."""
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
                return
            except Exception:
                pass
        try:
            pyautogui.press('playpause')
        except Exception:
            pass
