"""Autonomous multi-stage pipeline orchestrator."""

import os
import time

from ollama_client import OllamaClient
from tools import ToolExecutor
from xml_parser import parse_tool_calls, extract_reasoning
from stages import ALL_STAGES, build_user_prompt
from display import (
    console,
    show_stage_header,
    show_streaming_token,
    show_streaming_end,
    show_tool_call,
    show_tool_result,
    show_debug_attempt,
    show_summary,
    show_info,
    show_error,
)


class Pipeline:
    """Run the 7-stage autonomous coding pipeline."""

    MAX_TOOL_TURNS = 15  # max LLM<->tool round-trips per stage
    MAX_DEBUG_RETRIES = 5

    def __init__(self, client: OllamaClient, work_dir: str):
        self.client = client
        self.work_dir = os.path.abspath(work_dir)
        self.executor = ToolExecutor(self.work_dir)
        # Context accumulated across stages (stage_name -> output text)
        self.context: dict[str, str] = {}
        self.stats: dict = {
            "stages_completed": 0,
            "files_created": 0,
            "tests_passed": "N/A",
            "debug_iterations": 0,
            "total_time": "",
            "file_list": [],
            "output_dir": self.work_dir,
        }

    def run(self, user_request: str):
        """Execute the full autonomous pipeline."""
        start_time = time.time()
        os.makedirs(self.work_dir, exist_ok=True)
        total_stages = len(ALL_STAGES)

        for i, stage in enumerate(ALL_STAGES):
            stage_num = i + 1

            # Stage 6 (debugging, index 5) is handled specially
            if i == 5:
                self._run_debug_loop(user_request, stage_num, total_stages)
                self.stats["stages_completed"] += 1
                continue

            show_stage_header(stage_num, total_stages, stage.name)
            user_prompt = build_user_prompt(i, user_request, self.context)

            response = self._run_stage_with_tools(
                stage.system_prompt, user_prompt, stage.temperature
            )

            # Store context for next stages
            self._store_context(i, response)
            self.stats["stages_completed"] += 1

        # Final stats
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.stats["total_time"] = f"{minutes}m {seconds}s"
        self.stats["files_created"] = len(self.executor.files_created)
        self.stats["file_list"] = list(self.executor.files_created)
        show_summary(self.stats)

    def _run_stage_with_tools(
        self, system_prompt: str, user_prompt: str, temperature: float
    ) -> str:
        """Run a single stage, handling the tool-use conversation loop.

        The LLM may output tool_call tags. We execute them and feed results
        back as a user message, letting the LLM continue. This loops until
        the LLM produces no more tool calls or we hit MAX_TOOL_TURNS.

        Returns the concatenated response text from all turns.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        all_response_text = []

        for turn in range(self.MAX_TOOL_TURNS):
            # Call LLM with streaming
            response = self.client.chat(
                messages=messages,
                temperature=temperature,
                on_token=show_streaming_token,
            )
            show_streaming_end()
            all_response_text.append(response)

            # Parse tool calls
            tool_calls = parse_tool_calls(response)
            if not tool_calls:
                # No more tools to execute, stage is done
                break

            # Execute each tool call
            results = []
            for tc in tool_calls:
                show_tool_call(tc.name, tc.args)
                result = self.executor.execute(tc)
                show_tool_result(result.success, result.output)
                results.append(result)

            # Build tool results message to feed back to LLM
            result_text = self._format_tool_results(results)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": result_text})

        return "\n".join(all_response_text)

    def _run_debug_loop(self, user_request: str, stage_num: int, total_stages: int):
        """Run the debugging stage as a retry loop."""
        show_stage_header(stage_num, total_stages, "Debugging")

        # Check if tests passed in stage 5
        test_output = self.context.get("test_output", "")
        if self._tests_passed(test_output):
            show_debug_attempt(0, self.MAX_DEBUG_RETRIES, True)
            show_info("All tests passed in previous stage. Skipping debug loop.")
            self.stats["tests_passed"] = "All passed"
            return

        debug_stage = ALL_STAGES[5]  # debugging stage

        for attempt in range(1, self.MAX_DEBUG_RETRIES + 1):
            self.stats["debug_iterations"] = attempt
            show_info(f"Debug attempt {attempt}/{self.MAX_DEBUG_RETRIES}...")

            # Build debug prompt with test failure output
            user_prompt = build_user_prompt(5, user_request, self.context)
            response = self._run_stage_with_tools(
                debug_stage.system_prompt, user_prompt, debug_stage.temperature
            )

            # After debug stage, check if tests were re-run and passed
            # The LLM should have run tests via run_command
            # Check the latest test output from tool results
            latest_test_output = self._find_latest_test_output(response)
            if latest_test_output:
                self.context["test_output"] = latest_test_output

            passed = self._tests_passed(self.context.get("test_output", ""))
            show_debug_attempt(attempt, self.MAX_DEBUG_RETRIES, passed)

            if passed:
                self.stats["tests_passed"] = "All passed"
                return

        # Exhausted retries
        show_error(
            f"Tests still failing after {self.MAX_DEBUG_RETRIES} debug attempts. "
            "Proceeding to verification."
        )
        self.stats["tests_passed"] = "Some failures remain"

    def _store_context(self, stage_index: int, response: str):
        """Store stage output in context for downstream stages."""
        # Try to read generated docs files for cleaner context
        if stage_index == 0:
            content = self._try_read_file("docs/requirements.md")
            self.context["requirements"] = content or extract_reasoning(response)
        elif stage_index == 1:
            content = self._try_read_file("docs/architecture.md")
            self.context["architecture"] = content or extract_reasoning(response)
        elif stage_index == 2:
            content = self._try_read_file("docs/tasks.md")
            self.context["tasks"] = content or extract_reasoning(response)
        elif stage_index == 3:
            # For implementation, store a summary of created files
            files = self.executor.files_created
            self.context["implementation"] = (
                "Files created:\n" + "\n".join(f"- {f}" for f in files)
            )
        elif stage_index == 4:
            # Store test output - extract from the response
            test_output = self._find_latest_test_output(response)
            self.context["test_output"] = test_output or response

    def _try_read_file(self, rel_path: str) -> str | None:
        """Try to read a file from work_dir. Returns None if not found."""
        abs_path = os.path.join(self.work_dir, rel_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def _find_latest_test_output(self, response: str) -> str | None:
        """Find the last test execution output in a response.

        Looks for pytest-style output patterns.
        """
        # Search through tool results embedded in response for run_command output
        # that looks like pytest output
        lines = response.split("\n")
        output_lines = []
        capture = False
        for line in lines:
            # pytest output markers
            if "pytest" in line.lower() or "PASSED" in line or "FAILED" in line or "ERROR" in line:
                capture = True
            if capture:
                output_lines.append(line)
            # End of test output
            if capture and ("passed" in line.lower() or "error" in line.lower() or "failed" in line.lower()):
                if "==" in line:  # pytest summary line like "=== 5 passed ==="
                    break

        return "\n".join(output_lines) if output_lines else None

    @staticmethod
    def _tests_passed(test_output: str) -> bool:
        """Check if test output indicates all tests passed."""
        if not test_output:
            return False
        lower = test_output.lower()
        # pytest success patterns
        if "passed" in lower and "failed" not in lower and "error" not in lower:
            return True
        # Explicit check for "0 failed"
        if "0 failed" in lower:
            return True
        return False

    @staticmethod
    def _format_tool_results(results: list) -> str:
        """Format tool execution results as a message for the LLM."""
        parts = []
        for r in results:
            status = "SUCCESS" if r.success else "ERROR"
            # Truncate very long outputs to save context
            output = r.output
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"
            parts.append(f"[Tool Result: {r.tool_name} - {status}]\n{output}")
        return "\n\n".join(parts)
