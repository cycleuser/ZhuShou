"""Append-only conversation log stored as JSONL files.

Storage location: ``~/.zhushou/logs/{YYYY-MM-DD}.jsonl``
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


_DEFAULT_LOGS_DIR = Path.home() / ".zhushou" / "logs"


class ConversationLog:
    """JSONL-backed conversation logger.

    Each day produces one file containing timestamped message entries.

    Parameters
    ----------
    logs_dir : str | Path | None
        Override the default ``~/.zhushou/logs`` directory.
    """

    def __init__(self, logs_dir: str | Path | None = None) -> None:
        self._logs_dir: Path = Path(logs_dir) if logs_dir else _DEFAULT_LOGS_DIR
        os.makedirs(self._logs_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(
        self,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Append a message entry to today's log file.

        Parameters
        ----------
        role : str
            Message role (``"user"``, ``"assistant"``, ``"system"``, ``"tool"``).
        content : str
            Message content.
        metadata : dict | None
            Optional extra data (model, tokens, etc.).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if metadata:
            entry["metadata"] = metadata

        path = self.get_today_path()
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # best-effort logging

    def load_recent(self, n: int = 50) -> list[dict[str, Any]]:
        """Load the *n* most recent log entries across all log files.

        Entries are returned in chronological order (oldest first).
        """
        all_entries: list[dict[str, Any]] = []

        # Sort log files reverse-chronologically so we can stop early
        log_files = sorted(self._logs_dir.glob("*.jsonl"), reverse=True)

        for log_path in log_files:
            entries_in_file: list[dict[str, Any]] = []
            try:
                with open(log_path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                entries_in_file.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except OSError:
                continue

            all_entries = entries_in_file + all_entries
            if len(all_entries) >= n:
                break

        # Return only the last *n* entries
        return all_entries[-n:]

    def get_today_path(self) -> Path:
        """Return the log file path for today (UTC)."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._logs_dir / f"{date_str}.jsonl"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def list_log_files(self) -> list[Path]:
        """Return all log file paths sorted by date."""
        return sorted(self._logs_dir.glob("*.jsonl"))

    def __repr__(self) -> str:
        return f"ConversationLog(logs_dir={self._logs_dir!r})"
