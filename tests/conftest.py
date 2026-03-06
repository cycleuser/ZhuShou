"""Shared test fixtures for ZhuShou tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_work_dir(tmp_path: Path) -> Path:
    """Return a temporary directory suitable as a work_dir."""
    return tmp_path


@pytest.fixture
def tmp_memory_file(tmp_path: Path) -> Path:
    """Return a temporary file path for PersistentMemory."""
    return tmp_path / "memory.json"


@pytest.fixture
def tmp_logs_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for ConversationLog."""
    logs = tmp_path / "logs"
    logs.mkdir()
    return logs


@pytest.fixture
def tmp_usage_file(tmp_path: Path) -> Path:
    """Return a temporary file path for TokenTracker."""
    return tmp_path / "usage.json"
