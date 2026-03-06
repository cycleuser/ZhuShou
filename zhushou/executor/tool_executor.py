"""ZhuShou tool executor - dispatches tool calls to built-in handlers.

Evolved from ``old/tools.py`` with OpenAI function-calling integration,
sibling package discovery, and .git protection.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zhushou.executor.builtin_tools import ALL_TOOLS, TOOL_HANDLERS


class ToolExecutor:
    """Execute tool calls within a sandboxed working directory.

    Parameters
    ----------
    work_dir : str
        Root directory for all file operations.
    python_path : str
        Path to the Python interpreter (used by ``python_exec``).
        Falls back to the current interpreter when empty.
    """

    def __init__(self, work_dir: str, python_path: str = "") -> None:
        self.work_dir: str = os.path.abspath(work_dir)
        os.makedirs(self.work_dir, exist_ok=True)
        self.python_path: str = python_path
        self.files_created: list[str] = []

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, rel_path: str) -> str:
        """Resolve *rel_path* relative to ``work_dir``.

        Raises :class:`ValueError` when the resulting path escapes
        the working directory.
        """
        rel_path = rel_path.lstrip("/")
        abs_path = os.path.normpath(os.path.join(self.work_dir, rel_path))
        if not abs_path.startswith(self.work_dir):
            raise ValueError(f"Path escapes work directory: {rel_path}")
        return abs_path

    @staticmethod
    def _is_protected(path: str) -> bool:
        """Return ``True`` when *path* resides inside a ``.git`` directory."""
        parts = Path(path).parts
        return ".git" in parts

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call by *name* and return the result.

        Returns
        -------
        dict
            ``{"success": bool, "output": str}``
        """
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return {
                "success": False,
                "output": (
                    f"Unknown tool: {name}. "
                    f"Available tools: {', '.join(TOOL_HANDLERS)}"
                ),
            }

        try:
            result = handler(self.work_dir, arguments)

            # Track files created by write_file
            if name == "write_file" and result.get("success"):
                rel_path = arguments.get("path", "")
                if rel_path and rel_path not in self.files_created:
                    self.files_created.append(rel_path)

            return result
        except Exception as exc:
            return {
                "success": False,
                "output": f"Error executing {name}: {exc}",
            }

    # ------------------------------------------------------------------
    # Schema export
    # ------------------------------------------------------------------

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        """Return OpenAI-format tool definitions for all built-in tools."""
        return list(ALL_TOOLS)
