"""Thread-safe event bus for pipeline events.

The orchestrator emits events; CLI, GUI, and Web listeners consume them.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from zhushou.events.types import PipelineEvent

logger = logging.getLogger(__name__)

EventCallback = Callable[[PipelineEvent], None]


class PipelineEventBus:
    """Publish-subscribe event bus.

    Thread-safe: the orchestrator (background thread) emits events,
    and listeners (GUI/Web main threads) consume them.
    Listeners are responsible for marshaling to their own thread
    (e.g. Qt signals, asyncio ``call_soon_threadsafe``).
    """

    def __init__(self) -> None:
        self._listeners: list[EventCallback] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: EventCallback) -> None:
        """Register a listener callback."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unsubscribe(self, callback: EventCallback) -> None:
        """Remove a listener callback."""
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

    def emit(self, event: PipelineEvent) -> None:
        """Send *event* to all registered listeners.

        Takes a snapshot of listeners under the lock, then calls each
        outside the lock.  A broken listener cannot crash the pipeline.
        """
        with self._lock:
            snapshot = list(self._listeners)

        for callback in snapshot:
            try:
                callback(event)
            except Exception:
                logger.debug(
                    "Event listener %r raised an exception",
                    callback,
                    exc_info=True,
                )

    @property
    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)
