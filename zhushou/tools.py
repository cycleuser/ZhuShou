"""ZhuShou - OpenAI function-calling tool definitions."""

from __future__ import annotations

import json
from typing import Any


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "zhushou_chat",
            "description": "Send a message to the ZhuShou AI assistant and get a response. Supports multiple LLM providers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The user message to send to the assistant.",
                    },
                    "provider": {
                        "type": "string",
                        "description": "LLM provider name.",
                        "default": "ollama",
                        "enum": ["ollama", "openai", "anthropic", "deepseek", "gemini"],
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name. Empty uses provider default.",
                        "default": "",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "zhushou_run_pipeline",
            "description": "Run the 7-stage autonomous coding pipeline to generate a complete project from a description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "Project description or coding request.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for the generated project.",
                        "default": "./output",
                    },
                    "provider": {
                        "type": "string",
                        "description": "LLM provider name.",
                        "default": "ollama",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name.",
                        "default": "",
                    },
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "zhushou_search_pypi",
            "description": "Search PyPI for Python packages matching a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for PyPI packages.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def dispatch(name: str, arguments: dict[str, Any] | str) -> dict:
    """Dispatch a tool call to the appropriate API function."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if name == "zhushou_chat":
        from .api import chat
        result = chat(**arguments)
        return result.to_dict()

    if name == "zhushou_run_pipeline":
        from .api import run_pipeline
        result = run_pipeline(**arguments)
        return result.to_dict()

    if name == "zhushou_search_pypi":
        from .api import search_pypi
        result = search_pypi(**arguments)
        return result.to_dict()

    raise ValueError(f"Unknown tool: {name}")
