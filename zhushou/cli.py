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
        default=None,
        help="LLM provider: ollama, openai, anthropic, deepseek, gemini (default: from config or ollama)",
    )
    common.add_argument(
        "--model", "-m",
        default=None,
        help="Model name (default: from config or provider default)",
    )
    common.add_argument(
        "--api-key",
        default=None,
        dest="api_key",
        help="API key for cloud providers",
    )
    common.add_argument(
        "--base-url",
        default=None,
        dest="base_url",
        help="Custom API endpoint URL",
    )
    common.add_argument(
        "--proxy",
        default=None,
        help="HTTP/HTTPS proxy URL (default: disabled, ignores system proxy env vars)",
    )
    common.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="LLM request timeout in seconds (default: 300)",
    )
    common.add_argument(
        "--no-setup",
        action="store_true",
        help="Skip first-run setup wizard",
    )
    common.add_argument(
        "--no-world",
        action="store_true",
        help="Disable world-context injection (date/time awareness via ModelSensor)",
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
  zhushou pipeline "Build Gomoku" -o .     Run coding pipeline
  zhushou models                           List available models
  zhushou config                           Show configuration
  zhushou config --setup                   Re-run setup wizard
  zhushou gui                              Launch desktop GUI
  zhushou web                              Launch web interface
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
        help="Run the autonomous coding pipeline (8 stages; 10 with --full)",
        parents=[common],
    )
    pipeline_parser.add_argument(
        "request",
        help="Project description or coding request",
    )
    pipeline_parser.add_argument(
        "--full",
        action="store_true",
        help="Run additional documentation and packaging stages (10 stages total)",
    )
    pipeline_parser.add_argument(
        "--kb",
        nargs="*",
        default=None,
        help="Enable knowledge base context (e.g. --kb numpy flask, or --kb auto)",
    )

    # models subcommand
    subparsers.add_parser(
        "models",
        help="List available models across providers",
        parents=[common],
    )

    # config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Show or edit configuration",
        parents=[common],
    )
    config_parser.add_argument(
        "--setup",
        action="store_true",
        help="Re-run the setup wizard",
    )

    # kb subcommand group
    kb_parser = subparsers.add_parser(
        "kb",
        help="Knowledge base management (list, download, index, search, cheatsheet, upload, import, delete)",
        parents=[common],
    )
    kb_subs = kb_parser.add_subparsers(dest="kb_command")
    kb_subs.add_parser("list", help="List available knowledge base sources")
    kb_dl = kb_subs.add_parser("download", help="Download official docs for a source")
    kb_dl.add_argument("source", help="Source name (e.g. numpy, flask)")
    kb_idx = kb_subs.add_parser("index", help="Index downloaded docs into vector DB")
    kb_idx.add_argument("source", help="Source name (e.g. numpy, flask)")
    kb_search = kb_subs.add_parser("search", help="Search indexed knowledge base")
    kb_search.add_argument("query", help="Search query")
    kb_search.add_argument("--source", nargs="*", default=None, help="Limit to specific sources")
    kb_cs = kb_subs.add_parser("cheatsheet", help="Display built-in cheatsheet")
    kb_cs.add_argument("name", help="Framework name (e.g. numpy, flask)")
    kb_crawl = kb_subs.add_parser("crawl", help="Crawl a website into knowledge base using Huan")
    kb_crawl.add_argument("url", help="URL to crawl")
    kb_crawl.add_argument("--name", default=None, help="Source name (default: domain)")
    kb_crawl.add_argument("--max-pages", type=int, default=200, dest="max_pages",
                          help="Max pages to crawl (default: 200)")
    kb_crawl.add_argument("--prefix", default=None, help="Only crawl URLs with this path prefix")
    kb_upload = kb_subs.add_parser("upload", help="Upload markdown/text files to create a user KB")
    kb_upload.add_argument("name", help="Display name for the knowledge base")
    kb_upload.add_argument("files", nargs="+", help="Paths to .md / .txt files")
    kb_upload.add_argument("--overwrite", action="store_true",
                           help="Overwrite existing duplicate files (default: skip)")
    kb_imp = kb_subs.add_parser("import", help="Import a directory of markdown/text files")
    kb_imp.add_argument("name", help="Display name for the knowledge base")
    kb_imp.add_argument("dir_path", help="Path to the directory to import")
    kb_del = kb_subs.add_parser("delete", help="Delete a user-created knowledge base")
    kb_del.add_argument("name", help="Internal name of the KB to delete (user_* prefix)")

    # gui subcommand
    subparsers.add_parser(
        "gui",
        help="Launch PySide6 desktop GUI",
        parents=[common],
    )

    # web subcommand
    web_parser = subparsers.add_parser(
        "web",
        help="Launch web interface",
        parents=[common],
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Web server port (default: 8765)",
    )
    web_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web server host (default: 127.0.0.1)",
    )

    args = parser.parse_args(argv)

    # Configure logging
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Config loading + first-run wizard ──────────────────────────
    from zhushou.config.manager import ZhuShouConfig

    config = ZhuShouConfig.load()

    # First-run wizard (skip for certain commands and flags)
    command = args.command
    skip_wizard_commands = {"config", "gui", "web", "models", "kb"}
    if (config.is_first_run
            and not args.no_setup
            and command not in skip_wizard_commands):
        try:
            from zhushou.config.wizard import SetupWizard
            wizard = SetupWizard(config)
            config = wizard.run_cli()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup skipped.")

    # Merge stored config into CLI args (CLI args override config)
    config.resolve(args)

    # ── Dispatch ───────────────────────────────────────────────────

    if command == "chat":
        _cmd_chat(args)
    elif command == "pipeline":
        _cmd_pipeline(args)
    elif command == "models":
        _cmd_models(args)
    elif command == "config":
        _cmd_config(args, config)
    elif command == "kb":
        _cmd_kb(args)
    elif command == "gui":
        _cmd_gui(args, config)
    elif command == "web":
        _cmd_web(args, config)
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
    if hasattr(args, "timeout") and args.timeout and args.timeout != 300:
        kwargs["timeout"] = args.timeout

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
        api_key=args.api_key or "",
        base_url=args.base_url or "",
        work_dir=args.output or ".",
        proxy=args.proxy or "",
        timeout=args.timeout or 300,
        world_sense=not getattr(args, "no_world", False),
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
        api_key=args.api_key or "",
        base_url=args.base_url or "",
        proxy=args.proxy or "",
        full=args.full,
        timeout=args.timeout or 300,
        kb=args.kb,
        world_sense=not getattr(args, "no_world", False),
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


