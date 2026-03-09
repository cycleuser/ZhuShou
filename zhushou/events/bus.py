"""Thread-safe event bus supporting both sync and async listeners.

The orchestrator (async) and pipeline runners (sync background threads)
emit events.  CLI, GUI, and Web listeners consume them.

Extends the original sync-only bus with:
- ``subscribe_async()`` / ``emit_async()`` for asyncio consumers
- ``asyncio.Queue``-based delivery for async listeners
- Same thread-safe snapshot pattern for sync listeners
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine

from zhushou.events.types import PipelineEvent

logger = logging.getLogger(__name__)

EventCallback = Callable[[PipelineEvent], None]
AsyncEventCallback = Callable[[PipelineEvent], Coroutine[Any, Any, None]]


class PipelineEventBus:
    """Publish-subscribe event bus with sync + async listener support.

    Thread-safe: the orchestrator (asyncio loop) and pipeline runners
    (background threads) both emit events.  Listeners are responsible
    for marshaling to their own execution context (Qt signals, asyncio
    ``call_soon_threadsafe``, etc.).
    """

    def __init__(self) -> None:
        self._listeners: list[EventCallback] = []
        self._async_queues: list[asyncio.Queue[PipelineEvent]] = []
        self._lock = threading.Lock()

    # ── Sync listeners (GUI, CLI) ─────────────────────────────────

    def subscribe(self, callback: EventCallback) -> None:
        """Register a synchronous listener callback."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unsubscribe(self, callback: EventCallback) -> None:
        """Remove a synchronous listener callback."""
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

    def emit(self, event: PipelineEvent) -> None:
        """Send *event* to all sync listeners (thread-safe).

        Also pushes to all async queues for async consumers.
        """
        # Snapshot sync listeners under lock
        with self._lock:
            sync_snapshot = list(self._listeners)
            async_snapshot = list(self._async_queues)

        # Notify sync listeners outside lock
        for callback in sync_snapshot:
            try:
                callback(event)
            except Exception:
                logger.debug(
                    "Sync event listener %r raised an exception",
                    callback,
                    exc_info=True,
                )

        # Push to async queues (non-blocking)
        for queue in async_snapshot:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("Async event queue full, dropping event")
            except Exception:
                logger.debug("Failed to push to async queue", exc_info=True)

    # ── Async listeners (orchestrator, web dashboard) ─────────────

    def subscribe_async(self, maxsize: int = 1000) -> asyncio.Queue[PipelineEvent]:
        """Create and return an async queue that receives all events.

        The caller should consume events from the returned queue in an
        async loop.  Call ``unsubscribe_async()`` when done.
        """
        queue: asyncio.Queue[PipelineEvent] = asyncio.Queue(maxsize=maxsize)
        with self._lock:
            self._async_queues.append(queue)
        return queue

    def unsubscribe_async(self, queue: asyncio.Queue[PipelineEvent]) -> None:
        """Remove an async event queue."""
        with self._lock:
            try:
                self._async_queues.remove(queue)
            except ValueError:
                pass

    async def emit_async(self, event: PipelineEvent) -> None:
        """Emit an event from an async context.

        Calls sync listeners via the thread-safe ``emit()`` path, then
        awaits putting into async queues.
        """
        # Sync listeners still get called via emit()
        with self._lock:
            sync_snapshot = list(self._listeners)
            async_snapshot = list(self._async_queues)

        for callback in sync_snapshot:
            try:
                callback(event)
            except Exception:
                logger.debug(
                    "Sync listener %r raised during async emit",
                    callback,
                    exc_info=True,
                )

        for queue in async_snapshot:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("Async queue full during async emit")

    # ── Introspection ─────────────────────────────────────────────

    @property
    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners) + len(self._async_queues)

    @property
    def sync_listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    @property
    def async_listener_count(self) -> int:
        with self._lock:
            return len(self._async_queues)
