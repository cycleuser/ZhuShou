"""Event bridge: PipelineEventBus -> WebSocket broadcast.

Subscribes to the event bus and pushes JSON-serialized events to all
connected WebSocket clients via an asyncio queue.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from zhushou.events.bus import PipelineEventBus
from zhushou.events.types import PipelineEvent

logger = logging.getLogger(__name__)


class WebEventBridge:
    """Bridges synchronous pipeline events to async WebSocket broadcast.

    The pipeline runs in a background thread and emits events via
    ``PipelineEventBus``.  This bridge serializes them and puts them
    into an ``asyncio.Queue`` that the WebSocket handler reads from.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self._loop = loop
        self._clients: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def add_client(self) -> asyncio.Queue[str]:
        """Register a new WebSocket client and return its message queue."""
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._clients.add(q)
        return q

    async def remove_client(self, q: asyncio.Queue[str]) -> None:
        """Unregister a WebSocket client."""
        async with self._lock:
            self._clients.discard(q)

    def on_event(self, event: PipelineEvent) -> None:
        """Callback for PipelineEventBus (called from worker thread)."""
        try:
            payload = json.dumps(event.to_dict(), ensure_ascii=False)
        except Exception:
            logger.debug("Failed to serialize event: %s", event, exc_info=True)
            return

        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._broadcast_sync, payload)

    def _broadcast_sync(self, payload: str) -> None:
        """Schedule async broadcast from the event loop thread."""
        asyncio.ensure_future(self._broadcast(payload))

    async def _broadcast(self, payload: str) -> None:
        """Push payload to all connected client queues."""
        async with self._lock:
            dead: list[asyncio.Queue[str]] = []
            for q in self._clients:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                self._clients.discard(q)

    @property
    async def client_count(self) -> int:
        async with self._lock:
            return len(self._clients)
