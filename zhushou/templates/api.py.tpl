"""{{package_name}} unified Python API.

Every public function returns a :class:`ToolResult` so that callers
(CLI, agent tools, tests) always get a consistent interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """Standardised result wrapper for all API functions."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Add your API wrapper functions below.
#
# Each function should:
#   1. Accept clear parameters
#   2. Call core logic from core.py
#   3. Return ToolResult(success=True, data=...) on success
#   4. Catch exceptions and return ToolResult(success=False, error=str(e))
#
# Example:
#
#   def do_something(input_text: str) -> ToolResult:
#       try:
#           from .core import process
#           result = process(input_text)
#           return ToolResult(success=True, data=result)
#       except Exception as e:
#           return ToolResult(success=False, error=str(e))
# ---------------------------------------------------------------------------
