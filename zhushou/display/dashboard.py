"""Terminal-based orchestrator dashboard using Rich Live.

Renders a continuously updating status panel inspired by Symphony's
``StatusDashboard`` GenServer -- but built on Rich's ``Live`` widget
instead of raw ANSI escape codes.

The dashboard subscribes to the event bus and refreshes on every
``DashboardSnapshotEvent``, or at a configurable interval if no
events arrive (so the uptime clock still ticks).

Usage::

    dashboard = StatusDashboard(orchestrator, event_bus)
    await dashboard.run()        # blocks; call stop() to exit
    # -- or --
    dashboard.start_background() # returns immediately
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zhushou.events.bus import PipelineEventBus
from zhushou.events.types import (
    DashboardSnapshotEvent,
    PipelineEvent,
    TaskCompletedEvent,
    TaskDispatchedEvent,
    TaskRetryingEvent,
    TaskStalledEvent,
)
from zhushou.orchestrator.snapshot import OrchestratorSnapshot

logger = logging.getLogger(__name__)


def _format_duration(seconds: float) -> str:
    """Format seconds into ``Xh Ym Zs`` or ``Xm Zs``."""
    if seconds < 0:
        return "0s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _format_count(n: int) -> str:
    """Human-friendly large number: 1234 -> 1.2k, 1234567 -> 1.2M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


