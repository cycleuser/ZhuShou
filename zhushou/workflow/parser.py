"""Parse WORKFLOW.md files with YAML front matter and Jinja2 template body.

File format (mirrors Symphony's WORKFLOW.md convention)::

    ---
    tracker:
      kind: local
      file: tasks.yaml
    polling:
      interval_ms: 30000
    workspace:
      root: ~/.zhushou/workspaces
    agent:
      max_concurrent_agents: 3
    ...
    ---
    You are working on task `{{ task.identifier }}`.
    Title: {{ task.title }}
    ...

The front matter is parsed as YAML; the body after the closing ``---`` is
kept as a raw string (rendered later by the prompt builder).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class WorkflowData:
    """Result of parsing a WORKFLOW.md file."""

    config: dict[str, Any] = field(default_factory=dict)
    prompt_template: str = ""
    raw_content: str = ""
    source_path: str = ""


class WorkflowParseError(Exception):
    """Raised when a WORKFLOW.md file cannot be parsed."""


def parse_workflow(path: str | Path) -> WorkflowData:
    """Read and parse a WORKFLOW.md file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    WorkflowParseError
        If the YAML front matter is malformed.
    """
    filepath = Path(path)
    content = filepath.read_text(encoding="utf-8")
    config, prompt = _split_front_matter(content)

    return WorkflowData(
        config=config,
        prompt_template=prompt,
        raw_content=content,
        source_path=str(filepath.resolve()),
    )


def parse_workflow_string(content: str, source: str = "<string>") -> WorkflowData:
    """Parse workflow content from a string (useful for tests)."""
    config, prompt = _split_front_matter(content)
    return WorkflowData(
        config=config,
        prompt_template=prompt,
        raw_content=content,
        source_path=source,
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _split_front_matter(content: str) -> tuple[dict[str, Any], str]:
    """Split *content* into (YAML config dict, prompt template string).

    The YAML front matter is delimited by lines that consist of exactly
    ``---`` (with optional trailing whitespace).  Everything before the
    first ``---`` is ignored; everything between the first and second
    ``---`` is YAML; everything after the second ``---`` is the prompt.
    """
    lines = content.split("\n")
    fence_positions: list[int] = []

    for idx, line in enumerate(lines):
        if line.strip() == "---":
            fence_positions.append(idx)
            if len(fence_positions) == 2:
                break

    if len(fence_positions) < 2:
        # No valid front matter -- treat entire content as prompt, empty config
        logger.debug("No YAML front matter found; using defaults")
        return {}, content.strip()

    yaml_block = "\n".join(lines[fence_positions[0] + 1 : fence_positions[1]])
    prompt_block = "\n".join(lines[fence_positions[1] + 1 :]).strip()

    try:
        config = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise WorkflowParseError(f"Invalid YAML front matter: {exc}") from exc

    if not isinstance(config, dict):
        config = {}

    return config, prompt_block
