"""Orchestrator state model.

Defines the mutable runtime state that the orchestrator maintains
across ticks -- running workers, retry queue, claimed task set,
token totals, and timing information.

Mirrors Symphony's monolithic ``%State{}`` struct in ``orchestrator.ex``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from zhushou.tracker.task import Task


@dataclass
class TokenTotals:
    """Accumulated token counts across all pipeline runs."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, input_t: int = 0, output_t: int = 0) -> None:
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.total_tokens += input_t + output_t


@dataclass
class RunningEntry:
    """State of a single running pipeline worker."""

    task: Task
    workspace: str
    started_at: float = field(default_factory=time.monotonic)
    turn_count: int = 0
    current_stage: int = 0
    total_stages: int = 8
    last_event_at: float = field(default_factory=time.monotonic)
    asyncio_task: asyncio.Task[Any] | None = None
    token_totals: TokenTotals = field(default_factory=TokenTotals)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def seconds_since_last_event(self) -> float:
        return time.monotonic() - self.last_event_at


@dataclass
class RetryEntry:
    """State of a task queued for retry with exponential backoff."""

    task: Task
    attempt: int
    due_at: float  # monotonic time
    error: str = ""
    timer_handle: asyncio.TimerHandle | None = None

    @property
    def seconds_until_due(self) -> float:
        return max(0.0, self.due_at - time.monotonic())


@dataclass
class OrchestratorState:
    """Complete mutable runtime state of the orchestrator.

    This is the Python equivalent of Symphony's ``%State{}`` struct.
    All state transitions happen inside the orchestrator's asyncio
    event loop, so no locking is required.
    """

    running: dict[str, RunningEntry] = field(default_factory=dict)
    claimed: set[str] = field(default_factory=set)
    retry_queue: dict[str, RetryEntry] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    token_totals: TokenTotals = field(default_factory=TokenTotals)
    started_at: float = field(default_factory=time.monotonic)

    @property
    def running_count(self) -> int:
        return len(self.running)

    @property
    def retry_count(self) -> int:
        return len(self.retry_queue)

    def available_slots(self, max_concurrent: int) -> int:
        return max(0, max_concurrent - len(self.running))

    def is_claimed(self, task_id: str) -> bool:
        return task_id in self.claimed

    def claim(self, task_id: str) -> None:
        self.claimed.add(task_id)

    def release(self, task_id: str) -> None:
        self.claimed.discard(task_id)
        self.running.pop(task_id, None)
        self.retry_queue.pop(task_id, None)

    def mark_completed(self, task_id: str) -> None:
        self.completed.add(task_id)
        self.release(task_id)
