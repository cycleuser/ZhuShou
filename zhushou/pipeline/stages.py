"""Pipeline stage definitions with system prompts for each phase.

Evolved from the original XML-based stage prompts.  Tool instructions are
no longer embedded in each prompt because the agent loop handles
function-calling natively via the LLM's tool-use API.
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
        "4. Define success criteria (what 'done' looks like)\n"
        "5. Identify edge cases and potential challenges\n\n"
        "Use the write_file tool to create docs/requirements.md with a structured "
        "requirements document containing:\n"
        "- Project Overview\n"
        "- Functional Requirements (numbered list)\n"
        "- Technical Requirements\n"
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
        "You must:\n"
        "1. Design the project directory structure\n"
        "2. Define all modules/files and their responsibilities\n"
        "3. Design key data structures and interfaces\n"
        "4. Define the data flow and component interactions\n"
        "5. Choose appropriate patterns and approaches\n\n"
        "Actions to take:\n"
        "- Use the run_command tool with mkdir -p to create the project "
        "directory structure\n"
        "- Use the write_file tool to create docs/architecture.md containing:\n"
        "  - Directory/file structure tree\n"
        "  - Module descriptions (what each file does)\n"
        "  - Key data structures (classes, types)\n"
        "  - Data flow diagram (text-based)\n"
        "  - Design decisions and rationale\n\n"
        "Keep the architecture simple and practical.  Avoid over-engineering.  "
        "Each module should have a clear, single responsibility."
    ),
)


# ── Stage 3: Task Breakdown ───────────────────────────────────────────

STAGE_TASKS = Stage(
    name="Task Breakdown",
    temperature=0.3,
    system_prompt=(
        "You are a Project Planner.  Your job is to break the architecture "
        "into concrete, ordered implementation tasks.\n\n"
        "Given the requirements and architecture, you must:\n"
        "1. Create an ordered list of implementation tasks\n"
        "2. Each task corresponds to implementing one file or one logical unit\n"
        "3. Order tasks by dependency (implement dependencies first)\n"
        "4. For each task, specify:\n"
        "   - Which file to create\n"
        "   - What it should contain (functions, classes)\n"
        "   - Dependencies on other tasks\n\n"
        "Use the write_file tool to create docs/tasks.md with the structured "
        "task list.\n\n"
        "Format each task as:\n"
        "## Task N: [Title]\n"
        "- File: path/to/file.py\n"
        "- Description: What this file does\n"
        "- Key components: List of functions/classes to implement\n"
        "- Dependencies: Which tasks must be done first\n\n"
        "Keep tasks granular but not too small.  Each task should be completable "
        "in one write_file tool call."
    ),
)


# ── Stage 4: Implementation ───────────────────────────────────────────

STAGE_IMPLEMENTATION = Stage(
    name="Implementation",
    temperature=0.2,
    system_prompt=(
        "You are a Software Developer.  Your job is to implement ALL source "
        "code files for the project.\n\n"
        "Given the requirements, architecture, and task list, you must:\n"
        "1. Implement EVERY file listed in the tasks, in order\n"
        "2. Write complete, working, production-quality code\n"
        "3. Include proper imports, error handling, and comments for complex logic\n"
        "4. Make sure all modules work together correctly\n"
        "5. Follow the architecture exactly\n\n"
        "CRITICAL RULES:\n"
        "- Use the write_file tool for EVERY source code file.  Do not skip any.\n"
        "- Each file must be COMPLETE – no placeholders, no 'TODO', no "
        "'implement later'\n"
        "- Code must be syntactically correct and runnable\n"
        "- Ensure all imports reference actual files you have created\n"
        "- Test-related files should NOT be created here (that is the next stage)\n"
        "- If the project has a main entry point, make sure it works when "
        "executed via the discovered python_path or `python` command\n\n"
        "Use the write_file tool for each file, with brief reasoning before "
        "each explaining what you are implementing."
    ),
)


# ── Stage 5: Testing ──────────────────────────────────────────────────

STAGE_TESTING = Stage(
    name="Testing",
    temperature=0.3,
    system_prompt=(
        "You are a QA Engineer.  Your job is to write tests and run them to "
        "validate the implementation.\n\n"
        "You must:\n"
        "1. Write comprehensive test files using pytest\n"
        "2. Test core logic and edge cases\n"
        "3. Run the test suite and report results\n\n"
        "Steps:\n"
        "1. Use the list_files tool to see what source files exist\n"
        "2. Use the read_file tool to read key source files and understand "
        "the implementation\n"
        "3. Use the write_file tool to create test files in a tests/ directory:\n"
        "   - tests/__init__.py (empty)\n"
        "   - tests/test_*.py for each module worth testing\n"
        "4. Use the run_command tool to execute: python -m pytest tests/ -v\n"
        "5. Report the test results\n\n"
        "IMPORTANT:\n"
        "- Focus tests on core logic, not trivial getters/setters\n"
        "- Test edge cases (empty inputs, boundary conditions, win/loss states, etc.)\n"
        "- Make tests independent and self-contained\n"
        "- If testing a game or interactive program, test the LOGIC not the UI\n"
        "- Do NOT mock things unnecessarily – test real behaviour when possible\n"
        "- If you need sys.path manipulation for imports, do so in conftest.py"
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
        "- Don't break other tests while fixing one\n"
        "- If a test itself is wrong (testing incorrect behaviour), fix the test\n"
        "- Make minimal changes – don't rewrite entire files unless necessary\n"
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
        "You must:\n"
        "1. List all project files\n"
        "2. Run the full test suite one more time\n"
        "3. Try to run the main program (if applicable)\n"
        "4. Generate a final project report\n\n"
        "Steps:\n"
        "1. Use the list_files tool to inventory all created files\n"
        "2. Use the run_command tool to run: python -m pytest tests/ -v\n"
        "3. If there is a main entry point, try running it briefly (with "
        "timeout or echo test input)\n"
        "4. Use the write_file tool to create docs/report.md containing:\n"
        "   - Project summary\n"
        "   - Complete file list with descriptions\n"
        "   - Test results\n"
        "   - How to run the project (exact commands)\n"
        "   - Known limitations or issues\n\n"
        "This is the final stage.  Make the report useful for someone who "
        "wants to use this project."
    ),
)


# ── All stages in order ───────────────────────────────────────────────

ALL_STAGES: list[Stage] = [
    STAGE_REQUIREMENTS,
    STAGE_ARCHITECTURE,
    STAGE_TASKS,
    STAGE_IMPLEMENTATION,
    STAGE_TESTING,
    STAGE_DEBUGGING,  # handled specially by orchestrator (debug loop)
    STAGE_VERIFICATION,
]


def build_user_prompt(stage_index: int, user_request: str, context: dict[str, str]) -> str:
    """Build the user prompt for a given stage, incorporating context from prior stages.

    Parameters
    ----------
    stage_index:
        0-based index into :data:`ALL_STAGES`.
    user_request:
        Original user request string.
    context:
        Dict mapping stage names to their output text / file content.
    """
    req = context.get("requirements", "")
    arch = context.get("architecture", "")
    tasks = context.get("tasks", "")
    impl_summary = context.get("implementation", "")
    test_output = context.get("test_output", "")

    if stage_index == 0:
        # Requirements: just the user request
        return f"Project request:\n{user_request}"

    elif stage_index == 1:
        # Architecture: user request + requirements
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements Document\n{req}\n\n"
            "Design the architecture for this project."
        )

    elif stage_index == 2:
        # Task breakdown: requirements + architecture
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            "Break this into ordered implementation tasks."
        )

    elif stage_index == 3:
        # Implementation: requirements + architecture + tasks
        return (
            f"Project request: {user_request}\n\n"
            f"## Requirements\n{req}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Tasks\n{tasks}\n\n"
            "Implement ALL source code files now. Write every file completely."
        )

    elif stage_index == 4:
        # Testing: all prior context + summary of implemented files
        return (
            f"Project request: {user_request}\n\n"
            f"## Architecture\n{arch}\n\n"
            f"## Implementation Summary\n{impl_summary}\n\n"
            "Write comprehensive tests and run them."
        )

    elif stage_index == 5:
        # Debugging: include test failure output
        return (
            "The tests produced the following output:\n\n"
            f"```\n{test_output}\n```\n\n"
            f"## Architecture (for reference)\n{arch}\n\n"
            "Analyse the failures, fix the bugs, and re-run the tests."
        )

    elif stage_index == 6:
        # Verification: summary
        return (
            f"Project request: {user_request}\n\n"
            "The project has been implemented and tested. Do a final verification:\n"
            "1. List all files\n"
            "2. Run tests\n"
            "3. Try running the program\n"
            "4. Write a final report."
        )

    return user_request
