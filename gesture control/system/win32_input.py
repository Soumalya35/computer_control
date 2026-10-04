"""
Windows Input Backend Module
Defines the InputBackend interface, implements user-mode Win32 User32 automation via cached ctypes,
and provides a MockInputBackend for headless testing.
"""

import sys
import ctypes
from abc import ABC, abstractmethod
from typing import List, Tuple, Any

IS_WINDOWS = sys.platform == "win32"

# Windows User32 API Constants (User-mode API surface)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120

# Virtual Key Codes
VK_TAB = 0x09
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12       # ALT key
VK_LWIN = 0x5B       # Left Windows key
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


class InputBackend(ABC):
    """Abstract interface for operating system input automation."""

    @abstractmethod
    def move_mouse(self, x: int, y: int):
        pass

    @abstractmethod
    def left_down(self):
        pass

    @abstractmethod
    def left_up(self):
        pass

    @abstractmethod
    def click(self):
        pass

    @abstractmethod
    def right_click(self):
        pass

    @abstractmethod
    def wheel(self, delta: int):
        pass

    @abstractmethod
    def hotkey(self, *keys: str):
        pass

    @abstractmethod
    def media_key(self, key_name: str):
        pass

    @abstractmethod
    def release_all(self):
        pass


class Win32InputBackend(InputBackend):
    """
    High-performance user-mode Win32 User32 input backend using cached ctypes function pointers.
    Bypasses high-overhead Python libraries for sub-millisecond dispatch latency.
    """

    def __init__(self):
        self.is_left_down = False
        self.last_x = -1
        self.last_y = -1

        if IS_WINDOWS:
            # Cache ctypes function references at initialization
            self._set_cursor_pos = ctypes.windll.user32.SetCursorPos
            self._mouse_event = ctypes.windll.user32.mouse_event
            self._keybd_event = ctypes.windll.user32.keybd_event
        else:
            self._set_cursor_pos = None
            self._mouse_event = None
            self._keybd_event = None

    def move_mouse(self, x: int, y: int):
        """Moves cursor to absolute screen coordinates. Skips duplicate identical moves."""
        if x == self.last_x and y == self.last_y:
            return

        self.last_x = x
        self.last_y = y

        if IS_WINDOWS and self._set_cursor_pos:
            try:
                self._set_cursor_pos(x, y)
            except Exception:
                pass

    def left_down(self):
        """Presses and holds the primary mouse button."""
        if not self.is_left_down:
            if IS_WINDOWS and self._mouse_event:
                try:
                    self._mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    self.is_left_down = True
                except Exception:
                    pass

    def left_up(self):
        """Releases the primary mouse button."""
        if self.is_left_down:
            if IS_WINDOWS and self._mouse_event:
                try:
                    self._mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.is_left_down = False
                except Exception:
                    pass

    def click(self):
        """Dispatches an atomic primary mouse click."""
        if IS_WINDOWS and self._mouse_event:
            try:
                self._mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                self._mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass

    def right_click(self):
        """Dispatches an atomic secondary (right) mouse click."""
        if IS_WINDOWS and self._mouse_event:
            try:
                self._mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                self._mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            except Exception:
                pass

    def double_click(self):
        """Dispatches a double click with short inter-click spacing."""
        self.click()
        self.click()

    def wheel(self, delta_notches: int):
        """Sends native mouse wheel events scaled by WHEEL_DELTA (120 units)."""
        if delta_notches == 0:
            return
        if IS_WINDOWS and self._mouse_event:
            try:
                dw_data = int(delta_notches * WHEEL_DELTA)
                self._mouse_event(MOUSEEVENTF_WHEEL, 0, 0, dw_data, 0)
            except Exception:
                pass

    def _send_vk(self, vk: int, keyup: bool = False):
        if IS_WINDOWS and self._keybd_event:
            flags = KEYEVENTF_KEYUP if keyup else 0
            try:
                self._keybd_event(vk, 0, flags, 0)
            except Exception:
                pass

    def hotkey(self, *keys: str):
        """Dispatches key combinations such as Alt+Tab, Win+Tab, Ctrl+Tab."""
        vk_map = {
            "alt": VK_MENU,
            "tab": VK_TAB,
            "win": VK_LWIN,
            "ctrl": VK_CONTROL,
            "shift": VK_SHIFT
        }
        vks = [vk_map[k.lower()] for k in keys if k.lower() in vk_map]
        if not vks:
            return

        # Press down in order
        for vk in vks:
            self._send_vk(vk, keyup=False)

        # Release in reverse order
        for vk in reversed(vks):
            self._send_vk(vk, keyup=True)

    def media_key(self, key_name: str):
        """Dispatches multimedia virtual keys."""
        media_map = {
            "volume_up": VK_VOLUME_UP,
            "volume_down": VK_VOLUME_DOWN,
            "play_pause": VK_MEDIA_PLAY_PAUSE
        }
        vk = media_map.get(key_name.lower())
        if vk:
            self._send_vk(vk, keyup=False)
            self._send_vk(vk, keyup=True)

    def release_all(self):
        """Safety cleanup: ensures left mouse button and modifier keys are released."""
        if self.is_left_down:
            self.left_up()
        # Release potential held modifiers
        for vk in (VK_MENU, VK_LWIN, VK_CONTROL, VK_SHIFT):
            self._send_vk(vk, keyup=True)


class MockInputBackend(InputBackend):
    """
    Mock backend recording all calls in memory for headless automated unit testing.
    Does not interact with the host operating system or move the physical mouse cursor.
    """

    def __init__(self):
        self.calls: List[Tuple[str, Any]] = []
        self.cursor = (0, 0)
        self.is_left_down = False

    def move_mouse(self, x: int, y: int):
        self.cursor = (x, y)
        self.calls.append(("move_mouse", (x, y)))

    def left_down(self):
        self.is_left_down = True
        self.calls.append(("left_down", ()))

    def left_up(self):
        self.is_left_down = False
        self.calls.append(("left_up", ()))

    def click(self):
        self.calls.append(("click", ()))

    def right_click(self):
        self.calls.append(("right_click", ()))

    def double_click(self):
        self.calls.append(("double_click", ()))

    def wheel(self, delta: int):
        self.calls.append(("wheel", delta))

    def hotkey(self, *keys: str):
        self.calls.append(("hotkey", keys))

    def media_key(self, key_name: str):
        self.calls.append(("media_key", key_name))

    def release_all(self):
        self.is_left_down = False
        self.calls.append(("release_all", ()))
