"""Core agent while-loop with function-calling tool integration."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

if TYPE_CHECKING:
    from zhushou.agent.context import ContextManager
    from zhushou.executor.tool_executor import ToolExecutor
    from zhushou.memory.persistent import PersistentMemory
    from zhushou.tracking.tracker import TokenTracker

logger = logging.getLogger(__name__)

# ── Rich console instance ─────────────────────────────────────────────
_console = Console()

# ── Pipeline trigger keywords (English + Chinese) ─────────────────────
_PIPELINE_KEYWORDS: list[str] = [
    "create project",
    "build a",
    "make a program",
    "generate project",
    "code a",
    "write a program",
    "生成项目",
    "创建项目",
    "创建",
    "开发",
]

# ── Help text shown by /help ──────────────────────────────────────────
_HELP_TEXT = """\
[bold cyan]ZhuShou Interactive Commands[/bold cyan]

  [yellow]/help[/yellow]   Show this help message
  [yellow]/stats[/yellow]  Show token usage statistics
  [yellow]/clear[/yellow]  Clear conversation history
  [yellow]/quit[/yellow]   Exit the assistant  [dim](also /exit)[/dim]

Type any message to chat with the assistant.
"""


class AgentLoop:
    """Core while-loop agent that drives LLM ↔ tool interaction.

    The loop repeatedly calls the LLM, executes any requested tool calls,
    feeds results back, and returns the final textual answer.
    """

    MAX_TOOL_TURNS: int = 25

    def __init__(
        self,
        llm_client: Any,
        tool_executor: ToolExecutor,
        context_manager: ContextManager,
        memory: PersistentMemory,
        tracker: TokenTracker,
        persona: Any,
    ) -> None:
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.context_manager = context_manager
        self.memory = memory
        self.tracker = tracker
        self.persona = persona

        # Current session conversation history
        self._conversation: list[dict[str, Any]] = []

    # ── Public API ─────────────────────────────────────────────────────

    def run_interactive(self) -> None:
        """Run the interactive REPL loop using Rich console."""
        _console.print(
            Panel(
                "[bold cyan]ZhuShou[/bold cyan] - Type [yellow]/help[/yellow] for commands.",
                border_style="cyan",
            )
        )

        while True:
            try:
                user_input = _console.input("[bold green]You:[/bold green] ").strip()
            except (KeyboardInterrupt, EOFError):
                _console.print("\n[dim]Bye! 再见![/dim]")
                break

            if not user_input:
                continue

            # ── Slash commands ─────────────────────────────────────────
            lower = user_input.lower()
            if lower in ("/quit", "/exit"):
                _console.print("[dim]Bye! 再见![/dim]")
                break
            if lower == "/clear":
                self._conversation.clear()
                _console.print("[dim]Conversation cleared.[/dim]")
                continue
            if lower == "/stats":
                stats = self.tracker.get_session_stats()
                _console.print(Panel(json.dumps(stats, indent=2), title="Token Stats"))
                continue
            if lower == "/help":
                _console.print(_HELP_TEXT)
                continue

            # ── Normal message processing ──────────────────────────────
            try:
                response = self.process_message(user_input)
                _console.print()
                _console.print(Markdown(response))
                _console.print()
            except Exception as exc:
                logger.exception("Error processing message")
                _console.print(f"[bold red]Error:[/bold red] {exc}")

    def process_message(self, user_input: str) -> str:
        """Process a single user message through the agent cycle.

        Steps
        -----
        1. Build system prompt from persona.
        2. Fetch conversation messages via *context_manager*.
        3. Obtain tool definitions from *tool_executor*.
        4. Call llm_client.chat().
        5. Execute any tool_calls in a loop (up to MAX_TOOL_TURNS).
        6. Return the final textual response.
        7. Record token usage via *tracker*.
        """
        # 1. Build system prompt
        system_prompt = self._build_system_prompt()

        # 2. Append user message to conversation
        self._conversation.append({"role": "user", "content": user_input})

        # 3. Retrieve memory context (may be empty)
        memory_context = ""
        try:
            memory_context = self.memory.retrieve_context(user_input)
        except Exception:
            logger.debug("Memory retrieval skipped or failed")

        # 4. Build message list (trimmed to budget)
        messages = self.context_manager.build_messages(
            system_prompt=system_prompt,
            conversation=self._conversation,
            memory_context=memory_context,
        )

        # 5. Get tool definitions
        tool_defs = self.tool_executor.get_tool_definitions()

        # 6. LLM ↔ tool loop
        final_content: str = ""
        for _turn in range(self.MAX_TOOL_TURNS):
            response = self.llm_client.chat(messages=messages, tools=tool_defs)

            # 7. Record token usage
            try:
                self.tracker.record(
                    prompt_tokens=getattr(response, "prompt_tokens", 0),
                    completion_tokens=getattr(response, "completion_tokens", 0),
                    model=getattr(self.llm_client, "model", ""),
                )
            except Exception:
                logger.debug("Token tracking skipped")

            # 8. Check for tool calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # No tools requested → we have the final answer
                final_content = getattr(response, "content", "") or ""
                break

            # 9. Build assistant message with tool_calls attached
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": getattr(response, "content", "") or "",
                "tool_calls": [
                    {
                        "id": getattr(tc, "id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                            if isinstance(tc.arguments, str)
                            else json.dumps(tc.arguments),
                        },
                    }
                    for i, tc in enumerate(tool_calls)
                ],
            }
            messages.append(assistant_msg)

            # 10. Execute each tool call and append results
            for i, tc in enumerate(tool_calls):
                try:
                    args = (
                        json.loads(tc.arguments)
                        if isinstance(tc.arguments, str)
                        else tc.arguments
                    )
                except (json.JSONDecodeError, TypeError):
                    args = {}

                result = self.tool_executor.execute(tc.name, args)

                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": getattr(tc, "id", f"call_{i}"),
                    "name": tc.name,
                    "content": (
                        result["output"]
                        if isinstance(result, dict)
                        else str(result)
                    ),
                }
                messages.append(tool_msg)
        else:
            # Exhausted MAX_TOOL_TURNS without a text-only response
            final_content = (
                "[Agent reached maximum tool turns. "
                "Here is the last available response.]"
            )

        # 11. Store assistant reply in conversation history
        self._conversation.append({"role": "assistant", "content": final_content})

        return final_content

    def detect_pipeline_trigger(self, user_input: str) -> bool:
        """Return True if *user_input* looks like a pipeline-worthy request."""
        lower = user_input.lower()
        return any(kw in lower for kw in _PIPELINE_KEYWORDS)

    # ── Private helpers ────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Construct the system prompt, merging persona data if available."""
        base = (
            "You are ZhuShou (助手), a helpful AI development assistant. "
            "Answer clearly and concisely. When the user asks you to perform "
            "file operations, run commands, or inspect the project, use the "
            "available tools."
        )

        if self.persona is None:
            return base

        # Persona may be a dict or an object with attributes
        if isinstance(self.persona, dict):
            name = self.persona.get("name", "")
            instructions = self.persona.get("instructions", "")
        else:
            name = getattr(self.persona, "name", "")
            instructions = getattr(self.persona, "instructions", "")

        parts: list[str] = [base]
        if name:
            parts.append(f"Your persona name is '{name}'.")
        if instructions:
            parts.append(instructions)

        return "\n\n".join(parts)
