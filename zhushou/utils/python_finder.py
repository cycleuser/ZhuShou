"""Discover Python executables on the system."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PythonInterpreter:
    """Describes a discovered Python interpreter."""

    path: str
    version: str
    is_venv: bool = False
    is_current: bool = False


def discover_all_pythons() -> list[PythonInterpreter]:
    """Discover all Python 3 interpreters available on this system.

    Scans PATH, well-known install locations, pyenv, and conda.
    Returns a deduplicated list sorted by version (newest first).
    """
    candidates: set[str] = set()

    # 1. Current interpreter (always first candidate)
    if sys.executable:
        candidates.add(sys.executable)

    # 2. Scan PATH for python* executables
    for name in ("python3", "python3.10", "python3.11", "python3.12",
                 "python3.13", "python3.14", "python"):
        path = shutil.which(name)
        if path:
            candidates.add(path)

    # 3. Well-known install directories
    well_known_dirs = [
        "/usr/bin",
        "/usr/local/bin",
        str(Path.home() / ".local" / "bin"),
    ]
    for d in well_known_dirs:
        if os.path.isdir(d):
            for entry in os.listdir(d):
                if entry.startswith("python3") and not entry.endswith("-config"):
                    full = os.path.join(d, entry)
                    if os.path.isfile(full) and os.access(full, os.X_OK):
                        candidates.add(full)

    # 4. pyenv versions
    pyenv_root = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
    pyenv_versions = os.path.join(pyenv_root, "versions")
    if os.path.isdir(pyenv_versions):
        for pattern in glob.glob(os.path.join(pyenv_versions, "*/bin/python3")):
            if os.path.isfile(pattern) and os.access(pattern, os.X_OK):
                candidates.add(pattern)

    # 5. Conda environments
    conda_envs = os.path.join(Path.home(), ".conda", "envs")
    if os.path.isdir(conda_envs):
        for pattern in glob.glob(os.path.join(conda_envs, "*/bin/python3")):
            if os.path.isfile(pattern) and os.access(pattern, os.X_OK):
                candidates.add(pattern)

    # Deduplicate by resolved real path
    seen_real: set[str] = set()
    unique: list[str] = []
    for c in sorted(candidates):
        try:
            real = os.path.realpath(c)
        except OSError:
            real = c
        if real not in seen_real:
            seen_real.add(real)
            unique.append(c)

    # Probe each candidate for version
    results: list[PythonInterpreter] = []
    current_real = os.path.realpath(sys.executable) if sys.executable else ""

    for path in unique:
        version = _probe_version(path)
        if not version:
            continue  # Not a working Python interpreter
        if not version.startswith("3"):
            continue  # Only Python 3

        try:
            is_current = os.path.realpath(path) == current_real
        except OSError:
            is_current = path == sys.executable

        # Detect venv: presence of pyvenv.cfg next to the bin directory
        bin_dir = os.path.dirname(os.path.realpath(path))
        parent_dir = os.path.dirname(bin_dir)
        is_venv = os.path.isfile(os.path.join(parent_dir, "pyvenv.cfg"))

        results.append(PythonInterpreter(
            path=path,
            version=version,
            is_venv=is_venv,
            is_current=is_current,
        ))

    # Sort: current first, then by version descending
    results.sort(key=lambda p: (not p.is_current, p.version), reverse=False)
    # Re-sort by version descending but current always first
    results.sort(key=lambda p: (not p.is_current, [-int(x) for x in p.version.split(".")[:3] if x.isdigit()]))

    return results


def _probe_version(path: str) -> str:
    """Run ``<path> --version`` and return the version string, or ``""`` on failure."""
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Output is typically "Python 3.12.3"
        output = (result.stdout.strip() or result.stderr.strip())
        if output.startswith("Python "):
            return output[7:].strip()
        return output.strip()
    except Exception:
        return ""


def find_python() -> str:
    """Find a suitable Python 3 executable.

    Returns the path to the current interpreter first, then tries
    common locations via ``shutil.which``.
    """
    interpreters = discover_all_pythons()
    if interpreters:
        return interpreters[0].path

    # Fallback (original logic)
    current = sys.executable
    if current:
        return current

    for name in ("python3", "python"):
        path = shutil.which(name)
        if path:
            return path

    return "python3"
