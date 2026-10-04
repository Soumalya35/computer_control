"""
Drag & Click Control Module
Manages primary mouse button press, hold-to-drag lifecycle, and click dispatch.
"""

from system.win32_input import InputBackend


class DragController:
    """Controls primary mouse button states during clicks and drag-and-drop sessions."""

    def __init__(self, backend: InputBackend):
        self.backend = backend
        self.is_dragging = False

    def click(self):
        """Executes a single primary click."""
        self.backend.click()

    def right_click(self):
        """Executes a secondary (right) click."""
        self.backend.right_click()

    def double_click(self):
        """Executes a double click."""
        self.backend.double_click()

    def start_drag(self):
        """Presses and holds the left mouse button."""
        if not self.is_dragging:
            self.backend.left_down()
            self.is_dragging = True

    def end_drag(self):
        """Releases the held left mouse button."""
        if self.is_dragging:
            self.backend.left_up()
            self.is_dragging = False

    def reset(self):
        """Failsafe release."""
        self.end_drag()
