"""Programmatic entry points for the orchestration daemon.

Thin wrappers that wire together workflow store, tracker, event bus,
dashboard, and the async orchestration loop.  Called by the CLI
(``zhushou daemon``) and can be imported directly for embedding.

Usage::

    import asyncio
    from zhushou.api_daemon import run_daemon

    asyncio.run(run_daemon("./WORKFLOW.md"))
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def run_daemon(
    workflow_path: str | Path = "./WORKFLOW.md",
    *,
    dashboard: bool = True,
    llm_client_factory: Any = None,
) -> None:
    """Boot the orchestration loop and (optionally) the live dashboard.

    Parameters
    ----------
    workflow_path : str | Path
        Path to the ``WORKFLOW.md`` configuration file.
    dashboard : bool
        Whether to run the Rich terminal dashboard alongside the loop.
    llm_client_factory : callable | None
        Optional zero-arg callable returning an LLM client.  When *None*
        the default factory from ``ZhuShouConfig`` is used.
    """
    from zhushou.events.bus import PipelineEventBus
    from zhushou.orchestrator.loop import Orchestrator
    from zhushou.tracker import create_tracker
    from zhushou.workflow.store import WorkflowStore

    # 1. Load workflow configuration
    wf_path = Path(workflow_path).resolve()
    if not wf_path.is_file():
        raise FileNotFoundError(f"Workflow file not found: {wf_path}")

    store = WorkflowStore(str(wf_path))
    config = store.current_config

    # 2. Create tracker from config
    tracker = create_tracker(config)

    # 3. Create shared event bus
    event_bus = PipelineEventBus()

    # 4. Create orchestrator
    orch = Orchestrator(
        workflow_store=store,
        tracker=tracker,
        event_bus=event_bus,
        llm_client_factory=llm_client_factory,
    )

    # 5. Optionally start the live dashboard
    dash_task: asyncio.Task[None] | None = None
    if dashboard and config.dashboard_enabled:
        from zhushou.display.dashboard import StatusDashboard

        dash = StatusDashboard(
            orchestrator=orch,
            event_bus=event_bus,
            refresh_ms=config.dashboard_refresh_ms,
        )
        dash_task = dash.start_background()

    # 6. Run orchestrator (blocks until Ctrl-C or stop())
    try:
        await orch.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down")
    finally:
        await orch.stop()
        if dash_task and not dash_task.done():
            dash_task.cancel()
            try:
                await dash_task
            except asyncio.CancelledError:
                pass

    logger.info("Daemon stopped")


def get_snapshot_dict(
    workflow_path: str | Path = "./WORKFLOW.md",
) -> dict[str, Any]:
    """Return a one-shot orchestrator status snapshot (non-blocking).

    Useful for ``zhushou status`` -- reads the workflow config but does
    not start the loop.  Returns a dict suitable for display helpers.
    """
    from zhushou.workflow.store import WorkflowStore

    wf_path = Path(workflow_path).resolve()
    if not wf_path.is_file():
        return {"error": f"Workflow file not found: {wf_path}"}

    store = WorkflowStore(str(wf_path))
    config = store.current_config

    return {
        "tracker_kind": config.tracker_kind,
        "max_concurrent": config.max_concurrent_agents,
        "poll_interval_ms": config.poll_interval_ms,
        "workspace_root": config.workspace_root,
        "dashboard_enabled": config.dashboard_enabled,
        "workflow_path": str(wf_path),
        "running_count": 0,
        "completed_count": 0,
        "retry_count": 0,
        "uptime_seconds": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
