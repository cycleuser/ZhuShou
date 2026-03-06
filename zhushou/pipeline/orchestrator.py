"""Autonomous multi-stage pipeline orchestrator.

Evolved from the original ``old/pipeline.py``.  Instead of parsing XML
tool-call tags the orchestrator now uses native LLM function-calling:
each stage runs in a tool-use conversation loop handled by the LLM's
``chat()`` method with ``tools=`` definitions.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from zhushou.executor.tool_executor import ToolExecutor
from zhushou.pipeline.stages import ALL_STAGES, Stage, build_user_prompt

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Run the 7-stage autonomous coding pipeline."""

    MAX_TOOL_TURNS: int = 15
    MAX_DEBUG_RETRIES: int = 5

    def __init__(
        self,
        llm_client: Any,
        work_dir: str,
        python_path: str = "",
    ) -> None:
        self.llm_client = llm_client
        self.work_dir = os.path.abspath(work_dir)
        self.python_path = python_path or "python3"
        self.executor = ToolExecutor(work_dir=self.work_dir)

        # Context accumulated across stages  (stage_name → output text)
        self.context: dict[str, str] = {}

        self.stats: dict[str, Any] = {
            "stages_completed": 0,
            "files_created": 0,
            "tests_passed": "N/A",
            "debug_iterations": 0,
            "total_time": "",
            "file_list": [],
            "output_dir": self.work_dir,
        }

    # ── Public API ─────────────────────────────────────────────────────

    def run(self, user_request: str) -> dict[str, Any]:
        """Execute the full autonomous pipeline and return stats."""
        start_time = time.time()
        os.makedirs(self.work_dir, exist_ok=True)
        total_stages = len(ALL_STAGES)

        for i, stage in enumerate(ALL_STAGES):
            stage_num = i + 1

            # Stage 6 (debugging, index 5) uses a retry loop
            if i == 5:
                self._run_debug_loop(user_request, stage_num, total_stages)
                self.stats["stages_completed"] += 1
                continue

            self._show_stage_header(stage_num, total_stages, stage.name)
            user_prompt = build_user_prompt(i, user_request, self.context)

            response = self._run_stage_with_tools(
                system_prompt=stage.system_prompt,
                user_prompt=user_prompt,
                temperature=stage.temperature,
            )

            # Store context for downstream stages
            self._store_context(i, response)
            self.stats["stages_completed"] += 1

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
        return self.stats

    # ── Stage execution with tool loop ─────────────────────────────────

    def _run_stage_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Run a single stage, handling the LLM ↔ tool conversation loop.

        Returns the concatenated response text from all turns.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

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

            # Check for tool calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # No more tools to execute — stage is done
                break

            # Build assistant message with tool_calls
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

            # Execute each tool call and feed results back
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
                result = self.executor.execute(tc.name, args)
                self._show_tool_result(result)

                tool_msg: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": getattr(tc, "id", f"call_{j}"),
                    "name": tc.name,
                    "content": (
                        result.output if hasattr(result, "output") else str(result)
                    ),
                }
                messages.append(tool_msg)

        return "\n".join(all_response_text)

    # ── Debug loop ─────────────────────────────────────────────────────

    def _run_debug_loop(
        self,
        user_request: str,
        stage_num: int,
        total_stages: int,
    ) -> None:
        """Run the debugging stage as a retry loop."""
        self._show_stage_header(stage_num, total_stages, "Debugging")

        # If tests already passed in stage 5, skip debugging
        test_output = self.context.get("test_output", "")
        if self._tests_passed(test_output):
            logger.info("All tests passed in testing stage — skipping debug loop.")
            self._show_info("All tests passed in previous stage. Skipping debug loop.")
            self.stats["tests_passed"] = "All passed"
            return

        debug_stage: Stage = ALL_STAGES[5]

        for attempt in range(1, self.MAX_DEBUG_RETRIES + 1):
            self.stats["debug_iterations"] = attempt
            self._show_info(
                f"Debug attempt {attempt}/{self.MAX_DEBUG_RETRIES}..."
            )

            user_prompt = build_user_prompt(5, user_request, self.context)
            response = self._run_stage_with_tools(
                system_prompt=debug_stage.system_prompt,
                user_prompt=user_prompt,
                temperature=debug_stage.temperature,
            )

            # Check if the LLM re-ran tests and they passed
            latest_test_output = self._find_latest_test_output(response)
            if latest_test_output:
                self.context["test_output"] = latest_test_output

            passed = self._tests_passed(self.context.get("test_output", ""))
            if passed:
                self.stats["tests_passed"] = "All passed"
                self._show_info(
                    f"Debug attempt {attempt}/{self.MAX_DEBUG_RETRIES}: "
                    "Tests PASSED ✓"
                )
                return

            self._show_info(
                f"Debug attempt {attempt}/{self.MAX_DEBUG_RETRIES}: "
                "Tests still failing"
            )

        # Exhausted retries
        logger.warning(
            "Tests still failing after %d debug attempts", self.MAX_DEBUG_RETRIES
        )
        self._show_error(
            f"Tests still failing after {self.MAX_DEBUG_RETRIES} debug attempts. "
            "Proceeding to verification."
        )
        self.stats["tests_passed"] = "Some failures remain"

    # ── Context management ─────────────────────────────────────────────

    def _store_context(self, stage_index: int, response: str) -> None:
        """Store stage output in *self.context* for downstream stages."""
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
            # Implementation: store summary of created files
            files = self.executor.files_created
            self.context["implementation"] = (
                "Files created:\n" + "\n".join(f"- {f}" for f in files)
            )
        elif stage_index == 4:
            # Testing: extract test output
            test_output = self._find_latest_test_output(response)
            self.context["test_output"] = test_output or response

    # ── Helpers ────────────────────────────────────────────────────────

    def _try_read_file(self, rel_path: str) -> str | None:
        """Try to read a file from *work_dir*.  Returns ``None`` if missing."""
        abs_path = os.path.join(self.work_dir, rel_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8") as fh:
                return fh.read()
        return None

    def _find_latest_test_output(self, response: str) -> str | None:
        """Extract the last pytest-style output block from *response*."""
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
            # pytest summary line like "=== 5 passed ==="
            if capture and "==" in line and (
                "passed" in line.lower()
                or "error" in line.lower()
                or "failed" in line.lower()
            ):
                break

        return "\n".join(output_lines) if output_lines else None

    @staticmethod
    def _tests_passed(test_output: str) -> bool:
        """Return True when test output indicates all tests passed."""
        if not test_output:
            return False
        lower = test_output.lower()
        if "passed" in lower and "failed" not in lower and "error" not in lower:
            return True
        if "0 failed" in lower:
            return True
        return False

    @staticmethod
    def _format_tool_results(results: list[Any]) -> str:
        """Format tool execution results as a feedback message for the LLM."""
        parts: list[str] = []
        for r in results:
            status = "SUCCESS" if getattr(r, "success", False) else "ERROR"
            output = getattr(r, "output", str(r))
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"
            tool_name = getattr(r, "tool_name", "unknown")
            parts.append(f"[Tool Result: {tool_name} – {status}]\n{output}")
        return "\n\n".join(parts)

    def _try_auto_commit(self) -> None:
        """Attempt an automatic git commit after all tests pass."""
        try:
            from zhushou.git.manager import GitManager

            gm = GitManager(self.work_dir)
            gm.auto_commit()
            logger.info("Auto-committed project files")
        except Exception:
            logger.debug("Auto-commit skipped (git module unavailable or not a repo)")

    # ── Display helpers (thin wrappers for optional Rich output) ───────

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
