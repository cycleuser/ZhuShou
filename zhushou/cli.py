"""ZhuShou - Command Line Interface."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from zhushou import __version__


def _make_common_parser() -> argparse.ArgumentParser:
    """Build a parent parser with flags shared across all subcommands."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    common.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    common.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )
    common.add_argument(
        "-o", "--output",
        default=None,
        help="Working / output directory",
    )
    common.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider: ollama, openai, anthropic, deepseek, gemini (default: ollama)",
    )
    common.add_argument(
        "--model", "-m",
        default="",
        help="Model name (default: provider default)",
    )
    common.add_argument(
        "--api-key",
        default="",
        help="API key for cloud providers",
    )
    common.add_argument(
        "--base-url",
        default="",
        help="Custom API endpoint URL",
    )
    common.add_argument(
        "--proxy",
        default="",
        help="HTTP/HTTPS proxy URL (default: disabled, ignores system proxy env vars)",
    )
    return common


def main(argv: list[str] | None = None) -> None:
    """Entry point for the zhushou CLI."""
    common = _make_common_parser()

    parser = argparse.ArgumentParser(
        prog="zhushou",
        description="ZhuShou (助手) - AI-powered development assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
        epilog="""\
examples:
  zhushou                                  Launch interactive REPL
  zhushou chat "Explain decorators"        Single-turn chat
  zhushou pipeline "Build Gomoku" -o .     Run 7-stage coding pipeline
  zhushou models                           List available models
  zhushou models --provider openai         List OpenAI models
  zhushou config                           Show configuration
""",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"zhushou {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # chat subcommand
    chat_parser = subparsers.add_parser(
        "chat",
        help="Send a message to the assistant",
        parents=[common],
    )
    chat_parser.add_argument(
        "message",
        nargs="?",
        default="",
        help="Message to send (omit for interactive mode)",
    )

    # pipeline subcommand
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run the autonomous coding pipeline (7 stages; 9 with --full)",
        parents=[common],
    )
    pipeline_parser.add_argument(
        "request",
        help="Project description or coding request",
    )
    pipeline_parser.add_argument(
        "--full",
        action="store_true",
        help="Run additional documentation and packaging stages (9 stages total)",
    )

    # models subcommand
    subparsers.add_parser(
        "models",
        help="List available models across providers",
        parents=[common],
    )

    # config subcommand
    subparsers.add_parser(
        "config",
        help="Show or edit configuration",
        parents=[common],
    )

    args = parser.parse_args(argv)

    # Configure logging
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    command = args.command

    if command == "chat":
        _cmd_chat(args)
    elif command == "pipeline":
        _cmd_pipeline(args)
    elif command == "models":
        _cmd_models(args)
    elif command == "config":
        _cmd_config(args)
    else:
        # No subcommand -> interactive REPL
        _cmd_interactive(args)


def _resolve_model(args: argparse.Namespace) -> str:
    """Return a concrete model name, prompting the user if needed.

    If ``--model`` was supplied, return it directly.  Otherwise, create
    a temporary LLM client, list available models, and let the user
    pick one interactively.
    """
    if args.model:
        return args.model

    from zhushou.llm.factory import LLMClientFactory
    from zhushou.display.console import show_model_selector, show_info

    kwargs: dict = {}
    if args.base_url:
        kwargs["base_url"] = args.base_url
    if args.api_key:
        kwargs["api_key"] = args.api_key
    if args.proxy:
        kwargs["proxy"] = args.proxy

    client = LLMClientFactory.create_client(args.provider, **kwargs)

    if not client.is_available():
        print(f"Error: Cannot connect to {args.provider}. Is the service running?", file=sys.stderr)
        sys.exit(1)

    models = client.list_models()
    if not models:
        print(f"Error: No models found for provider '{args.provider}'.", file=sys.stderr)
        sys.exit(1)

    selected = show_model_selector(models)
    show_info(f"Using {args.provider} / {selected}")
    return selected


