"""Universal task model used across the orchestration system.

Every tracker adapter normalises its native issue/ticket format into this
canonical ``Task`` dataclass so that the orchestrator, workspace manager,
and pipeline runner can work with a single, stable interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Task:
    """A unit of work dispatched by the orchestrator.

    Fields mirror the common denominator of issue trackers (Linear, GitHub
    Issues, local YAML).  Tracker adapters populate whatever subset applies.
    """

    id: str
    identifier: str
    title: str
    description: str = ""
    state: str = "todo"
    priority: int = 0
    labels: list[str] = field(default_factory=list)
    assignee: str = ""
    url: str = ""
    blocked_by: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_blocked_by_active(self, terminal_states: set[str]) -> bool:
        """True when at least one blocker is in a non-terminal state.

        ``blocked_by`` stores task identifiers.  The caller (tracker adapter)
        must resolve them to states before calling this; here we just check
        whether there are any non-empty entries left.  For the simple case,
        the orchestrator filters using fetched states directly.
        """
        return len(self.blocked_by) > 0

    def to_template_dict(self) -> dict[str, Any]:
        """Convert to a plain dict suitable for Jinja2 template rendering.

        * ``datetime`` values become ISO-8601 strings.
        * Nested dataclasses / objects become dicts recursively.
        """
        return _to_plain(self.__dict__)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return NotImplemented
        return self.id == other.id


def _to_plain(obj: Any) -> Any:
    """Recursively convert *obj* to JSON-safe primitives."""
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return _to_plain(obj.__dict__)
    return obj
