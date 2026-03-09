"""flask_api -- A RESTful web API framework with unified Python interface for Flask-based services"""

__version__ = "0.1.0"

from .api import ToolResult  # noqa: F401

__all__ = ["__version__", "ToolResult"]
