"""Typed accessor over WORKFLOW.md configuration with safe defaults.

Every orchestration-relevant setting is accessed through this class so
that the rest of the system never touches raw dicts.  Missing keys
fall back to sensible defaults (matching Symphony's ``config.ex``).

Supports ``$ENV_VAR`` expansion in string values.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

_ENV_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_env(value: str) -> str:
    """Replace ``$VAR_NAME`` with the environment variable's value."""
    def _replacer(m: re.Match[str]) -> str:
        return os.environ.get(m.group(1), m.group(0))
    return _ENV_RE.sub(_replacer, value)


def _get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Drill into nested dicts: ``_get_nested(d, 'a', 'b')`` -> ``d['a']['b']``."""
    current: Any = data
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k)
        if current is None:
            return default
    return current


class WorkflowConfig:
    """Read-only typed accessor over the raw YAML config dict.

    All getters expand ``$ENV_VAR`` references in string values and
    return documented defaults for missing keys.
    """

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        self._raw: dict[str, Any] = raw if raw is not None else {}

    # ── Tracker ───────────────────────────────────────────────────

    @property
    def tracker_kind(self) -> str:
        """``local`` | ``github`` | ``memory``.  Default ``local``."""
        val = _get_nested(self._raw, "tracker", "kind", default="local")
        return _expand_env(str(val))

    @property
    def tracker_file(self) -> str:
        """Path to local task file (for ``kind: local``).  Default ``tasks.yaml``."""
        val = _get_nested(self._raw, "tracker", "file", default="tasks.yaml")
        return _expand_env(str(val))

    @property
    def tracker_repo(self) -> str:
        """GitHub ``owner/repo`` (for ``kind: github``).  Default ``""``."""
        val = _get_nested(self._raw, "tracker", "repo", default="")
        return _expand_env(str(val))

    @property
    def tracker_label(self) -> str:
        """GitHub label filter.  Default ``""``."""
        val = _get_nested(self._raw, "tracker", "label", default="")
        return _expand_env(str(val))

    @property
    def tracker_api_key(self) -> str:
        """API key / token for the tracker backend.  Default ``""``."""
        val = _get_nested(self._raw, "tracker", "api_key", default="")
        return _expand_env(str(val))

    @property
    def active_states(self) -> list[str]:
        val = _get_nested(self._raw, "tracker", "active_states",
                          default=["todo", "in_progress"])
        return [str(s) for s in val] if isinstance(val, list) else ["todo", "in_progress"]

    @property
    def terminal_states(self) -> list[str]:
        val = _get_nested(self._raw, "tracker", "terminal_states",
                          default=["done", "cancelled"])
        return [str(s) for s in val] if isinstance(val, list) else ["done", "cancelled"]

    # ── Polling ───────────────────────────────────────────────────

    @property
    def poll_interval_ms(self) -> int:
        return int(_get_nested(self._raw, "polling", "interval_ms", default=30_000))

    # ── Workspace ─────────────────────────────────────────────────

    @property
    def workspace_root(self) -> str:
        val = _get_nested(self._raw, "workspace", "root",
                          default="~/.zhushou/workspaces")
        expanded = _expand_env(str(val))
        return str(Path(expanded).expanduser())

    # ── Agent ─────────────────────────────────────────────────────

    @property
    def max_concurrent_agents(self) -> int:
        return int(_get_nested(self._raw, "agent", "max_concurrent_agents", default=3))

    @property
    def max_turns(self) -> int:
        return int(_get_nested(self._raw, "agent", "max_turns", default=20))

    @property
    def max_retry_backoff_ms(self) -> int:
        return int(_get_nested(self._raw, "agent", "max_retry_backoff_ms", default=300_000))

    @property
    def stall_timeout_ms(self) -> int:
        return int(_get_nested(self._raw, "agent", "stall_timeout_ms", default=600_000))

    # ── Hooks ─────────────────────────────────────────────────────

    def _hook(self, name: str) -> str | None:
        val = _get_nested(self._raw, "hooks", name, default=None)
        if val is None:
            return None
        return _expand_env(str(val))

    @property
    def hook_after_create(self) -> str | None:
        return self._hook("after_create")

    @property
    def hook_before_run(self) -> str | None:
        return self._hook("before_run")

    @property
    def hook_after_run(self) -> str | None:
        return self._hook("after_run")

    @property
    def hook_before_remove(self) -> str | None:
        return self._hook("before_remove")

    @property
    def hook_timeout_ms(self) -> int:
        return int(_get_nested(self._raw, "hooks", "timeout_ms", default=60_000))

    # ── Stages ────────────────────────────────────────────────────

    @property
    def enabled_stages(self) -> list[str]:
        val = _get_nested(self._raw, "stages", "enabled", default=None)
        if isinstance(val, list):
            return [str(s) for s in val]
        return [
            "requirements", "architecture", "tasks", "function_design",
            "implementation", "testing", "debugging", "verification",
        ]

    def stage_prompt_override(self, stage_key: str) -> str | None:
        """Return a custom system-prompt override for *stage_key*, or None."""
        overrides = _get_nested(self._raw, "stages", "prompts", default=None)
        if isinstance(overrides, dict):
            val = overrides.get(stage_key)
            if val is not None:
                return _expand_env(str(val))
        return None

    # ── Observability ─────────────────────────────────────────────

    @property
    def dashboard_enabled(self) -> bool:
        return bool(_get_nested(self._raw, "observability", "dashboard_enabled", default=True))

    @property
    def dashboard_refresh_ms(self) -> int:
        return int(_get_nested(self._raw, "observability", "refresh_ms", default=1000))

    # ── Logging ───────────────────────────────────────────────────

    @property
    def log_file(self) -> str:
        val = _get_nested(self._raw, "logging", "file",
                          default="~/.zhushou/logs/zhushou.log")
        expanded = _expand_env(str(val))
        return str(Path(expanded).expanduser())

    @property
    def log_max_bytes(self) -> int:
        return int(_get_nested(self._raw, "logging", "max_bytes", default=10_485_760))

    @property
    def log_max_files(self) -> int:
        return int(_get_nested(self._raw, "logging", "max_files", default=5))

    # ── Validation ────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return a list of validation warnings (empty means all OK)."""
        warnings: list[str] = []
        if self.max_concurrent_agents < 1:
            warnings.append("agent.max_concurrent_agents must be >= 1")
        if self.poll_interval_ms < 1000:
            warnings.append("polling.interval_ms should be >= 1000")
        if self.tracker_kind not in ("local", "github", "memory"):
            warnings.append(f"tracker.kind '{self.tracker_kind}' is not recognised")
        if self.tracker_kind == "github" and not self.tracker_repo:
            warnings.append("tracker.repo is required when tracker.kind is github")
        return warnings

    # ── Repr ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"WorkflowConfig(tracker={self.tracker_kind}, "
            f"agents={self.max_concurrent_agents}, "
            f"poll={self.poll_interval_ms}ms)"
        )
