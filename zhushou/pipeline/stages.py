"""Pipeline stage definitions with system prompts for each phase.

Evolved from the original XML-based stage prompts.  Tool instructions are
no longer embedded in each prompt because the agent loop handles
function-calling natively via the LLM's tool-use API.

Development standards from the unified project specification are embedded
directly into each stage prompt so that even small models produce
well-structured, complete output.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Stage:
    """A single pipeline stage definition."""

    name: str
    system_prompt: str
    temperature: float = 0.3


# ── Stage 1: Requirements Analysis ────────────────────────────────────

STAGE_REQUIREMENTS = Stage(
    name="Requirements Analysis",
    temperature=0.3,
    system_prompt=(
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


# ── Stage 2: Architecture Design ──────────────────────────────────────

STAGE_ARCHITECTURE = Stage(
    name="Architecture Design",
    temperature=0.4,
    system_prompt=(
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


# ── Stage 3: Task Breakdown ───────────────────────────────────────────

STAGE_TASKS = Stage(
    name="Task Breakdown",
    temperature=0.3,
    system_prompt=(
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


# ── Stage 3.5: Function-Level Design ─────────────────────────────────

STAGE_FUNCTION_DESIGN = Stage(
    name="Function Design",
    temperature=0.3,
    system_prompt=(
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


# ── Stage 4: Implementation ───────────────────────────────────────────

STAGE_IMPLEMENTATION = Stage(
    name="Implementation",
    temperature=0.2,
    system_prompt=(
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


# ── Stage 5: Testing ──────────────────────────────────────────────────

STAGE_TESTING = Stage(
    name="Testing",
    temperature=0.3,
    system_prompt=(
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
        "   - test_success_result: ToolResult(success=True, data=...) "
        "works correctly\n"
        "   - test_failure_result: ToolResult(success=False, error=...) "
        "has error set\n"
        "   - test_to_dict: to_dict() returns dict with 4 keys "
        "(success, data, error, metadata)\n"
        "   - test_default_metadata_is_independent: two instances don't "
        "share metadata dict\n\n"

        "2. class TestXxxAPI (3+ tests per API function):\n"
        "   - test with invalid input -> success is False\n"
        "   - test with valid input -> success is True\n"
        "   - test return type is ToolResult\n\n"

        "3. class TestToolsSchema (4 tests):\n"
        "   - test_tools_is_list: TOOLS is a non-empty list\n"
        "   - test_tool_names: each name starts with 'packagename_'\n"
        "   - test_tool_structure: each has type='function' + "
        "function.name/description/parameters\n"
        "   - test_required_fields_exist_in_properties: required list "
        "matches properties keys\n\n"

        "4. class TestToolsDispatch (3+ tests):\n"
        "   - test_dispatch_unknown_tool: raises ValueError\n"
        "   - test_dispatch_json_string_args: JSON string args work\n"
        "   - test_dispatch_dict_args: dict args work\n\n"

        "5. class TestCLIFlags (2-5 tests):\n"
        "   - test_version_flag: subprocess run -V returns version\n"
        "   - test_help_has_standard_flags: --help output contains "
        "--json, --quiet, --verbose\n\n"

        "6. class TestPackageExports (3+ tests):\n"
        "   - test_version_exported: package has __version__\n"
        "   - test_toolresult_exported: from package import ToolResult\n"
        "   - test_api_functions_exported: all API functions importable\n\n"

        "Also create tests/__init__.py (empty file).\n\n"

        "IMPORTANT:\n"
        "- Use subprocess for CLI tests, mock for external dependencies\n"
        "- Use tempfile.TemporaryDirectory() for file system tests\n"
        "- Test edge cases (empty inputs, boundary conditions)\n"
        "- Make tests independent and self-contained\n"
        "- If testing a game or interactive program, test the LOGIC not "
        "the UI\n"
        "- If you need sys.path manipulation, do so in conftest.py"
    ),
)


# ── Stage 6: Debugging ────────────────────────────────────────────────

STAGE_DEBUGGING = Stage(
    name="Debugging",
    temperature=0.4,
    system_prompt=(
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
        "- If a function is a STUB (contains only 'pass', '# Implementation'"
        ", or '# TODO'), you MUST rewrite it with REAL implementation logic\n"
        "- Don't break other tests while fixing one\n"
        "- If a test itself is wrong (testing incorrect behaviour), fix "
        "the test\n"
        "- Make minimal changes — don't rewrite entire files unless necessary\n"
        "- After your fixes, always run the tests again"
    ),
)


# ── Stage 7: Verification ────────────────────────────────────────────

STAGE_VERIFICATION = Stage(
    name="Verification",
    temperature=0.3,
    system_prompt=(
        "You are a Project Verifier.  Your job is to do a final check on the "
        "completed project.\n\n"

        "You MUST perform ALL of these checks:\n\n"

        "1. Use the list_files tool to inventory all created files\n\n"

        "2. SYNTAX CHECK — for each .py file, run:\n"
        "   python -m py_compile <file>\n"
        "   Fix any syntax errors before proceeding.\n\n"

        "3. IMPORT CHECKS — run these commands:\n"
        "   python -c 'from <package>.api import ToolResult'\n"
        "   python -c 'from <package>.tools import TOOLS, dispatch'\n"
        "   python -c 'from <package> import __version__'\n"
        "   If any fail, fix the imports.\n\n"

        "4. CLI CHECKS (if project has CLI):\n"
        "   python -m <package> -V  (should print version)\n"
        "   python -m <package> --help  (should show -V, -v, --json, -q, "
        "-o flags)\n\n"

        "5. Run the full test suite:\n"
        "   python -m pytest tests/ -v\n\n"

        "6. If there is a main entry point, try running it briefly\n\n"

        "7. Generate a final project report — use the write_file tool to "
        "create docs/report.md containing:\n"
        "   - Project summary\n"
        "   - Complete file list with line counts and descriptions\n"
        "   - Test results (pass/fail counts)\n"
        "   - How to install: pip install -e .\n"
        "   - How to run: python -m <package> (with example commands)\n"
        "   - Known limitations or issues\n\n"

        "This is the final stage.  Make the report useful for someone who "
        "wants to use this project."
    ),
)


# ── Stage 8: Documentation (--full mode only) ────────────────────────

STAGE_DOCUMENTATION = Stage(
    name="Documentation",
    temperature=0.3,
    system_prompt=(
        "You are a Technical Writer.  Your job is to generate comprehensive "
        "documentation for the completed project.\n\n"

        "You MUST create these files using the write_file tool:\n\n"

        "═══ 1. README.md (English) ═══\n\n"
        "Use this exact section structure:\n"
        "  # ProjectName — one-sentence description\n"
        "  ## Features\n"
        "  ## Requirements\n"
        "  ## Installation\n"
        "    - From PyPI: pip install projectname\n"
        "    - From source: git clone ... && pip install -e .\n"
        "  ## Quick Start\n"
        "    - 3-5 example commands showing the most common use cases\n"
        "  ## Usage\n"
        "    - Global options table (Flag | Short | Description)\n"
        "    - Subcommands (if any)\n"
        "  ## Python API\n"
        "    - Code example showing: from package import func; "
        "result = func(...); print(result.success, result.data)\n"
        "  ## Agent Integration (OpenAI Function Calling)\n"
        "    - Code example showing: from package.tools import TOOLS, "
        "dispatch; result = dispatch(name, args)\n"
        "  ## CLI Help\n"
        "    - Embed: ![CLI Help](images/projectname_help.png)\n"
        "  ## Development\n"
        "    - pip install -e '.[dev]' && pytest\n"
        "  ## License\n\n"

        "═══ 2. README_CN.md (Chinese) ═══\n\n"
        "Translate README.md into Chinese.  Keep the same section structure.  "
        "Code examples stay identical.  Only translate headings and "
        "descriptive text.\n\n"

        "═══ 3. requirements.txt ═══\n\n"
        "List all third-party dependencies, one per line.  Do NOT include "
        "standard library modules.  Include version constraints if known "
        "(e.g., httpx>=0.24)."
    ),
)


# ── Stage 9: Packaging (--full mode only) ─────────────────────────────

STAGE_PACKAGING = Stage(
    name="Packaging",
    temperature=0.2,
    system_prompt=(
        "You are a Build Engineer.  Your job is to generate packaging and "
        "distribution files for the completed project.\n\n"

        "You MUST create these files using the write_file tool:\n\n"

        "═══ 1. pyproject.toml ═══\n\n"
        "[build-system]\n"
        "requires = ['setuptools>=68.0', 'wheel']\n"
        "build-backend = 'setuptools.backends._legacy:_Backend'\n\n"
        "[project]\n"
        "name = 'projectname'\n"
        "dynamic = ['version']\n"
        "description = 'One-line description'\n"
        "readme = 'README.md'\n"
        "license = {text = 'MIT'}\n"
        "requires-python = '>=3.9'\n"
        "authors = [{name = 'Author'}]\n"
        "keywords = [...]\n"
        "classifiers = [...]\n"
        "dependencies = [list from requirements.txt]\n\n"
        "[project.scripts]\n"
        "toolname = 'packagename.cli:main'\n\n"
        "[project.optional-dependencies]\n"
        "dev = ['pytest', 'build', 'twine']\n"
        "gui = ['PySide6']  # if GUI exists\n\n"
        "[tool.setuptools.dynamic]\n"
        "version = {attr = 'packagename.__version__'}\n\n"
        "[tool.setuptools.packages.find]\n"
        "include = ['packagename*']\n\n"
        "[tool.pytest.ini_options]\n"
        "testpaths = ['tests']\n\n"

        "═══ 2. upload_pypi.sh ═══\n\n"
        "A bash script that:\n"
        "  - Removes old dist/ and build/ directories\n"
        "  - Runs: python3 -m build\n"
        "  - Runs: twine check dist/*\n"
        "  - Accepts an argument: 'test' for TestPyPI, no arg for "
        "production PyPI\n"
        "  - test mode: twine upload --repository testpypi dist/*\n"
        "  - prod mode: twine upload dist/*\n"
        "  - Must be executable (include #!/bin/bash)\n\n"

        "═══ 3. upload_pypi.bat ═══\n\n"
        "Windows batch equivalent of upload_pypi.sh with the same logic.\n\n"

        "═══ 4. scripts/generate_help_screenshots.py ═══\n\n"
        "A Python script that:\n"
        "  - Runs 'python -m packagename --help' and captures the output\n"
        "  - Creates images/ directory\n"
        "  - Saves output as images/toolname_help.txt\n"
        "  - Optionally renders to images/toolname_help.png using Pillow "
        "(PIL) with dark background (30,30,30) and light text (204,204,204) "
        "using a monospace font\n"
        "  - Handles Pillow not being installed gracefully (just skip PNG)\n"
        "  - Uses COLUMNS=80 environment variable for consistent width"
    ),
)


# ── Stage lists ───────────────────────────────────────────────────────

ALL_STAGES: list[Stage] = [
    STAGE_REQUIREMENTS,       # 0
    STAGE_ARCHITECTURE,       # 1
    STAGE_TASKS,              # 2
    STAGE_FUNCTION_DESIGN,    # 3 (new)
    STAGE_IMPLEMENTATION,     # 4 (was 3)
    STAGE_TESTING,            # 5 (was 4)
    STAGE_DEBUGGING,          # 6 (was 5) — handled specially (debug loop)
    STAGE_VERIFICATION,       # 7 (was 6)
]

FULL_STAGES: list[Stage] = [
    *ALL_STAGES,
    STAGE_DOCUMENTATION,      # 8 (was 7)
    STAGE_PACKAGING,          # 9 (was 8)
]


def build_user_prompt(stage_index: int, user_request: str, context: dict[str, str]) -> str:
    """Build the user prompt for a given stage, incorporating context from prior stages.

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
        # Requirements: just the user request
        return f"Project request:\n{user_request}"

    elif stage_index == 1:
        # Architecture: user request + requirements
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements Document\n{req}\n\n"
            "Design the architecture for this project following the "
            "standard module layout."
        )

    elif stage_index == 2:
        # Task breakdown: requirements + architecture
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            "Break this into ordered implementation tasks.  Include "
            "tasks for every standard module (__init__.py, core.py, "
            "api.py, cli.py, tools.py, __main__.py)."
        )

    elif stage_index == 3:
        # Function design: tasks + architecture
        return (
            f"Project request: {user_request}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Tasks\n{tasks}\n\n"
            "Read the architecture and tasks above.  List EVERY function "
            "and class with its signature, purpose, and dependencies.  "
            "Write the result to docs/function_design.md."
        )

    elif stage_index == 4:
        # Implementation: requirements + architecture + tasks + function design
        prompt = (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Tasks\n{tasks}\n\n"
            f"## Function Design\n{func_design}\n\n"
            "The package scaffold has already been created by "
            "scaffold_project in the previous stage.  The following "
            "files already exist with boilerplate code:\n"
            "  - __init__.py (with __version__ and ToolResult re-export)\n"
            "  - __main__.py (complete — do NOT touch)\n"
            "  - api.py (with ToolResult dataclass — add API functions)\n"
            "  - cli.py (with 5 standard flags — add project args)\n"
            "  - tools.py (with dispatch skeleton — add TOOLS entries)\n"
            "  - tests/conftest.py (complete)\n\n"
            "Read each scaffolded file with read_file first, then:\n"
            "1. Create core.py from scratch\n"
            "2. Edit api.py, cli.py, tools.py, __init__.py to add "
            "project-specific code\n"
            "3. No stubs, no pass, no TODO — write REAL code."
        )
        if kb_context:
            prompt += f"\n\n## Reference Documentation\n{kb_context}"
        return prompt

    elif stage_index == 5:
        # Testing: all prior context + summary of implemented files
        return (
            f"Project request: {user_request}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Write the 6-class test suite and run it."
        )

    elif stage_index == 6:
        # Debugging: include test failure output
        return (
            "The tests produced the following output:\n\n"
            f"```\n{test_output}\n```\n\n"
            f"## Architecture (for reference)\n{arch}\n\n"
            "Analyse the failures, fix the bugs, and re-run the tests.  "
            "If any function is a stub (pass / # Implementation), rewrite "
            "it with real logic."
        )

    elif stage_index == 7:
        # Verification: summary
        return (
            f"Project request: {user_request}\n\n"
            "The project has been implemented and tested.  Do a final "
            "verification:\n"
            "1. List all files\n"
            "2. Syntax-check each .py file with py_compile\n"
            "3. Verify imports: ToolResult, TOOLS, dispatch, __version__\n"
            "4. Verify CLI: -V and --help\n"
            "5. Run tests\n"
            "6. Try running the program\n"
            "7. Write a final report to docs/report.md"
        )

    elif stage_index == 8:
        # Documentation (--full mode)
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Generate README.md (English), README_CN.md (Chinese), and "
            "requirements.txt for this project."
        )

    elif stage_index == 9:
        # Packaging (--full mode)
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Generate pyproject.toml, upload_pypi.sh, upload_pypi.bat, "
            "and scripts/generate_help_screenshots.py for this project."
        )

    return user_request
