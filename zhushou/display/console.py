"""Rich console display utilities for ZhuShou.

Evolved from ``old/display.py`` with additional helpers for token
usage, model listing, and info messages.
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


# ------------------------------------------------------------------
# Welcome
# ------------------------------------------------------------------

def show_welcome() -> None:
    """Display the ZhuShou welcome banner."""
    banner = Text()
    banner.append("ZhuShou ", style="bold cyan")
    banner.append("(助手) ", style="bold white")
    banner.append("- AI-Powered Development Assistant\n", style="bold white")
    banner.append("Multi-provider LLM support  |  Autonomous coding pipeline", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))


# ------------------------------------------------------------------
# Model selection / listing
# ------------------------------------------------------------------

def show_model_selector(models: list[Any]) -> str:
    """Display an interactive model selection table and return the chosen name.

    Each item in *models* should have ``.name``, ``.size`` and
    ``.modified`` attributes (or be a plain string).
    """
    if not models:
        console.print("[red]No models available. Please configure a provider first.[/red]")
        sys.exit(1)

    table = Table(title="Available Models", border_style="cyan")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Model", style="bold white")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Modified", style="dim")

    for i, m in enumerate(models, 1):
        if isinstance(m, str):
            table.add_row(str(i), m, "", "")
        else:
            table.add_row(
                str(i),
                getattr(m, "name", str(m)),
                getattr(m, "size", ""),
                getattr(m, "modified", ""),
            )

    console.print(table)
    console.print()

    while True:
        try:
            choice = console.input("[bold cyan]Select model (enter number): [/bold cyan]")
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                m = models[idx]
                selected = m if isinstance(m, str) else getattr(m, "name", str(m))
                console.print(f"  Selected: [bold green]{selected}[/bold green]\n")
                return selected
            console.print(f"[red]Please enter a number between 1 and {len(models)}[/red]")
        except (ValueError, EOFError):
            console.print("[red]Invalid input. Please enter a number.[/red]")


def show_model_list(models: list[Any]) -> None:
    """Display-only model table (no interactive selection)."""
    table = Table(title="Available Models", border_style="cyan")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Model", style="bold white")
    table.add_column("Provider", style="green")

    for i, m in enumerate(models, 1):
        if isinstance(m, str):
            table.add_row(str(i), m, "")
        elif isinstance(m, dict):
            table.add_row(str(i), m.get("name", ""), m.get("provider", ""))
        else:
            table.add_row(
                str(i),
                getattr(m, "name", str(m)),
                getattr(m, "provider", ""),
            )

    console.print(table)


# ------------------------------------------------------------------
# Pipeline stages
# ------------------------------------------------------------------

def show_stage_header(num: int, total: int, name: str) -> None:
    """Display a stage header panel."""
    title = f"Stage {num}/{total}: {name}"
    console.print()
    console.print(Panel(title, style="bold magenta", border_style="magenta", padding=(0, 2)))


# ------------------------------------------------------------------
# Streaming output
# ------------------------------------------------------------------

def show_streaming_token(token: str) -> None:
    """Print a single streamed token without a trailing newline."""
    sys.stdout.write(token)
    sys.stdout.flush()


def show_streaming_end() -> None:
    """End streaming output with a newline."""
    console.print()


# ------------------------------------------------------------------
# Tool calls
# ------------------------------------------------------------------

def show_tool_call(name: str, args: dict[str, Any]) -> None:
    """Display a tool call being executed."""
    arg_display = ""
    if "path" in args:
        arg_display = str(args["path"])
    elif "command" in args:
        cmd = str(args["command"])
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        arg_display = cmd
    elif "pattern" in args:
        arg_display = str(args["pattern"])
    elif "query" in args:
        arg_display = str(args["query"])
    elif "code" in args:
        code = str(args["code"])
        if len(code) > 60:
            code = code[:57] + "..."
        arg_display = code

    console.print(f"  [bold yellow]>> Tool:[/bold yellow] {name}", end="")
    if arg_display:
        console.print(f" [dim]({arg_display})[/dim]", end="")
    console.print()


def show_tool_result(success: bool, output: str) -> None:
    """Display tool execution result."""
    if success:
        display = output if len(output) <= 200 else output[:200] + "..."
        console.print(f"     [green]OK[/green] [dim]{display}[/dim]")
    else:
        display = output if len(output) <= 300 else output[:300] + "..."
        console.print(f"     [red]FAIL[/red] {display}")


# ------------------------------------------------------------------
# Debug loop
# ------------------------------------------------------------------

def show_debug_attempt(attempt: int, max_retries: int, passed: bool) -> None:
    """Display debug loop attempt status."""
    status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
    console.print(f"  [bold]Debug attempt {attempt}/{max_retries}:[/bold] Tests {status}")


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

def show_summary(stats: dict[str, Any]) -> None:
    """Display final pipeline summary table."""
    console.print()
    table = Table(title="Pipeline Complete", border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Stages completed", str(stats.get("stages_completed", 0)))
    table.add_row("Files created", str(stats.get("files_created", 0)))
    table.add_row("Tests passed", str(stats.get("tests_passed", "N/A")))
    table.add_row("Debug iterations", str(stats.get("debug_iterations", 0)))
    table.add_row("Total time", stats.get("total_time", "N/A"))

    console.print(table)

    files = stats.get("file_list", [])
    if files:
        console.print("\n[bold]Created files:[/bold]")
        for f in files:
            console.print(f"  [dim]>[/dim] {f}")

    output_dir = stats.get("output_dir", "")
    if output_dir:
        console.print(f"\n[bold green]Project directory:[/bold green] {output_dir}")


# ------------------------------------------------------------------
# Messages
# ------------------------------------------------------------------

def show_error(msg: str) -> None:
    """Display an error message in red."""
    console.print(f"[bold red]Error:[/bold red] {msg}")


def show_info(msg: str) -> None:
    """Display a dim informational message."""
    console.print(f"[dim]{msg}[/dim]")


# ------------------------------------------------------------------
# Token / cost usage
# ------------------------------------------------------------------

def show_token_usage(stats: dict[str, Any]) -> None:
    """Display a token usage and cost summary table.

    Expected keys in *stats*: ``prompt_tokens``, ``completion_tokens``,
    ``total_tokens``, ``estimated_cost``, ``provider``, ``model``.
    """
    console.print()
    table = Table(title="Token Usage", border_style="blue")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan", justify="right")

    table.add_row("Provider", str(stats.get("provider", "unknown")))
    table.add_row("Model", str(stats.get("model", "unknown")))
    table.add_row("Prompt tokens", f"{stats.get('prompt_tokens', 0):,}")
    table.add_row("Completion tokens", f"{stats.get('completion_tokens', 0):,}")
    table.add_row("Total tokens", f"{stats.get('total_tokens', 0):,}")

    cost = stats.get("estimated_cost", 0.0)
    if cost and cost > 0:
        table.add_row("Estimated cost", f"${cost:.4f}")

    console.print(table)
