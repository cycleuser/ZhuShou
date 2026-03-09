"""Command-line interface for Flask-based services.

This module provides a robust CLI with support for standard flags,
verbose output, JSON mode, and quiet operation.
"""

import argparse
import json
import sys
from typing import Optional

from .core import (
    main_processing,
    validate_request,
    process_text,
    transform_data,
    aggregate_results
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with standard flags.
    
    Returns:
        ArgumentParser configured with all standard and custom flags
    """
    parser = argparse.ArgumentParser(
        prog="flask_api",
        description="Flask-based service API CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s process --text "Hello World"
  %(prog)s validate --text "Invalid input"
  %(prog)s transform --json
  %(prog)s aggregate --input data.json --mode average
"""
    )
    
    # Standard flags (required by specification)
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with detailed information"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results in JSON format"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output"
    )
    
    # Command-specific flags
    parser.add_argument(
        "command",
        nargs="?",
        choices=["process", "validate", "transform", "aggregate", "health"],
        default="process",
        help="Command to execute (default: process)"
    )
    
    # Common input/output flags
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input text or file path"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path"
    )
    
    # Command-specific arguments
    parser.add_argument(
        "--text", "-t",
        type=str,
        default=None,
        help="Text to process (alternative to --input)"
    )
    
    parser.add_argument(
        "--mode", "-m",
        type=str,
        default="default",
        choices=["default", "strict", "lenient"],
        help="Processing mode"
    )
    
    parser.add_argument(
        "--parameters", "-p",
        type=str,
        dest="params_json",
        help="JSON string of additional parameters"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of texts to process in batch mode"
    )
    
    parser.add_argument(
        "--aggregation-mode",
        type=str,
        default="average",
        choices=["average", "sum", "count"],
        help="Mode for aggregation operation"
    )
    
    return parser


def execute_command(args: argparse.Namespace) -> int:
    """Execute the specified command with given arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Get input text
        if args.text:
            input_text = args.text
        elif args.input:
            # In a real implementation, this would read from file
            input_text = f"Input from {args.input}"
        else:
            return 1
        
        # Execute command
        if args.command == "process":
            result = process_text(
                text=input_text,
                mode=args.mode,
                parameters=json.loads(args.params_json) if args.params_json else None
            )
            
        elif args.command == "validate":
            result = validate_request(
                input_text=input_text,
                mode=args.mode
            )
            
        elif args.command == "transform":
            # Transform a sample response data
            sample_data = {
                "output_text": "Transformed text",
                "confidence": 0.95,
                "flags": ["flag1", "flag2"]
            }
            result = transform_data(sample_data)
            
        elif args.command == "aggregate":
            # Aggregate sample results
            sample_results = [
                {"output_text": "Result 1", "confidence": 0.9},
                {"output_text": "Result 2", "confidence": 0.85}
            ]
            result = aggregate_results(sample_results, args.aggregation_mode)
            
        elif args.command == "health":
            # Simulate health check
            result = {
                "status": "healthy",
                "components": ["core", "api", "tools"],
                "timestamp": "2024-01-15T10:30:00Z"
            }
            
        else:
            return 1
        
        # Output result
        if args.json_output or args.verbose:
            output = json.dumps(result.to_dict(), indent=2)
        else:
            output = str(result)
        
        if not args.quiet and args.command != "health":
            print(output)
        
        return 0
        
    except Exception as e:
        error_output = f"Error: {str(e)}"
        if args.json_output or args.verbose:
            import traceback
            error_output = json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }, indent=2)
        else:
            print(error_output, file=sys.stderr)
        
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    return execute_command(args)


if __name__ == "__main__":
    sys.exit(main())
