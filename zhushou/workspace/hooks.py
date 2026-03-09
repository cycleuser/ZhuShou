"""Lifecycle hook runner for workspaces.

Executes shell commands at workspace lifecycle events (after_create,
before_run, after_run, before_remove) with configurable timeouts.

Mirrors Symphony's workspace hook execution model where hooks run via
``sh -lc`` inside the workspace directory with captured output.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HookPhase(str, Enum):
    """When in the workspace lifecycle the hook fires."""

    AFTER_CREATE = "after_create"
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_REMOVE = "before_remove"


@dataclass
class HookResult:
    """Outcome of a single hook execution."""

    phase: HookPhase
    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class HookError(Exception):
    """Raised when a *fatal* hook fails (after_create, before_run)."""

    def __init__(self, result: HookResult) -> None:
        self.result = result
        super().__init__(
            f"Hook {result.phase.value} failed "
            f"(exit={result.exit_code}, timeout={result.timed_out})"
        )


async def run_hook(
    command: str,
    workspace: str,
    phase: HookPhase,
    timeout_ms: int = 60_000,
) -> HookResult:
    """Execute *command* inside *workspace* and return the result.

    Parameters
    ----------
    command:
        Shell command string passed to ``sh -lc``.
    workspace:
        Working directory for the subprocess.
    phase:
        Which lifecycle phase this hook corresponds to.
    timeout_ms:
        Maximum wall-clock time in milliseconds.

    Returns
    -------
    HookResult with captured stdout/stderr and success flag.
    """
    timeout_s = timeout_ms / 1000.0
    logger.info("Running %s hook in %s", phase.value, workspace)

    try:
        proc = await asyncio.create_subprocess_exec(
            "sh", "-lc", command,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            result = HookResult(
                phase=phase,
                success=False,
                exit_code=-1,
                timed_out=True,
            )
            logger.warning(
                "Hook %s timed out after %.1fs in %s",
                phase.value, timeout_s, workspace,
            )
            return result

        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
        exit_code = proc.returncode or 0

        result = HookResult(
            phase=phase,
            success=(exit_code == 0),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )

        if result.success:
            logger.info("Hook %s completed (exit 0) in %s", phase.value, workspace)
        else:
            logger.warning(
                "Hook %s failed (exit %d) in %s: %s",
                phase.value, exit_code, workspace,
                stderr[:500] if stderr else "(no stderr)",
            )

        return result

    except OSError as exc:
        logger.error("Failed to start hook %s: %s", phase.value, exc)
        return HookResult(
            phase=phase,
            success=False,
            exit_code=-1,
            stderr=str(exc),
        )


async def run_lifecycle_hook(
    command: str | None,
    workspace: str,
    phase: HookPhase,
    timeout_ms: int = 60_000,
    *,
    fatal: bool = False,
) -> HookResult | None:
    """Run a hook if *command* is non-empty; optionally raise on failure.

    Parameters
    ----------
    fatal:
        If ``True`` and the hook fails, raise :class:`HookError`.
        Used for ``after_create`` and ``before_run`` hooks where
        failure should abort the pipeline run.
    """
    if not command or not command.strip():
        return None

    result = await run_hook(command, workspace, phase, timeout_ms)

    if not result.success and fatal:
        raise HookError(result)

    return result
