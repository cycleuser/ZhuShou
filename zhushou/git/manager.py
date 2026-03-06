"""ZhuShou git integration manager.

Provides safe git operations with ``.git`` directory protection.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Optional


class GitManager:
    """High-level helpers for common git operations.

    All methods are **static / class-level** so they can be used
    without instantiation when only a ``work_dir`` is available.
    """

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @staticmethod
    def is_git_repo(path: str) -> bool:
        """Return ``True`` when *path* (or a parent) contains a ``.git`` directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False

    @staticmethod
    def protect_git_dir(target_path: str) -> bool:
        """Return ``False`` if *target_path* resides inside a ``.git`` directory.

        Use this before any write operation to safeguard the repository
        metadata.

        Returns
        -------
        bool
            ``True`` when the path is safe (not inside ``.git``),
            ``False`` when it is protected and should **not** be modified.
        """
        parts = Path(target_path).resolve().parts
        return ".git" not in parts

    # ------------------------------------------------------------------
    # Informational
    # ------------------------------------------------------------------

    @staticmethod
    def get_diff_summary(work_dir: str) -> str:
        """Run ``git diff --stat`` and return the output.

        Returns an empty string when the command fails or the
        directory is not a git repo.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @staticmethod
    def auto_commit(
        work_dir: str,
        message: Optional[str] = None,
    ) -> dict[str, Any]:
        """Stage all changes and create a commit.

        Parameters
        ----------
        work_dir : str
            The repository working directory.
        message : str | None
            Commit message.  When ``None`` an auto-generated message
            based on the diff summary is used.

        Returns
        -------
        dict
            ``{"success": bool, "output": str}``
        """
        if not GitManager.is_git_repo(work_dir):
            return {"success": False, "output": "Not a git repository."}

        # Generate message if not provided
        if not message:
            diff_summary = GitManager.get_diff_summary(work_dir)
            if diff_summary:
                # Extract number of files changed
                lines = diff_summary.strip().splitlines()
                summary_line = lines[-1] if lines else "changes"
                message = f"zhushou: auto-commit ({summary_line})"
            else:
                message = "zhushou: auto-commit"

        try:
            # Stage everything
            add_result = subprocess.run(
                ["git", "add", "."],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if add_result.returncode != 0:
                return {
                    "success": False,
                    "output": f"git add failed: {add_result.stderr.strip()}",
                }

            # Check if there's anything to commit
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if not status_result.stdout.strip():
                return {"success": True, "output": "Nothing to commit (working tree clean)."}

            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = commit_result.stdout
            if commit_result.stderr:
                output += "\n" + commit_result.stderr

            return {
                "success": commit_result.returncode == 0,
                "output": output.strip(),
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "Git operation timed out."}
        except Exception as exc:
            return {"success": False, "output": f"Git error: {exc}"}
