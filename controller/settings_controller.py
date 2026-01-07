from sciplex_core.controller.events import EventEmitter, SimpleEventEmitter
from sciplex_core.model.settings_model import settings as settings_model

# Global settings controller instance for easy access
_settings_controller_instance = None

def get_settings_controller():
    """Get the global settings controller instance."""
    global _settings_controller_instance
    if _settings_controller_instance is None:
        # For desktop, use Qt adapter
        try:
            from desktop.adapters.qt_settings_controller import QtSettingsController
            _settings_controller_instance = QtSettingsController(set_global=True)
        except ImportError:
            # Fallback to core controller if Qt not available
            from sciplex_core.controller.settings_controller import SettingsController
            _settings_controller_instance = SettingsController(set_global=True)
    return _settings_controller_instance


class SettingsController:
    """
    Core settings controller (framework-agnostic).
    
    Uses EventEmitter for reactive updates.
    Desktop views should use QtSettingsController adapter instead.
    """

    def __init__(self, event_emitter: EventEmitter = None, set_global: bool = True):
        """
        Initialize the settings controller.

        Args:
            event_emitter: Event emitter for reactive updates. If None, creates SimpleEventEmitter
            set_global: Whether to set as global singleton instance
        """
        self._model = settings_model
        self.events = event_emitter if event_emitter is not None else SimpleEventEmitter()

        # Set as global singleton instance if requested (default True)
        # This allows widgets that can't get controller via DI to use get_settings_controller()
        if set_global:
            global _settings_controller_instance
            _settings_controller_instance = self

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------
    def get_stylesheet(self, colors_data=None) -> str:
        return self._model.get_stylesheet(colors_data)

    def get_initial_stylesheet(self) -> str:
        return self._model.get_initial_stylesheet()

    def is_dark_theme_enabled(self) -> bool:
        return self._model.is_dark_theme_enabled()

    @property
    def config(self):
        return self._model.config

    @property
    def colors(self):
        return self._model.colors

    # ------------------------------------------------------------------
    # Mutating actions
    # ------------------------------------------------------------------
    def update_parameter(self, group: str, key: str, value):
        """Update parameter and emit appropriate events."""
        self._model.update_parameter(group, key, value)

        # Emit specific events based on what changed
        if group == "scene" and key == "Socket Annotation":
            self.events.emit("socket_annotation_changed", value)
        elif group == "Display" and key == "Edge Type":
            self.events.emit("edge_type_changed")
        elif group == "Library" and key == "Show Tutorials":
            self.events.emit("show_tutorials_changed", value)



