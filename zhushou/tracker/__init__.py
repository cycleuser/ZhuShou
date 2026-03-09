"""Pluggable task-source adapters for the orchestrator.

Use :func:`create_tracker` to instantiate the correct adapter based on
the ``tracker.kind`` setting in the workflow configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zhushou.tracker.base import TrackerAdapter
    from zhushou.workflow.config import WorkflowConfig


def create_tracker(config: WorkflowConfig) -> TrackerAdapter:
    """Factory: build a tracker adapter from workflow config.

    Supported ``tracker.kind`` values:

    * ``"local"``  -- reads/writes ``tasks.yaml`` (default)
    * ``"github"`` -- reads/writes GitHub Issues
    * ``"memory"`` -- in-process list (testing only)
    """
    kind = config.tracker_kind.strip().lower()

    if kind == "github":
        from zhushou.tracker.github_issues import GitHubIssuesTracker

        return GitHubIssuesTracker(
            repo=config.tracker_repo,
            token=config.tracker_api_key,
            label_filter=config.tracker_label,
        )

    if kind == "memory":
        from zhushou.tracker.memory import MemoryTracker

        return MemoryTracker()

    # Default: local YAML
    from zhushou.tracker.local_yaml import LocalYAMLTracker

    return LocalYAMLTracker(file_path=config.tracker_file)
