"""{{package_name}} command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="{{package_name}}",
        description="{{description}}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --help\n"
            "  %(prog)s -V\n"
        ),
    )

    # ── Standard flags ────────────────────────────────────────────
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output path",
    )

    # ── Project-specific arguments ────────────────────────────────
    # TODO: Add your project-specific arguments here.
    # Example:
    #   parser.add_argument("input", help="Input file or value")
    #   parser.add_argument("--format", choices=["csv","json"], default="json")

    args = parser.parse_args(argv)

    # ── Dispatch ──────────────────────────────────────────────────
    # TODO: Call your core logic or API functions here.
    # Example:
    #   from .api import do_something
    #   result = do_something(args.input)
    #   if args.json_output:
    #       print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    #   elif result.success:
    #       print(result.data)
    #   else:
    #       print(f"Error: {result.error}", file=sys.stderr)
    #       sys.exit(1)

    parser.print_help()
