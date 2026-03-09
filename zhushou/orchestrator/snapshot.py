"""Immutable snapshots of orchestrator state for UI rendering.

Snapshots are created inside the event loop and consumed by the
dashboard renderer (terminal or web).  Being immutable dataclasses
they are safe to pass across threads without locking.

Mirrors Symphony's snapshot/fingerprint pattern from ``orchestrator.ex``.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from zhushou.orchestrator.state import OrchestratorState, RunningEntry, RetryEntry


@dataclass(frozen=True)
class RunningSnapshot:
    """Immutable view of a single running worker."""

    task_id: str = ""
    identifier: str = ""
    title: str = ""
    state: str = ""
    workspace: str = ""
    elapsed_seconds: float = 0.0
    current_stage: int = 0
    total_stages: int = 8
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class RetrySnapshot:
    """Immutable view of a retry-queued task."""

    task_id: str = ""
    identifier: str = ""
    attempt: int = 0
    seconds_until_due: float = 0.0
    error: str = ""


@dataclass(frozen=True)
class OrchestratorSnapshot:
    """Complete immutable snapshot of the orchestrator state.

    Used by the dashboard to render without holding any locks.
    """

    running: list[RunningSnapshot] = field(default_factory=list)
    retrying: list[RetrySnapshot] = field(default_factory=list)
    completed_count: int = 0
    running_count: int = 0
    retry_count: int = 0
    max_concurrent: int = 3
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    uptime_seconds: float = 0.0
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_snapshot(
    state: OrchestratorState,
    max_concurrent: int = 3,
) -> OrchestratorSnapshot:
    """Create an immutable snapshot from the current mutable state."""
    running_snaps = []
    for task_id, entry in state.running.items():
        running_snaps.append(RunningSnapshot(
            task_id=task_id,
            identifier=entry.task.identifier,
            title=entry.task.title,
            state=entry.task.state,
            workspace=entry.workspace,
            elapsed_seconds=entry.elapsed_seconds,
            current_stage=entry.current_stage,
            total_stages=entry.total_stages,
            input_tokens=entry.token_totals.input_tokens,
            output_tokens=entry.token_totals.output_tokens,
            total_tokens=entry.token_totals.total_tokens,
        ))

    retry_snaps = []
    for task_id, entry in state.retry_queue.items():
        retry_snaps.append(RetrySnapshot(
            task_id=task_id,
            identifier=entry.task.identifier,
            attempt=entry.attempt,
            seconds_until_due=entry.seconds_until_due,
            error=entry.error,
        ))

    snap = OrchestratorSnapshot(
        running=running_snaps,
        retrying=retry_snaps,
        completed_count=len(state.completed),
        running_count=state.running_count,
        retry_count=state.retry_count,
        max_concurrent=max_concurrent,
        input_tokens=state.token_totals.input_tokens,
        output_tokens=state.token_totals.output_tokens,
        total_tokens=state.token_totals.total_tokens,
        uptime_seconds=time.monotonic() - state.started_at,
    )

    # Compute fingerprint for change detection
    fp_data = json.dumps(snap.to_dict(), sort_keys=True, default=str)
    fingerprint = hashlib.sha256(fp_data.encode()).hexdigest()[:16]

    # Reconstruct with fingerprint (frozen dataclass workaround)
    return OrchestratorSnapshot(
        running=snap.running,
        retrying=snap.retrying,
        completed_count=snap.completed_count,
        running_count=snap.running_count,
        retry_count=snap.retry_count,
        max_concurrent=snap.max_concurrent,
        input_tokens=snap.input_tokens,
        output_tokens=snap.output_tokens,
        total_tokens=snap.total_tokens,
        uptime_seconds=snap.uptime_seconds,
        fingerprint=fingerprint,
    )
