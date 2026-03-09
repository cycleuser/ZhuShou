"""Single-pipeline runner for one task in one workspace.

Refactored from the original ``orchestrator.py``.  This module no longer
owns polling, dispatch, or concurrency -- those responsibilities belong
to ``zhushou.orchestrator.loop``.

``PipelineRunner`` accepts a ``Task`` (or plain string request), a
workspace path, and optionally a ``WorkflowConfig``, then runs the
8/10-stage coding pipeline end-to-end, returning stats.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from zhushou.events.bus import PipelineEventBus
from zhushou.events.types import (
    CodeOutputEvent,
    DebugAttemptEvent,
    ErrorEvent,
    InfoEvent,
    PipelineCompleteEvent,
    PipelineEvent,
    StageCompleteEvent,
    StageStartEvent,
    TestResultEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from zhushou.executor.tool_executor import ToolExecutor
from zhushou.pipeline.function_design import FunctionRegistry, parse_function_design
from zhushou.pipeline.stages import (
    ALL_STAGES,
    FULL_STAGES,
    Stage,
    StageRegistry,
    build_user_prompt,
)

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Execute a single 8/10-stage coding pipeline for one task.

    This class is instantiated per-task by the orchestrator (or directly
    by ``zhushou pipeline`` for single-shot mode).

    Parameters
    ----------
    llm_client:
        Any LLM client implementing ``chat(messages, tools, temperature)``.
    work_dir:
        Absolute path to the isolated workspace directory.
    python_path:
        Path to the Python interpreter for subprocess operations.
    full_mode:
        If True, run 10 stages (adds Documentation + Packaging).
    kb_collections:
        Optional knowledge-base collection names for RAG injection.
    event_bus:
        Optional event bus for real-time UI updates.
    world_sense:
        Whether to inject date/time context into prompts.
    stage_registry:
        Optional ``StageRegistry`` for workflow-overridable prompts.
    task_context:
        Optional rendered task prompt (from prompt builder) to prepend
        to every stage's user prompt.
    """

    MAX_TOOL_TURNS: int = 15
    MAX_DEBUG_RETRIES: int = 5
    MAX_TOTAL_DEBUG_ITERATIONS: int = 10

    def __init__(
        self,
        llm_client: Any,
        work_dir: str,
        python_path: str = "",
        full_mode: bool = False,
        kb_collections: list[str] | None = None,
        event_bus: PipelineEventBus | None = None,
        world_sense: bool = True,
        stage_registry: StageRegistry | None = None,
        task_context: str = "",
    ) -> None:
        self.llm_client = llm_client
        self.work_dir = os.path.abspath(work_dir)
        self.python_path = python_path or "python3"
        self.full_mode = full_mode
        self.event_bus = event_bus
        self.world_sense = world_sense
        self.task_context = task_context
        self.executor = ToolExecutor(work_dir=self.work_dir)

        # Stage registry: uses defaults unless workflow overrides provided
        self.stage_registry = stage_registry or StageRegistry()

        # Knowledge base
        self.kb_collections = kb_collections
        self.kb_manager: Any = None
        if kb_collections is not None:
            self._init_kb()

        # Function design registry (populated by Stage 3.5)
        self.function_registry: FunctionRegistry | None = None

        # Context accumulated across stages (stage_name -> output text)
        self.context: dict[str, str] = {}

        # Latest pytest output captured from run_command tool results
        self.last_test_output: str = ""

        # Total debug iterations across all debug phases
        self._total_debug_iterations: int = 0

        self.stats: dict[str, Any] = {
            "stages_completed": 0,
            "files_created": 0,
            "tests_passed": "N/A",
            "debug_iterations": 0,
            "total_time": "",
            "file_list": [],
            "output_dir": self.work_dir,
        }

    # ── Public API ────────────────────────────────────────────────

    def _emit(self, event: PipelineEvent) -> None:
        if self.event_bus is not None:
            self.event_bus.emit(event)

    def run(self, user_request: str) -> dict[str, Any]:
        """Execute the full autonomous pipeline and return stats."""
        start_time = time.time()
        os.makedirs(self.work_dir, exist_ok=True)

        # Resolve stages from registry
        stages_to_run = self.stage_registry.get_stages(full_mode=self.full_mode)
        total_stages = len(stages_to_run)

        # Prepend task context to user request if provided
        effective_request = user_request
        if self.task_context:
            effective_request = f"{self.task_context}\n\n{user_request}"

        for i, stage in enumerate(stages_to_run):
            stage_num = i + 1

            # Stage 3.5: Function Design (index 3)
            if stage.key == "function_design":
                self._run_function_design(
                    effective_request, stage, stage_num, total_stages,
                )
                self.stats["stages_completed"] += 1
                continue

            # Stage 4: Implementation — per-function splitting
            if stage.key == "implementation":
                response = self._run_implementation_by_function(
                    effective_request, stage, stage_num, total_stages,
                )
                self._store_context(i, response)
                self.stats["stages_completed"] += 1
                continue

            # Stage 6: Debugging — retry loop
            if stage.key == "debugging":
                self._run_debug_loop(
                    effective_request, stage, stage_num, total_stages,
                )
                self.stats["stages_completed"] += 1
                continue

            # Stage 7: Verification — may trigger re-debug
            if stage.key == "verification":
                self._run_verify_debug_loop(
                    effective_request, stage, stage_num, total_stages,
                )
                self.stats["stages_completed"] += 1
                continue

            # Normal stage execution
            self._show_stage_header(stage_num, total_stages, stage.name)
            self._emit(StageStartEvent(
                stage_num=stage_num, total_stages=total_stages,
                stage_name=stage.name,
            ))
            stage_start = time.time()
            user_prompt = build_user_prompt(i, effective_request, self.context)

            response = self._run_stage_with_tools(
                system_prompt=stage.system_prompt,
                user_prompt=user_prompt,
                temperature=stage.temperature,
                stage_num=stage_num,
            )

            self._store_context(i, response)
            self.stats["stages_completed"] += 1
            self._emit(StageCompleteEvent(
                stage_num=stage_num, stage_name=stage.name,
                duration_seconds=time.time() - stage_start,
            ))

        # Auto-commit if tests all passed
        if self.stats.get("tests_passed") == "All passed":
            self._try_auto_commit()

        # Final stats
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.stats["total_time"] = f"{minutes}m {seconds}s"
        self.stats["files_created"] = len(self.executor.files_created)
        self.stats["file_list"] = list(self.executor.files_created)

        self._show_summary()
        self._emit(PipelineCompleteEvent(stats=dict(self.stats)))
        return self.stats

    # ── Stage execution with tool loop ────────────────────────────

    def _run_stage_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        stage_num: int = 0,
    ) -> str:
        """Run a single stage in an LLM <-> tool conversation loop."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Inject world context into system prompt
        from zhushou.utils.world_context import get_world_context

        world_ctx = get_world_context(self.world_sense)
        if world_ctx:
            messages[0]["content"] = system_prompt + "\n\n" + world_ctx

        tool_defs = self.executor.get_tool_definitions()
        all_response_text: list[str] = []

        for _turn in range(self.MAX_TOOL_TURNS):
            response = self.llm_client.chat(
                messages=messages,
                tools=tool_defs,
                temperature=temperature,
            )

            content = getattr(response, "content", "") or ""
            all_response_text.append(content)

            if content.strip():
                self._emit(ThinkingEvent(stage_num=stage_num, content=content))

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                break

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": getattr(tc, "id", f"call_{j}"),
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": (
                                tc.arguments
                                if isinstance(tc.arguments, str)
                                else json.dumps(tc.arguments)
                            ),
                        },
                    }
                    for j, tc in enumerate(tool_calls)
                ],
            }
            messages.append(assistant_msg)

            for j, tc in enumerate(tool_calls):
                try:
                    args = (
                        json.loads(tc.arguments)
                        if isinstance(tc.arguments, str)
                        else tc.arguments
                    )
                except (json.JSONDecodeError, TypeError):
                    args = {}

                self._show_tool_call(tc.name, args)
                self._emit(ToolCallEvent(
                    stage_num=stage_num, tool_name=tc.name, arguments=args,
                ))
                result = self.executor.execute(tc.name, args)
                self._show_tool_result(result)

                if isinstance(result, dict):
                    _success = result.get("success", False)
                    _output = result.get("output", str(result))
                else:
                    _success = getattr(result, "success", False)
                    _output = getattr(result, "output", str(result))
                self._emit(ToolResultEvent(
                    stage_num=stage_num, tool_name=tc.name,
                    success=_success, output=_output,
                ))

                if tc.name in ("write_file", "edit_file"):
                    file_path = args.get("file_path", args.get("path", ""))
                    action = "create" if tc.name == "write_file" else "edit"
                    if file_path:
                        self._emit(CodeOutputEvent(
                            stage_num=stage_num, file_path=file_path,
                            action=action,
                        ))

                if tc.name == "run_command" and isinstance(result, dict):
                    cmd = args.get("command", "")
                    if "pytest" in cmd or "py_compile" in cmd:
                        self.last_test_output = result.get("output", "")

                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": getattr(tc, "id", f"call_{j}"),
                    "name": tc.name,
                    "content": (
                        result["output"]
                        if isinstance(result, dict)
                        else str(result)
                    ),
                }
                messages.append(tool_msg)

        return "\n".join(all_response_text)

    # ── Debug loop ────────────────────────────────────────────────

    def _run_debug_loop(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> None:
        self._show_stage_header(stage_num, total_stages, "Debugging")
        self._emit(StageStartEvent(
            stage_num=stage_num, total_stages=total_stages,
            stage_name="Debugging",
        ))
        debug_start = time.time()

        test_output = self.context.get("test_output", "")
        if self._tests_passed(test_output):
            logger.info("All tests passed — skipping debug loop.")
            self._emit(InfoEvent(message="All tests passed. Skipping debug loop."))
            self.stats["tests_passed"] = "All passed"
            self._emit(StageCompleteEvent(
                stage_num=stage_num, stage_name="Debugging",
                duration_seconds=time.time() - debug_start,
            ))
            return

        for attempt in range(1, self.MAX_DEBUG_RETRIES + 1):
            if self._total_debug_iterations >= self.MAX_TOTAL_DEBUG_ITERATIONS:
                self._show_error(
                    f"Total debug budget exhausted "
                    f"({self.MAX_TOTAL_DEBUG_ITERATIONS} iterations). Stopping."
                )
                break

            self._total_debug_iterations += 1
            self.stats["debug_iterations"] = self._total_debug_iterations
            self.last_test_output = ""
            self._show_info(
                f"Debug attempt {attempt}/{self.MAX_DEBUG_RETRIES} "
                f"(total: {self._total_debug_iterations}/"
                f"{self.MAX_TOTAL_DEBUG_ITERATIONS})..."
            )

            # Use the stage's key to find correct index for build_user_prompt
            user_prompt = build_user_prompt(6, user_request, self.context)
            response = self._run_stage_with_tools(
                system_prompt=stage.system_prompt,
                user_prompt=user_prompt,
                temperature=stage.temperature,
                stage_num=stage_num,
            )

            if self.last_test_output:
                self.context["test_output"] = self.last_test_output
            else:
                latest_test_output = self._find_latest_test_output(response)
                if latest_test_output:
                    self.context["test_output"] = latest_test_output

            passed = self._tests_passed(self.context.get("test_output", ""))
            self._emit(DebugAttemptEvent(
                attempt=attempt, max_retries=self.MAX_DEBUG_RETRIES,
                passed=passed,
            ))
            if passed:
                self.stats["tests_passed"] = "All passed"
                self._show_info(f"Debug attempt {attempt}: Tests PASSED")
                self._emit(StageCompleteEvent(
                    stage_num=stage_num, stage_name="Debugging",
                    duration_seconds=time.time() - debug_start,
                ))
                return

            self._show_info(f"Debug attempt {attempt}: Tests still failing")

        logger.warning(
            "Tests still failing after %d debug attempts (%d total)",
            self.MAX_DEBUG_RETRIES, self._total_debug_iterations,
        )
        self._emit(ErrorEvent(
            message=f"Tests still failing after {self.MAX_DEBUG_RETRIES} attempts.",
        ))
        self.stats["tests_passed"] = "Some failures remain"
        self._emit(StageCompleteEvent(
            stage_num=stage_num, stage_name="Debugging",
            duration_seconds=time.time() - debug_start,
        ))

    # ── Verification <-> Debug feedback loop ──────────────────────

    def _run_verification(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> str:
        self._show_stage_header(stage_num, total_stages, stage.name)
        self._emit(StageStartEvent(
            stage_num=stage_num, total_stages=total_stages,
            stage_name=stage.name,
        ))
        self.last_test_output = ""

        user_prompt = build_user_prompt(7, user_request, self.context)
        response = self._run_stage_with_tools(
            system_prompt=stage.system_prompt,
            user_prompt=user_prompt,
            temperature=stage.temperature,
            stage_num=stage_num,
        )

        if self.last_test_output:
            self.context["test_output"] = self.last_test_output
        else:
            latest = self._find_latest_test_output(response)
            if latest:
                self.context["test_output"] = latest

        test_out = self.context.get("test_output", "")
        self._emit(TestResultEvent(
            stage_num=stage_num,
            passed=self._tests_passed(test_out),
            output=test_out[:1000] if test_out else "",
        ))

        return response

    def _run_verify_debug_loop(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> None:
        response = self._run_verification(
            user_request, stage, stage_num, total_stages,
        )
        self._store_context(7, response)

        if self._tests_passed(self.context.get("test_output", "")):
            self.stats["tests_passed"] = "All passed"
            self._show_info("Verification: all tests PASSED")
            return

        # Resolve debugging stage from registry
        debug_stage = self.stage_registry.get_stage("debugging")

        while (
            not self._tests_passed(self.context.get("test_output", ""))
            and self._total_debug_iterations < self.MAX_TOTAL_DEBUG_ITERATIONS
        ):
            self._show_info(
                "Verification found failures — re-entering debug loop "
                f"(total: {self._total_debug_iterations}/"
                f"{self.MAX_TOTAL_DEBUG_ITERATIONS})"
            )

            self._run_debug_loop(
                user_request, debug_stage, stage_num - 1, total_stages,
            )

            if self._tests_passed(self.context.get("test_output", "")):
                self.stats["tests_passed"] = "All passed"
                return

            response = self._run_verification(
                user_request, stage, stage_num, total_stages,
            )
            self._store_context(7, response)

        if self._tests_passed(self.context.get("test_output", "")):
            self.stats["tests_passed"] = "All passed"
        else:
            self._show_error(
                f"Tests still failing after {self._total_debug_iterations} "
                "total debug iterations."
            )
            self.stats["tests_passed"] = "Some failures remain"

    # ── Per-file / per-function implementation ─────────────────────

    @staticmethod
    def _parse_task_files(tasks_markdown: str) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        patterns = [
            re.compile(r'-\s*File:\s*(.+\.py)', re.IGNORECASE),
            re.compile(r'#{2,4}\s*(?:Task\s*\d+[:\s]+)?(\S+\.py)'),
            re.compile(r'^\d+\.\s+(\S+\.py)', re.MULTILINE),
            re.compile(r'^-\s+(\S+\.py)\s', re.MULTILINE),
        ]
        for pat in patterns:
            for match in pat.finditer(tasks_markdown):
                path = match.group(1).strip()
                if path not in seen:
                    seen.add(path)
                    paths.append(path)
        return paths

    @staticmethod
    def _build_file_prompt(
        file_path: str,
        user_request: str,
        architecture: str,
        task_details: str,
    ) -> str:
        is_scaffolded = any(
            file_path.endswith(f)
            for f in ("__init__.py", "api.py", "cli.py", "tools.py",
                       "__main__.py")
        )
        if is_scaffolded:
            action = (
                f"This file was already scaffolded.  Use read_file to read "
                f"'{file_path}' first, then use edit_file to replace the "
                f"TODO comments with real implementation code."
            )
        else:
            action = (
                f"This is a NEW file.  Use write_file to create "
                f"'{file_path}' with the complete implementation."
            )
        return (
            f"Project request: {user_request}\n\n"
            f"IMPLEMENT ONLY THIS FILE: {file_path}\n\n"
            f"{action}\n\n"
            f"## Architecture (for reference)\n{architecture}\n\n"
            f"## Task details for this file\n{task_details}\n\n"
            f"RULES:\n"
            f"- Write ONLY '{file_path}' — do NOT touch other files.\n"
            f"- Every function body MUST have real implementation.\n"
            f"- No stubs, no pass, no TODO — write REAL code.\n"
        )

    @staticmethod
    def _extract_task_for_file(file_path: str, tasks_markdown: str) -> str:
        basename = os.path.basename(file_path)
        lines = tasks_markdown.split("\n")
        result_lines: list[str] = []
        capturing = False
        for line in lines:
            if basename in line and (
                line.strip().startswith("#")
                or line.strip().startswith("-")
                or re.match(r'^\d+\.', line.strip())
            ):
                capturing = True
                result_lines.append(line)
                continue
            if capturing:
                if (
                    line.strip().startswith("##")
                    or (re.match(r'^\d+\.', line.strip()) and basename not in line)
                ):
                    break
                result_lines.append(line)
        return "\n".join(result_lines) if result_lines else f"Implement {file_path}"

    def _run_implementation_by_file(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> str:
        self._show_stage_header(stage_num, total_stages, stage.name)
        tasks = self.context.get("tasks", "")
        arch = self.context.get("architecture", "")
        files = self._parse_task_files(tasks)

        if not files:
            self._show_info("No per-file tasks found, running monolithic implementation.")
            user_prompt = build_user_prompt(3, user_request, self.context)
            return self._run_stage_with_tools(
                system_prompt=stage.system_prompt,
                user_prompt=user_prompt,
                temperature=stage.temperature,
                stage_num=stage_num,
            )

        all_responses: list[str] = []
        for i, file_path in enumerate(files):
            self._show_info(f"  Implementing file {i + 1}/{len(files)}: {file_path}")
            task_details = self._extract_task_for_file(file_path, tasks)
            sub_prompt = self._build_file_prompt(
                file_path, user_request, arch, task_details,
            )
            response = self._run_stage_with_tools(
                system_prompt=stage.system_prompt,
                user_prompt=sub_prompt,
                temperature=stage.temperature,
                stage_num=stage_num,
            )
            all_responses.append(response)
        return "\n".join(all_responses)

    # ── Function design ───────────────────────────────────────────

    def _init_kb(self) -> None:
        try:
            from zhushou.knowledge.kb_manager import KBManager
            self.kb_manager = KBManager()
        except Exception:
            logger.warning("Failed to initialise KBManager")
            self.kb_manager = None

    def _run_function_design(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> None:
        self._show_stage_header(stage_num, total_stages, stage.name)
        self._emit(StageStartEvent(
            stage_num=stage_num, total_stages=total_stages,
            stage_name=stage.name,
        ))
        stage_start = time.time()
        user_prompt = build_user_prompt(3, user_request, self.context)

        response = self._run_stage_with_tools(
            system_prompt=stage.system_prompt,
            user_prompt=user_prompt,
            temperature=stage.temperature,
            stage_num=stage_num,
        )
        self._store_context(3, response)

        design_md = self.context.get("function_design", "")
        if design_md:
            specs = parse_function_design(design_md)
            if specs:
                self.function_registry = FunctionRegistry()
                self.function_registry.register(specs)
                self._show_info(
                    f"Function design parsed: {len(specs)} functions across "
                    f"{len(self.function_registry.file_paths())} files"
                )
            else:
                self._show_info("Could not parse function design — "
                                "will use file-level implementation.")
        self._emit(StageCompleteEvent(
            stage_num=stage_num, stage_name=stage.name,
            duration_seconds=time.time() - stage_start,
        ))

    def _run_implementation_by_function(
        self,
        user_request: str,
        stage: Stage,
        stage_num: int,
        total_stages: int,
    ) -> str:
        # Inject KB context if available
        if self.kb_manager and self.kb_collections:
            try:
                kb_ctx = self.kb_manager.build_context(
                    user_request,
                    collections=self.kb_collections,
                    max_chars=6000,
                )
                if kb_ctx:
                    self.context["kb_context"] = kb_ctx
            except Exception:
                logger.warning("KB context injection failed")

        if self.function_registry is None:
            return self._run_implementation_by_file(
                user_request, stage, stage_num, total_stages,
            )

        self._show_stage_header(stage_num, total_stages, stage.name)
        self._emit(StageStartEvent(
            stage_num=stage_num, total_stages=total_stages,
            stage_name=stage.name,
        ))
        impl_start = time.time()
        file_paths = self.function_registry.file_paths()

        if not file_paths:
            return self._run_implementation_by_file(
                user_request, stage, stage_num, total_stages,
            )

        arch = self.context.get("architecture", "")
        kb_context = self.context.get("kb_context", "")
        all_responses: list[str] = []

        for file_idx, file_path in enumerate(file_paths):
            funcs = self.function_registry.get_unimplemented_for_file(file_path)
            if not funcs:
                continue

            self._show_info(
                f"  File {file_idx + 1}/{len(file_paths)}: {file_path} "
                f"({len(funcs)} functions)"
            )

            for func_idx, func_spec in enumerate(funcs):
                self._show_info(f"    [{func_idx + 1}/{len(funcs)}] {func_spec.signature}")

                implemented_sigs = self.function_registry.get_implemented_signatures(file_path)
                dep_sigs = self.function_registry.get_dependency_signatures(func_spec.name)
                current_content = self._try_read_file(file_path) or ""

                is_first = func_idx == 0 and not current_content
                is_scaffolded = any(
                    file_path.endswith(f)
                    for f in ("__init__.py", "api.py", "cli.py", "tools.py",
                              "__main__.py")
                )

                if is_first and not is_scaffolded:
                    action = f"Create '{file_path}' with this function."
                elif is_scaffolded and func_idx == 0:
                    action = (
                        f"Read '{file_path}' first, then add this function "
                        f"while keeping ALL existing boilerplate."
                    )
                else:
                    action = (
                        f"Read '{file_path}', then write the complete "
                        f"updated file with this function added."
                    )

                sub_prompt = (
                    f"Project request: {user_request}\n\n"
                    f"IMPLEMENT: {func_spec.signature}\n\n"
                    f"File: {file_path}\n"
                    f"Purpose: {func_spec.docstring}\n"
                    f"{action}\n\n"
                )

                if dep_sigs:
                    sub_prompt += f"## Dependencies\n{dep_sigs}\n\n"
                if implemented_sigs:
                    sub_prompt += f"## Already in this file\n{implemented_sigs}\n\n"
                if arch:
                    sub_prompt += f"## Architecture\n{arch[:2000]}\n\n"
                if kb_context:
                    sub_prompt += f"## Reference Documentation\n{kb_context[:3000]}\n\n"

                sub_prompt += (
                    "RULES:\n"
                    "- Write REAL implementation — no stubs, no pass, no TODO.\n"
                    "- Include ALL previously written code in the file.\n"
                )

                response = self._run_stage_with_tools(
                    system_prompt=stage.system_prompt,
                    user_prompt=sub_prompt,
                    temperature=stage.temperature,
                    stage_num=stage_num,
                )
                all_responses.append(response)
                self.function_registry.mark_implemented(func_spec.name)

            self._show_info(
                f"  {file_path} complete — {self.function_registry.summary()}"
            )

        self._emit(StageCompleteEvent(
            stage_num=stage_num, stage_name=stage.name,
            duration_seconds=time.time() - impl_start,
        ))
        return "\n".join(all_responses)

    # ── Context management ────────────────────────────────────────

    def _store_context(self, stage_index: int, response: str) -> None:
        if stage_index == 0:
            content = self._try_read_file("docs/requirements.md")
            self.context["requirements"] = content or response
        elif stage_index == 1:
            content = self._try_read_file("docs/architecture.md")
            self.context["architecture"] = content or response
        elif stage_index == 2:
            content = self._try_read_file("docs/tasks.md")
            self.context["tasks"] = content or response
        elif stage_index == 3:
            content = self._try_read_file("docs/function_design.md")
            self.context["function_design"] = content or response
        elif stage_index == 4:
            files = self.executor.files_created
            self.context["implementation"] = (
                "Files created:\n" + "\n".join(f"- {f}" for f in files)
            )
        elif stage_index == 5:
            self.context["test_output"] = (
                self.last_test_output
                or self._find_latest_test_output(response)
                or response
            )
            test_out = self.context["test_output"]
            self._emit(TestResultEvent(
                stage_num=stage_index + 1,
                passed=self._tests_passed(test_out),
                output=test_out[:1000] if test_out else "",
            ))
        elif stage_index == 7:
            if self.last_test_output:
                self.context["test_output"] = self.last_test_output
            else:
                latest = self._find_latest_test_output(response)
                if latest:
                    self.context["test_output"] = latest
        elif stage_index == 8:
            content = self._try_read_file("README.md")
            self.context["documentation"] = content or response
        elif stage_index == 9:
            content = self._try_read_file("pyproject.toml")
            self.context["packaging"] = content or response

    # ── Helpers ────────────────────────────────────────────────────

    def _try_read_file(self, rel_path: str) -> str | None:
        abs_path = os.path.join(self.work_dir, rel_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8") as fh:
                return fh.read()
        return None

    def _find_latest_test_output(self, response: str) -> str | None:
        lines = response.split("\n")
        output_lines: list[str] = []
        capture = False
        for line in lines:
            if (
                "pytest" in line.lower()
                or "PASSED" in line
                or "FAILED" in line
                or "ERROR" in line
            ):
                capture = True
            if capture:
                output_lines.append(line)
            if capture and "==" in line and (
                "passed" in line.lower()
                or "error" in line.lower()
                or "failed" in line.lower()
            ):
                break
        return "\n".join(output_lines) if output_lines else None

    @staticmethod
    def _tests_passed(test_output: str) -> bool:
        if not test_output:
            return False
        lower = test_output.lower()
        if "passed" in lower and "failed" not in lower and "error" not in lower:
            return True
        if "0 failed" in lower:
            return True
        return False

    def _try_auto_commit(self) -> None:
        try:
            from zhushou.git.manager import GitManager
            gm = GitManager(self.work_dir)
            gm.auto_commit()
        except Exception:
            logger.debug("Auto-commit skipped")

    # ── Display helpers ───────────────────────────────────────────

    @staticmethod
    def _show_stage_header(num: int, total: int, name: str) -> None:
        try:
            from zhushou.display.console import show_stage_header
            show_stage_header(num, total, name)
        except Exception:
            logger.info("Stage %d/%d: %s", num, total, name)

    @staticmethod
    def _show_tool_call(name: str, args: dict[str, Any]) -> None:
        try:
            from zhushou.display.console import show_tool_call
            show_tool_call(name, args)
        except Exception:
            logger.debug("Tool call: %s(%s)", name, args)

    @staticmethod
    def _show_tool_result(result: Any) -> None:
        try:
            from zhushou.display.console import show_tool_result
            if isinstance(result, dict):
                success = result.get("success", False)
                output = result.get("output", str(result))
            else:
                success = getattr(result, "success", False)
                output = getattr(result, "output", str(result))
            show_tool_result(success, output)
        except Exception:
            logger.debug("Tool result: %s", result)

    @staticmethod
    def _show_info(msg: str) -> None:
        try:
            from zhushou.display.console import show_info
            show_info(msg)
        except Exception:
            logger.info(msg)

    @staticmethod
    def _show_error(msg: str) -> None:
        try:
            from zhushou.display.console import show_error
            show_error(msg)
        except Exception:
            logger.error(msg)

    def _show_summary(self) -> None:
        try:
            from zhushou.display.console import show_summary
            show_summary(self.stats)
        except Exception:
            logger.info("Pipeline stats: %s", self.stats)


# ── Backward compatibility alias ──────────────────────────────────────
# Existing code that imports PipelineOrchestrator will still work.
PipelineOrchestrator = PipelineRunner
