"""ZhuShou built-in tool definitions and handlers.

Each tool is defined with an OpenAI-format schema and a handler callable.
Handlers accept ``(work_dir: str, args: dict)`` and return
``{"success": bool, "output": str}``.
"""

from __future__ import annotations

import ast
import glob as _glob
import os
import re
import subprocess
import urllib.request
import json as _json
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _resolve_path(work_dir: str, rel_path: str) -> str:
    """Resolve *rel_path* relative to *work_dir*; reject escapes."""
    rel_path = rel_path.lstrip("/")
    abs_path = os.path.normpath(os.path.join(os.path.abspath(work_dir), rel_path))
    if not abs_path.startswith(os.path.abspath(work_dir)):
        raise ValueError(f"Path escapes work directory: {rel_path}")
    return abs_path


def _is_git_protected(path: str) -> bool:
    """Return ``True`` when *path* lives inside a ``.git`` directory."""
    parts = Path(path).parts
    return ".git" in parts


def _validate_python_file(abs_path: str) -> list[str]:
    """Validate a Python file for syntax errors and stub patterns.

    Returns a list of warning strings (empty if file is clean).
    """
    warnings: list[str] = []

    try:
        with open(abs_path, "r", encoding="utf-8") as fh:
            source = fh.read()
    except Exception:
        return warnings

    # 1. Syntax check via ast.parse
    try:
        tree = ast.parse(source, filename=abs_path)
    except SyntaxError as e:
        line_info = f" on line {e.lineno}" if e.lineno else ""
        msg = e.msg or "invalid syntax"
        warnings.append(f"SYNTAX ERROR{line_info}: {msg}")
        return warnings  # can't do further checks on broken AST

    # 2. Detect stub functions (body is only `pass`, or only a docstring)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            # Skip if the function is just `pass`
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                warnings.append(
                    f"STUB on line {node.lineno}: function '{node.name}' "
                    f"body is only 'pass' — write real implementation"
                )
            # Skip if the body is docstring + pass
            elif (
                len(body) == 2
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[1], ast.Pass)
            ):
                warnings.append(
                    f"STUB on line {node.lineno}: function '{node.name}' "
                    f"has only a docstring and 'pass' — write real implementation"
                )
            # Detect `# TODO` / `# Implementation` as sole body (comment-only
            # functions still parse as having just `pass` or `Expr(Constant)`)
            elif len(body) == 1 and isinstance(body[0], ast.Expr):
                val = body[0].value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    s = val.value
                    if isinstance(s, str) and s.strip().startswith(("#", "TODO", "Implementation")):
                        warnings.append(
                            f"STUB on line {node.lineno}: function "
                            f"'{node.name}' has only a comment string — "
                            f"write real implementation"
                        )

    return warnings


# ───────────────────────────────────────────────────────────────────
# read_file
# ───────────────────────────────────────────────────────────────────

READ_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the content of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                },
            },
            "required": ["path"],
        },
    },
}


def _handle_read_file(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", "")
    if not path:
        return {"success": False, "output": "Missing 'path' argument."}
    abs_path = _resolve_path(work_dir, path)
    if not os.path.isfile(abs_path):
        return {"success": False, "output": f"File not found: {path}"}
    with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    return {"success": True, "output": content}


# ───────────────────────────────────────────────────────────────────
# write_file
# ───────────────────────────────────────────────────────────────────

WRITE_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories as needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                },
                "content": {
                    "type": "string",
                    "description": "Full content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
}


def _handle_write_file(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", "")
    content = args.get("content")
    if not path:
        return {"success": False, "output": "Missing 'path' argument."}
    if content is None:
        return {"success": False, "output": "Missing 'content' argument."}
    abs_path = _resolve_path(work_dir, path)
    if _is_git_protected(abs_path):
        return {"success": False, "output": "Refusing to write inside .git directory."}
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
        if content and not content.endswith("\n"):
            fh.write("\n")

    output = f"File written: {path}"

    # Validate Python files immediately after writing
    if path.endswith(".py"):
        warnings = _validate_python_file(abs_path)
        if warnings:
            output += "\n\nWARNING — issues detected, fix them NOW:\n"
            output += "\n".join(f"  - {w}" for w in warnings)
            output += (
                "\n\nYou MUST rewrite this file to fix the above issues. "
                "Use write_file again with corrected content."
            )

    return {"success": True, "output": output}


# ───────────────────────────────────────────────────────────────────
# edit_file
# ───────────────────────────────────────────────────────────────────

EDIT_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Replace a specific string in a file with a new string.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file.",
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find and replace.",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}


def _handle_edit_file(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", "")
    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    if not path:
        return {"success": False, "output": "Missing 'path' argument."}
    if not old_text:
        return {"success": False, "output": "Missing 'old_text' argument."}
    abs_path = _resolve_path(work_dir, path)
    if _is_git_protected(abs_path):
        return {"success": False, "output": "Refusing to edit inside .git directory."}
    if not os.path.isfile(abs_path):
        return {"success": False, "output": f"File not found: {path}"}
    with open(abs_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    if old_text not in content:
        return {"success": False, "output": "old_text not found in file."}
    updated = content.replace(old_text, new_text, 1)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(updated)

    output = f"Edited {path}: replaced 1 occurrence."

    # Validate Python files immediately after editing
    if path.endswith(".py"):
        warnings = _validate_python_file(abs_path)
        if warnings:
            output += "\n\nWARNING — issues detected after edit:\n"
            output += "\n".join(f"  - {w}" for w in warnings)

    return {"success": True, "output": output}


# ───────────────────────────────────────────────────────────────────
# run_command
# ───────────────────────────────────────────────────────────────────

RUN_COMMAND_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Execute a shell command in the working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120).",
                    "default": 120,
                },
            },
            "required": ["command"],
        },
    },
}


