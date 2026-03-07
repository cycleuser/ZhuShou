"""Background worker threads for running the pipeline in the GUI.

The pipeline runs in a QThread.  Events from the PipelineEventBus are
bridged to Qt signals so the GUI can safely update from the main thread.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from zhushou.events.bus import PipelineEventBus
from zhushou.events.types import (
    CodeOutputEvent,
    DebugAttemptEvent,
    ErrorEvent,
    InfoEvent,
    PipelineCompleteEvent,
    PipelineEvent,
    StageCompleteEvent,
    StageStartEvent,
    TestResultEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)

logger = logging.getLogger(__name__)


class EventBridge(QObject):
    """Bridges PipelineEventBus callbacks (background thread) to Qt signals.

    Subscribe this to the event bus; it re-emits every event as a
    Qt signal so that widgets connected in the main thread update safely.
    """

    # Generic event signal (carries the event object)
    event_received = Signal(object)

    # Typed convenience signals
    stage_started = Signal(int, int, str)        # stage_num, total, name
    stage_completed = Signal(int, str, float)     # stage_num, name, duration
    thinking = Signal(int, str)                   # stage_num, content
    code_output = Signal(int, str, str)           # stage_num, file_path, action
    tool_called = Signal(int, str, dict)          # stage_num, tool_name, args
    tool_resulted = Signal(int, str, bool, str)   # stage_num, tool_name, ok, out
    test_result = Signal(int, bool, str)          # stage_num, passed, output
    debug_attempt = Signal(int, int, bool)        # attempt, max, passed
    pipeline_complete = Signal(dict)              # stats
    info_message = Signal(str)                    # message
    error_message = Signal(str)                   # message

    def on_event(self, event: PipelineEvent) -> None:
        """Callback for the PipelineEventBus — runs in the worker thread."""
        # Always emit the generic signal
        self.event_received.emit(event)

        # Emit typed signal
        if isinstance(event, StageStartEvent):
            self.stage_started.emit(
                event.stage_num, event.total_stages, event.stage_name,
            )
        elif isinstance(event, StageCompleteEvent):
            self.stage_completed.emit(
                event.stage_num, event.stage_name, event.duration_seconds,
            )
        elif isinstance(event, ThinkingEvent):
            self.thinking.emit(event.stage_num, event.content)
        elif isinstance(event, CodeOutputEvent):
            self.code_output.emit(
                event.stage_num, event.file_path, event.action,
            )
        elif isinstance(event, ToolCallEvent):
            self.tool_called.emit(
                event.stage_num, event.tool_name, dict(event.arguments),
            )
        elif isinstance(event, ToolResultEvent):
            self.tool_resulted.emit(
                event.stage_num, event.tool_name, event.success, event.output,
            )
        elif isinstance(event, TestResultEvent):
            self.test_result.emit(
                event.stage_num, event.passed, event.output,
            )
        elif isinstance(event, DebugAttemptEvent):
            self.debug_attempt.emit(
                event.attempt, event.max_retries, event.passed,
            )
        elif isinstance(event, PipelineCompleteEvent):
            self.pipeline_complete.emit(dict(event.stats))
        elif isinstance(event, InfoEvent):
            self.info_message.emit(event.message)
        elif isinstance(event, ErrorEvent):
            self.error_message.emit(event.message)


class PipelineWorker(QThread):
    """Runs PipelineOrchestrator.run() in a background thread.

    Usage::

        bus = PipelineEventBus()
        bridge = EventBridge()
        bus.subscribe(bridge.on_event)

        worker = PipelineWorker(
            request="Build a calculator",
            provider="ollama",
            model="qwen2.5-coder:7b",
            event_bus=bus,
        )
        # Connect bridge signals to GUI slots ...
        worker.finished_with_stats.connect(on_done)
        worker.error_occurred.connect(on_error)
        worker.start()
    """

    finished_with_stats = Signal(dict)  # pipeline stats dict
    error_occurred = Signal(str)        # error message

    def __init__(
        self,
        request: str,
        provider: str,
        model: str,
        event_bus: PipelineEventBus,
        *,
        output_dir: str = "./output",
        api_key: str = "",
        base_url: str = "",
        proxy: str = "",
        timeout: int = 300,
        full_mode: bool = False,
        python_path: str = "",
        kb_collections: list[str] | None = None,
        world_sense: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._provider = provider
        self._model = model
        self._event_bus = event_bus
        self._output_dir = output_dir
        self._api_key = api_key
        self._base_url = base_url
        self._proxy = proxy
        self._timeout = timeout
        self._full_mode = full_mode
        self._python_path = python_path
        self._kb_collections = kb_collections
        self._world_sense = world_sense

    def run(self) -> None:
        """Execute the pipeline (called by QThread.start)."""
        try:
            from zhushou.llm.factory import LLMClientFactory
            from zhushou.pipeline.orchestrator import PipelineOrchestrator
            from zhushou.utils.python_finder import find_python

            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._base_url:
                kwargs["base_url"] = self._base_url
            if self._proxy:
                kwargs["proxy"] = self._proxy
            if self._timeout != 300:
                kwargs["timeout"] = self._timeout
            if self._model:
                kwargs["model"] = self._model

            client = LLMClientFactory.create_client(self._provider, **kwargs)
            python_path = self._python_path or find_python()

            orchestrator = PipelineOrchestrator(
                llm_client=client,
                work_dir=self._output_dir,
                python_path=python_path,
                full_mode=self._full_mode,
                kb_collections=self._kb_collections,
                event_bus=self._event_bus,
                world_sense=self._world_sense,
            )

            stats = orchestrator.run(self._request)
            self.finished_with_stats.emit(stats)

        except Exception as exc:
            logger.exception("Pipeline worker failed")
            self.error_occurred.emit(str(exc))


class KBCrawlWorker(QThread):
    """Background thread for crawling a website into the knowledge base."""

    crawl_finished = Signal(int, str)   # pages_saved, output_dir
    crawl_error = Signal(str)           # error message

    def __init__(
        self,
        url: str,
        *,
        name: str | None = None,
        max_pages: int = 200,
        prefix: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._name = name
        self._max_pages = max_pages
        self._prefix = prefix

    def run(self) -> None:
        try:
            from zhushou.knowledge.kb_manager import KBManager
            from zhushou.knowledge.kb_config import KBConfig

            mgr = KBManager(KBConfig())
            pages_saved, output_dir = mgr.crawl(
                self._url,
                name=self._name,
                max_pages=self._max_pages,
                prefix=self._prefix,
            )
            self.crawl_finished.emit(pages_saved, output_dir)
        except Exception as exc:
            logger.exception("KB crawl worker failed")
            self.crawl_error.emit(str(exc))


class KBUploadWorker(QThread):
    """Background thread for uploading files into a user KB."""

    upload_finished = Signal(dict)  # result dict
    upload_error = Signal(str)      # error message

    def __init__(
        self,
        name: str,
        file_paths: list[str],
        *,
        duplicate_action: str = "skip",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._file_paths = file_paths
        self._duplicate_action = duplicate_action

    def run(self) -> None:
        try:
            from zhushou.knowledge.kb_manager import KBManager
            from zhushou.knowledge.kb_config import KBConfig

            mgr = KBManager(KBConfig())
            result = mgr.upload_files(
                self._name, self._file_paths,
                duplicate_action=self._duplicate_action,
            )
            self.upload_finished.emit(result)
        except Exception as exc:
            logger.exception("KB upload worker failed")
            self.upload_error.emit(str(exc))


class KBImportDirWorker(QThread):
    """Background thread for importing a directory into a user KB."""

    import_finished = Signal(dict)  # result dict
    import_error = Signal(str)      # error message

    def __init__(
        self,
        name: str,
        dir_path: str,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._dir_path = dir_path

    def run(self) -> None:
        try:
            from zhushou.knowledge.kb_manager import KBManager
            from zhushou.knowledge.kb_config import KBConfig

            mgr = KBManager(KBConfig())
            result = mgr.import_directory(self._name, self._dir_path)
            self.import_finished.emit(result)
        except Exception as exc:
            logger.exception("KB import worker failed")
            self.import_error.emit(str(exc))
