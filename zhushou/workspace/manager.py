"""Per-task isolated workspace management.

Creates, validates, and cleans up dedicated directories for each task
dispatched by the orchestrator -- ensuring path containment, symlink
escape detection, and proper lifecycle hook execution.

Mirrors Symphony's ``workspace.ex`` safety model.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

from zhushou.tracker.task import Task
from zhushou.workspace.hooks import (
    HookPhase,
    HookResult,
    run_lifecycle_hook,
)

logger = logging.getLogger(__name__)

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]")
_EXCLUDED_ARTIFACTS = {".elixir_ls", "tmp", "__pycache__", ".pytest_cache"}


class WorkspaceError(Exception):
    """Raised for workspace safety violations or creation failures."""


def sanitize_identifier(identifier: str) -> str:
    """Replace non-safe chars with ``_``.

    >>> sanitize_identifier("TASK-1")
    'TASK-1'
    >>> sanitize_identifier("issue/special chars!")
    'issue_special_chars_'
    """
    return _SAFE_ID_RE.sub("_", identifier)


def _validate_path(workspace: Path, root: Path) -> None:
    """Ensure *workspace* is safely contained inside *root*.

    Raises :class:`WorkspaceError` on violations.
    """
    resolved_workspace = workspace.resolve()
    resolved_root = root.resolve()

    # Must be a child of root, not root itself
    if resolved_workspace == resolved_root:
        raise WorkspaceError(
            f"Workspace path equals root: {resolved_workspace}"
        )

    if not resolved_workspace.is_relative_to(resolved_root):
        raise WorkspaceError(
            f"Workspace {resolved_workspace} escapes root {resolved_root}"
        )

    # Walk each path component and reject symlinks
    current = resolved_root
    relative_parts = resolved_workspace.relative_to(resolved_root).parts
    for part in relative_parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise WorkspaceError(
                f"Symlink detected in workspace path: {current}"
            )


class WorkspaceManager:
    """Manages isolated workspace directories under a common root.

    Parameters
    ----------
    root:
        Parent directory where all workspaces live.
        Created automatically if it doesn't exist.
    hooks:
        Dict with optional hook commands keyed by phase name.
    hook_timeout_ms:
        Default timeout for hook execution.
    """

    def __init__(
        self,
        root: str | Path,
        hooks: dict[str, str | None] | None = None,
        hook_timeout_ms: int = 60_000,
    ) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._hooks = hooks or {}
        self._hook_timeout_ms = hook_timeout_ms

    @property
    def root(self) -> Path:
        return self._root

    # ── Workspace lifecycle ───────────────────────────────────────

    async def create_for_task(self, task: Task) -> Path:
        """Create (or reuse) an isolated workspace for *task*.

        Returns the workspace path.  Runs the ``after_create`` hook only
        if the directory was freshly created.
        """
        safe_id = sanitize_identifier(task.identifier)
        workspace = self._root / safe_id
        _validate_path(workspace, self._root)

        newly_created = not workspace.exists()

        workspace.mkdir(parents=True, exist_ok=True)

        if not newly_created:
            # Clean stale build artifacts on reuse
            self._clean_artifacts(workspace)

        if newly_created:
            await run_lifecycle_hook(
                self._hooks.get("after_create"),
                str(workspace),
                HookPhase.AFTER_CREATE,
                self._hook_timeout_ms,
                fatal=True,
            )

        logger.info(
            "%s workspace for %s at %s",
            "Created" if newly_created else "Reusing",
            task.identifier, workspace,
        )
        return workspace

    async def before_run(self, workspace: Path) -> HookResult | None:
        """Run the ``before_run`` hook.  Fatal on failure."""
        return await run_lifecycle_hook(
            self._hooks.get("before_run"),
            str(workspace),
            HookPhase.BEFORE_RUN,
            self._hook_timeout_ms,
            fatal=True,
        )

    async def after_run(self, workspace: Path) -> HookResult | None:
        """Run the ``after_run`` hook.  Non-fatal (logged only)."""
        return await run_lifecycle_hook(
            self._hooks.get("after_run"),
            str(workspace),
            HookPhase.AFTER_RUN,
            self._hook_timeout_ms,
            fatal=False,
        )

    async def cleanup_task(self, task: Task) -> None:
        """Remove the workspace for *task*, running ``before_remove`` hook."""
        safe_id = sanitize_identifier(task.identifier)
        workspace = self._root / safe_id
        if not workspace.exists():
            return

        await run_lifecycle_hook(
            self._hooks.get("before_remove"),
            str(workspace),
            HookPhase.BEFORE_REMOVE,
            self._hook_timeout_ms,
            fatal=False,
        )

        try:
            shutil.rmtree(workspace)
            logger.info("Removed workspace for %s", task.identifier)
        except OSError as exc:
            logger.warning("Failed to remove workspace %s: %s", workspace, exc)

    async def cleanup_terminal_tasks(
        self,
        terminal_task_ids: set[str],
        id_to_task: dict[str, Task],
    ) -> int:
        """Remove workspaces for tasks in terminal states.

        Called at orchestrator startup to prevent stale workspace accumulation.
        Returns the count of workspaces removed.
        """
        removed = 0
        for task_id in terminal_task_ids:
            task = id_to_task.get(task_id)
            if task:
                await self.cleanup_task(task)
                removed += 1
        return removed

    def workspace_path(self, task: Task) -> Path:
        """Return the workspace path for *task* (may not exist yet)."""
        safe_id = sanitize_identifier(task.identifier)
        return self._root / safe_id

    def list_workspaces(self) -> list[Path]:
        """Return paths of all existing workspaces."""
        if not self._root.exists():
            return []
        return [p for p in self._root.iterdir() if p.is_dir()]

    # ── Internal ──────────────────────────────────────────────────

    @staticmethod
    def _clean_artifacts(workspace: Path) -> None:
        """Remove known temporary build artifacts on workspace reuse."""
        for entry in workspace.iterdir():
            if entry.name in _EXCLUDED_ARTIFACTS and entry.is_dir():
                try:
                    shutil.rmtree(entry)
                except OSError:
                    pass