def _handle_run_command(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    cmd = args.get("command", "")
    timeout = int(args.get("timeout", 120))
    if not cmd:
        return {"success": False, "output": "Missing 'command' argument."}
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if not output:
            output = "(no output)"
        success = result.returncode == 0
        if not success:
            output = f"Exit code: {result.returncode}\n{output}"
        return {"success": success, "output": output.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"Command timed out ({timeout}s): {cmd}"}
    except Exception as exc:
        return {"success": False, "output": f"Command error: {exc}"}


# ───────────────────────────────────────────────────────────────────
# glob_files
# ───────────────────────────────────────────────────────────────────

GLOB_FILES_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "glob_files",
        "description": "Find files matching a glob pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py').",
                },
                "path": {
                    "type": "string",
                    "description": "Base directory for the glob (default '.').",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
    },
}


def _handle_glob_files(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    pattern = args.get("pattern", "")
    base = args.get("path", ".")
    if not pattern:
        return {"success": False, "output": "Missing 'pattern' argument."}
    abs_base = _resolve_path(work_dir, base)
    full_pattern = os.path.join(abs_base, pattern)
    matches = sorted(_glob.glob(full_pattern, recursive=True))
    # Return paths relative to work_dir
    rel_matches = []
    for m in matches:
        try:
            rel_matches.append(os.path.relpath(m, work_dir))
        except ValueError:
            rel_matches.append(m)
    return {"success": True, "output": "\n".join(rel_matches) if rel_matches else "(no matches)"}


# ───────────────────────────────────────────────────────────────────
# grep_content
# ───────────────────────────────────────────────────────────────────

GREP_CONTENT_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "grep_content",
        "description": "Search file contents for a regex pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (default '.').",
                    "default": ".",
                },
                "flags": {
                    "type": "string",
                    "description": "Regex flags: 'i' for case-insensitive.",
                    "default": "",
                },
            },
            "required": ["pattern"],
        },
    },
}