def _cmd_config(args: argparse.Namespace, config: object = None) -> None:
    """Handle the config subcommand."""
    from zhushou.config.manager import ZhuShouConfig

    if config is None:
        config = ZhuShouConfig.load()

    # --setup flag: re-run wizard
    if getattr(args, "setup", False):
        from zhushou.config.wizard import SetupWizard
        wizard = SetupWizard(config)
        try:
            wizard.run_cli()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
        return

    if args.json_output:
        print(json.dumps(config.to_display_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Config directory: {config.config_path.parent}")
        print(f"Config file: {config.config_path}")
        d = config.to_display_dict()
        for k, v in d.items():
            print(f"  {k}: {v}")


def _cmd_kb(args: argparse.Namespace) -> None:
    """Handle the kb subcommand group."""
    from zhushou.knowledge.kb_manager import KBManager
    from zhushou.knowledge.kb_config import KBConfig

    kb = KBManager(KBConfig())
    sub = getattr(args, "kb_command", None)

    if sub == "list":
        sources = kb.list_sources()
        if args.json_output:
            print(json.dumps(sources, ensure_ascii=False, indent=2))
        else:
            fmt = "{:<20} {:<16} {:>4}  {:>5}  {:>5}  {:>7}  {:>6}"
            print(fmt.format("Key", "Name", "Type", "Down", "Index", "Chunks", "Sheet"))
            print("-" * 82)
            for s in sources:
                print(fmt.format(
                    s["key"], s["name"],
                    s.get("type", "?")[:4],
                    "yes" if s["downloaded"] else "-",
                    "yes" if s["indexed"] else "-",
                    str(s["index_chunks"]) if s["indexed"] else "-",
                    "yes" if s["cheatsheet"] else "-",
                ))
    elif sub == "download":
        saved, errors = kb.download(args.source)
        if args.json_output:
            print(json.dumps({"saved": saved, "errors": errors}, ensure_ascii=False))
        else:
            print(f"Downloaded {saved} file(s) for '{args.source}'")
            for e in errors:
                print(f"  Error: {e}", file=sys.stderr)
    elif sub == "index":
        chunks, files = kb.index(args.source)
        if args.json_output:
            print(json.dumps({"chunks": chunks, "files": files}, ensure_ascii=False))
        else:
            print(f"Indexed {chunks} chunks from {files} file(s) for '{args.source}'")
    elif sub == "search":
        results = kb.search(args.query, collections=args.source)
        if args.json_output:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            if not results:
                print("No results found.")
            else:
                for i, hit in enumerate(results, 1):
                    meta = hit.get("metadata", {})
                    src = meta.get("source", "?")
                    fname = meta.get("file", "?")
                    dist = hit.get("distance", 0)
                    print(f"\n--- Result {i} [{src}/{fname}] (dist: {dist:.3f}) ---")
                    print(hit.get("text", "")[:500])
    elif sub == "cheatsheet":
        cs = kb.get_cheatsheet(args.name)
        if cs:
            print(cs)
        else:
            available = ", ".join(sorted(
                s["key"] for s in kb.list_sources() if s["cheatsheet"]
            ))
            print(f"No cheatsheet for '{args.name}'. Available: {available}")
    elif sub == "crawl":
        try:
            pages_saved, output_dir = kb.crawl(
                args.url,
                name=args.name,
                max_pages=args.max_pages,
                prefix=args.prefix,
            )
            if args.json_output:
                print(json.dumps({"pages_saved": pages_saved, "output_dir": output_dir},
                                 ensure_ascii=False))
            else:
                print(f"Crawled {pages_saved} page(s) from '{args.url}'")
                print(f"Saved to: {output_dir}")
                print("Auto-indexed into knowledge base.")
        except ImportError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif sub == "upload":
        dup_action = "overwrite" if getattr(args, "overwrite", False) else "skip"
        result = kb.upload_files(args.name, args.files, duplicate_action=dup_action)
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"KB '{args.name}' (internal: {result['internal_name']})")
            print(f"  Saved: {result['saved']}  Skipped: {result['skipped']}")
            if result["errors"]:
                for e in result["errors"]:
                    print(f"  Error: {e}", file=sys.stderr)
    elif sub == "import":
        result = kb.import_directory(args.name, args.dir_path)
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"KB '{args.name}' (internal: {result['internal_name']})")
            print(f"  Imported: {result['saved']} file(s)")
            if result["errors"]:
                for e in result["errors"]:
                    print(f"  Error: {e}", file=sys.stderr)
    elif sub == "delete":
        if not args.name.startswith("user_"):
            print("Error: Only user-created KBs (user_* prefix) can be deleted.", file=sys.stderr)
            sys.exit(1)
        deleted = kb.delete_user_kb(args.name)
        if args.json_output:
            print(json.dumps({"deleted": deleted, "name": args.name}, ensure_ascii=False))
        elif deleted:
            print(f"Deleted KB '{args.name}'")
        else:
            print(f"KB '{args.name}' not found.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: zhushou kb {list|download|index|search|cheatsheet|crawl|upload|import|delete}")
        print("Run 'zhushou kb --help' for details.")


def _cmd_gui(args: argparse.Namespace, config: object = None) -> None:
    """Launch the PySide6 desktop GUI."""
    try:
        from zhushou.gui.app import launch_gui
        launch_gui(config=config)
    except ImportError:
        print(
            "Error: PySide6 is required for GUI mode.\n"
            "Install with: pip install zhushou[gui]  or  pip install PySide6",
            file=sys.stderr,
        )
        sys.exit(1)


def _cmd_web(args: argparse.Namespace, config: object = None) -> None:
    """Launch the FastAPI web interface."""
    try:
        from zhushou.web.app import launch_web
        launch_web(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8765),
            config=config,
        )
    except ImportError:
        print(
            "Error: fastapi and uvicorn are required for web mode.\n"
            "Install with: pip install zhushou[web]  or  pip install fastapi uvicorn",
            file=sys.stderr,
        )
        sys.exit(1)


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
        if hasattr(args, "timeout") and args.timeout and args.timeout != 300:
            kwargs["timeout"] = args.timeout
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
            world_sense=not getattr(args, "no_world", False),
        )
        loop.run_interactive()

    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
