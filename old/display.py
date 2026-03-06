"""Rich console display utilities for the AI coding assistant."""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.columns import Columns

console = Console()


def show_welcome():
    """Display the welcome banner."""
    banner = Text()
    banner.append("Quest ", style="bold cyan")
    banner.append("- Autonomous AI Coding Assistant\n", style="bold white")
    banner.append("Powered by local Ollama models", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))


def show_model_selector(models: list) -> str:
    """Display model selection table and return selected model name."""
    if not models:
        console.print("[red]No models found in Ollama. Please pull a model first.[/red]")
        sys.exit(1)

    table = Table(title="Available Ollama Models", border_style="cyan")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Model", style="bold white")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Modified", style="dim")

    for i, m in enumerate(models, 1):
        table.add_row(str(i), m.name, f"{m.size} GB", m.modified)

    console.print(table)
    console.print()

    while True:
        try:
            choice = console.input("[bold cyan]Select model (enter number): [/bold cyan]")
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx].name
                console.print(f"  Selected: [bold green]{selected}[/bold green]\n")
                return selected
            console.print(f"[red]Please enter a number between 1 and {len(models)}[/red]")
        except (ValueError, EOFError):
            console.print("[red]Invalid input. Please enter a number.[/red]")


def show_stage_header(num: int, total: int, name: str):
    """Display a stage header panel."""
    title = f"Stage {num}/{total}: {name}"
    console.print()
    console.print(Panel(title, style="bold magenta", border_style="magenta", padding=(0, 2)))


def show_streaming_token(token: str):
    """Print a single streamed token without newline."""
    sys.stdout.write(token)
    sys.stdout.flush()


def show_streaming_end():
    """End the streaming output with a newline."""
    console.print()


def show_tool_call(name: str, args: dict):
    """Display a tool call being executed."""
    arg_display = ""
    if "path" in args:
        arg_display = args["path"]
    elif "command" in args:
        cmd = args["command"]
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        arg_display = cmd
    elif "dir" in args:
        arg_display = args["dir"]

    console.print(f"  [bold yellow]>> Tool:[/bold yellow] {name}", end="")
    if arg_display:
        console.print(f" [dim]({arg_display})[/dim]", end="")
    console.print()


def show_tool_result(success: bool, output: str):
    """Display tool execution result."""
    if success:
        # Truncate long output for display
        display = output if len(output) <= 200 else output[:200] + "..."
        console.print(f"     [green]OK[/green] [dim]{display}[/dim]")
    else:
        display = output if len(output) <= 300 else output[:300] + "..."
        console.print(f"     [red]FAIL[/red] {display}")


def show_debug_attempt(attempt: int, max_retries: int, passed: bool):
    """Display debug loop attempt status."""
    status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
    console.print(
        f"  [bold]Debug attempt {attempt}/{max_retries}:[/bold] Tests {status}"
    )


def show_summary(stats: dict):
    """Display final pipeline summary."""
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


def show_error(msg: str):
    """Display an error message."""
    console.print(f"[bold red]Error:[/bold red] {msg}")


def show_info(msg: str):
    """Display an info message."""
    console.print(f"[dim]{msg}[/dim]")
