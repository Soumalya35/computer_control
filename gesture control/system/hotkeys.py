"""
Hotkey & Media Dispatcher Module
Translates high-level discrete gesture actions into Windows hotkeys and multimedia keys.
"""

from typing import Optional
from .win32_input import InputBackend


class HotkeyManager:
    """Dispatches discrete keyboard shortcuts and media keys through the InputBackend."""

    def __init__(self, backend: InputBackend):
        self.backend = backend

    def dispatch(self, action_name: str) -> bool:
        """Executes the mapped keyboard or media shortcut for the given action name."""
        if action_name == "ALT_TAB":
            self.backend.hotkey("alt", "tab")
            return True
        elif action_name == "TASK_VIEW":
            self.backend.hotkey("win", "tab")
            return True
        elif action_name == "NEXT_TAB":
            self.backend.hotkey("ctrl", "tab")
            return True
        elif action_name == "PREVIOUS_TAB":
            self.backend.hotkey("ctrl", "shift", "tab")
            return True
        elif action_name == "VOLUME_UP":
            self.backend.media_key("volume_up")
            return True
        elif action_name == "VOLUME_DOWN":
            self.backend.media_key("volume_down")
            return True
        elif action_name == "PLAY_PAUSE":
            self.backend.media_key("play_pause")
            return True
        return False
