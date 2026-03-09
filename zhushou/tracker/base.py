"""Abstract base class for tracker adapters.

A tracker adapter bridges the orchestrator with an external (or local) task
source -- e.g. a local YAML file, GitHub Issues, or an in-memory list used
for testing.

Every adapter implements the same five-method interface so that the
orchestrator can poll for work, update state, and post comments regardless
of which backend is active.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from zhushou.tracker.task import Task


class TrackerAdapter(ABC):
    """Contract every tracker backend must fulfil."""

    @abstractmethod
    async def fetch_candidate_tasks(
        self,
        active_states: Sequence[str],
        terminal_states: Sequence[str],
    ) -> list[Task]:
        """Return tasks whose current state is in *active_states*.

        The adapter should exclude tasks in *terminal_states* and any
        tasks that are blocked by non-terminal siblings (if the backend
        supports blocker relationships).
        """

    @abstractmethod
    async def fetch_task_by_id(self, task_id: str) -> Task | None:
        """Fetch a single task by its unique *task_id*.

        Returns ``None`` when the task no longer exists.
        """

    @abstractmethod
    async def fetch_task_states_by_ids(
        self,
        task_ids: Sequence[str],
    ) -> dict[str, str]:
        """Return ``{task_id: current_state}`` for each given id.

        Missing tasks should be omitted from the result rather than raising.
        """

    @abstractmethod
    async def update_task_state(self, task_id: str, new_state: str) -> None:
        """Transition *task_id* to *new_state* in the backend."""

    @abstractmethod
    async def create_comment(self, task_id: str, body: str) -> None:
        """Post a comment / note on *task_id*."""
