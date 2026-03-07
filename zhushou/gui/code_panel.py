"""Code output panel — displays created/edited source files.

Shows a list of files on the left and the file content (syntax-highlighted)
on the right.  Updated in real time as the pipeline emits CodeOutputEvent
and ToolResultEvent for write_file / edit_file calls.
"""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from zhushou.gui.styles import Colors, Fonts


class _PythonHighlighter(QSyntaxHighlighter):
    """Minimal Python syntax highlighter for the code preview."""

    KEYWORDS = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else",
        "except", "finally", "for", "from", "global", "if", "import",
        "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise",
        "return", "try", "while", "with", "yield",
    }

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        self._formats: list[tuple[str, QTextCharFormat]] = []

        # Keywords
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor(Colors.CODE_KEYWORD))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in self.KEYWORDS:
            self._formats.append((rf"\b{kw}\b", kw_fmt))

        # Strings (single and double quoted)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor(Colors.CODE_STRING))
        self._formats.append((r'"[^"\\]*(\\.[^"\\]*)*"', str_fmt))
        self._formats.append((r"'[^'\\]*(\\.[^'\\]*)*'", str_fmt))

        # Comments
        cmt_fmt = QTextCharFormat()
        cmt_fmt.setForeground(QColor(Colors.CODE_COMMENT))
        self._formats.append((r"#[^\n]*", cmt_fmt))

        # Numbers
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor(Colors.CODE_NUMBER))
        self._formats.append((r"\b\d+\.?\d*\b", num_fmt))

        # Function definitions
        fn_fmt = QTextCharFormat()
        fn_fmt.setForeground(QColor(Colors.CODE_FUNCTION))
        self._formats.append((r"\bdef\s+(\w+)", fn_fmt))
        self._formats.append((r"\bclass\s+(\w+)", fn_fmt))

        # Compile patterns
        import re
        self._rules = [
            (re.compile(pattern), fmt) for pattern, fmt in self._formats
        ]

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self._rules:
            for match in regex.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class CodePanel(QWidget):
    """Split panel: file list (left) + code viewer (right)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: file list ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)

        header = QLabel("Files")
        header.setObjectName("headerLabel")
        left_layout.addWidget(header)

        self._file_list = QListWidget()
        self._file_list.currentItemChanged.connect(self._on_file_selected)
        left_layout.addWidget(self._file_list)

        self._file_count_label = QLabel("0 files")
        self._file_count_label.setObjectName("dimLabel")
        left_layout.addWidget(self._file_count_label)

        splitter.addWidget(left)

        # ── Right: code viewer ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self._file_path_label = QLabel("Select a file to view")
        self._file_path_label.setObjectName("dimLabel")
        right_layout.addWidget(self._file_path_label)

        self._code_viewer = QPlainTextEdit()
        self._code_viewer.setReadOnly(True)
        self._code_viewer.setFont(
            QFont(Fonts.FAMILY_MONO.split(",")[0].strip(), Fonts.SIZE_NORMAL)
        )
        self._code_viewer.setStyleSheet(
            f"background-color: {Colors.CODE_BG}; "
            f"color: {Colors.FG_PRIMARY}; "
            f"border: none; "
            f"padding: 8px;"
        )
        self._highlighter = _PythonHighlighter(self._code_viewer.document())
        right_layout.addWidget(self._code_viewer)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)  # file list ~25%
        splitter.setStretchFactor(1, 3)  # code viewer ~75%

        layout.addWidget(splitter)

        # Internal state: file_path -> content
        self._files: dict[str, str] = {}
        self._work_dir: str = ""

    def set_work_dir(self, work_dir: str) -> None:
        """Set the pipeline working directory for resolving file paths."""
        self._work_dir = work_dir

    @Slot(int, str, str)
    def on_code_output(self, stage_num: int, file_path: str, action: str) -> None:
        """Handle a CodeOutputEvent — read file content and update list."""
        abs_path = file_path
        if self._work_dir and not os.path.isabs(file_path):
            abs_path = os.path.join(self._work_dir, file_path)

        content = ""
        try:
            if os.path.isfile(abs_path):
                with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
        except OSError:
            content = f"# Could not read {abs_path}"

        display_path = file_path
        self._files[display_path] = content

        # Update list widget
        existing = self._file_list.findItems(display_path, Qt.MatchFlag.MatchExactly)
        if not existing:
            item = QListWidgetItem(display_path)
            if action == "create":
                item.setForeground(QColor(Colors.SUCCESS))
            else:
                item.setForeground(QColor(Colors.WARNING))
            self._file_list.addItem(item)

        self._file_count_label.setText(f"{self._file_list.count()} files")

        # Auto-select latest file
        self._file_list.setCurrentRow(self._file_list.count() - 1)

    @Slot(int, str, bool, str)
    def on_tool_result(
        self, stage_num: int, tool_name: str, success: bool, output: str,
    ) -> None:
        """Handle ToolResultEvent — refresh file content after write/edit."""
        if tool_name in ("write_file", "edit_file"):
            current = self._file_list.currentItem()
            if current:
                self._on_file_selected(current, None)

    def _on_file_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None,
    ) -> None:
        """Display the selected file's content in the code viewer."""
        if current is None:
            return
        path = current.text()
        self._file_path_label.setText(path)

        content = self._files.get(path, "")
        if not content:
            # Try re-reading from disk
            abs_path = path
            if self._work_dir and not os.path.isabs(path):
                abs_path = os.path.join(self._work_dir, path)
            try:
                if os.path.isfile(abs_path):
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    self._files[path] = content
            except OSError:
                pass

        self._code_viewer.setPlainText(content)

    def clear(self) -> None:
        """Reset the panel for a new pipeline run."""
        self._file_list.clear()
        self._code_viewer.clear()
        self._files.clear()
        self._file_path_label.setText("Select a file to view")
        self._file_count_label.setText("0 files")
