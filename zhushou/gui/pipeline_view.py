"""Pipeline view — the main working area with split panels.

Layout:  StageSidebar | CodePanel / ThinkingPanel (tabbed or split)

Connects the EventBridge signals to the individual panel slots.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from zhushou.gui.code_panel import CodePanel
from zhushou.gui.stage_sidebar import StageSidebar
from zhushou.gui.styles import Colors
from zhushou.gui.thinking_panel import ThinkingPanel
from zhushou.gui.workers import EventBridge


class PipelineView(QWidget):
    """Central widget showing live pipeline progress.

    Structure::

        +------------+---------------------------+
        |            |        Code Output        |
        |   Stage    |---------------------------|
        |  Sidebar   |   Thinking / Reasoning    |
        |            |                           |
        +------------+---------------------------+
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main horizontal splitter: sidebar | content
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: stage sidebar
        self._sidebar = StageSidebar()
        self._main_splitter.addWidget(self._sidebar)

        # Right: vertical splitter with code (top) and thinking (bottom)
        self._content_splitter = QSplitter(Qt.Orientation.Vertical)

        self._code_panel = CodePanel()
        self._thinking_panel = ThinkingPanel()

        self._content_splitter.addWidget(self._code_panel)
        self._content_splitter.addWidget(self._thinking_panel)
        self._content_splitter.setStretchFactor(0, 3)  # code 60%
        self._content_splitter.setStretchFactor(1, 2)  # thinking 40%

        self._main_splitter.addWidget(self._content_splitter)
        self._main_splitter.setStretchFactor(0, 0)  # sidebar fixed
        self._main_splitter.setStretchFactor(1, 1)  # content stretches

        layout.addWidget(self._main_splitter)

    # ── Public API ─────────────────────────────────────────────────

    def connect_bridge(self, bridge: EventBridge) -> None:
        """Wire up all EventBridge signals to the panel slots."""
        # Sidebar
        bridge.stage_started.connect(self._sidebar.on_stage_started)
        bridge.stage_completed.connect(self._sidebar.on_stage_completed)
        bridge.error_message.connect(self._sidebar.on_error)
        bridge.pipeline_complete.connect(self._sidebar.on_pipeline_complete)

        # Code panel
        bridge.code_output.connect(self._code_panel.on_code_output)
        bridge.tool_resulted.connect(self._code_panel.on_tool_result)

        # Thinking panel
        bridge.thinking.connect(self._thinking_panel.on_thinking)
        bridge.tool_called.connect(self._thinking_panel.on_tool_call)
        bridge.tool_resulted.connect(self._thinking_panel.on_tool_result)
        bridge.test_result.connect(self._thinking_panel.on_test_result)
        bridge.debug_attempt.connect(self._thinking_panel.on_debug_attempt)
        bridge.info_message.connect(self._thinking_panel.on_info)
        bridge.error_message.connect(self._thinking_panel.on_error)

    def set_work_dir(self, work_dir: str) -> None:
        """Pass the pipeline working directory to child panels."""
        self._code_panel.set_work_dir(work_dir)

    def clear(self) -> None:
        """Reset all panels for a new pipeline run."""
        self._sidebar.clear()
        self._code_panel.clear()
        self._thinking_panel.clear()

    @property
    def sidebar(self) -> StageSidebar:
        return self._sidebar

    @property
    def code_panel(self) -> CodePanel:
        return self._code_panel

    @property
    def thinking_panel(self) -> ThinkingPanel:
        return self._thinking_panel
