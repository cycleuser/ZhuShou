"""Pytest configuration — ensure the package is importable."""

import sys
from pathlib import Path

# Add project root to sys.path so that `import flask_api` works
# even when running pytest from the tests/ directory.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
