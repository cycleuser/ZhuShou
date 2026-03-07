"""Stage sidebar — shows pipeline progress as a vertical step list.

Each stage is rendered as a row with a status indicator (pending,
running spinner, complete checkmark, or error X).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from zhushou.gui.styles import Colors, Fonts


class _StageRow(QWidget):
    """A single stage row: status indicator + name + optional duration."""

    def __init__(self, num: int, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.num = num
        self.name = name
        self._status = "pending"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Status indicator (circle/icon)
        self._indicator = QLabel("\u25cb")  # empty circle
        self._indicator.setFixedWidth(20)
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._indicator.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_NORMAL))
        layout.addWidget(self._indicator)

        # Stage info
        info = QVBoxLayout()
        info.setSpacing(0)

        self._name_label = QLabel(f"{num}. {name}")
        self._name_label.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_NORMAL))
        info.addWidget(self._name_label)

        self._detail_label = QLabel("")
        self._detail_label.setObjectName("dimLabel")
        self._detail_label.setFont(QFont(Fonts.FAMILY_UI, Fonts.SIZE_SMALL))
        self._detail_label.hide()
        info.addWidget(self._detail_label)

        layout.addLayout(info)
        layout.addStretch()

        self._update_style()

    @property
    def status(self) -> str:
        return self._status

    def set_running(self) -> None:
        self._status = "running"
        self._indicator.setText("\u25cf")  # filled circle
        self._update_style()

    def set_complete(self, duration: float = 0.0) -> None:
        self._status = "complete"
        self._indicator.setText("\u2713")  # checkmark
        if duration > 0:
            self._detail_label.setText(f"{duration:.1f}s")
            self._detail_label.show()
        self._update_style()

    def set_error(self, message: str = "") -> None:
        self._status = "error"
        self._indicator.setText("\u2717")  # X mark
        if message:
            self._detail_label.setText(message[:50])
            self._detail_label.show()
        self._update_style()

    def _update_style(self) -> None:
        colors = {
            "pending": Colors.STAGE_PENDING,
            "running": Colors.STAGE_RUNNING,
            "complete": Colors.STAGE_COMPLETE,
            "error": Colors.STAGE_ERROR,
        }
        color = colors.get(self._status, Colors.FG_DIM)
        self._indicator.setStyleSheet(f"color: {color}; background: transparent;")
        self._name_label.setStyleSheet(f"color: {color}; background: transparent;")
        self._detail_label.setStyleSheet(
            f"color: {Colors.FG_DIM}; background: transparent;"
        )

        if self._status == "running":
            self.setStyleSheet(
                f"background-color: {Colors.BG_HOVER}; "
                f"border-radius: 6px;"
            )
        else:
            self.setStyleSheet("background: transparent;")


class StageSidebar(QWidget):
    """Vertical sidebar listing all pipeline stages with live status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Pipeline Stages")
        header.setObjectName("headerLabel")
        header.setContentsMargins(12, 12, 12, 4)
        outer.addWidget(header)

        # Scrollable area for stages
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self._layout.addStretch()

        scroll.setWidget(self._container)
        outer.addWidget(scroll)

        # Progress summary
        self._progress_label = QLabel("Waiting to start...")
        self._progress_label.setObjectName("dimLabel")
        self._progress_label.setContentsMargins(12, 4, 12, 12)
        outer.addWidget(self._progress_label)

        self._rows: dict[int, _StageRow] = {}
        self._current_stage: int = 0

    @Slot(int, int, str)
    def on_stage_started(self, stage_num: int, total_stages: int, name: str) -> None:
        """A new stage has started."""
        # Create row if it doesn't exist yet
        if stage_num not in self._rows:
            row = _StageRow(stage_num, name)
            # Insert before the stretch
            self._layout.insertWidget(self._layout.count() - 1, row)
            self._rows[stage_num] = row

        self._rows[stage_num].set_running()
        self._current_stage = stage_num
        self._progress_label.setText(
            f"Stage {stage_num}/{total_stages}: {name}"
        )

    @Slot(int, str, float)
    def on_stage_completed(
        self, stage_num: int, name: str, duration: float,
    ) -> None:
        """A stage has finished successfully."""
        if stage_num in self._rows:
            self._rows[stage_num].set_complete(duration)

    @Slot(str)
    def on_error(self, message: str) -> None:
        """Mark the current stage as errored."""
        if self._current_stage in self._rows:
            self._rows[self._current_stage].set_error(message)

    @Slot(dict)
    def on_pipeline_complete(self, stats: dict) -> None:
        """Pipeline finished."""
        total = stats.get("stages_completed", 0)
        tests = stats.get("tests_passed", "N/A")
        time_str = stats.get("total_time", "")
        self._progress_label.setText(
            f"Done: {total} stages | Tests: {tests} | {time_str}"
        )

    def clear(self) -> None:
        """Reset for a new pipeline run."""
        for row in self._rows.values():
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()
        self._current_stage = 0
        self._progress_label.setText("Waiting to start...")
