"""Pipeline event type definitions.

All events are frozen dataclasses (immutable, safe to pass between threads).
Each carries a ``to_dict()`` method for JSON serialization (Web/WebSocket).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PipelineEvent:
    """Base event — every pipeline event inherits from this."""

    event_type: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Stage lifecycle ───────────────────────────────────────────────


@dataclass(frozen=True)
class StageStartEvent(PipelineEvent):
    """Emitted when a pipeline stage begins."""

    event_type: str = field(default="stage_start", init=False)
    stage_num: int = 0
    total_stages: int = 0
    stage_name: str = ""


@dataclass(frozen=True)
class StageCompleteEvent(PipelineEvent):
    """Emitted when a pipeline stage finishes."""

    event_type: str = field(default="stage_complete", init=False)
    stage_num: int = 0
    stage_name: str = ""
    duration_seconds: float = 0.0


# ── LLM output ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ThinkingEvent(PipelineEvent):
    """LLM reasoning / response text."""

    event_type: str = field(default="thinking", init=False)
    stage_num: int = 0
    content: str = ""


# ── Code / file operations ────────────────────────────────────────


@dataclass(frozen=True)
class CodeOutputEvent(PipelineEvent):
    """A source file was created or edited."""

    event_type: str = field(default="code_output", init=False)
    stage_num: int = 0
    file_path: str = ""
    action: str = ""  # "create" | "edit"


# ── Tool calls ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolCallEvent(PipelineEvent):
    """A tool is about to be executed."""

    event_type: str = field(default="tool_call", init=False)
    stage_num: int = 0
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Truncate large argument values for serialization
        args = d.get("arguments", {})
        for k, v in args.items():
            if isinstance(v, str) and len(v) > 500:
                args[k] = v[:500] + "..."
        return d


@dataclass(frozen=True)
class ToolResultEvent(PipelineEvent):
    """A tool execution completed."""

    event_type: str = field(default="tool_result", init=False)
    stage_num: int = 0
    tool_name: str = ""
    success: bool = True
    output: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Truncate large output
        if isinstance(d.get("output"), str) and len(d["output"]) > 1000:
            d["output"] = d["output"][:1000] + "..."
        return d


# ── Testing ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class TestResultEvent(PipelineEvent):
    """Test suite execution result."""

    event_type: str = field(default="test_result", init=False)
    stage_num: int = 0
    passed: bool = False
    output: str = ""


@dataclass(frozen=True)
class DebugAttemptEvent(PipelineEvent):
    """Debug loop iteration status."""

    event_type: str = field(default="debug_attempt", init=False)
    attempt: int = 0
    max_retries: int = 0
    passed: bool = False


# ── Pipeline lifecycle ────────────────────────────────────────────


@dataclass(frozen=True)
class PipelineCompleteEvent(PipelineEvent):
    """Pipeline finished (success or failure)."""

    event_type: str = field(default="pipeline_complete", init=False)
    stats: dict[str, Any] = field(default_factory=dict)


# ── Messages ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class InfoEvent(PipelineEvent):
    """General informational message."""

    event_type: str = field(default="info", init=False)
    message: str = ""


@dataclass(frozen=True)
class ErrorEvent(PipelineEvent):
    """Error message."""

    event_type: str = field(default="error", init=False)
    message: str = ""
