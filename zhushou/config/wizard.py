"""First-run setup wizard for ZhuShou.

Guides the user through selecting a Python interpreter, LLM provider,
and model.  Supports both CLI (Rich) and GUI (PySide6) modes.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from zhushou.config.manager import ZhuShouConfig
from zhushou.utils.python_finder import PythonInterpreter, discover_all_pythons

logger = logging.getLogger(__name__)

# Cloud providers that require an API key
_CLOUD_PROVIDERS = {"openai", "anthropic", "deepseek", "gemini", "claude"}


class SetupWizard:
    """Interactive setup wizard — discovers system resources and saves config."""

    def __init__(self, config: ZhuShouConfig | None = None) -> None:
        self.config = config or ZhuShouConfig()

    # ── CLI Mode (Rich) ───────────────────────────────────────────

    def run_cli(self) -> ZhuShouConfig:
        """Run the setup wizard in CLI mode using Rich."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()

        # Welcome banner
        banner = Text()
        banner.append("ZhuShou ", style="bold cyan")
        banner.append("Setup Wizard\n", style="bold white")
        banner.append("Configure your Python interpreter and LLM provider", style="dim")
        console.print(Panel(banner, border_style="cyan", padding=(1, 2)))
        console.print()

        # Step 1: Python interpreter
        self._cli_select_python(console)

        # Step 2: LLM provider
        self._cli_select_provider(console)

        # Step 3: API key (if cloud provider)
        if self.config.provider in _CLOUD_PROVIDERS:
            self._cli_enter_api_key(console)

        # Step 4: Model selection
        self._cli_select_model(console)

        # Step 5: Summary + confirm
        self._cli_show_summary(console)

        # Save
        self.config.first_run_complete = True
        self.config.save()
        console.print("[bold green]Configuration saved![/bold green]\n")

        return self.config

    def _cli_select_python(self, console: Any) -> None:
        """Step 1: Select Python interpreter."""
        from rich.table import Table

        console.print("[bold cyan]Step 1/4:[/bold cyan] Select Python interpreter\n")

        interpreters = discover_all_pythons()
        if not interpreters:
            console.print("[yellow]No Python interpreters found. Using default.[/yellow]")
            self.config.python_path = sys.executable or "python3"
            console.print()
            return

        table = Table(border_style="cyan")
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Path", style="white")
        table.add_column("Version", style="green")
        table.add_column("Info", style="dim")

        for i, p in enumerate(interpreters, 1):
            info_parts = []
            if p.is_current:
                info_parts.append("current")
            if p.is_venv:
                info_parts.append("venv")
            table.add_row(str(i), p.path, p.version, ", ".join(info_parts))

        console.print(table)
        console.print()

        choice = self._cli_prompt_choice(
            console, len(interpreters),
            default=1,
            prompt="Select interpreter (Enter for default)",
        )
        selected = interpreters[choice - 1]
        self.config.python_path = selected.path
        console.print(f"  Selected: [bold green]{selected.path}[/bold green] ({selected.version})\n")

    def _cli_select_provider(self, console: Any) -> None:
        """Step 2: Select LLM provider."""
        from rich.table import Table

        console.print("[bold cyan]Step 2/4:[/bold cyan] Select LLM provider\n")

        try:
            from zhushou.llm.factory import LLMClientFactory
            providers = LLMClientFactory.list_providers()
        except Exception:
            providers = ["ollama", "openai", "anthropic", "deepseek", "gemini"]

        table = Table(border_style="cyan")
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Provider", style="white")
        table.add_column("Type", style="dim")

        for i, p in enumerate(providers, 1):
            ptype = "local" if p in ("ollama", "lmstudio", "vllm") else "cloud"
            table.add_row(str(i), p, ptype)

        console.print(table)
        console.print()

        choice = self._cli_prompt_choice(
            console, len(providers),
            default=1,
            prompt="Select provider (Enter for default)",
        )
        self.config.provider = providers[choice - 1]
        console.print(f"  Selected: [bold green]{self.config.provider}[/bold green]\n")

    def _cli_enter_api_key(self, console: Any) -> None:
        """Step 3: Enter API key for cloud providers."""
        console.print(f"[bold cyan]API Key:[/bold cyan] {self.config.provider} requires an API key\n")

        current = self.config.api_key
        if current:
            masked = current[:4] + "****" + current[-4:] if len(current) > 8 else "****"
            console.print(f"  Current key: [dim]{masked}[/dim]")

        try:
            key = console.input("[bold cyan]Enter API key (Enter to keep current): [/bold cyan]").strip()
            if key:
                self.config.api_key = key
                console.print("  [green]API key updated[/green]\n")
            else:
                console.print("  [dim]Keeping current key[/dim]\n")
        except (EOFError, KeyboardInterrupt):
            console.print("\n  [dim]Skipped[/dim]\n")

    def _cli_select_model(self, console: Any) -> None:
        """Step 4: Select LLM model."""
        from rich.table import Table

        console.print("[bold cyan]Step 3/4:[/bold cyan] Select LLM model\n")

        models: list[Any] = []
        try:
            from zhushou.llm.factory import LLMClientFactory

            kwargs: dict[str, Any] = {}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.proxy:
                kwargs["proxy"] = self.config.proxy

            client = LLMClientFactory.create_client(self.config.provider, **kwargs)
            if client.is_available():
                models = client.list_models()
        except Exception as e:
            logger.debug("Failed to list models: %s", e)

        if not models:
            console.print(f"[yellow]Cannot connect to {self.config.provider} or no models available.[/yellow]")
            try:
                name = console.input("[bold cyan]Enter model name manually (or Enter to skip): [/bold cyan]").strip()
                if name:
                    self.config.model = name
                    console.print(f"  Selected: [bold green]{name}[/bold green]\n")
                else:
                    console.print("  [dim]Skipped — will be selected at runtime[/dim]\n")
            except (EOFError, KeyboardInterrupt):
                console.print("\n  [dim]Skipped[/dim]\n")
            return

        table = Table(border_style="cyan")
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Model", style="white")
        table.add_column("Size", style="green", justify="right")

        for i, m in enumerate(models, 1):
            if isinstance(m, str):
                table.add_row(str(i), m, "")
            else:
                table.add_row(
                    str(i),
                    getattr(m, "name", str(m)),
                    getattr(m, "size", ""),
                )

        console.print(table)
        console.print()

        choice = self._cli_prompt_choice(
            console, len(models),
            default=1,
            prompt="Select model (Enter for default)",
        )
        m = models[choice - 1]
        self.config.model = m if isinstance(m, str) else getattr(m, "name", str(m))
        console.print(f"  Selected: [bold green]{self.config.model}[/bold green]\n")

    def _cli_show_summary(self, console: Any) -> None:
        """Step 5: Show configuration summary."""
        from rich.panel import Panel
        from rich.table import Table

        console.print("[bold cyan]Step 4/4:[/bold cyan] Configuration Summary\n")

        table = Table(border_style="green", show_header=False)
        table.add_column("Setting", style="bold")
        table.add_column("Value", style="cyan")

        table.add_row("Python", self.config.python_path or "(default)")
        table.add_row("Provider", self.config.provider)
        table.add_row("Model", self.config.model or "(select at runtime)")
        if self.config.api_key:
            key = self.config.api_key
            masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
            table.add_row("API Key", masked)
        table.add_row("Config file", str(self.config.config_path))

        console.print(Panel(table, title="Configuration", border_style="green"))
        console.print()

    @staticmethod
    def _cli_prompt_choice(console: Any, max_val: int, default: int = 1,
                           prompt: str = "Enter number") -> int:
        """Prompt for a numeric choice, returning *default* on empty input."""
        while True:
            try:
                raw = console.input(f"[bold cyan]{prompt}: [/bold cyan]").strip()
                if not raw:
                    return default
                idx = int(raw)
                if 1 <= idx <= max_val:
                    return idx
                console.print(f"[red]Please enter a number between 1 and {max_val}[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number.[/red]")
            except (EOFError, KeyboardInterrupt):
                return default

    # ── GUI Mode (PySide6) ────────────────────────────────────────

    def run_gui(self, parent: Any = None) -> ZhuShouConfig:
        """Run the setup wizard as a PySide6 dialog.

        Raises ImportError if PySide6 is not available.
        """
        from zhushou.gui.wizard_dialog import SetupWizardDialog

        dialog = SetupWizardDialog(self.config, parent=parent)
        if dialog.exec():
            self.config = dialog.get_config()
            self.config.first_run_complete = True
            self.config.save()
        return self.config