class StatusDashboard:
    """Rich-based terminal dashboard for the orchestrator.

    Parameters
    ----------
    orchestrator
        An ``Orchestrator`` instance (must have ``get_snapshot()``).
    event_bus
        The shared ``PipelineEventBus`` for event-driven refresh.
    refresh_ms : int
        Minimum auto-refresh interval in milliseconds (default 1000).
    console : Console | None
        Custom Rich Console (useful for testing).
    """

    def __init__(
        self,
        orchestrator: Any,
        event_bus: PipelineEventBus,
        refresh_ms: int = 1000,
        console: Console | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._event_bus = event_bus
        self._refresh_ms = max(200, refresh_ms)
        self._console = console or Console()
        self._running = False
        self._last_fingerprint: str = ""
        self._recent_events: list[str] = []
        self._max_recent_events = 12
        self._start_time = time.monotonic()

    # ── Public API ────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the dashboard, blocking until ``stop()`` is called."""
        self._running = True
        self._start_time = time.monotonic()
        queue = self._event_bus.subscribe_async(maxsize=500)

        try:
            with Live(
                self._render_layout(),
                console=self._console,
                refresh_per_second=0,  # we control refresh ourselves
                screen=True,
            ) as live:
                while self._running:
                    # Wait for event or timeout
                    try:
                        event = await asyncio.wait_for(
                            queue.get(),
                            timeout=self._refresh_ms / 1000.0,
                        )
                        self._handle_event(event)
                    except asyncio.TimeoutError:
                        pass

                    live.update(self._render_layout())
        finally:
            self._event_bus.unsubscribe_async(queue)

    def stop(self) -> None:
        """Signal the dashboard to stop rendering."""
        self._running = False

    def start_background(self) -> asyncio.Task[None]:
        """Start the dashboard as a background asyncio task."""
        return asyncio.create_task(self.run(), name="status-dashboard")

    # ── Event handling ────────────────────────────────────────────

    def _handle_event(self, event: PipelineEvent) -> None:
        """Record notable events in the activity log."""
        ts = time.strftime("%H:%M:%S")
        msg: str | None = None

        if isinstance(event, TaskDispatchedEvent):
            msg = f"[green]+[/green] Dispatched {event.identifier}: {event.title}"
        elif isinstance(event, TaskCompletedEvent):
            msg = f"[bold green]\u2713[/bold green] Completed {event.identifier}"
        elif isinstance(event, TaskRetryingEvent):
            delay_s = event.delay_ms / 1000.0
            msg = f"[yellow]\u21bb[/yellow] Retry {event.identifier} (#{event.attempt}, {delay_s:.0f}s)"
        elif isinstance(event, TaskStalledEvent):
            msg = f"[red]![/red] Stalled {event.identifier} ({event.elapsed_ms // 1000}s)"

        if msg:
            self._recent_events.append(f"[dim]{ts}[/dim] {msg}")
            if len(self._recent_events) > self._max_recent_events:
                self._recent_events = self._recent_events[-self._max_recent_events:]

    # ── Rendering ─────────────────────────────────────────────────

    def _render_layout(self) -> Panel:
        """Build the full dashboard layout."""
        snapshot = self._orchestrator.get_snapshot()
        self._last_fingerprint = snapshot.fingerprint

        header = self._render_header(snapshot)
        running_table = self._render_running_table(snapshot)
        retry_table = self._render_retry_table(snapshot)
        activity_log = self._render_activity_log()

        body = Group(header, running_table, retry_table, activity_log)
        return Panel(
            body,
            title="[bold cyan]ZhuShou Orchestrator[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

    def _render_header(self, snap: OrchestratorSnapshot) -> Table:
        """Render the top status summary."""
        grid = Table.grid(padding=(0, 3))
        grid.add_column(style="bold")
        grid.add_column()

        grid.add_row(
            "Agents",
            f"[green]{snap.running_count}[/green][dim]/{snap.max_concurrent}[/dim]",
        )
        grid.add_row(
            "Runtime",
            f"[magenta]{_format_duration(snap.uptime_seconds)}[/magenta]",
        )
        grid.add_row(
            "Tokens",
            (
                f"[yellow]in {_format_count(snap.input_tokens)}[/yellow]"
                f" [dim]|[/dim] "
                f"[yellow]out {_format_count(snap.output_tokens)}[/yellow]"
                f" [dim]|[/dim] "
                f"[yellow]total {_format_count(snap.total_tokens)}[/yellow]"
            ),
        )
        grid.add_row(
            "Completed",
            f"[green]{snap.completed_count}[/green]",
        )
        grid.add_row(
            "Retrying",
            f"[yellow]{snap.retry_count}[/yellow]" if snap.retry_count else "[dim]0[/dim]",
        )

        return grid

    def _render_running_table(self, snap: OrchestratorSnapshot) -> Panel:
        """Render the running workers table."""
        table = Table(
            title="Running",
            border_style="green",
            show_header=True,
            expand=True,
        )
        table.add_column("ID", style="bold", width=12, no_wrap=True)
        table.add_column("Title", style="white", ratio=2)
        table.add_column("Stage", justify="center", width=8)
        table.add_column("Elapsed", justify="right", width=10)
        table.add_column("Tokens", justify="right", width=10)

        if not snap.running:
            table.add_row(
                "[dim]---[/dim]", "[dim]No active agents[/dim]",
                "", "", "",
            )
        else:
            for r in snap.running:
                title = r.title[:40] + "..." if len(r.title) > 40 else r.title
                table.add_row(
                    r.identifier,
                    title,
                    f"{r.current_stage}/{r.total_stages}",
                    _format_duration(r.elapsed_seconds),
                    _format_count(r.total_tokens),
                )

        return Panel(table, border_style="dim")

    def _render_retry_table(self, snap: OrchestratorSnapshot) -> Panel:
        """Render the backoff / retry queue."""
        table = Table(
            title="Backoff Queue",
            border_style="yellow",
            show_header=True,
            expand=True,
        )
        table.add_column("ID", style="bold", width=12, no_wrap=True)
        table.add_column("Attempt", justify="center", width=8)
        table.add_column("Due In", justify="right", width=10)
        table.add_column("Error", style="red", ratio=2)

        if not snap.retrying:
            table.add_row(
                "[dim]---[/dim]", "[dim]empty[/dim]", "", "",
            )
        else:
            for r in snap.retrying:
                due = _format_duration(max(0, r.seconds_until_due))
                error_display = r.error[:60] + "..." if len(r.error) > 60 else r.error
                table.add_row(
                    r.identifier,
                    str(r.attempt),
                    due,
                    error_display,
                )

        return Panel(table, border_style="dim")

    def _render_activity_log(self) -> Panel:
        """Render the recent activity log."""
        if not self._recent_events:
            content = Text("No recent activity", style="dim")
        else:
            from rich.markup import escape
            lines = "\n".join(self._recent_events[-self._max_recent_events:])
            content = Text.from_markup(lines)

        return Panel(
            content,
            title="Activity",
            border_style="blue",
        )


def render_snapshot_panel(snapshot_dict: dict[str, Any]) -> Panel:
    """Render a one-shot snapshot panel from a plain dict.

    Useful for non-Live contexts (e.g. ``zhushou status`` command)
    where you just want to print the current state once.
    """
    snap = _dict_to_snapshot(snapshot_dict)

    grid = Table.grid(padding=(0, 3))
    grid.add_column(style="bold")
    grid.add_column()

    grid.add_row("Agents", f"{snap.running_count}/{snap.max_concurrent}")
    grid.add_row("Completed", str(snap.completed_count))
    grid.add_row("Retrying", str(snap.retry_count))
    grid.add_row("Runtime", _format_duration(snap.uptime_seconds))
    grid.add_row(
        "Tokens",
        f"in={_format_count(snap.input_tokens)} "
        f"out={_format_count(snap.output_tokens)} "
        f"total={_format_count(snap.total_tokens)}",
    )

    return Panel(grid, title="[bold]ZhuShou Status[/bold]", border_style="cyan")


def _dict_to_snapshot(d: dict[str, Any]) -> OrchestratorSnapshot:
    """Best-effort conversion from dict to snapshot (for render helpers)."""
    return OrchestratorSnapshot(
        running=[],
        retrying=[],
        completed_count=d.get("completed_count", 0),
        running_count=d.get("running_count", 0),
        retry_count=d.get("retry_count", 0),
        max_concurrent=d.get("max_concurrent", 3),
        input_tokens=d.get("input_tokens", 0),
        output_tokens=d.get("output_tokens", 0),
        total_tokens=d.get("total_tokens", 0),
        uptime_seconds=d.get("uptime_seconds", 0.0),
        fingerprint=d.get("fingerprint", ""),
    )