def _cmd_chat(args: argparse.Namespace) -> None:
    """Handle the chat subcommand."""
    if not args.message:
        # Fall through to interactive mode
        _cmd_interactive(args)
        return

    model = _resolve_model(args)

    from zhushou.api import chat

    result = chat(
        args.message,
        provider=args.provider,
        model=model,
        api_key=args.api_key,
        base_url=args.base_url,
        work_dir=args.output or ".",
        proxy=args.proxy,
    )

    if args.json_output:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif result.success:
        print(result.data)
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def _cmd_pipeline(args: argparse.Namespace) -> None:
    """Handle the pipeline subcommand."""
    model = _resolve_model(args)

    from zhushou.api import run_pipeline

    output_dir = args.output or "./output"
    result = run_pipeline(
        args.request,
        output_dir=output_dir,
        provider=args.provider,
        model=model,
        api_key=args.api_key,
        base_url=args.base_url,
        proxy=args.proxy,
        full=args.full,
    )

    if args.json_output:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif result.success:
        stats = result.data or {}
        print(f"Pipeline complete: {stats.get('files_created', 0)} files created")
        print(f"Tests: {stats.get('tests_passed', 'N/A')}")
        print(f"Output: {output_dir}")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def _cmd_models(args: argparse.Namespace) -> None:
    """Handle the models subcommand."""
    try:
        from zhushou.llm.factory import LLMClientFactory

        kwargs: dict = {}
        if args.base_url:
            kwargs["base_url"] = args.base_url
        if args.api_key:
            kwargs["api_key"] = args.api_key
        if args.model:
            kwargs["model"] = args.model
        if args.proxy:
            kwargs["proxy"] = args.proxy

        client = LLMClientFactory.create_client(args.provider, **kwargs)
        models = client.list_models()

        if args.json_output:
            data = [{"name": m.name, "size_gb": m.size_gb, "provider": m.provider} for m in models]
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            if not models:
                print(f"No models found for provider '{args.provider}'.")
                return
            from zhushou.display.console import show_model_list
            show_model_list(models)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_config(args: argparse.Namespace) -> None:
    """Handle the config subcommand."""
    from zhushou.utils.constants import DATA_DIR, CONFIG_FILE
    import json as _json

    if CONFIG_FILE.exists():
        data = _json.loads(CONFIG_FILE.read_text())
    else:
        data = {}

    if args.json_output:
        print(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"Config directory: {DATA_DIR}")
        print(f"Config file: {CONFIG_FILE}")
        if data:
            for k, v in data.items():
                print(f"  {k}: {v}")
        else:
            print("  (no configuration set)")


def _cmd_interactive(args: argparse.Namespace) -> None:
    """Launch the interactive REPL."""
    try:
        from zhushou.display.console import show_welcome, show_info, show_error
        from zhushou.llm.factory import LLMClientFactory
        from zhushou.agent.loop import AgentLoop
        from zhushou.executor.tool_executor import ToolExecutor
        from zhushou.agent.context import ContextManager
        from zhushou.tracking.tracker import TokenTracker
        from zhushou.memory.persistent import PersistentMemory
        from zhushou.persona.loader import PersonaLoader

        show_welcome()

        model = _resolve_model(args)

        kwargs: dict = {}
        if args.base_url:
            kwargs["base_url"] = args.base_url
        if args.api_key:
            kwargs["api_key"] = args.api_key
        if args.proxy:
            kwargs["proxy"] = args.proxy
        kwargs["model"] = model

        client = LLMClientFactory.create_client(args.provider, **kwargs)

        show_info(f"Using {args.provider} / {client.model}")

        work_dir = args.output or "."
        executor = ToolExecutor(work_dir=work_dir)
        context_mgr = ContextManager(max_tokens=client.max_context_tokens)
        tracker = TokenTracker()
        memory = PersistentMemory()
        persona = PersonaLoader.load(work_dir)

        loop = AgentLoop(
            llm_client=client,
            tool_executor=executor,
            context_manager=context_mgr,
            memory=memory,
            tracker=tracker,
            persona=persona,
        )
        loop.run_interactive()

    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
