#!/usr/bin/env python3
"""Quest - Autonomous AI Coding Assistant powered by local Ollama models."""

import os
import sys

import click

from ollama_client import OllamaClient
from pipeline import Pipeline
from display import console, show_welcome, show_model_selector, show_error, show_info


@click.group()
def cli():
    """Quest - Autonomous AI Coding Assistant powered by Ollama."""
    pass


@cli.command()
@click.argument("request")
@click.option(
    "--output", "-o",
    default=None,
    help="Output directory for the generated project (default: ./output)",
)
@click.option(
    "--model", "-m",
    default=None,
    help="Ollama model name to use (skips interactive selection)",
)
@click.option(
    "--url",
    default="http://localhost:11434",
    help="Ollama server URL",
)
def run(request: str, output: str, model: str, url: str):
    """Run the autonomous coding pipeline for a project REQUEST.

    Example:
        python quest.py run "Build a terminal Gomoku game" -o ./gomoku
    """
    show_welcome()

    # Initialize Ollama client
    client = OllamaClient(base_url=url)

    # Check connection
    if not client.check_connection():
        show_error(f"Cannot connect to Ollama at {url}. Is it running?")
        sys.exit(1)
    show_info(f"Connected to Ollama at {url}")

    # Model selection
    if model:
        client.model = model
        show_info(f"Using model: {model}")
    else:
        models = client.list_models()
        selected = show_model_selector(models)
        client.model = selected

    # Output directory
    if output is None:
        # Generate a default name from the request
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in request[:30])
        safe_name = safe_name.strip().replace(" ", "_") or "output"
        output = os.path.join(".", safe_name)
    output = os.path.abspath(output)
    show_info(f"Output directory: {output}")

    console.print()
    console.rule("[bold cyan]Starting Autonomous Pipeline[/bold cyan]")
    console.print()

    # Run pipeline
    pipeline = Pipeline(client=client, work_dir=output)
    try:
        pipeline.run(user_request=request)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
        sys.exit(1)
    except ConnectionError as e:
        show_error(str(e))
        sys.exit(1)
    finally:
        client.close()


@cli.command()
@click.option(
    "--url",
    default="http://localhost:11434",
    help="Ollama server URL",
)
def models(url: str):
    """List available Ollama models."""
    client = OllamaClient(base_url=url)
    if not client.check_connection():
        show_error(f"Cannot connect to Ollama at {url}. Is it running?")
        sys.exit(1)
    model_list = client.list_models()
    show_model_selector(model_list)
    client.close()


if __name__ == "__main__":
    cli()
