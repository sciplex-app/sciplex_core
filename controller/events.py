"""
Framework-agnostic event emitter for controllers.

This module provides an abstraction layer for events/signals that works
with both Qt (desktop) and web frameworks (React, etc.).

Controllers should use EventEmitter instead of Qt signals directly.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List


class EventEmitter(ABC):
    """
    Abstract event emitter interface.

    Controllers use this instead of Qt signals to remain framework-agnostic.
    """

    @abstractmethod
    def on(self, event_name: str, callback: Callable) -> None:
        """Register a callback for an event."""
        pass

    @abstractmethod
    def emit(self, event_name: str, *args, **kwargs) -> None:
        """Emit an event, calling all registered callbacks."""
        pass

    @abstractmethod
    def disconnect(self, event_name: str, callback: Callable = None) -> None:
        """Disconnect a callback from an event. If callback is None, disconnect all."""
        pass


class SimpleEventEmitter(EventEmitter):
    """
    Simple Python implementation of EventEmitter.

    Works for both desktop and web. For desktop, can be wrapped with
    QtEventEmitterAdapter to convert to Qt signals.
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable) -> None:
        """Register a callback for an event."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def emit(self, event_name: str, *args, **kwargs) -> None:
        """Emit an event, calling all registered callbacks."""
        if event_name in self._listeners:
            # Copy list to avoid modification during iteration
            for callback in list(self._listeners[event_name]):
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    # Log error but don't break other callbacks
                    import logging
                    logging.error(f"Error in event callback for {event_name}: {e}")

    def disconnect(self, event_name: str, callback: Callable = None) -> None:
        """Disconnect a callback from an event."""
        if event_name not in self._listeners:
            return

        if callback is None:
            # Disconnect all callbacks for this event
            self._listeners[event_name].clear()
        else:
            # Disconnect specific callback
            if callback in self._listeners[event_name]:
                self._listeners[event_name].remove(callback)


class QtEventEmitterAdapter(EventEmitter):
    """
    Adapter that wraps Qt QObject signals as EventEmitter.

    This allows controllers to use EventEmitter interface while
    still using Qt signals under the hood for desktop apps.
    """

    def __init__(self, qobject):
        """
        Initialize adapter with a Qt QObject.

        Args:
            qobject: A QObject instance with Signal attributes
        """
        self._qobject = qobject
        self._qt_connections: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable) -> None:
        """Connect callback to Qt signal."""
        if not hasattr(self._qobject, event_name):
            raise AttributeError(f"QObject has no signal '{event_name}'")

        signal = getattr(self._qobject, event_name)
        signal.connect(callback)

        # Track connection for disconnect
        if event_name not in self._qt_connections:
            self._qt_connections[event_name] = []
        self._qt_connections[event_name].append(callback)

    def emit(self, event_name: str, *args, **kwargs) -> None:
        """Emit Qt signal."""
        if not hasattr(self._qobject, event_name):
            raise AttributeError(f"QObject has no signal '{event_name}'")

        signal = getattr(self._qobject, event_name)
        signal.emit(*args, **kwargs)

    def disconnect(self, event_name: str, callback: Callable = None) -> None:
        """Disconnect callback from Qt signal."""
        if event_name not in self._qt_connections:
            return

        signal = getattr(self._qobject, event_name)

        if callback is None:
            # Disconnect all
            for cb in self._qt_connections[event_name]:
                signal.disconnect(cb)
            self._qt_connections[event_name].clear()
        else:
            # Disconnect specific callback
            if callback in self._qt_connections[event_name]:
                signal.disconnect(callback)
                self._qt_connections[event_name].remove(callback)

