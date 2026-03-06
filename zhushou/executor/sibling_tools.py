"""Discover and dispatch tools from sibling ZhuShou packages.

Each sibling package is expected to expose:
  - ``TOOLS``: a list of OpenAI-format tool schemas
  - ``dispatch(name, arguments) -> dict``: handler function
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


class SiblingToolDiscovery:
    """Dynamically discover tool definitions from sibling packages."""

    SIBLING_PACKAGES: list[str] = [
        "chou",
        "gangdan",
        "huan",
        "liao",
        "nuoyi",
        "copytalker",
        "lapian",
    ]

    @classmethod
    def discover(cls) -> tuple[list[dict[str, Any]], dict[str, Callable[..., Any]]]:
        """Try importing each sibling package and collect their tools.

        Returns
        -------
        tuple[list[dict], dict]
            A ``(merged_tools, dispatch_map)`` tuple where
            ``merged_tools`` is the combined list of OpenAI-format tool
            schemas and ``dispatch_map`` maps tool names to their
            originating module's ``dispatch`` callable.
        """
        merged_tools: list[dict[str, Any]] = []
        dispatch_map: dict[str, Callable[..., Any]] = {}

        for pkg_name in cls.SIBLING_PACKAGES:
            try:
                mod = importlib.import_module(pkg_name)
            except ImportError:
                continue

            # Collect schemas
            tools: list[dict[str, Any]] = getattr(mod, "TOOLS", [])
            if not isinstance(tools, list):
                continue

            # Collect dispatch callable
            pkg_dispatch: Callable[..., Any] | None = getattr(mod, "dispatch", None)
            if pkg_dispatch is None or not callable(pkg_dispatch):
                continue

            for tool_def in tools:
                func_info = tool_def.get("function", {})
                tool_name = func_info.get("name", "")
                if tool_name and tool_name not in dispatch_map:
                    merged_tools.append(tool_def)
                    dispatch_map[tool_name] = pkg_dispatch

        return merged_tools, dispatch_map

    @staticmethod
    def dispatch(
        tool_name: str,
        arguments: dict[str, Any],
        dispatch_map: dict[str, Callable[..., Any]],
    ) -> dict[str, Any]:
        """Route a tool call to the correct sibling package handler.

        Parameters
        ----------
        tool_name : str
            The function name to invoke.
        arguments : dict
            Arguments dictionary for the tool.
        dispatch_map : dict
            Mapping from tool name to sibling ``dispatch`` callable.

        Returns
        -------
        dict
            ``{"success": bool, "output": str}`` (or sibling's return format).
        """
        handler = dispatch_map.get(tool_name)
        if handler is None:
            return {
                "success": False,
                "output": f"No sibling handler found for tool: {tool_name}",
            }
        try:
            result = handler(tool_name, arguments)
            # Normalise to our standard format if needed
            if isinstance(result, dict):
                return result
            return {"success": True, "output": str(result)}
        except Exception as exc:
            return {
                "success": False,
                "output": f"Sibling tool error ({tool_name}): {exc}",
            }