def _handle_grep_content(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    pattern = args.get("pattern", "")
    base = args.get("path", ".")
    flags_str = args.get("flags", "")
    if not pattern:
        return {"success": False, "output": "Missing 'pattern' argument."}
    abs_base = _resolve_path(work_dir, base)

    re_flags = 0
    if "i" in flags_str:
        re_flags |= re.IGNORECASE

    try:
        regex = re.compile(pattern, re_flags)
    except re.error as exc:
        return {"success": False, "output": f"Invalid regex: {exc}"}

    results: list[str] = []
    max_results = 200

    def _search_file(fpath: str) -> None:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if len(results) >= max_results:
                        return
                    if regex.search(line):
                        rel = os.path.relpath(fpath, work_dir)
                        results.append(f"{rel}:{lineno}: {line.rstrip()}")
        except (OSError, UnicodeDecodeError):
            pass

    if os.path.isfile(abs_base):
        _search_file(abs_base)
    else:
        for root, dirs, files in os.walk(abs_base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in sorted(files):
                if len(results) >= max_results:
                    break
                _search_file(os.path.join(root, fname))

    output = "\n".join(results) if results else "(no matches)"
    return {"success": True, "output": output}


# ───────────────────────────────────────────────────────────────────
# list_files
# ───────────────────────────────────────────────────────────────────

LIST_FILES_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "Recursively list files in a directory, skipping hidden directories.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list (default '.').",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
}


def _handle_list_files(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")
    abs_path = _resolve_path(work_dir, path)
    if not os.path.isdir(abs_path):
        return {"success": False, "output": f"Directory not found: {path}"}

    lines: list[str] = []
    for root, dirs, files in os.walk(abs_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        level = root.replace(abs_path, "").count(os.sep)
        indent = "  " * level
        basename = os.path.basename(root) or path
        lines.append(f"{indent}{basename}/")
        sub_indent = "  " * (level + 1)
        for f in sorted(files):
            if not f.startswith("."):
                lines.append(f"{sub_indent}{f}")
    return {"success": True, "output": "\n".join(lines)}


# ───────────────────────────────────────────────────────────────────
# search_pypi
# ───────────────────────────────────────────────────────────────────

SEARCH_PYPI_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_pypi",
        "description": "Search PyPI for Python packages by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Package name or search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def _handle_search_pypi(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query", "")
    max_results = int(args.get("max_results", 5))
    if not query:
        return {"success": False, "output": "Missing 'query' argument."}

    results: list[dict[str, str]] = []
    # Try exact match via JSON API
    try:
        url = f"https://pypi.org/pypi/{query}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            info = data.get("info", {})
            results.append({
                "name": info.get("name", query),
                "version": info.get("version", ""),
                "summary": info.get("summary", ""),
            })
    except Exception:
        pass

    if len(results) < max_results:
        # Fallback: search via simple endpoint
        try:
            url = f"https://pypi.org/simple/"
            req = urllib.request.Request(url, headers={"Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")
                existing = {r["name"].lower() for r in results}
                for match in re.finditer(r'href="[^"]*">([^<]+)</a>', html):
                    pkg_name = match.group(1).strip()
                    if query.lower() in pkg_name.lower() and pkg_name.lower() not in existing:
                        results.append({"name": pkg_name, "version": "", "summary": ""})
                        existing.add(pkg_name.lower())
                        if len(results) >= max_results:
                            break
        except Exception:
            pass

    output = _json.dumps(results[:max_results], indent=2)
    return {"success": True, "output": output}


# ───────────────────────────────────────────────────────────────────
# python_exec
# ───────────────────────────────────────────────────────────────────

PYTHON_EXEC_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "python_exec",
        "description": "Execute a Python code snippet and return stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute.",
                },
            },
            "required": ["code"],
        },
    },
}


def _handle_python_exec(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    code = args.get("code", "")
    if not code:
        return {"success": False, "output": "Missing 'code' argument."}
    import sys

    python_bin = sys.executable or "python3"
    try:
        result = subprocess.run(
            [python_bin, "-c", code],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if not output:
            output = "(no output)"
        success = result.returncode == 0
        if not success:
            output = f"Exit code: {result.returncode}\n{output}"
        return {"success": success, "output": output.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Python execution timed out (60s)."}
    except Exception as exc:
        return {"success": False, "output": f"Python exec error: {exc}"}


# ───────────────────────────────────────────────────────────────────
# git_status
# ───────────────────────────────────────────────────────────────────

GIT_STATUS_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "git_status",
        "description": "Run 'git status' in the working directory.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def _handle_git_status(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        return {"success": result.returncode == 0, "output": output.strip()}
    except Exception as exc:
        return {"success": False, "output": f"git status error: {exc}"}


# ───────────────────────────────────────────────────────────────────
# git_commit
# ───────────────────────────────────────────────────────────────────

GIT_COMMIT_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "git_commit",
        "description": "Stage all changes and create a git commit.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message.",
                },
            },
            "required": ["message"],
        },
    },
}


def _handle_git_commit(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    message = args.get("message", "")
    if not message:
        return {"success": False, "output": "Missing 'message' argument."}
    try:
        # Stage all changes
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
        # Commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = commit_result.stdout + (
            "\n" + commit_result.stderr if commit_result.stderr else ""
        )
        return {
            "success": commit_result.returncode == 0,
            "output": output.strip(),
        }
    except Exception as exc:
        return {"success": False, "output": f"git commit error: {exc}"}


# ───────────────────────────────────────────────────────────────────
# scaffold_project
# ───────────────────────────────────────────────────────────────────

SCAFFOLD_PROJECT_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "scaffold_project",
        "description": (
            "Generate a complete Python package scaffold from templates. "
            "Creates __init__.py, __main__.py, api.py, cli.py, tools.py, "
            "tests/conftest.py, and an empty tests/__init__.py. "
            "Use this ONCE at the start of implementation to set up the "
            "deterministic boilerplate; then use write_file / edit_file "
            "to fill in project-specific logic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "package_name": {
                    "type": "string",
                    "description": (
                        "Python-importable package name (lowercase, "
                        "underscores OK, e.g. 'gomoku' or 'my_tool')."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": "One-line project description.",
                },
            },
            "required": ["package_name", "description"],
        },
    },
}


