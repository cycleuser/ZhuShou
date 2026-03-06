"""Tool execution engine for the AI coding assistant."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from xml_parser import ToolCall


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    output: str


VALID_TOOLS = {"write_file", "read_file", "run_command", "list_files"}


class ToolExecutor:
    """Execute tool calls within a sandboxed working directory."""

    def __init__(self, work_dir: str):
        self.work_dir = os.path.abspath(work_dir)
        os.makedirs(self.work_dir, exist_ok=True)
        self.files_created: list[str] = []

    def _resolve_path(self, rel_path: str) -> str:
        """Resolve a relative path to an absolute path within work_dir.

        Rejects paths that escape work_dir.
        """
        # Strip leading / to treat all paths as relative to work_dir
        rel_path = rel_path.lstrip("/")
        abs_path = os.path.normpath(os.path.join(self.work_dir, rel_path))
        if not abs_path.startswith(self.work_dir):
            raise ValueError(f"Path escapes work directory: {rel_path}")
        return abs_path

    def execute(self, call: ToolCall) -> ToolResult:
        """Execute a single tool call and return the result."""
        if call.name not in VALID_TOOLS:
            return ToolResult(
                tool_name=call.name,
                success=False,
                output=f"Unknown tool: {call.name}. Valid tools: {', '.join(VALID_TOOLS)}",
            )
        try:
            handler = getattr(self, f"_tool_{call.name}")
            return handler(call.args)
        except Exception as e:
            return ToolResult(
                tool_name=call.name,
                success=False,
                output=f"Error executing {call.name}: {e}",
            )

    def execute_all(self, calls: list[ToolCall]) -> list[ToolResult]:
        """Execute a list of tool calls sequentially."""
        return [self.execute(call) for call in calls]

    # ── Tool implementations ──────────────────────────────────────────

    def _tool_write_file(self, args: dict) -> ToolResult:
        path = args.get("path")
        content = args.get("content")
        if not path:
            return ToolResult("write_file", False, "Missing 'path' argument")
        if content is None:
            return ToolResult("write_file", False, "Missing 'content' argument")

        abs_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")

        rel = os.path.relpath(abs_path, self.work_dir)
        if rel not in self.files_created:
            self.files_created.append(rel)
        return ToolResult("write_file", True, f"File written: {rel}")

    def _tool_read_file(self, args: dict) -> ToolResult:
        path = args.get("path")
        if not path:
            return ToolResult("read_file", False, "Missing 'path' argument")

        abs_path = self._resolve_path(path)
        if not os.path.isfile(abs_path):
            return ToolResult("read_file", False, f"File not found: {path}")
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult("read_file", True, content)

    def _tool_run_command(self, args: dict) -> ToolResult:
        cmd = args.get("command")
        if not cmd:
            return ToolResult("run_command", False, "Missing 'command' argument")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if not output:
                output = "(no output)"
            success = result.returncode == 0
            if not success:
                output = f"Exit code: {result.returncode}\n{output}"
            return ToolResult("run_command", success, output.strip())
        except subprocess.TimeoutExpired:
            return ToolResult("run_command", False, f"Command timed out (120s): {cmd}")

    def _tool_list_files(self, args: dict) -> ToolResult:
        path = args.get("path", ".")
        abs_path = self._resolve_path(path)
        if not os.path.isdir(abs_path):
            return ToolResult("list_files", False, f"Directory not found: {path}")

        lines = []
        for root, dirs, files in os.walk(abs_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            level = root.replace(abs_path, "").count(os.sep)
            indent = "  " * level
            basename = os.path.basename(root) or path
            lines.append(f"{indent}{basename}/")
            sub_indent = "  " * (level + 1)
            for f in sorted(files):
                if not f.startswith("."):
                    lines.append(f"{sub_indent}{f}")
        return ToolResult("list_files", True, "\n".join(lines))
