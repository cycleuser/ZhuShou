"""GitHub Issues tracker adapter.

Maps GitHub Issues to the universal ``Task`` model so that the orchestrator
can work directly with a GitHub repository's issue tracker.

Features:
- Fetches open issues filtered by label and/or milestone.
- Maps GitHub issue state (``open`` / ``closed``) and labels to the
  internal state machine (``todo``, ``in_progress``, ``done``, etc.).
- Supports state transitions via label manipulation and issue close/reopen.
- Posts comments on issues for progress updates.
- Respects ``blocked_by`` relationships encoded as issue references in the
  body (e.g. ``blocked by #12``).

Requires ``httpx`` (already a ZhuShou core dependency).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Sequence

import httpx

from zhushou.tracker.base import TrackerAdapter
from zhushou.tracker.task import Task

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_BLOCKED_BY_RE = re.compile(
    r"(?:blocked\s+by|depends\s+on)\s+#(\d+)",
    re.IGNORECASE,
)

# Default mapping from GitHub labels to internal states.
# The first matching label wins (checked in order).
_LABEL_STATE_MAP: list[tuple[str, str]] = [
    ("in progress", "in_progress"),
    ("in-progress", "in_progress"),
    ("doing", "in_progress"),
    ("done", "done"),
    ("completed", "done"),
    ("cancelled", "cancelled"),
    ("wontfix", "cancelled"),
]


class GitHubIssuesTracker(TrackerAdapter):
    """Tracker adapter backed by GitHub Issues.

    Parameters
    ----------
    repo : str
        ``owner/repo`` slug (e.g. ``"cycleuser/ZhuShou"``).
    token : str
        GitHub personal access token or fine-grained token with
        ``issues: read/write`` scope.
    label_filter : str
        Only fetch issues carrying this label.  Empty string means all.
    label_state_map : list[tuple[str, str]] | None
        Custom label → internal-state mapping.  Falls back to defaults.
    state_label_prefix : str
        Prefix used for state labels managed by the adapter.  When the
        adapter sets a task to ``in_progress`` it will add a label
        ``<prefix>in_progress`` and remove other state labels with
        the same prefix.  Default ``"zhushou:"``.
    """

    def __init__(
        self,
        repo: str,
        token: str,
        label_filter: str = "",
        label_state_map: list[tuple[str, str]] | None = None,
        state_label_prefix: str = "zhushou:",
    ) -> None:
        self._repo = repo.strip("/")
        self._token = token
        self._label_filter = label_filter.strip()
        self._label_state_map = label_state_map or _LABEL_STATE_MAP
        self._state_label_prefix = state_label_prefix
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # HTTP client lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_GITHUB_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self._token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # TrackerAdapter implementation
    # ------------------------------------------------------------------

    async def fetch_candidate_tasks(
        self,
        active_states: Sequence[str],
        terminal_states: Sequence[str],
    ) -> list[Task]:
        issues = await self._fetch_open_issues()
        active_set = {s.strip().lower() for s in active_states}
        terminal_set = {s.strip().lower() for s in terminal_states}

        # Build state map to resolve blockers
        tasks = [self._issue_to_task(iss) for iss in issues]
        state_map = {t.id: t.state.strip().lower() for t in tasks}

        candidates: list[Task] = []
        for t in tasks:
            normalised = t.state.strip().lower()
            if normalised not in active_set:
                continue
            if normalised in terminal_set:
                continue
            if _has_active_blocker(t, state_map, terminal_set):
                continue
            candidates.append(t)

        return candidates

    async def fetch_task_by_id(self, task_id: str) -> Task | None:
        client = await self._get_client()
        url = f"/repos/{self._repo}/issues/{task_id}"
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            logger.warning("GitHub API error fetching issue %s: %s", task_id, exc)
            return None
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._issue_to_task(resp.json())

    async def fetch_task_states_by_ids(
        self,
        task_ids: Sequence[str],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for task_id in task_ids:
            task = await self.fetch_task_by_id(task_id)
            if task is not None:
                result[task.id] = task.state
        return result

    async def update_task_state(self, task_id: str, new_state: str) -> None:
        client = await self._get_client()
        url = f"/repos/{self._repo}/issues/{task_id}"

        # Determine GitHub-level changes
        patch: dict[str, Any] = {}
        normalised = new_state.strip().lower()

        if normalised in ("done", "completed", "cancelled"):
            patch["state"] = "closed"
            if normalised == "cancelled":
                patch["state_reason"] = "not_planned"
        else:
            patch["state"] = "open"

        # Update state labels
        current_task = await self.fetch_task_by_id(task_id)
        if current_task:
            current_labels = set(current_task.labels)
            # Remove old state labels with our prefix
            new_labels = {
                lbl for lbl in current_labels
                if not lbl.startswith(self._state_label_prefix)
            }
            # Add new state label
            state_label = f"{self._state_label_prefix}{normalised}"
            new_labels.add(state_label)
            patch["labels"] = sorted(new_labels)

        try:
            resp = await client.patch(url, json=patch)
            resp.raise_for_status()
            logger.debug("Updated issue %s → state=%s", task_id, new_state)
        except httpx.HTTPError as exc:
            logger.error("Failed to update issue %s: %s", task_id, exc)
            raise

    async def create_comment(self, task_id: str, body: str) -> None:
        client = await self._get_client()
        url = f"/repos/{self._repo}/issues/{task_id}/comments"
        try:
            resp = await client.post(url, json={"body": body})
            resp.raise_for_status()
            logger.debug("Posted comment on issue %s", task_id)
        except httpx.HTTPError as exc:
            logger.error("Failed to comment on issue %s: %s", task_id, exc)
            raise

    # ------------------------------------------------------------------
    # GitHub API helpers
    # ------------------------------------------------------------------

    async def _fetch_open_issues(self) -> list[dict[str, Any]]:
        """Fetch all open issues, paginating automatically."""
        client = await self._get_client()
        all_issues: list[dict[str, Any]] = []
        page = 1

        while True:
            params: dict[str, Any] = {
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "asc",
            }
            if self._label_filter:
                params["labels"] = self._label_filter

            try:
                resp = await client.get(
                    f"/repos/{self._repo}/issues",
                    params=params,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("GitHub API error fetching issues: %s", exc)
                break

            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break

            # Filter out pull requests (GitHub API returns them in /issues)
            for item in batch:
                if "pull_request" not in item:
                    all_issues.append(item)

            # Stop if we got fewer than a full page
            if len(batch) < 100:
                break
            page += 1

        return all_issues

    def _issue_to_task(self, issue: dict[str, Any]) -> Task:
        """Convert a GitHub issue JSON object to a ``Task``."""
        issue_number = str(issue.get("number", ""))
        labels = _extract_label_names(issue)
        state = self._resolve_state(issue, labels)

        # Parse blocked_by from issue body
        body = issue.get("body") or ""
        blocked_by = _parse_blocked_by(body)

        assignee = issue.get("assignee") or {}
        assignee_login = assignee.get("login", "") if isinstance(assignee, dict) else ""

        return Task(
            id=issue_number,
            identifier=f"#{issue_number}",
            title=str(issue.get("title", "")),
            description=body,
            state=state,
            priority=_priority_from_labels(labels),
            labels=labels,
            assignee=assignee_login,
            url=str(issue.get("html_url", "")),
            blocked_by=blocked_by,
            created_at=_parse_gh_datetime(issue.get("created_at")),
            updated_at=_parse_gh_datetime(issue.get("updated_at")),
            metadata={"github_id": issue.get("id"), "node_id": issue.get("node_id")},
        )

    def _resolve_state(
        self,
        issue: dict[str, Any],
        labels: list[str],
    ) -> str:
        """Determine internal state from GitHub issue state and labels.

        Priority order:
        1. Labels with the ``state_label_prefix`` (e.g. ``zhushou:in_progress``).
        2. Labels matching ``_label_state_map``.
        3. GitHub issue state (open → todo, closed → done).
        """
        lower_labels = [lbl.lower() for lbl in labels]

        # Check prefixed state labels first
        for lbl in lower_labels:
            if lbl.startswith(self._state_label_prefix):
                return lbl[len(self._state_label_prefix):]

        # Check generic label → state mapping
        for label_pattern, internal_state in self._label_state_map:
            if label_pattern.lower() in lower_labels:
                return internal_state

        # Fall back to GitHub state
        gh_state = str(issue.get("state", "open")).lower()
        if gh_state == "closed":
            reason = str(issue.get("state_reason", "")).lower()
            return "cancelled" if reason == "not_planned" else "done"
        return "todo"


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_label_names(issue: dict[str, Any]) -> list[str]:
    """Extract label name strings from a GitHub issue object."""
    raw_labels = issue.get("labels", [])
    if not isinstance(raw_labels, list):
        return []
    names: list[str] = []
    for lbl in raw_labels:
        if isinstance(lbl, dict):
            name = lbl.get("name")
            if name:
                names.append(str(name))
        elif isinstance(lbl, str):
            names.append(lbl)
    return names


def _parse_blocked_by(body: str) -> list[str]:
    """Extract issue numbers from ``blocked by #N`` patterns in the body."""
    return list(dict.fromkeys(_BLOCKED_BY_RE.findall(body)))


def _priority_from_labels(labels: list[str]) -> int:
    """Derive a numeric priority from well-known priority labels.

    Returns 1 (urgent) through 4 (low), or 0 (unset) if no match.
    """
    lower = {lbl.lower() for lbl in labels}
    if "priority: urgent" in lower or "p0" in lower:
        return 1
    if "priority: high" in lower or "p1" in lower:
        return 2
    if "priority: medium" in lower or "p2" in lower:
        return 3
    if "priority: low" in lower or "p3" in lower:
        return 4
    return 0


def _parse_gh_datetime(value: Any) -> datetime | None:
    """Parse a GitHub ISO-8601 timestamp."""
    if not value:
        return None
    try:
        # GitHub uses e.g. "2024-01-15T10:30:00Z"
        s = str(value)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _has_active_blocker(
    task: Task,
    state_map: dict[str, str],
    terminal_states: set[str],
) -> bool:
    """True when *task* has at least one blocker in a non-terminal state."""
    for blocker_id in task.blocked_by:
        blocker_state = state_map.get(blocker_id, "")
        if blocker_state and blocker_state not in terminal_states:
            return True
    return False