def _handle_scaffold_project(work_dir: str, args: dict[str, Any]) -> dict[str, Any]:
    pkg = args.get("package_name", "").strip()
    desc = args.get("description", "").strip()

    if not pkg:
        return {"success": False, "output": "Missing 'package_name' argument."}
    if not desc:
        return {"success": False, "output": "Missing 'description' argument."}

    # Validate package name
    if not re.match(r'^[a-z][a-z0-9_]*$', pkg):
        return {
            "success": False,
            "output": (
                f"Invalid package_name '{pkg}': must start with a lowercase "
                "letter and contain only lowercase letters, digits, and "
                "underscores."
            ),
        }

    # Locate templates directory (sibling of executor/)
    templates_dir = Path(__file__).resolve().parent.parent / "templates"

    template_files = {
        "__init__.py": "__init__.py.tpl",
        "__main__.py": "__main__.py.tpl",
        "api.py": "api.py.tpl",
        "cli.py": "cli.py.tpl",
        "tools.py": "tools.py.tpl",
    }

    pkg_dir = os.path.join(os.path.abspath(work_dir), pkg)
    tests_dir = os.path.join(os.path.abspath(work_dir), "tests")

    created: list[str] = []
    errors: list[str] = []

    # Create package directory
    os.makedirs(pkg_dir, exist_ok=True)

    # Render and write each template
    for target_name, tpl_name in template_files.items():
        tpl_path = templates_dir / tpl_name
        if not tpl_path.is_file():
            errors.append(f"Template not found: {tpl_name}")
            continue
        content = tpl_path.read_text(encoding="utf-8")
        content = content.replace("{{package_name}}", pkg)
        content = content.replace("{{description}}", desc)
        out_path = os.path.join(pkg_dir, target_name)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        created.append(f"{pkg}/{target_name}")

    # Create tests/ directory with conftest.py and __init__.py
    os.makedirs(tests_dir, exist_ok=True)

    conftest_tpl = templates_dir / "conftest.py.tpl"
    if conftest_tpl.is_file():
        content = conftest_tpl.read_text(encoding="utf-8")
        content = content.replace("{{package_name}}", pkg)
        conftest_path = os.path.join(tests_dir, "conftest.py")
        with open(conftest_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        created.append("tests/conftest.py")

    init_path = os.path.join(tests_dir, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as fh:
        fh.write("")
    created.append("tests/__init__.py")

    # Create docs/ directory
    docs_dir = os.path.join(os.path.abspath(work_dir), "docs")
    os.makedirs(docs_dir, exist_ok=True)

    if errors:
        return {
            "success": False,
            "output": (
                f"Scaffold partially created with errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
                + "\n\nFiles created:\n"
                + "\n".join(f"  - {f}" for f in created)
            ),
        }

    output = (
        f"Project scaffold created for '{pkg}'.\n\n"
        f"Files created:\n"
        + "\n".join(f"  - {f}" for f in created)
        + "\n\n"
        + "Directories created:\n"
        + f"  - {pkg}/\n"
        + "  - tests/\n"
        + "  - docs/\n\n"
        + "Next steps:\n"
        + f"  1. Create {pkg}/core.py with your core business logic\n"
        + f"  2. Edit {pkg}/api.py — add API wrapper functions that "
        + "return ToolResult\n"
        + f"  3. Edit {pkg}/cli.py — add project-specific arguments "
        + "and dispatch logic\n"
        + f"  4. Edit {pkg}/tools.py — add tool schemas and dispatch "
        + "cases\n"
        + f"  5. Edit {pkg}/__init__.py — update __all__ with your "
        + "public API symbols"
    )
    return {"success": True, "output": output}


# ===================================================================
# Registry
# ===================================================================

ALL_TOOLS: list[dict[str, Any]] = [
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    RUN_COMMAND_SCHEMA,
    GLOB_FILES_SCHEMA,
    GREP_CONTENT_SCHEMA,
    LIST_FILES_SCHEMA,
    SEARCH_PYPI_SCHEMA,
    PYTHON_EXEC_SCHEMA,
    GIT_STATUS_SCHEMA,
    GIT_COMMIT_SCHEMA,
    SCAFFOLD_PROJECT_SCHEMA,
]

TOOL_HANDLERS: dict[str, Callable[[str, dict[str, Any]], dict[str, Any]]] = {
    "read_file": _handle_read_file,
    "write_file": _handle_write_file,
    "edit_file": _handle_edit_file,
    "run_command": _handle_run_command,
    "glob_files": _handle_glob_files,
    "grep_content": _handle_grep_content,
    "list_files": _handle_list_files,
    "search_pypi": _handle_search_pypi,
    "python_exec": _handle_python_exec,
    "git_status": _handle_git_status,
    "git_commit": _handle_git_commit,
    "scaffold_project": _handle_scaffold_project,
}
