"""{{package_name}} OpenAI function-calling tool definitions.

Provides a ``TOOLS`` list (OpenAI format) and a ``dispatch()`` function
so that LLM agents can call {{package_name}} as a tool.
"""

from __future__ import annotations

import json as _json
from typing import Any


# ---------------------------------------------------------------------------
# Tool schema list — add one dict per API function.
#
# Example entry:
#
#   {
#       "type": "function",
#       "function": {
#           "name": "{{package_name}}_do_something",
#           "description": "Do something useful.",
#           "parameters": {
#               "type": "object",
#               "properties": {
#                   "input_text": {
#                       "type": "string",
#                       "description": "The text to process.",
#                   },
#               },
#               "required": ["input_text"],
#           },
#       },
#   }
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    # TODO: Add your tool definitions here.
]


def dispatch(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    """Route a tool call to the matching API function.

    Parameters
    ----------
    name : str
        Tool name (must match a ``function.name`` in :data:`TOOLS`).
    arguments : dict or str
        Arguments dict, or a JSON string that will be parsed.

    Returns
    -------
    dict
        Result from ``ToolResult.to_dict()``.

    Raises
    ------
    ValueError
        If *name* does not match any known tool.
    """
    if isinstance(arguments, str):
        arguments = _json.loads(arguments)

    # TODO: Add dispatch cases here.  Example:
    #
    #   if name == "{{package_name}}_do_something":
    #       from .api import do_something
    #       return do_something(**arguments).to_dict()

    raise ValueError(f"Unknown tool: {name}")
