"""Async orchestration loop -- the heart of ZhuShou v2.

Continuously polls a tracker for tasks, dispatches concurrent pipeline
workers to isolated workspaces, reconciles running state, and manages
retry scheduling with exponential backoff.

Python asyncio equivalent of Symphony's GenServer-based ``orchestrator.ex``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from zhushou.events.bus import PipelineEventBus
from zhushou.events.types import (
    DashboardSnapshotEvent,
    ErrorEvent,
    InfoEvent,
    OrchestratorTickEvent,
    TaskCompletedEvent,
    TaskDispatchedEvent,
    TaskRetryingEvent,
    TaskStalledEvent,
)
from zhushou.orchestrator.retry import retry_delay
from zhushou.orchestrator.snapshot import OrchestratorSnapshot, create_snapshot
from zhushou.orchestrator.state import (
    OrchestratorState,
    RetryEntry,
    RunningEntry,
)
from zhushou.tracker.base import TrackerAdapter
from zhushou.tracker.task import Task
from zhushou.workflow.config import WorkflowConfig
from zhushou.workflow.store import WorkflowStore
from zhushou.workspace.hooks import HookError
from zhushou.workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Async orchestration loop managing concurrent pipeline runs.

    Usage::

        orch = Orchestrator(workflow_path="./WORKFLOW.md", ...)
        await orch.start()  # blocks until stop() or KeyboardInterrupt
    """

    def __init__(
        self,
        workflow_store: WorkflowStore,
        tracker: TrackerAdapter,
        event_bus: PipelineEventBus | None = None,
        llm_client_factory: Any = None,
    ) -> None:
        self._workflow_store = workflow_store
        self._tracker = tracker
        self._event_bus = event_bus or PipelineEventBus()
        self._llm_client_factory = llm_client_factory
        self._state = OrchestratorState()
        self._semaphore: asyncio.Semaphore | None = None
        self._tick_handle: asyncio.TimerHandle | None = None
        self._running = False
        self._workspace_mgr: WorkspaceManager | None = None
        self._last_snapshot_fingerprint: str = ""

    # ── Public API ────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the orchestration loop.  Blocks until ``stop()``."""
        config = self._workflow_store.current_config
        self._workspace_mgr = WorkspaceManager(
            root=config.workspace_root,
            hooks={
                "after_create": config.hook_after_create,
                "before_run": config.hook_before_run,
                "after_run": config.hook_after_run,
                "before_remove": config.hook_before_remove,
            },
            hook_timeout_ms=config.hook_timeout_ms,
        )
        self._semaphore = asyncio.Semaphore(config.max_concurrent_agents)
        self._running = True
        self._state = OrchestratorState()

        # Start workflow file watcher
        self._workflow_store.start_watching()

        logger.info(
            "Orchestrator starting (tracker=%s, agents=%d, poll=%dms)",
            config.tracker_kind,
            config.max_concurrent_agents,
            config.poll_interval_ms,
        )
        self._emit(InfoEvent(
            message=f"Orchestrator started: max_agents={config.max_concurrent_agents}, "
                    f"poll={config.poll_interval_ms}ms",
        ))

        # Startup cleanup: remove workspaces for terminal-state tasks
        await self._startup_cleanup()

        # Main tick loop
        try:
            while self._running:
                await self._tick()
                config = self._workflow_store.current_config
                await asyncio.sleep(config.poll_interval_ms / 1000.0)
        except asyncio.CancelledError:
            logger.info("Orchestrator cancelled")
        finally:
            await self._shutdown()

    async def stop(self) -> None:
        """Signal the orchestration loop to stop."""
        self._running = False

    def get_snapshot(self) -> OrchestratorSnapshot:
        """Return an immutable snapshot of current state."""
        config = self._workflow_store.current_config
        return create_snapshot(self._state, config.max_concurrent_agents)

    # ── Tick cycle ────────────────────────────────────────────────

    async def _tick(self) -> None:
        """One complete poll/dispatch/reconcile cycle."""
        config = self._workflow_store.current_config

        # 1. Reconcile running tasks
        await self._reconcile_running_tasks(config)

        # 2. Fetch candidate tasks from tracker
        try:
            candidates = await self._tracker.fetch_candidate_tasks(
                active_states=config.active_states,
                terminal_states=config.terminal_states,
            )
        except Exception as exc:
            logger.warning("Tracker fetch failed: %s", exc)
            self._emit(ErrorEvent(message=f"Tracker fetch failed: {exc}"))
            return

        # 3. Dispatch eligible tasks
        slots = self._state.available_slots(config.max_concurrent_agents)
        dispatched = 0

        # Sort by priority (ascending: 1=urgent first), then created_at
        candidates.sort(key=lambda t: (t.priority or 99, t.created_at or ""))

        for task in candidates:
            if dispatched >= slots:
                break
            if self._state.is_claimed(task.id):
                continue
            if task.id in self._state.completed:
                continue

            await self._dispatch_task(task, config)
            dispatched += 1

        # 4. Emit tick event
        self._emit(OrchestratorTickEvent(
            running_count=self._state.running_count,
            retry_count=self._state.retry_count,
            available_slots=self._state.available_slots(config.max_concurrent_agents),
        ))

        # 5. Emit dashboard snapshot if changed
        snapshot = self.get_snapshot()
        if snapshot.fingerprint != self._last_snapshot_fingerprint:
            self._last_snapshot_fingerprint = snapshot.fingerprint
            self._emit(DashboardSnapshotEvent(snapshot=snapshot.to_dict()))

    # ── Task dispatch ─────────────────────────────────────────────

    async def _dispatch_task(self, task: Task, config: WorkflowConfig) -> None:
        """Create workspace and spawn a pipeline worker for *task*."""
        self._state.claim(task.id)

        try:
            assert self._workspace_mgr is not None
            workspace = await self._workspace_mgr.create_for_task(task)
        except Exception as exc:
            logger.error("Failed to create workspace for %s: %s", task.identifier, exc)
            self._state.release(task.id)
            self._emit(ErrorEvent(
                message=f"Workspace creation failed for {task.identifier}: {exc}",
            ))
            return

        entry = RunningEntry(
            task=task,
            workspace=str(workspace),
        )
        self._state.running[task.id] = entry

        # Spawn worker as asyncio.Task
        worker_task = asyncio.create_task(
            self._worker(task, str(workspace), config),
            name=f"worker-{task.identifier}",
        )
        entry.asyncio_task = worker_task
        worker_task.add_done_callback(
            lambda t: asyncio.get_event_loop().call_soon(
                self._on_worker_done, task.id, t,
            )
        )

        self._emit(TaskDispatchedEvent(
            task_id=task.id,
            identifier=task.identifier,
            title=task.title,
        ))
        logger.info("Dispatched %s to %s", task.identifier, workspace)

    async def _worker(
        self,
        task: Task,
        workspace: str,
        config: WorkflowConfig,
    ) -> dict[str, Any]:
        """Run a single pipeline end-to-end for *task* in *workspace*."""
        assert self._workspace_mgr is not None
        from pathlib import Path

        # Run before_run hook
        try:
            await self._workspace_mgr.before_run(Path(workspace))
        except HookError as exc:
            logger.warning("before_run hook failed for %s: %s", task.identifier, exc)
            raise

        # Build prompt context from workflow template
        from zhushou.workflow.prompt_builder import render_prompt

        workflow_data = self._workflow_store.current_data
        task_prompt = render_prompt(
            workflow_data.prompt_template,
            task,
            attempt=None,
        )

        # Create LLM client
        llm_client = self._create_llm_client(config)

        # Create and run pipeline
        from zhushou.pipeline.runner import PipelineRunner
        from zhushou.pipeline.stages import StageRegistry

        stage_registry = StageRegistry.from_workflow_config(config)

        runner = PipelineRunner(
            llm_client=llm_client,
            work_dir=workspace,
            event_bus=self._event_bus,
            world_sense=True,
            stage_registry=stage_registry,
            task_context=task_prompt,
        )

        # Run pipeline (synchronous LLM calls wrapped in thread)
        stats = await asyncio.to_thread(runner.run, task.title)

        # Run after_run hook
        try:
            await self._workspace_mgr.after_run(Path(workspace))
        except Exception:
            logger.debug("after_run hook error (non-fatal)", exc_info=True)

        return stats

    def _on_worker_done(self, task_id: str, future: asyncio.Task[Any]) -> None:
        """Callback when a worker task completes or fails."""
        entry = self._state.running.get(task_id)
        if entry is None:
            return

        config = self._workflow_store.current_config

        try:
            stats = future.result()
            # Success
            self._state.mark_completed(task_id)
            self._emit(TaskCompletedEvent(
                task_id=task_id,
                identifier=entry.task.identifier,
                stats=stats if isinstance(stats, dict) else {},
            ))
            logger.info("Task %s completed", entry.task.identifier)

            # Update tracker state
            asyncio.create_task(
                self._tracker.update_task_state(task_id, "done"),
            )

        except Exception as exc:
            # Failure: schedule retry with exponential backoff
            attempt = 1
            existing_retry = self._state.retry_queue.get(task_id)
            if existing_retry:
                attempt = existing_retry.attempt + 1

            delay_ms = retry_delay(
                attempt,
                max_ms=config.max_retry_backoff_ms,
            )

            self._state.running.pop(task_id, None)

            due_at = time.monotonic() + (delay_ms / 1000.0)
            retry_entry = RetryEntry(
                task=entry.task,
                attempt=attempt,
                due_at=due_at,
                error=str(exc)[:500],
            )

            # Schedule retry timer
            loop = asyncio.get_event_loop()
            handle = loop.call_later(
                delay_ms / 1000.0,
                lambda tid=task_id: asyncio.create_task(self._handle_retry(tid)),
            )
            retry_entry.timer_handle = handle
            self._state.retry_queue[task_id] = retry_entry

            self._emit(TaskRetryingEvent(
                task_id=task_id,
                identifier=entry.task.identifier,
                attempt=attempt,
                delay_ms=delay_ms,
                error=str(exc)[:200],
            ))
            logger.warning(
                "Task %s failed (attempt %d), retrying in %.1fs: %s",
                entry.task.identifier, attempt, delay_ms / 1000.0, exc,
            )

    # ── Retry handling ────────────────────────────────────────────

    async def _handle_retry(self, task_id: str) -> None:
        """Re-dispatch a task from the retry queue."""
        retry = self._state.retry_queue.pop(task_id, None)
        if retry is None:
            return

        config = self._workflow_store.current_config

        # Re-check task state in tracker
        try:
            current_task = await self._tracker.fetch_task_by_id(task_id)
        except Exception:
            current_task = None

        if current_task is None:
            logger.info("Retried task %s no longer exists, releasing", task_id)
            self._state.release(task_id)
            return

        # Check if task is now terminal
        terminal = {s.strip().lower() for s in config.terminal_states}
        if current_task.state.strip().lower() in terminal:
            logger.info("Task %s is now terminal (%s), releasing",
                        task_id, current_task.state)
            self._state.release(task_id)
            return

        # Check for available slots
        if self._state.available_slots(config.max_concurrent_agents) <= 0:
            # Re-queue with next attempt
            delay_ms = retry_delay(
                retry.attempt + 1,
                max_ms=config.max_retry_backoff_ms,
            )
            due_at = time.monotonic() + (delay_ms / 1000.0)
            new_entry = RetryEntry(
                task=current_task,
                attempt=retry.attempt + 1,
                due_at=due_at,
                error="no available slots",
            )
            loop = asyncio.get_event_loop()
            handle = loop.call_later(
                delay_ms / 1000.0,
                lambda: asyncio.create_task(self._handle_retry(task_id)),
            )
            new_entry.timer_handle = handle
            self._state.retry_queue[task_id] = new_entry
            return

        # Re-dispatch
        await self._dispatch_task(current_task, config)

    # ── Reconciliation ────────────────────────────────────────────

    async def _reconcile_running_tasks(self, config: WorkflowConfig) -> None:
        """Check running tasks for stalls and state changes."""
        stall_timeout_ms = config.stall_timeout_ms
        if stall_timeout_ms <= 0:
            return

        stall_timeout_s = stall_timeout_ms / 1000.0
        terminal = {s.strip().lower() for s in config.terminal_states}

        # Check for stalled workers
        stalled_ids: list[str] = []
        for task_id, entry in list(self._state.running.items()):
            if entry.seconds_since_last_event > stall_timeout_s:
                stalled_ids.append(task_id)

        for task_id in stalled_ids:
            entry = self._state.running.get(task_id)
            if entry is None:
                continue
            self._emit(TaskStalledEvent(
                task_id=task_id,
                identifier=entry.task.identifier,
                elapsed_ms=int(entry.seconds_since_last_event * 1000),
            ))
            logger.warning(
                "Task %s stalled (%.0fs since last event), cancelling",
                entry.task.identifier,
                entry.seconds_since_last_event,
            )
            # Cancel the worker
            if entry.asyncio_task and not entry.asyncio_task.done():
                entry.asyncio_task.cancel()

        # Reconcile tracker states for running tasks
        running_ids = list(self._state.running.keys())
        if not running_ids:
            return

        try:
            current_states = await self._tracker.fetch_task_states_by_ids(running_ids)
        except Exception:
            # Tracker failure: keep running, retry next tick
            return

        for task_id, current_state in current_states.items():
            if current_state.strip().lower() in terminal:
                entry = self._state.running.get(task_id)
                if entry:
                    logger.info(
                        "Task %s moved to terminal state %s, cancelling",
                        entry.task.identifier, current_state,
                    )
                    if entry.asyncio_task and not entry.asyncio_task.done():
                        entry.asyncio_task.cancel()
                    self._state.mark_completed(task_id)
                    # Cleanup workspace
                    if self._workspace_mgr:
                        asyncio.create_task(
                            self._workspace_mgr.cleanup_task(entry.task),
                        )

    # ── Startup / shutdown ────────────────────────────────────────

    async def _startup_cleanup(self) -> None:
        """Remove workspaces for tasks in terminal states at startup."""
        config = self._workflow_store.current_config
        if not self._workspace_mgr:
            return

        try:
            all_tasks = await self._tracker.fetch_candidate_tasks(
                active_states=config.terminal_states,
                terminal_states=[],
            )
            terminal_ids = {t.id for t in all_tasks}
            id_to_task = {t.id: t for t in all_tasks}
            removed = await self._workspace_mgr.cleanup_terminal_tasks(
                terminal_ids, id_to_task,
            )
            if removed:
                logger.info("Cleaned up %d terminal workspaces at startup", removed)
        except Exception:
            logger.debug("Startup cleanup failed", exc_info=True)

    async def _shutdown(self) -> None:
        """Gracefully shut down all workers."""
        logger.info("Orchestrator shutting down...")
        self._workflow_store.stop_watching()

        # Cancel all running workers
        for task_id, entry in list(self._state.running.items()):
            if entry.asyncio_task and not entry.asyncio_task.done():
                entry.asyncio_task.cancel()

        # Cancel retry timers
        for task_id, retry in list(self._state.retry_queue.items()):
            if retry.timer_handle:
                retry.timer_handle.cancel()

        # Wait briefly for workers to finish
        tasks = [
            entry.asyncio_task
            for entry in self._state.running.values()
            if entry.asyncio_task and not entry.asyncio_task.done()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Orchestrator stopped")

    # ── Helpers ────────────────────────────────────────────────────

    def _emit(self, event: Any) -> None:
        if self._event_bus:
            self._event_bus.emit(event)

    def _create_llm_client(self, config: WorkflowConfig) -> Any:
        """Create an LLM client.  Uses the factory if provided, otherwise
        falls back to loading from ZhuShou config."""
        if self._llm_client_factory:
            return self._llm_client_factory()

        from zhushou.config.manager import load_config
        from zhushou.llm.factory import LLMClientFactory

        cfg = load_config()
        return LLMClientFactory.create_client(
            provider=cfg.provider,
            model=cfg.model,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            proxy=cfg.proxy,
            timeout=cfg.timeout,
        )
