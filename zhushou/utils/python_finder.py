"""Discover Python executable on the system."""

from __future__ import annotations

import shutil
import sys


def find_python() -> str:
    """Find a suitable Python 3 executable.

    Returns the path to the current interpreter first, then tries
    common locations via ``shutil.which``.
    """
    # Prefer the interpreter that is running ZhuShou
    current = sys.executable
    if current:
        return current

    for name in ("python3", "python"):
        path = shutil.which(name)
        if path:
            return path

    return "python3"  # fallback
