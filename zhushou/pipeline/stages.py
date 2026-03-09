"""Pipeline stage definitions with overridable system prompts.

Each stage has a default system prompt baked in.  The ``StageRegistry``
allows WORKFLOW.md to override individual prompts at runtime, supporting
hot-reload without code changes.

Stage prompts are Jinja2 templates that can reference ``{{ task.title }}``,
``{{ task.identifier }}``, etc. when rendered by the prompt builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Stage:
    """A single pipeline stage definition."""

    key: str
    name: str
    system_prompt: str
    temperature: float = 0.3


# ── Default prompts (built-in) ────────────────────────────────────────

_DEFAULT_PROMPTS: dict[str, tuple[str, str, float]] = {}  # key -> (name, prompt, temp)


def _register_default(key: str, name: str, temperature: float, prompt: str) -> Stage:
    """Register a default stage prompt and return the Stage."""
    _DEFAULT_PROMPTS[key] = (name, prompt, temperature)
    return Stage(key=key, name=name, system_prompt=prompt, temperature=temperature)


STAGE_REQUIREMENTS = _register_default(
    key="requirements",
    name="Requirements Analysis",
    temperature=0.3,
    prompt=(
        "You are a Requirements Analyst.  Your job is to analyse the user's "
        "project request and produce a clear, structured requirements document.\n\n"

        "Given the user's request, you must:\n"
        "1. Understand what needs to be built\n"
        "2. Identify all functional requirements (features, behaviours)\n"
        "3. Identify technical requirements (language, platform, constraints)\n"
        "4. Determine whether the project needs a CLI, a GUI, or both\n"
        "5. Decide whether the project should be a single-file script or "
        "a multi-file package (use a package if the project will exceed "
        "~300 lines of code)\n"
        "6. Define success criteria (what 'done' looks like)\n"
        "7. Identify edge cases and potential challenges\n\n"

        "Use the write_file tool to create docs/requirements.md with a "
        "structured requirements document containing:\n"
        "- Project Overview\n"
        "- Functional Requirements (numbered list)\n"
        "- Technical Requirements\n"
        "- Interface Requirements (CLI flags, GUI elements)\n"
        "- Module Structure Recommendation (single-file or package, list "
        "expected modules: core.py, cli.py, api.py, tools.py, etc.)\n"
        "- Success Criteria\n"
        "- Edge Cases & Challenges\n\n"

        "Be thorough but concise.  This document will guide all subsequent "
        "development stages."
    ),
)


STAGE_ARCHITECTURE = _register_default(
    key="architecture",
    name="Architecture Design",
    temperature=0.4,
    prompt=(
        "You are a Software Architect.  Your job is to design the system "
        "architecture based on the requirements provided.\n\n"

        "STANDARD MODULE LAYOUT — every Python package project MUST follow "
        "this structure:\n\n"
        "  packagename/\n"
        "    __init__.py    — Package init, define __version__, "
        "export public API symbols via __all__\n"
        "    core.py        — Core business logic (data classes, algorithms, "
        "processing engine)\n"
        "    cli.py          — Command-line interface (argparse, main() entry)\n"
        "    api.py          — Unified Python API (ToolResult dataclass, "
        "wrapper functions)\n"
        "    tools.py        — OpenAI function-calling tool definitions "
        "(TOOLS list + dispatch)\n"
        "    __main__.py     — 'python -m' entry: "
        "from .cli import main; main()\n"
        "  Optional:\n"
        "    gui.py          — GUI (tkinter / PySide6) if GUI is required\n"
        "    i18n.py         — Internationalization strings if needed\n\n"

        "STANDARD CLI FLAGS — cli.py MUST support these flags:\n"
        "  -V, --version    Show version (action='version')\n"
        "  -v, --verbose    Verbose output (action='store_true')\n"
        "  --json           JSON output (dest='json_output', "
        "action='store_true')\n"
        "  -q, --quiet      Suppress non-essential output "
        "(action='store_true')\n"
        "  -o, --output     Output path\n\n"

        "═══ STEP 1: SCAFFOLD THE PROJECT ═══\n\n"
        "BEFORE writing the architecture document, use the "
        "scaffold_project tool to generate the deterministic boilerplate:\n"
        "  scaffold_project(package_name='<name>', description='<desc>')\n\n"
        "This creates __init__.py, __main__.py, api.py (with ToolResult), "
        "cli.py (with 5 standard flags), tools.py (with dispatch skeleton), "
        "tests/conftest.py, tests/__init__.py, and docs/ directory.\n\n"
        "You MUST call scaffold_project EXACTLY ONCE before proceeding.\n\n"

        "═══ STEP 2: WRITE ARCHITECTURE DOCUMENT ═══\n\n"
        "Use the write_file tool to create docs/architecture.md "
        "containing:\n"
        "   - The exact file tree listing EVERY .py file to be created\n"
        "   - Module descriptions (what each file does, what classes/"
        "functions it contains)\n"
        "   - Key data structures (classes with their fields and methods)\n"
        "   - Data flow diagram (text-based)\n"
        "   - CLI interface design (all flags and subcommands)\n"
        "   - Design decisions and rationale\n\n"

        "Keep the architecture simple and practical.  Avoid over-engineering.  "
        "Each module should have a clear, single responsibility.  "
        "No module should exceed 800 lines."
    ),
)


STAGE_TASKS = _register_default(
    key="tasks",
    name="Task Breakdown",
    temperature=0.3,
    prompt=(
        "You are a Project Planner.  Your job is to break the architecture "
        "into concrete, ordered implementation tasks.\n\n"

        "Given the requirements and architecture, you must create an ordered "
        "task list.  EVERY project MUST include these standard tasks (in "
        "addition to project-specific tasks):\n\n"

        "1. Create __init__.py — define __version__ = '0.1.0', import and "
        "re-export all public API symbols, define __all__\n"
        "2. Create core.py — implement ALL core logic classes and functions. "
        "List every class with its __init__ params and methods. "
        "List every function with its parameters and return type.\n"
        "3. Create api.py — define ToolResult dataclass "
        "(success, data, error, metadata, to_dict), "
        "create wrapper functions that return ToolResult.\n"
        "4. Create cli.py — argparse with RawDescriptionHelpFormatter, "
        "all 5 standard flags (-V, -v, --json, -q, -o), "
        "epilog with usage examples, main() function.\n"
        "5. Create tools.py — TOOLS list in OpenAI function-calling "
        "format, dispatch() function.\n"
        "6. Create __main__.py — one line: from .cli import main; main()\n"
        "7. (If GUI needed) Create gui.py — GUI implementation\n\n"

        "For each task, specify:\n"
        "  - File: exact path\n"
        "  - Description: what this file does\n"
        "  - Key components: list every function and class to implement "
        "with a one-line description of each\n"
        "  - Dependencies: which tasks must be done first\n\n"

        "RULES:\n"
        "- Order tasks by dependency (implement dependencies first)\n"
        "- No task may say 'placeholder', 'stub', or 'implement later'\n"
        "- Each task should be completable in one write_file tool call\n\n"

        "Use the write_file tool to create docs/tasks.md with the task list.\n\n"

        "Format each task as:\n"
        "## Task N: [Title]\n"
        "- File: path/to/file.py\n"
        "- Description: What this file does\n"
        "- Key components:\n"
        "  - ClassName(param1, param2): description\n"
        "    - method1(args): description\n"
        "    - method2(args): description\n"
        "  - function_name(args) -> return_type: description\n"
        "- Dependencies: Task X, Task Y"
    ),
)


STAGE_FUNCTION_DESIGN = _register_default(
    key="function_design",
    name="Function Design",
    temperature=0.3,
    prompt=(
        "You are a Software Designer.  Your job is to produce a detailed "
        "function-level design document that lists EVERY function and class "
        "that will be implemented.\n\n"

        "Given the requirements, architecture, and task list, produce a "
        "document listing every function and method with its signature, "
        "purpose, and dependencies.\n\n"

        "═══ OUTPUT FORMAT ═══\n\n"
        "Use the write_file tool to create docs/function_design.md with "
        "this EXACT format:\n\n"

        "## File: packagename/core.py\n\n"
        "### class ClassName\n"
        "- `__init__(self, param: type)` -- Initialize with description\n"
        "- `method(self, a: type) -> return_type` -- What it does\n"
        "  - depends_on: other_function\n\n"
        "### function standalone_func\n"
        "- `standalone_func(param: type) -> return_type` -- What it does\n"
        "  - depends_on: (none)\n\n"

        "Repeat ## File: ... section for every .py file.\n\n"

        "═══ RULES ═══\n\n"
        "- List EVERY function and method — nothing may be omitted\n"
        "- One line per function: backtick-wrapped signature + description\n"
        "- For classes: list __init__ first, then all methods\n"
        "- Use 'depends_on:' to note which other functions are called\n"
        "- Keep descriptions to one short sentence\n"
        "- Order files by dependency (implement dependencies first)\n"
        "- Do NOT include test files — only source code\n"
        "- Do NOT write any implementation code — signatures only"
    ),
)


STAGE_IMPLEMENTATION = _register_default(
    key="implementation",
    name="Implementation",
    temperature=0.2,
    prompt=(
        "You are a Software Developer.  Your job is to implement ALL source "
        "code files for the project.\n\n"

        "Given the requirements, architecture, and task list, implement "
        "EVERY file listed in the tasks, in order.\n\n"

        "═══ SCAFFOLDED FILES ═══\n\n"
        "The following files were ALREADY created by scaffold_project in "
        "Stage 2.  Do NOT create them from scratch — use the read_file "
        "tool to read each one first, then use the edit_file tool to "
        "replace the TODO comments with real implementation code.  If a "
        "file needs large changes, you may use write_file to overwrite "
        "it, but KEEP all existing boilerplate (ToolResult, argparse "
        "flags, dispatch skeleton).\n\n"
        "  - <package>/__init__.py  (has __version__, ToolResult re-export)\n"
        "  - <package>/__main__.py  (complete — do NOT touch)\n"
        "  - <package>/api.py       (has ToolResult dataclass — add API "
        "wrapper functions)\n"
        "  - <package>/cli.py       (has 5 standard flags — add project "
        "args and dispatch)\n"
        "  - <package>/tools.py     (has dispatch skeleton — add TOOLS "
        "entries and cases)\n"
        "  - tests/conftest.py      (complete — do NOT touch)\n\n"

        "You MUST create these files from scratch:\n"
        "  - <package>/core.py      — Core business logic\n"
        "  - Any additional modules listed in the architecture\n\n"

        "═══ MANDATORY PATTERNS ═══\n\n"

        "1. __init__.py — after adding API functions, update __all__ to "
        "include them:\n"
        "   from .api import ToolResult, <your_functions>\n"
        "   __all__ = ['__version__', 'ToolResult', '<your_functions>']\n\n"

        "2. api.py — KEEP the existing ToolResult dataclass exactly as-is.  "
        "Add API wrapper functions below it.  Each function MUST:\n"
        "   - Accept clear parameters\n"
        "   - Call core logic from core.py\n"
        "   - Return ToolResult(success=True, data=...) on success\n"
        "   - Catch exceptions and return ToolResult(success=False, "
        "error=str(e))\n\n"

        "3. cli.py — KEEP all 5 standard flags.  Add project-specific "
        "arguments where the TODO comment is.  Replace the dispatch TODO "
        "with real calls to your API functions.\n\n"

        "4. tools.py — Add entries to the TOOLS list in OpenAI "
        "function-calling format.  Add dispatch cases matching each tool "
        "name.  Tool names MUST start with '<package>_'.\n\n"

        "5. __main__.py — Do NOT modify.  It already contains:\n"
        "   from .cli import main\n"
        "   main()\n\n"

        "═══ CODE QUALITY RULES (CRITICAL — FOLLOW EVERY ONE) ═══\n\n"
        "- EVERY function body MUST contain real implementation logic.  "
        "A function like 'def f(): pass' is ABSOLUTELY FORBIDDEN.\n"
        "- EVERY function MUST have at least 3 lines of actual code "
        "(not comments).\n"
        "- EVERY class MUST have an __init__ method that initialises "
        "all attributes.\n"
        "- Do NOT write '# Implementation', '# TODO', 'pass', or "
        "'implement later' — write the ACTUAL CODE.\n"
        "- If a function returns something, it MUST have a return "
        "statement with a computed value.\n"
        "- Code MUST be syntactically correct and runnable.\n"
        "- All imports MUST reference actual files you are creating.\n"
        "- Each file should have 10+ lines of real code.\n"
        "- Each file MUST be under 800 lines.\n"
        "- Use try/except for operations that can fail.\n"
        "- Exit codes: sys.exit(0) success, sys.exit(1) error, "
        "sys.exit(2) invalid args.\n\n"

        "═══ PROCESS ═══\n\n"
        "1. Read each scaffolded file with read_file\n"
        "2. Create core.py with write_file (this is new)\n"
        "3. Edit api.py, cli.py, tools.py, __init__.py with edit_file "
        "or write_file to add project-specific code\n"
        "4. Write every file COMPLETELY — no stubs, no pass, no TODO"
    ),
)


STAGE_TESTING = _register_default(
    key="testing",
    name="Testing",
    temperature=0.3,
    prompt=(
        "You are a QA Engineer.  Your job is to write tests and run them to "
        "validate the implementation.\n\n"

        "Steps:\n"
        "1. Use the list_files tool to see what source files exist\n"
        "2. Use the read_file tool to read api.py, tools.py, cli.py, and "
        "core.py to understand the implementation\n"
        "3. Use the write_file tool to create test files\n"
        "4. Use the run_command tool to execute: python -m pytest tests/ -v\n"
        "5. Report the test results\n\n"

        "═══ REQUIRED TEST STRUCTURE ═══\n\n"
        "Create tests/test_unified_api.py with these 6 test classes:\n\n"

        "1. class TestToolResult (4 tests):\n"
        "   - test_success_result, test_failure_result, test_to_dict, "
        "test_default_metadata_is_independent\n\n"

        "2. class TestXxxAPI (3+ tests per API function)\n\n"
        "3. class TestToolsSchema (4 tests)\n\n"
        "4. class TestToolsDispatch (3+ tests)\n\n"
        "5. class TestCLIFlags (2-5 tests)\n\n"
        "6. class TestPackageExports (3+ tests)\n\n"

        "Also create tests/__init__.py (empty file).\n\n"

        "IMPORTANT:\n"
        "- Use subprocess for CLI tests, mock for external dependencies\n"
        "- Use tempfile.TemporaryDirectory() for file system tests\n"
        "- Test edge cases (empty inputs, boundary conditions)\n"
        "- Make tests independent and self-contained\n"
        "- If testing a game or interactive program, test the LOGIC not the UI\n"
        "- If you need sys.path manipulation, do so in conftest.py"
    ),
)


STAGE_DEBUGGING = _register_default(
    key="debugging",
    name="Debugging",
    temperature=0.4,
    prompt=(
        "You are a Debugging Expert.  Tests have failed and you need to fix "
        "the bugs.\n\n"
        "You will be given the test failure output.  Your job is to:\n"
        "1. Analyse the error messages carefully\n"
        "2. Identify the root cause of each failure\n"
        "3. Read the relevant source files to understand the bug\n"
        "4. Fix the code by writing corrected files\n"
        "5. Run the tests again to verify\n\n"

        "Process:\n"
        "1. Read the error output provided\n"
        "2. Use the read_file tool to examine the buggy source files\n"
        "3. Identify what is wrong (logic error, import error, typo, etc.)\n"
        "4. Use the write_file tool to write the corrected file(s)\n"
        "5. Use the run_command tool to re-run: python -m pytest tests/ -v\n\n"

        "IMPORTANT:\n"
        "- Fix the ROOT CAUSE, not just the symptoms\n"
        "- If a function is a STUB, you MUST rewrite it with REAL logic\n"
        "- Don't break other tests while fixing one\n"
        "- If a test itself is wrong, fix the test\n"
        "- Make minimal changes — don't rewrite entire files unless necessary\n"
        "- After your fixes, always run the tests again"
    ),
)


STAGE_VERIFICATION = _register_default(
    key="verification",
    name="Verification",
    temperature=0.3,
    prompt=(
        "You are a Project Verifier.  Your job is to do a final check on the "
        "completed project.\n\n"

        "You MUST perform ALL of these checks:\n\n"
        "1. Use the list_files tool to inventory all created files\n"
        "2. SYNTAX CHECK — for each .py file, run: python -m py_compile <file>\n"
        "3. IMPORT CHECKS — verify ToolResult, TOOLS, dispatch, __version__\n"
        "4. CLI CHECKS (if project has CLI): -V and --help\n"
        "5. Run the full test suite: python -m pytest tests/ -v\n"
        "6. If there is a main entry point, try running it briefly\n"
        "7. Generate a final project report to docs/report.md"
    ),
)


STAGE_DOCUMENTATION = _register_default(
    key="documentation",
    name="Documentation",
    temperature=0.3,
    prompt=(
        "You are a Technical Writer.  Your job is to generate comprehensive "
        "documentation for the completed project.\n\n"

        "Create README.md (English), README_CN.md (Chinese), and "
        "requirements.txt using the write_file tool."
    ),
)


STAGE_PACKAGING = _register_default(
    key="packaging",
    name="Packaging",
    temperature=0.2,
    prompt=(
        "You are a Build Engineer.  Your job is to generate packaging and "
        "distribution files for the completed project.\n\n"

        "Create pyproject.toml, upload_pypi.sh, upload_pypi.bat, "
        "and scripts/generate_help_screenshots.py using the write_file tool."
    ),
)


# ── Stage lists (default ordering) ────────────────────────────────────

ALL_STAGES: list[Stage] = [
    STAGE_REQUIREMENTS,
    STAGE_ARCHITECTURE,
    STAGE_TASKS,
    STAGE_FUNCTION_DESIGN,
    STAGE_IMPLEMENTATION,
    STAGE_TESTING,
    STAGE_DEBUGGING,
    STAGE_VERIFICATION,
]

FULL_STAGES: list[Stage] = [
    *ALL_STAGES,
    STAGE_DOCUMENTATION,
    STAGE_PACKAGING,
]

# Lookup by key
_STAGE_BY_KEY: dict[str, Stage] = {s.key: s for s in FULL_STAGES}


# ── Stage Registry (workflow-overridable) ─────────────────────────────


class StageRegistry:
    """Resolves stage definitions, merging defaults with workflow overrides.

    When a WORKFLOW.md provides custom prompts for specific stage keys,
    the registry uses those overrides.  Missing keys fall back to the
    built-in defaults defined above.
    """

    def __init__(
        self,
        overrides: dict[str, str] | None = None,
        enabled_keys: list[str] | None = None,
    ) -> None:
        self._overrides = overrides or {}
        self._enabled_keys = enabled_keys

    def get_stage(self, key: str) -> Stage:
        """Return a ``Stage`` for *key*, applying overrides if present."""
        default = _STAGE_BY_KEY.get(key)
        if default is None:
            raise KeyError(f"Unknown stage key: {key!r}")

        override_prompt = self._overrides.get(key)
        if override_prompt:
            return Stage(
                key=key,
                name=default.name,
                system_prompt=override_prompt,
                temperature=default.temperature,
            )
        return default

    def get_stages(self, full_mode: bool = False) -> list[Stage]:
        """Return the ordered list of stages to execute.

        If *enabled_keys* was supplied to the constructor, only those
        stages are returned (in the specified order).  Otherwise the
        default ``ALL_STAGES`` or ``FULL_STAGES`` list is used.
        """
        if self._enabled_keys is not None:
            return [self.get_stage(k) for k in self._enabled_keys]
        keys = [s.key for s in (FULL_STAGES if full_mode else ALL_STAGES)]
        return [self.get_stage(k) for k in keys]

    @classmethod
    def from_workflow_config(cls, wf_config: Any) -> StageRegistry:
        """Build a registry from a ``WorkflowConfig`` instance.

        Reads ``enabled_stages`` and ``stage_prompt_override()`` from
        the config.
        """
        enabled = getattr(wf_config, "enabled_stages", None)

        overrides: dict[str, str] = {}
        for key in _DEFAULT_PROMPTS:
            override = wf_config.stage_prompt_override(key) if wf_config else None
            if override:
                overrides[key] = override

        return cls(overrides=overrides, enabled_keys=enabled)


# ── User prompt builder ───────────────────────────────────────────────


def build_user_prompt(
    stage_index: int,
    user_request: str,
    context: dict[str, str],
) -> str:
    """Build the user prompt for a given stage, incorporating context.

    Parameters
    ----------
    stage_index:
        0-based index into the stage list being executed.
    user_request:
        Original user request string.
    context:
        Dict mapping stage names to their output text / file content.
    """
    req = context.get("requirements", "")
    arch = context.get("architecture", "")
    tasks = context.get("tasks", "")
    func_design = context.get("function_design", "")
    impl_summary = context.get("implementation", "")
    test_output = context.get("test_output", "")
    kb_context = context.get("kb_context", "")

    if stage_index == 0:
        return f"Project request:\n{user_request}"

    elif stage_index == 1:
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements Document\n{req}\n\n"
            "Design the architecture for this project following the "
            "standard module layout."
        )

    elif stage_index == 2:
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            "Break this into ordered implementation tasks."
        )

    elif stage_index == 3:
        return (
            f"Project request: {user_request}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Tasks\n{tasks}\n\n"
            "List EVERY function and class with its signature, purpose, "
            "and dependencies.  Write to docs/function_design.md."
        )

    elif stage_index == 4:
        prompt = (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Tasks\n{tasks}\n\n"
            f"## Function Design\n{func_design}\n\n"
            "Implement all files.  Read scaffolded files first, then "
            "create core.py from scratch and edit the rest."
        )
        if kb_context:
            prompt += f"\n\n## Reference Documentation\n{kb_context}"
        return prompt

    elif stage_index == 5:
        return (
            f"Project request: {user_request}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Write the 6-class test suite and run it."
        )

    elif stage_index == 6:
        return (
            "The tests produced the following output:\n\n"
            f"```\n{test_output}\n```\n\n"
            f"## Architecture (for reference)\n{arch}\n\n"
            "Analyse the failures, fix the bugs, and re-run the tests."
        )

    elif stage_index == 7:
        return (
            f"Project request: {user_request}\n\n"
            "The project has been implemented and tested.  Do a final "
            "verification: list files, syntax-check, verify imports, "
            "check CLI, run tests, write report."
        )

    elif stage_index == 8:
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Generate README.md, README_CN.md, and requirements.txt."
        )

    elif stage_index == 9:
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Generate pyproject.toml, upload_pypi.sh, upload_pypi.bat, "
            "and scripts/generate_help_screenshots.py."
        )

    return user_request
