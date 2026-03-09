"""In-memory tracker adapter for testing.

Stores tasks in a plain Python list -- no I/O, no persistence.  Useful for
unit tests and the orchestrator's own test harness.
"""

from __future__ import annotations

from typing import Sequence

from zhushou.tracker.base import TrackerAdapter
from zhushou.tracker.task import Task


class MemoryTracker(TrackerAdapter):
    """Fully in-process tracker backed by a ``list[Task]``."""

    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks: list[Task] = list(tasks) if tasks else []
        self._comments: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Mutations (test helpers, not part of the ABC)
    # ------------------------------------------------------------------

    def add_task(self, task: Task) -> None:
        self._tasks.append(task)

    def get_comments(self, task_id: str) -> list[str]:
        return list(self._comments.get(task_id, []))

    # ------------------------------------------------------------------
    # TrackerAdapter implementation
    # ------------------------------------------------------------------

    async def fetch_candidate_tasks(
        self,
        active_states: Sequence[str],
        terminal_states: Sequence[str],
    ) -> list[Task]:
        active_set = {s.strip().lower() for s in active_states}
        terminal_set = {s.strip().lower() for s in terminal_states}
        candidates: list[Task] = []
        for t in self._tasks:
            normalised = t.state.strip().lower()
            if normalised in active_set and normalised not in terminal_set:
                candidates.append(t)
        return candidates

    async def fetch_task_by_id(self, task_id: str) -> Task | None:
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    async def fetch_task_states_by_ids(
        self,
        task_ids: Sequence[str],
    ) -> dict[str, str]:
        id_set = set(task_ids)
        return {t.id: t.state for t in self._tasks if t.id in id_set}

    async def update_task_state(self, task_id: str, new_state: str) -> None:
        for t in self._tasks:
            if t.id == task_id:
                t.state = new_state
                return

    async def create_comment(self, task_id: str, body: str) -> None:
        self._comments.setdefault(task_id, []).append(body)
