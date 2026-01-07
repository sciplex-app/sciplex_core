"""
Framework-agnostic clipboard interface.

This module provides an abstraction for clipboard operations that works
with both Qt (desktop) and web frameworks.
"""

from abc import ABC, abstractmethod


class ClipboardInterface(ABC):
    """
    Abstract clipboard interface.

    Controllers use this instead of Qt clipboard API to remain framework-agnostic.
    """

    @abstractmethod
    def get_text(self) -> str:
        """Get text from clipboard."""
        pass

    @abstractmethod
    def set_text(self, text: str) -> None:
        """Set text to clipboard."""
        pass


class QtClipboard(ClipboardInterface):
    """
    Qt implementation of clipboard interface.

    For desktop applications using PySide6/PyQt5.
    """

    def get_text(self) -> str:
        """Get text from Qt clipboard."""
        try:
            from PySide6.QtWidgets import QApplication
            return QApplication.instance().clipboard().text()
        except ImportError:
            # Fallback if Qt not available
            return ""

    def set_text(self, text: str) -> None:
        """Set text to Qt clipboard."""
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().clipboard().setText(text)
        except ImportError:
            # Fallback if Qt not available
            pass


class WebClipboard(ClipboardInterface):
    """
    Web implementation of clipboard interface.

    For web applications using browser Clipboard API.
    Note: This would typically be called from JavaScript/TypeScript,
    but the interface is defined here for consistency.
    """

    def get_text(self) -> str:
        """
        Get text from web clipboard.

        Note: In actual web implementation, this would be async
        and called via JavaScript bridge.
        """
        # This would be implemented in JavaScript/TypeScript
        # For now, return empty string
        return ""

    def set_text(self, text: str) -> None:
        """
        Set text to web clipboard.

        Note: In actual web implementation, this would be async
        and called via JavaScript bridge.
        """
        # This would be implemented in JavaScript/TypeScript
        pass


class MockClipboard(ClipboardInterface):
    """
    Mock clipboard for testing.

    Stores clipboard data in memory.
    """

    def __init__(self):
        self._text: str = ""

    def get_text(self) -> str:
        """Get text from mock clipboard."""
        return self._text

    def set_text(self, text: str) -> None:
        """Set text to mock clipboard."""
        self._text = text

