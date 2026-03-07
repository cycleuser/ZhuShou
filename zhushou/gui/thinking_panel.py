"""Thinking / reasoning panel — displays LLM thought process.

Shows a scrollable, append-only rich text view of LLM reasoning,
info messages, tool calls, and test results.  Each event type gets
a distinct visual treatment.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zhushou.gui.styles import Colors, Fonts


class ThinkingPanel(QWidget):
    """Append-only rich-text view of LLM reasoning and pipeline events."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Thinking / Reasoning")
        header.setObjectName("headerLabel")
        layout.addWidget(header)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(
            QFont(Fonts.FAMILY_MONO.split(",")[0].strip(), Fonts.SIZE_NORMAL)
        )
        self._text.setStyleSheet(
            f"background-color: {Colors.BG_TERTIARY}; "
            f"color: {Colors.FG_PRIMARY}; "
            f"border: none; "
            f"padding: 8px;"
        )
        layout.addWidget(self._text)

    # ── Event slots ────────────────────────────────────────────────

    @Slot(int, str)
    def on_thinking(self, stage_num: int, content: str) -> None:
        """Append LLM reasoning text."""
        if not content.strip():
            return
        self._append_html(
            f'<div style="color:{Colors.FG_PRIMARY}; margin-bottom:8px;">'
            f'{_escape(content)}</div>'
        )

    @Slot(int, str, dict)
    def on_tool_call(self, stage_num: int, tool_name: str, args: dict) -> None:
        """Show a tool being called."""
        arg_summary = _summarize_args(args)
        self._append_html(
            f'<div style="margin:4px 0;">'
            f'<span style="color:{Colors.WARNING}; font-weight:bold;">'
            f'&gt;&gt; {_escape(tool_name)}</span>'
            f'<span style="color:{Colors.FG_DIM};"> ({_escape(arg_summary)})</span>'
            f'</div>'
        )

    @Slot(int, str, bool, str)
    def on_tool_result(
        self, stage_num: int, tool_name: str, success: bool, output: str,
    ) -> None:
        """Show tool execution result."""
        color = Colors.SUCCESS if success else Colors.ERROR
        label = "OK" if success else "FAIL"
        short = output[:200] + "..." if len(output) > 200 else output
        self._append_html(
            f'<div style="margin:2px 0 6px 16px;">'
            f'<span style="color:{color}; font-weight:bold;">{label}</span> '
            f'<span style="color:{Colors.FG_DIM};">{_escape(short)}</span>'
            f'</div>'
        )

    @Slot(int, bool, str)
    def on_test_result(self, stage_num: int, passed: bool, output: str) -> None:
        """Show test suite result."""
        color = Colors.SUCCESS if passed else Colors.ERROR
        icon = "PASSED" if passed else "FAILED"
        short = output[:300] + "..." if len(output) > 300 else output
        self._append_html(
            f'<div style="margin:8px 0; padding:8px; '
            f'border-left:3px solid {color}; '
            f'background-color:{Colors.BG_SECONDARY};">'
            f'<span style="color:{color}; font-weight:bold;">Tests {icon}</span><br/>'
            f'<span style="color:{Colors.FG_DIM}; font-size:{Fonts.SIZE_SMALL}px;">'
            f'{_escape(short)}</span>'
            f'</div>'
        )

    @Slot(int, int, bool)
    def on_debug_attempt(self, attempt: int, max_retries: int, passed: bool) -> None:
        """Show debug loop iteration."""
        color = Colors.SUCCESS if passed else Colors.WARNING
        status = "PASSED" if passed else "retrying..."
        self._append_html(
            f'<div style="margin:4px 0;">'
            f'<span style="color:{color};">Debug attempt '
            f'{attempt}/{max_retries}: {status}</span>'
            f'</div>'
        )

    @Slot(str)
    def on_info(self, message: str) -> None:
        """Show an informational message."""
        self._append_html(
            f'<div style="color:{Colors.INFO}; margin:4px 0;">'
            f'{_escape(message)}</div>'
        )

    @Slot(str)
    def on_error(self, message: str) -> None:
        """Show an error message."""
        self._append_html(
            f'<div style="color:{Colors.ERROR}; font-weight:bold; margin:4px 0;">'
            f'Error: {_escape(message)}</div>'
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _append_html(self, html: str) -> None:
        """Append HTML and auto-scroll to bottom."""
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self) -> None:
        """Reset for a new pipeline run."""
        self._text.clear()


# ── Module helpers ──────────────────────────────────────────────────

def _escape(text: str) -> str:
    """HTML-escape text content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _summarize_args(args: dict[str, Any]) -> str:
    """Create a short one-line summary of tool arguments."""
    for key in ("path", "file_path", "command", "pattern", "query"):
        if key in args:
            val = str(args[key])
            return val[:80] + "..." if len(val) > 80 else val
    if args:
        first_key = next(iter(args))
        val = str(args[first_key])
        return val[:60] + "..." if len(val) > 60 else val
    return ""
