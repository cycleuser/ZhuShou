"""Local YAML file tracker adapter.

Reads tasks from a YAML file on disk (default ``tasks.yaml``).  Each task
is a mapping with at least ``id`` and ``title``; everything else is
optional and falls back to ``Task`` defaults.

State transitions are written back to the same file atomically
(write-to-temp then rename) so that a crash mid-write never corrupts
the task list.

Example ``tasks.yaml``::

    - id: "1"
      identifier: PROJ-1
      title: Add login form
      description: Implement OAuth login page
      state: todo
      priority: 1
      labels: [frontend, auth]

    - id: "2"
      identifier: PROJ-2
      title: Fix CSV export
      state: in_progress
      blocked_by: ["1"]

Comments are stored in a companion file ``<stem>.comments.yaml`` next to
the task file so the task file stays clean.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from zhushou.tracker.base import TrackerAdapter
from zhushou.tracker.task import Task

logger = logging.getLogger(__name__)


class LocalYAMLTracker(TrackerAdapter):
    """Tracker adapter backed by a local YAML file."""

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path).resolve()
        self._comment_path = self._path.with_suffix(".comments.yaml")

    # ------------------------------------------------------------------
    # TrackerAdapter implementation
    # ------------------------------------------------------------------

    async def fetch_candidate_tasks(
        self,
        active_states: Sequence[str],
        terminal_states: Sequence[str],
    ) -> list[Task]:
        tasks = self._load_tasks()
        active_set = {s.strip().lower() for s in active_states}
        terminal_set = {s.strip().lower() for s in terminal_states}

        # Pre-fetch all states to resolve blockers
        state_map = {t.id: t.state.strip().lower() for t in tasks}

        candidates: list[Task] = []
        for t in tasks:
            normalised = t.state.strip().lower()
            if normalised not in active_set:
                continue
            if normalised in terminal_set:
                continue
            # Skip tasks blocked by non-terminal siblings
            if _has_active_blocker(t, state_map, terminal_set):
                continue
            candidates.append(t)

        return candidates

    async def fetch_task_by_id(self, task_id: str) -> Task | None:
        for t in self._load_tasks():
            if t.id == task_id:
                return t
        return None

    async def fetch_task_states_by_ids(
        self,
        task_ids: Sequence[str],
    ) -> dict[str, str]:
        id_set = set(task_ids)
        return {
            t.id: t.state
            for t in self._load_tasks()
            if t.id in id_set
        }

    async def update_task_state(self, task_id: str, new_state: str) -> None:
        raw_list = self._load_raw()
        changed = False
        for entry in raw_list:
            if isinstance(entry, dict) and str(entry.get("id", "")) == task_id:
                entry["state"] = new_state
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
                break

        if changed:
            self._save_raw(raw_list)
            logger.debug("Updated task %s → %s", task_id, new_state)
        else:
            logger.warning("update_task_state: task %s not found in %s", task_id, self._path)

    async def create_comment(self, task_id: str, body: str) -> None:
        comments = self._load_comments()
        comments.setdefault(task_id, []).append({
            "body": body,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save_comments(comments)
        logger.debug("Added comment on task %s", task_id)

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _load_raw(self) -> list[dict[str, Any]]:
        """Load the raw YAML list from disk.  Returns ``[]`` if missing."""
        if not self._path.is_file():
            return []
        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.error("Failed to read %s: %s", self._path, exc)
            return []
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict)]

    def _save_raw(self, raw_list: list[dict[str, Any]]) -> None:
        """Atomically write *raw_list* back to disk."""
        _atomic_write_yaml(self._path, raw_list)

    def _load_tasks(self) -> list[Task]:
        """Parse all entries into ``Task`` dataclasses."""
        return [_dict_to_task(entry) for entry in self._load_raw()]

    def _load_comments(self) -> dict[str, list[dict[str, Any]]]:
        if not self._comment_path.is_file():
            return {}
        try:
            data = yaml.safe_load(
                self._comment_path.read_text(encoding="utf-8"),
            )
        except (yaml.YAMLError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_comments(self, comments: dict[str, Any]) -> None:
        _atomic_write_yaml(self._comment_path, comments)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _dict_to_task(entry: dict[str, Any]) -> Task:
    """Convert a raw YAML mapping to a ``Task``, tolerating missing keys."""
    task_id = str(entry.get("id", ""))
    return Task(
        id=task_id,
        identifier=str(entry.get("identifier", task_id)),
        title=str(entry.get("title", "")),
        description=str(entry.get("description", "")),
        state=str(entry.get("state", "todo")),
        priority=int(entry.get("priority", 0)) if entry.get("priority") is not None else 0,
        labels=[str(l) for l in entry.get("labels", []) if l is not None],
        assignee=str(entry.get("assignee", "")),
        url=str(entry.get("url", "")),
        blocked_by=[str(b) for b in entry.get("blocked_by", []) if b is not None],
        created_at=_parse_dt(entry.get("created_at")),
        updated_at=_parse_dt(entry.get("updated_at")),
        metadata={k: v for k, v in entry.items()
                  if k not in _TASK_FIELDS},
    )


_TASK_FIELDS = frozenset({
    "id", "identifier", "title", "description", "state", "priority",
    "labels", "assignee", "url", "blocked_by", "created_at", "updated_at",
})


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _has_active_blocker(
    task: Task,
    state_map: dict[str, str],
    terminal_states: set[str],
) -> bool:
    """True when *task* has at least one blocker in a non-terminal state."""
    for blocker_id in task.blocked_by:
        blocker_state = state_map.get(blocker_id, "")
        if blocker_state and blocker_state not in terminal_states:
            return True
    return False


def _atomic_write_yaml(path: Path, data: Any) -> None:
    """Write YAML to *path* atomically via a temporary file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    # Write to a temp file in the same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, str(path))
    except BaseException:
        os.close(fd) if not _fd_closed(fd) else None
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _fd_closed(fd: int) -> bool:
    """Check if file descriptor is already closed."""
    try:
        os.fstat(fd)
        return False
    except OSError:
        return True
