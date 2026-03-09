"""Hot-reloading workflow store.

Watches a WORKFLOW.md file for changes and keeps a cached, parsed copy
that the orchestrator reads at the start of every tick.  On parse
errors the last-known-good configuration is preserved (fail-safe).

Inspired by Symphony's ``workflow_store.ex``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable

from zhushou.workflow.config import WorkflowConfig
from zhushou.workflow.parser import WorkflowData, WorkflowParseError, parse_workflow

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 1.0  # seconds -- fallback when watchdog unavailable

FileStamp = tuple[float, int, str]  # (mtime, size, content_hash)


def _compute_stamp(path: Path) -> FileStamp | None:
    """Return ``(mtime, size, content_hash)`` or ``None`` if unreadable."""
    try:
        stat = path.stat()
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()[:16]
        return (stat.st_mtime, stat.st_size, digest)
    except OSError:
        return None


class WorkflowStore:
    """Thread-safe cached store for a single WORKFLOW.md file.

    Call :meth:`current` from any thread to get the latest
    ``WorkflowData`` and ``WorkflowConfig``.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).resolve()
        self._lock = threading.Lock()
        self._data: WorkflowData | None = None
        self._config: WorkflowConfig | None = None
        self._stamp: FileStamp | None = None
        self._watcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._on_reload_callbacks: list[Callable[[WorkflowConfig], None]] = []

        # Initial load
        self._reload()

    # ── Public API ────────────────────────────────────────────────

    def current(self) -> tuple[WorkflowData, WorkflowConfig]:
        """Return the cached ``(WorkflowData, WorkflowConfig)`` pair.

        If no workflow has ever loaded successfully, returns empty defaults.
        """
        with self._lock:
            data = self._data or WorkflowData()
            config = self._config or WorkflowConfig()
            return data, config

    @property
    def current_config(self) -> WorkflowConfig:
        _, cfg = self.current()
        return cfg

    @property
    def current_data(self) -> WorkflowData:
        data, _ = self.current()
        return data

    @property
    def path(self) -> Path:
        return self._path

    def on_reload(self, callback: Callable[[WorkflowConfig], None]) -> None:
        """Register a callback invoked after every successful reload."""
        self._on_reload_callbacks.append(callback)

    # ── Watcher lifecycle ─────────────────────────────────────────

    def start_watching(self) -> None:
        """Begin background file-watching (polling fallback)."""
        if self._watcher_thread is not None:
            return
        self._stop_event.clear()

        try:
            self._start_watchdog()
        except Exception:
            logger.debug("watchdog unavailable; falling back to polling")
            self._start_polling()

    def stop_watching(self) -> None:
        """Stop background file-watching."""
        self._stop_event.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=5.0)
            self._watcher_thread = None

    # ── Internal: reload ──────────────────────────────────────────

    def _reload(self) -> bool:
        """Re-read and parse the workflow file.

        Returns ``True`` on success.  On failure, logs a warning and
        keeps the previous (last-known-good) configuration.
        """
        if not self._path.is_file():
            logger.warning("Workflow file not found: %s", self._path)
            return False

        new_stamp = _compute_stamp(self._path)
        with self._lock:
            if new_stamp == self._stamp:
                return False  # unchanged

        try:
            data = parse_workflow(self._path)
            config = WorkflowConfig(data.config)
            warnings = config.validate()
            for w in warnings:
                logger.warning("Workflow config: %s", w)
        except (WorkflowParseError, Exception) as exc:
            logger.warning(
                "Failed to reload %s, keeping previous config: %s",
                self._path, exc,
            )
            return False

        with self._lock:
            self._data = data
            self._config = config
            self._stamp = new_stamp

        logger.info("Workflow reloaded from %s", self._path)
        for cb in self._on_reload_callbacks:
            try:
                cb(config)
            except Exception:
                logger.debug("Reload callback raised", exc_info=True)
        return True

    # ── Internal: polling watcher ─────────────────────────────────

    def _start_polling(self) -> None:
        def _poll_loop() -> None:
            while not self._stop_event.is_set():
                self._reload()
                self._stop_event.wait(_POLL_INTERVAL)

        self._watcher_thread = threading.Thread(
            target=_poll_loop, daemon=True, name="workflow-poll",
        )
        self._watcher_thread.start()

    # ── Internal: watchdog watcher ────────────────────────────────

    def _start_watchdog(self) -> None:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        store = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event: Any) -> None:
                if Path(event.src_path).resolve() == store._path:
                    store._reload()

        observer = Observer()
        observer.schedule(_Handler(), str(self._path.parent), recursive=False)
        observer.daemon = True
        observer.start()

        # Wrap observer into our stop protocol
        def _watchdog_loop() -> None:
            self._stop_event.wait()
            observer.stop()
            observer.join(timeout=5.0)

        self._watcher_thread = threading.Thread(
            target=_watchdog_loop, daemon=True, name="workflow-watchdog",
        )
        self._watcher_thread.start()
