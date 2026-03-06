"""Persistent key-value memory backed by a JSON file.

Storage location: ``~/.zhushou/memory.json``
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


_DEFAULT_PATH = Path.home() / ".zhushou" / "memory.json"


class PersistentMemory:
    """Simple JSON key-value store with auto-save on mutation.

    Parameters
    ----------
    path : str | Path | None
        Override the default storage location for testing.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path: Path = Path(path) if path else _DEFAULT_PATH
        self._data: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by *key*, returning *default* if absent."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a *key* to *value* and persist to disk."""
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        """Delete *key* if it exists. Returns ``True`` when removed."""
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def search(self, query: str) -> list[tuple[str, Any]]:
        """Return all ``(key, value)`` pairs where *query* appears in the key or string value."""
        query_lower = query.lower()
        results: list[tuple[str, Any]] = []
        for key, value in self._data.items():
            if query_lower in key.lower():
                results.append((key, value))
            elif isinstance(value, str) and query_lower in value.lower():
                results.append((key, value))
        return results

    def keys(self) -> list[str]:
        """Return all stored keys."""
        return list(self._data.keys())

    def clear(self) -> None:
        """Remove all entries and persist."""
        self._data.clear()
        self._save()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load data from disk if the file exists."""
        if self._path.is_file():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        """Persist current data to disk."""
        os.makedirs(self._path.parent, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            tmp_path.replace(self._path)
        except OSError:
            # Best-effort; don't crash the assistant
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def __repr__(self) -> str:
        return f"PersistentMemory(path={self._path!r}, keys={len(self._data)})"
