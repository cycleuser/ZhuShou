"""
Comprehensive tests for ZhuShou unified API, tools, and CLI flags.

Tests cover:
- ToolResult dataclass
- api.py: chat(), run_pipeline(), search_pypi()
- tools.py: TOOLS schema, dispatch()
- CLI: unified flags (-V, -v, --json, -q)
- __init__.py: public exports
- LLM: base dataclasses, factory, model_registry
- Executor: builtin_tools, tool_executor
- Memory: persistent, conversation_log
- Context: ContextManager
- Tracking: TokenTracker
- Persona: PersonaLoader
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# ToolResult
# ===========================================================================

class TestToolResult:
    def test_success_result(self):
        from zhushou.api import ToolResult
        r = ToolResult(success=True, data={"key": "value"}, metadata={"v": "1"})
        assert r.success is True
        assert r.data == {"key": "value"}
        assert r.error is None
        assert r.metadata == {"v": "1"}

    def test_failure_result(self):
        from zhushou.api import ToolResult
        r = ToolResult(success=False, error="something broke")
        assert r.success is False
        assert r.data is None
        assert r.error == "something broke"

    def test_to_dict(self):
        from zhushou.api import ToolResult
        r = ToolResult(success=True, data=[1, 2], error=None, metadata={"x": 1})
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["data"] == [1, 2]
        assert d["error"] is None
        assert d["metadata"] == {"x": 1}

    def test_default_metadata_is_independent(self):
        from zhushou.api import ToolResult
        r1 = ToolResult(success=True)
        r2 = ToolResult(success=True)
        r1.metadata["a"] = 1
        assert "a" not in r2.metadata


# ===========================================================================
# api.py — chat / run_pipeline / search_pypi
# ===========================================================================

class TestChatAPI:
    def test_chat_returns_toolresult(self):
        from zhushou.api import chat, ToolResult
        # Without a running LLM server it will fail, but must return ToolResult
        result = chat("test message")
        assert isinstance(result, ToolResult)

    def test_chat_bad_provider(self):
        from zhushou.api import chat
        result = chat("hi", provider="nonexistent_provider")
        assert result.success is False
        assert result.error is not None


class TestRunPipelineAPI:
    def test_pipeline_returns_toolresult(self):
        from zhushou.api import run_pipeline, ToolResult
        result = run_pipeline("build something")
        assert isinstance(result, ToolResult)

    def test_pipeline_bad_provider(self):
        from zhushou.api import run_pipeline
        result = run_pipeline("test", provider="nonexistent_provider")
        assert result.success is False


class TestSearchPyPIAPI:
    def test_search_returns_toolresult(self):
        from zhushou.api import search_pypi, ToolResult
        result = search_pypi("requests")
        assert isinstance(result, ToolResult)

    def test_search_result_structure(self):
        from zhushou.api import search_pypi
        result = search_pypi("requests", max_results=1)
        # May succeed or fail depending on network, but shape is correct
        if result.success:
            assert isinstance(result.data, list)
            assert "query" in result.metadata


# ===========================================================================
# tools.py — TOOLS schema & dispatch
# ===========================================================================

class TestToolsSchema:
    def test_tools_is_list(self):
        from zhushou.tools import TOOLS
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 3

    def test_tool_names(self):
        from zhushou.tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "zhushou_chat" in names
        assert "zhushou_run_pipeline" in names
        assert "zhushou_search_pypi" in names

    def test_tool_structure(self):
        from zhushou.tools import TOOLS
        for tool in TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]
            assert "required" in func["parameters"]

    def test_required_fields_exist_in_properties(self):
        from zhushou.tools import TOOLS
        for tool in TOOLS:
            func = tool["function"]
            props = func["parameters"]["properties"]
            for req in func["parameters"]["required"]:
                assert req in props, f"Required field '{req}' not in properties of {func['name']}"

    def test_tool_name_prefix(self):
        from zhushou.tools import TOOLS
        for tool in TOOLS:
            assert tool["function"]["name"].startswith("zhushou_")


class TestToolsDispatch:
    def test_dispatch_unknown_tool(self):
        from zhushou.tools import dispatch
        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch("nonexistent_tool", {})

    def test_dispatch_json_string_args(self):
        from zhushou.tools import dispatch
        # chat will likely fail without LLM, but should return dict
        args = json.dumps({"message": "test"})
        result = dispatch("zhushou_chat", args)
        assert isinstance(result, dict)
        assert "success" in result

    def test_dispatch_search_pypi(self):
        from zhushou.tools import dispatch
        result = dispatch("zhushou_search_pypi", {"query": "requests"})
        assert isinstance(result, dict)
        assert "success" in result


# ===========================================================================
# CLI unified flags
# ===========================================================================

class TestCLIFlags:
    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "zhushou"] + list(args),
            capture_output=True, text=True, timeout=15,
        )

    def test_version_flag_short(self):
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert "zhushou" in r.stdout.lower()

    def test_version_flag_long(self):
        r = self._run_cli("--version")
        assert r.returncode == 0
        assert "zhushou" in r.stdout.lower()

    def test_help_contains_json_flag(self):
        r = self._run_cli("--help")
        assert r.returncode == 0
        assert "--json" in r.stdout

    def test_help_contains_quiet_flag(self):
        r = self._run_cli("--help")
        assert "--quiet" in r.stdout or "-q" in r.stdout

    def test_help_contains_verbose_flag(self):
        r = self._run_cli("--help")
        assert "--verbose" in r.stdout or "-v" in r.stdout

    def test_help_contains_provider_flag(self):
        r = self._run_cli("--help")
        assert "--provider" in r.stdout

    def test_help_contains_model_flag(self):
        r = self._run_cli("--help")
        assert "--model" in r.stdout

    def test_chat_subcommand_help(self):
        r = self._run_cli("chat", "--help")
        assert r.returncode == 0
        assert "message" in r.stdout.lower()

    def test_pipeline_subcommand_help(self):
        r = self._run_cli("pipeline", "--help")
        assert r.returncode == 0
        assert "request" in r.stdout.lower()

    def test_pipeline_output_flag_after_subcommand(self):
        """zhushou pipeline 'x' -o ./out -m model must NOT fail with unrecognized arguments."""
        r = self._run_cli("pipeline", "test request", "-o", "./test_out", "-m", "llama3", "--provider", "nonexistent")
        # Should not be an argparse error; will fail at provider level but that's OK
        assert "unrecognized arguments" not in r.stderr

    def test_chat_model_flag_after_subcommand(self):
        """zhushou chat 'x' -m model must NOT fail."""
        r = self._run_cli("chat", "test", "-m", "llama3", "--provider", "nonexistent")
        assert "unrecognized arguments" not in r.stderr

    def test_models_json_flag_after_subcommand(self):
        """zhushou models --json must work."""
        r = self._run_cli("models", "--json")
        assert r.returncode == 0
        # Output should be valid JSON
        import json as _json
        data = _json.loads(r.stdout)
        assert isinstance(data, list)

    def test_models_provider_flag_after_subcommand(self):
        """zhushou models --provider ollama must work."""
        r = self._run_cli("models", "--provider", "ollama")
        assert r.returncode == 0

    def test_config_json_flag_after_subcommand(self):
        """zhushou config --json must work."""
        r = self._run_cli("config", "--json")
        assert r.returncode == 0

    def test_pipeline_help_has_output_flag(self):
        r = self._run_cli("pipeline", "--help")
        assert r.returncode == 0
        assert "-o" in r.stdout or "--output" in r.stdout

    def test_chat_help_has_provider_flag(self):
        r = self._run_cli("chat", "--help")
        assert r.returncode == 0
        assert "--provider" in r.stdout

    def test_models_help_has_proxy_flag(self):
        r = self._run_cli("models", "--help")
        assert r.returncode == 0
        assert "--proxy" in r.stdout


# ===========================================================================
# __init__.py exports
# ===========================================================================

class TestPackageExports:
    def test_version_exported(self):
        import zhushou
        assert hasattr(zhushou, "__version__")
        assert isinstance(zhushou.__version__, str)

    def test_toolresult_exported(self):
        from zhushou import ToolResult
        r = ToolResult(success=True)
        assert r.success is True

    def test_chat_exported(self):
        from zhushou import chat
        assert callable(chat)

    def test_run_pipeline_exported(self):
        from zhushou import run_pipeline
        assert callable(run_pipeline)

    def test_search_pypi_exported(self):
        from zhushou import search_pypi
        assert callable(search_pypi)


# ===========================================================================
# LLM base dataclasses
# ===========================================================================

class TestLLMBaseDataclasses:
    def test_token_usage_defaults(self):
        from zhushou.llm.base import TokenUsage
        u = TokenUsage()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_model_info(self):
        from zhushou.llm.base import ModelInfo
        m = ModelInfo(name="gpt-4o", size_gb=0.0, context_window=128000, provider="openai")
        assert m.name == "gpt-4o"
        assert m.provider == "openai"

    def test_tool_call_request(self):
        from zhushou.llm.base import ToolCallRequest
        t = ToolCallRequest(id="call_1", name="read_file", arguments='{"path": "x.py"}')
        assert t.id == "call_1"
        assert t.name == "read_file"

    def test_llm_response_defaults(self):
        from zhushou.llm.base import LLMResponse
        r = LLMResponse()
        assert r.content == ""
        assert r.tool_calls == []
        assert r.finish_reason == ""

    def test_llm_response_with_tool_calls(self):
        from zhushou.llm.base import LLMResponse, ToolCallRequest
        tc = ToolCallRequest(id="1", name="test", arguments="{}")
        r = LLMResponse(content="", tool_calls=[tc], finish_reason="tool_calls")
        assert len(r.tool_calls) == 1
        assert r.tool_calls[0].name == "test"


# ===========================================================================
# LLM factory
# ===========================================================================

class TestLLMFactory:
    def test_unknown_provider_raises(self):
        from zhushou.llm.factory import LLMClientFactory
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMClientFactory.create_client("nonexistent_provider_xyz")

    def test_providers_dict(self):
        from zhushou.llm.factory import LLMClientFactory
        assert isinstance(LLMClientFactory.PROVIDERS, dict)
        assert "ollama" in LLMClientFactory.PROVIDERS
        assert "openai" in LLMClientFactory.PROVIDERS
        assert "anthropic" in LLMClientFactory.PROVIDERS

    def test_list_providers(self):
        from zhushou.llm.factory import LLMClientFactory
        providers = LLMClientFactory.list_providers()
        assert isinstance(providers, list)
        assert "ollama" in providers
        assert "deepseek" in providers

    def test_create_ollama_client(self):
        from zhushou.llm.factory import LLMClientFactory
        client = LLMClientFactory.create_client("ollama")
        assert client.provider_name == "ollama"


# ===========================================================================
# Model registry
# ===========================================================================

class TestModelRegistry:
    def test_registry_structure(self):
        from zhushou.llm.model_registry import MODEL_REGISTRY
        assert isinstance(MODEL_REGISTRY, dict)
        assert "openai" in MODEL_REGISTRY
        assert "anthropic" in MODEL_REGISTRY
        assert "deepseek" in MODEL_REGISTRY
        assert "gemini" in MODEL_REGISTRY

    def test_get_context_window_known(self):
        from zhushou.llm.model_registry import get_context_window
        ctx = get_context_window("openai", "gpt-4o")
        assert ctx == 128_000

    def test_get_context_window_unknown_model(self):
        from zhushou.llm.model_registry import get_context_window
        ctx = get_context_window("openai", "unknown-model-xyz")
        assert ctx == 128_000  # provider default

    def test_get_context_window_unknown_provider(self):
        from zhushou.llm.model_registry import get_context_window
        ctx = get_context_window("unknown_provider", "x")
        assert ctx == 4_096  # global fallback

    def test_get_cost_local(self):
        from zhushou.llm.model_registry import get_cost
        from zhushou.llm.base import TokenUsage
        cost = get_cost("ollama", "llama3", TokenUsage(1000, 500, 1500))
        assert cost == 0.0

    def test_get_cost_openai(self):
        from zhushou.llm.model_registry import get_cost
        from zhushou.llm.base import TokenUsage
        cost = get_cost("openai", "gpt-4o", TokenUsage(1_000_000, 1_000_000, 2_000_000))
        assert cost > 0.0


# ===========================================================================
# Executor — builtin_tools
# ===========================================================================

class TestBuiltinTools:
    def test_all_tools_is_list(self):
        from zhushou.executor.builtin_tools import ALL_TOOLS
        assert isinstance(ALL_TOOLS, list)
        assert len(ALL_TOOLS) == 12

    def test_tool_handlers_match_schemas(self):
        from zhushou.executor.builtin_tools import ALL_TOOLS, TOOL_HANDLERS
        schema_names = {t["function"]["name"] for t in ALL_TOOLS}
        handler_names = set(TOOL_HANDLERS.keys())
        assert schema_names == handler_names

    def test_read_file(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        # Create a test file
        test_file = tmp_work_dir / "hello.txt"
        test_file.write_text("Hello, World!")
        result = TOOL_HANDLERS["read_file"](str(tmp_work_dir), {"path": "hello.txt"})
        assert result["success"] is True
        assert "Hello, World!" in result["output"]

    def test_read_file_not_found(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        result = TOOL_HANDLERS["read_file"](str(tmp_work_dir), {"path": "no_such_file.txt"})
        assert result["success"] is False

    def test_write_file(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        result = TOOL_HANDLERS["write_file"](
            str(tmp_work_dir), {"path": "out.txt", "content": "test content"}
        )
        assert result["success"] is True
        assert (tmp_work_dir / "out.txt").read_text().strip() == "test content"

    def test_write_file_git_protected(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        result = TOOL_HANDLERS["write_file"](
            str(tmp_work_dir), {"path": ".git/config", "content": "bad"}
        )
        assert result["success"] is False
        assert "Refusing" in result["output"]

    def test_edit_file(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        f = tmp_work_dir / "edit_me.txt"
        f.write_text("foo bar baz")
        result = TOOL_HANDLERS["edit_file"](
            str(tmp_work_dir), {"path": "edit_me.txt", "old_text": "bar", "new_text": "qux"}
        )
        assert result["success"] is True
        assert f.read_text() == "foo qux baz"

    def test_run_command(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        result = TOOL_HANDLERS["run_command"](
            str(tmp_work_dir), {"command": "echo hello"}
        )
        assert result["success"] is True
        assert "hello" in result["output"]

    def test_glob_files(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        (tmp_work_dir / "a.py").write_text("")
        (tmp_work_dir / "b.py").write_text("")
        result = TOOL_HANDLERS["glob_files"](str(tmp_work_dir), {"pattern": "*.py"})
        assert result["success"] is True
        assert "a.py" in result["output"]
        assert "b.py" in result["output"]

    def test_list_files(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        (tmp_work_dir / "file1.txt").write_text("")
        result = TOOL_HANDLERS["list_files"](str(tmp_work_dir), {})
        assert result["success"] is True
        assert "file1.txt" in result["output"]

    def test_python_exec(self, tmp_work_dir):
        from zhushou.executor.builtin_tools import TOOL_HANDLERS
        result = TOOL_HANDLERS["python_exec"](
            str(tmp_work_dir), {"code": "print(2+2)"}
        )
        assert result["success"] is True
        assert "4" in result["output"]


# ===========================================================================
# Executor — ToolExecutor
# ===========================================================================

class TestToolExecutor:
    def test_execute_unknown_tool(self, tmp_work_dir):
        from zhushou.executor.tool_executor import ToolExecutor
        ex = ToolExecutor(work_dir=str(tmp_work_dir))
        result = ex.execute("nonexistent_tool", {})
        assert result["success"] is False
        assert "Unknown tool" in result["output"]

    def test_execute_read_file(self, tmp_work_dir):
        from zhushou.executor.tool_executor import ToolExecutor
        (tmp_work_dir / "test.txt").write_text("content")
        ex = ToolExecutor(work_dir=str(tmp_work_dir))
        result = ex.execute("read_file", {"path": "test.txt"})
        assert result["success"] is True
        assert "content" in result["output"]

    def test_get_tool_definitions(self):
        from zhushou.executor.tool_executor import ToolExecutor
        defs = ToolExecutor.get_tool_definitions()
        assert isinstance(defs, list)
        assert len(defs) == 12

    def test_files_created_tracking(self, tmp_work_dir):
        from zhushou.executor.tool_executor import ToolExecutor
        ex = ToolExecutor(work_dir=str(tmp_work_dir))
        ex.execute("write_file", {"path": "new.txt", "content": "data"})
        assert "new.txt" in ex.files_created

    def test_path_escape_protection(self, tmp_work_dir):
        from zhushou.executor.tool_executor import ToolExecutor
        ex = ToolExecutor(work_dir=str(tmp_work_dir))
        result = ex.execute("read_file", {"path": "../../etc/passwd"})
        assert result["success"] is False


# ===========================================================================
# Memory — PersistentMemory
# ===========================================================================

class TestPersistentMemory:
    def test_set_and_get(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set("key1", "value1")
        assert mem.get("key1") == "value1"

    def test_get_default(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        assert mem.get("missing", "default") == "default"

    def test_delete(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set("k", "v")
        assert mem.delete("k") is True
        assert mem.get("k") is None
        assert mem.delete("k") is False

    def test_search(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set("python_version", "3.12")
        mem.set("node_version", "20")
        results = mem.search("python")
        assert len(results) == 1
        assert results[0][0] == "python_version"

    def test_clear(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set("a", 1)
        mem.set("b", 2)
        mem.clear()
        assert mem.keys() == []

    def test_persistence(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem1 = PersistentMemory(path=tmp_memory_file)
        mem1.set("persistent", True)
        # Reload from disk
        mem2 = PersistentMemory(path=tmp_memory_file)
        assert mem2.get("persistent") is True


# ===========================================================================
# Memory — ConversationLog
# ===========================================================================

class TestConversationLog:
    def test_append_and_load(self, tmp_logs_dir):
        from zhushou.memory.conversation_log import ConversationLog
        log = ConversationLog(logs_dir=tmp_logs_dir)
        log.append("user", "hello")
        log.append("assistant", "hi there")
        entries = log.load_recent(10)
        assert len(entries) == 2
        assert entries[0]["role"] == "user"
        assert entries[1]["role"] == "assistant"

    def test_today_path_format(self, tmp_logs_dir):
        from zhushou.memory.conversation_log import ConversationLog
        log = ConversationLog(logs_dir=tmp_logs_dir)
        path = log.get_today_path()
        assert path.suffix == ".jsonl"
        assert path.parent == tmp_logs_dir

    def test_load_recent_limit(self, tmp_logs_dir):
        from zhushou.memory.conversation_log import ConversationLog
        log = ConversationLog(logs_dir=tmp_logs_dir)
        for i in range(20):
            log.append("user", f"msg {i}")
        entries = log.load_recent(5)
        assert len(entries) == 5


# ===========================================================================
# Context — ContextManager
# ===========================================================================

class TestContextManager:
    def test_build_messages_basic(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager(max_tokens=32768)
        conv = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        msgs = cm.build_messages("You are helpful.", conv)
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are helpful."
        assert len(msgs) == 3

    def test_build_messages_with_memory(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager(max_tokens=32768)
        msgs = cm.build_messages("sys prompt", [], memory_context="some context")
        assert len(msgs) == 2
        assert "memory" in msgs[1]["content"].lower()

    def test_estimate_tokens_latin(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager()
        tokens = cm.estimate_tokens("Hello world, this is a test.")
        assert tokens > 0
        assert tokens == len("Hello world, this is a test.") // 4

    def test_estimate_tokens_cjk(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager()
        # CJK-heavy text should use divisor of 3
        text = "这是一个中文测试字符串用来验证分词"
        tokens = cm.estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_empty(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager()
        assert cm.estimate_tokens("") == 0

    def test_needs_compaction(self):
        from zhushou.agent.context import ContextManager
        cm = ContextManager(max_tokens=100)
        # A very long message should trigger compaction
        msgs = [{"role": "user", "content": "x" * 500}]
        assert cm.needs_compaction(msgs) is True
        # A short message should not
        msgs = [{"role": "user", "content": "hi"}]
        assert cm.needs_compaction(msgs) is False


# ===========================================================================
# Tracking — TokenTracker
# ===========================================================================

class TestTokenTracker:
    def test_record_and_stats(self, tmp_usage_file):
        from zhushou.tracking.tracker import TokenTracker
        t = TokenTracker(usage_path=tmp_usage_file)
        t.record("openai", "gpt-4o", 100, 50)
        stats = t.get_session_stats()
        assert stats["prompt_tokens"] == 100
        assert stats["completion_tokens"] == 50
        assert stats["total_tokens"] == 150
        assert stats["calls"] == 1

    def test_cost_ollama_is_free(self, tmp_usage_file):
        from zhushou.tracking.tracker import TokenTracker
        t = TokenTracker(usage_path=tmp_usage_file)
        t.record("ollama", "llama3", 1000, 500)
        stats = t.get_session_stats()
        assert stats["estimated_cost"] == 0.0

    def test_save_and_load(self, tmp_usage_file):
        from zhushou.tracking.tracker import TokenTracker
        t = TokenTracker(usage_path=tmp_usage_file)
        t.record("openai", "gpt-4o", 100, 50)
        t.save()
        assert tmp_usage_file.is_file()
        data = json.loads(tmp_usage_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_repr(self, tmp_usage_file):
        from zhushou.tracking.tracker import TokenTracker
        t = TokenTracker(usage_path=tmp_usage_file)
        r = repr(t)
        assert "TokenTracker" in r


# ===========================================================================
# Persona — PersonaLoader
# ===========================================================================

class TestPersonaLoader:
    def test_default_persona(self):
        from zhushou.persona.loader import PersonaLoader
        # Loading from a nonexistent dir falls back to default
        persona = PersonaLoader.load("/nonexistent/path/xyz")
        assert "ZhuShou" in persona
        assert "# Identity" in persona

    def test_custom_persona(self, tmp_work_dir):
        from zhushou.persona.loader import PersonaLoader
        persona_dir = tmp_work_dir / ".zhushou"
        persona_dir.mkdir()
        (persona_dir / "persona.md").write_text("# Custom\nYou are a custom bot.")
        persona = PersonaLoader.load(str(tmp_work_dir))
        assert "custom bot" in persona.lower()

    def test_empty_persona_fallback(self, tmp_work_dir):
        from zhushou.persona.loader import PersonaLoader
        persona_dir = tmp_work_dir / ".zhushou"
        persona_dir.mkdir()
        (persona_dir / "persona.md").write_text("")
        persona = PersonaLoader.load(str(tmp_work_dir))
        # Should fall back to default since file is empty
        assert "ZhuShou" in persona


# ===========================================================================
# LLM base — validate_messages (via concrete minimal stub)
# ===========================================================================

class TestValidateMessages:
    def _make_stub(self):
        """Create a minimal concrete subclass for testing the mixin."""
        from zhushou.llm.base import BaseLLMClient, LLMResponse, ModelInfo

        class Stub(BaseLLMClient):
            def chat(self, messages, temperature=0.3, tools=None):
                return LLMResponse()
            def chat_stream(self, messages, temperature=0.3, tools=None):
                yield ""
            def is_available(self):
                return False
            def list_models(self):
                return []
            @property
            def model(self):
                return "stub"
            @model.setter
            def model(self, value):
                pass
            @property
            def provider_name(self):
                return "stub"
            @property
            def max_context_tokens(self):
                return 4096

        return Stub()

    def test_valid_messages(self):
        stub = self._make_stub()
        msgs = [{"role": "user", "content": "hello"}]
        result = stub.validate_messages(msgs)
        assert len(result) == 1

    def test_empty_messages_raises(self):
        stub = self._make_stub()
        with pytest.raises(ValueError, match="non-empty"):
            stub.validate_messages([])

    def test_invalid_role_raises(self):
        stub = self._make_stub()
        with pytest.raises(ValueError, match="invalid role"):
            stub.validate_messages([{"role": "invalid_role", "content": "x"}])

    def test_missing_content_raises(self):
        stub = self._make_stub()
        with pytest.raises(ValueError, match="content"):
            stub.validate_messages([{"role": "user"}])

    def test_tool_calls_message_accepted(self):
        stub = self._make_stub()
        msgs = [{"role": "assistant", "tool_calls": [], "content": None}]
        result = stub.validate_messages(msgs)
        assert len(result) == 1


# ===========================================================================
# Proxy support
# ===========================================================================

class TestProxySupport:
    def test_ollama_client_no_env_proxy(self, monkeypatch):
        """System SOCKS proxy env var must NOT crash OllamaLLMClient."""
        monkeypatch.setenv("ALL_PROXY", "socks://127.0.0.1:9999")
        monkeypatch.setenv("HTTP_PROXY", "socks://127.0.0.1:9999")
        monkeypatch.setenv("HTTPS_PROXY", "socks://127.0.0.1:9999")
        from zhushou.llm.ollama_client import OllamaLLMClient
        # Must not raise "Unknown scheme for proxy URL"
        client = OllamaLLMClient()
        assert client.provider_name == "ollama"

    def test_ollama_client_accepts_proxy(self):
        from zhushou.llm.ollama_client import OllamaLLMClient
        client = OllamaLLMClient(proxy="http://proxy:8080")
        assert client.provider_name == "ollama"

    def test_factory_passes_proxy(self):
        from zhushou.llm.factory import LLMClientFactory
        client = LLMClientFactory.create_client("ollama", proxy="http://proxy:8080")
        assert client.provider_name == "ollama"

    def test_cli_help_has_proxy_flag(self):
        import subprocess, sys
        r = subprocess.run(
            [sys.executable, "-m", "zhushou", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0
        assert "--proxy" in r.stdout


# ===========================================================================
# Documented CLI examples — argparse unit tests
# ===========================================================================

class TestDocumentedArgParsing:
    """Test argparse parsing for every CLI example in README.md / README_CN.md.

    Uses ``main(argv=...)`` with mocked command handlers so no LLM server
    is needed and tests run in milliseconds.
    """

    def test_chat_message_parses(self):
        """README: zhushou chat 'Explain Python decorators'"""
        with patch("zhushou.cli._cmd_chat") as mock:
            from zhushou.cli import main
            main(["chat", "Explain Python decorators"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.command == "chat"
            assert args.message == "Explain Python decorators"

    def test_chat_chinese_message_parses(self):
        """README_CN: zhushou chat '解释 Python 装饰器'"""
        with patch("zhushou.cli._cmd_chat") as mock:
            from zhushou.cli import main
            main(["chat", "解释 Python 装饰器"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.message == "解释 Python 装饰器"

    def test_pipeline_with_output_parses(self):
        """README: zhushou pipeline 'Build a Gomoku game' -o ./output"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "Build a Gomoku game", "-o", "./output"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.command == "pipeline"
            assert args.request == "Build a Gomoku game"
            assert args.output == "./output"

    def test_pipeline_chinese_with_output_parses(self):
        """README_CN: zhushou pipeline '开发一个五子棋游戏' -o ./output"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "开发一个五子棋游戏", "-o", "./output"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.request == "开发一个五子棋游戏"
            assert args.output == "./output"

    def test_pipeline_flask_example(self):
        """README: zhushou pipeline 'Build a REST API with Flask' -o ./my_api"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "Build a REST API with Flask", "-o", "./my_api"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.request == "Build a REST API with Flask"
            assert args.output == "./my_api"

    def test_pipeline_flask_chinese_example(self):
        """README_CN: zhushou pipeline '用 Flask 开发一个 REST API' -o ./my_api"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "用 Flask 开发一个 REST API", "-o", "./my_api"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.request == "用 Flask 开发一个 REST API"
            assert args.output == "./my_api"

    def test_models_subcommand_parses(self):
        """README: zhushou models"""
        with patch("zhushou.cli._cmd_models") as mock:
            from zhushou.cli import main
            main(["models"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.command == "models"

    def test_config_subcommand_parses(self):
        """README: zhushou config"""
        with patch("zhushou.cli._cmd_config") as mock:
            from zhushou.cli import main
            main(["config"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.command == "config"

    def test_provider_ollama_model_llama3(self):
        """README: zhushou --provider ollama --model llama3"""
        with patch("zhushou.cli._cmd_interactive") as mock:
            from zhushou.cli import main
            main(["--provider", "ollama", "--model", "llama3"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.provider == "ollama"
            assert args.model == "llama3"

    def test_provider_openai_with_key_and_model(self):
        """README: zhushou --provider openai --api-key sk-... --model gpt-4o"""
        with patch("zhushou.cli._cmd_interactive") as mock:
            from zhushou.cli import main
            main(["--provider", "openai", "--api-key", "sk-test", "--model", "gpt-4o"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.provider == "openai"
            assert args.api_key == "sk-test"
            assert args.model == "gpt-4o"

    def test_provider_deepseek_with_key(self):
        """README: zhushou --provider deepseek --api-key sk-..."""
        with patch("zhushou.cli._cmd_interactive") as mock:
            from zhushou.cli import main
            main(["--provider", "deepseek", "--api-key", "sk-test"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.provider == "deepseek"
            assert args.api_key == "sk-test"

    def test_provider_custom_base_url(self):
        """README: zhushou --provider openai --base-url http://localhost:8080/v1"""
        with patch("zhushou.cli._cmd_interactive") as mock:
            from zhushou.cli import main
            main(["--provider", "openai", "--base-url", "http://localhost:8080/v1"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.provider == "openai"
            assert args.base_url == "http://localhost:8080/v1"

    def test_no_subcommand_launches_interactive(self):
        """README: zhushou (no args) -> interactive REPL"""
        with patch("zhushou.cli._cmd_interactive") as mock:
            from zhushou.cli import main
            main([])
            mock.assert_called_once()

    def test_chat_no_message_launches_interactive(self):
        """zhushou chat (no message) -> interactive mode"""
        with patch("zhushou.cli._cmd_chat") as mock:
            from zhushou.cli import main
            main(["chat"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.message == ""

    def test_pipeline_flags_before_request(self):
        """Flags before positional: zhushou pipeline -o ./out -m model 'request'"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "-o", "./out", "-m", "llama3", "my request"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.output == "./out"
            assert args.model == "llama3"
            assert args.request == "my request"

    def test_pipeline_flags_after_request(self):
        """Flags after positional: zhushou pipeline 'request' -o ./out -m model"""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "my request", "-o", "./out", "-m", "llama3"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.output == "./out"
            assert args.model == "llama3"
            assert args.request == "my request"

    def test_chat_with_all_flags(self):
        """All flags on chat subcommand."""
        with patch("zhushou.cli._cmd_chat") as mock:
            from zhushou.cli import main
            main([
                "chat", "test message",
                "-v", "--json", "-q",
                "-o", "/tmp/test",
                "--provider", "openai",
                "-m", "gpt-4o",
                "--api-key", "sk-test",
                "--base-url", "http://localhost:8080/v1",
                "--proxy", "http://proxy:8080",
            ])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.verbose is True
            assert args.json_output is True
            assert args.quiet is True
            assert args.output == "/tmp/test"
            assert args.provider == "openai"
            assert args.model == "gpt-4o"
            assert args.api_key == "sk-test"
            assert args.base_url == "http://localhost:8080/v1"
            assert args.proxy == "http://proxy:8080"

    def test_pipeline_with_all_flags(self):
        """All flags on pipeline subcommand."""
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main([
                "pipeline", "build something",
                "-v", "--json", "-q",
                "-o", "/tmp/out",
                "--provider", "deepseek",
                "-m", "deepseek-chat",
                "--api-key", "sk-test",
                "--base-url", "https://api.deepseek.com",
                "--proxy", "http://proxy:8080",
            ])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.verbose is True
            assert args.json_output is True
            assert args.quiet is True
            assert args.output == "/tmp/out"
            assert args.provider == "deepseek"
            assert args.model == "deepseek-chat"

    def test_models_with_json_flag(self):
        """zhushou models --json"""
        with patch("zhushou.cli._cmd_models") as mock:
            from zhushou.cli import main
            main(["models", "--json"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.json_output is True

    def test_models_with_provider_flag(self):
        """zhushou models --provider openai"""
        with patch("zhushou.cli._cmd_models") as mock:
            from zhushou.cli import main
            main(["models", "--provider", "openai"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.provider == "openai"

    def test_config_with_json_flag(self):
        """zhushou config --json"""
        with patch("zhushou.cli._cmd_config") as mock:
            from zhushou.cli import main
            main(["config", "--json"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.json_output is True

    def test_proxy_flag_on_all_subcommands(self):
        """--proxy flag is accepted on every subcommand."""
        for cmd, handler, extra_args in [
            ("chat", "_cmd_chat", ["test"]),
            ("pipeline", "_cmd_pipeline", ["request"]),
            ("models", "_cmd_models", []),
            ("config", "_cmd_config", []),
        ]:
            with patch(f"zhushou.cli.{handler}") as mock:
                from zhushou.cli import main
                main([cmd] + extra_args + ["--proxy", "http://proxy:8080"])
                args = mock.call_args[0][0]
                assert args.proxy == "http://proxy:8080", f"--proxy failed on {cmd}"


# ===========================================================================
# Documented CLI examples — subprocess integration tests
# ===========================================================================

class TestDocumentedCLIIntegration:
    """Subprocess-based tests for CLI examples that can run without an LLM."""

    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "zhushou"] + list(args),
            capture_output=True, text=True, timeout=15,
        )

    def test_version_short(self):
        """README: zhushou -V"""
        from zhushou import __version__
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert __version__ in r.stdout

    def test_version_long(self):
        """README: zhushou --version"""
        from zhushou import __version__
        r = self._run_cli("--version")
        assert r.returncode == 0
        assert __version__ in r.stdout

    def test_config_shows_directory(self):
        """README: zhushou config"""
        r = self._run_cli("config")
        assert r.returncode == 0
        assert "Config directory:" in r.stdout
        assert ".zhushou" in r.stdout

    def test_config_json_returns_valid_json(self):
        """README: zhushou config --json"""
        r = self._run_cli("config", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_models_json_returns_valid_json(self):
        """README: zhushou models --json"""
        r = self._run_cli("models", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, list)

    def test_models_default_provider(self):
        """README: zhushou models"""
        r = self._run_cli("models")
        assert r.returncode == 0

    def test_models_with_provider(self):
        """README: zhushou models --provider ollama"""
        r = self._run_cli("models", "--provider", "ollama")
        assert r.returncode == 0

    def test_chat_help(self):
        """zhushou chat --help"""
        r = self._run_cli("chat", "--help")
        assert r.returncode == 0
        assert "message" in r.stdout.lower()

    def test_pipeline_help(self):
        """zhushou pipeline --help"""
        r = self._run_cli("pipeline", "--help")
        assert r.returncode == 0
        assert "request" in r.stdout.lower()

    def test_models_help(self):
        """zhushou models --help"""
        r = self._run_cli("models", "--help")
        assert r.returncode == 0

    def test_config_help(self):
        """zhushou config --help"""
        r = self._run_cli("config", "--help")
        assert r.returncode == 0


# ===========================================================================
# Documented Global Options — verify all documented flags exist
# ===========================================================================

class TestDocumentedGlobalOptions:
    """Verify every flag listed in the README Global Options table exists
    in the --help output of the main parser AND every subcommand."""

    # Flags from the Global Options table in README.md (excluding -V which is main-only)
    DOCUMENTED_FLAGS = [
        "--verbose", "-v",
        "--json",
        "--quiet", "-q",
        "--output", "-o",
        "--provider",
        "--model", "-m",
        "--api-key",
        "--base-url",
        "--proxy",
    ]

    def _get_help(self, *args):
        r = subprocess.run(
            [sys.executable, "-m", "zhushou"] + list(args) + ["--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0
        return r.stdout

    def test_main_help_has_all_flags(self):
        help_text = self._get_help()
        for flag in self.DOCUMENTED_FLAGS:
            assert flag in help_text, f"Missing {flag} in main help"
        # -V is main-only
        assert "-V" in help_text

    def test_chat_help_has_all_flags(self):
        help_text = self._get_help("chat")
        for flag in self.DOCUMENTED_FLAGS:
            assert flag in help_text, f"Missing {flag} in 'chat' help"

    def test_pipeline_help_has_all_flags(self):
        help_text = self._get_help("pipeline")
        for flag in self.DOCUMENTED_FLAGS:
            assert flag in help_text, f"Missing {flag} in 'pipeline' help"

    def test_models_help_has_all_flags(self):
        help_text = self._get_help("models")
        for flag in self.DOCUMENTED_FLAGS:
            assert flag in help_text, f"Missing {flag} in 'models' help"

    def test_config_help_has_all_flags(self):
        help_text = self._get_help("config")
        for flag in self.DOCUMENTED_FLAGS:
            assert flag in help_text, f"Missing {flag} in 'config' help"


# ===========================================================================
# Documented Subcommands — verify all exist
# ===========================================================================

class TestDocumentedSubcommands:
    """Verify every subcommand listed in the README exists."""

    DOCUMENTED_SUBCOMMANDS = ["chat", "pipeline", "models", "config"]

    def test_all_subcommands_in_main_help(self):
        r = subprocess.run(
            [sys.executable, "-m", "zhushou", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0
        for cmd in self.DOCUMENTED_SUBCOMMANDS:
            assert cmd in r.stdout, f"Missing subcommand '{cmd}' in main help"

    def test_each_subcommand_has_help(self):
        for cmd in self.DOCUMENTED_SUBCOMMANDS:
            r = subprocess.run(
                [sys.executable, "-m", "zhushou", cmd, "--help"],
                capture_output=True, text=True, timeout=15,
            )
            assert r.returncode == 0, f"'{cmd} --help' failed with rc={r.returncode}"


# ===========================================================================
# Documented Providers — verify all exist in factory
# ===========================================================================

class TestDocumentedProviders:
    """Verify every provider listed in the README is available."""

    DOCUMENTED_PROVIDERS = [
        "ollama", "openai", "anthropic", "deepseek", "gemini", "lmstudio", "vllm",
    ]

    def test_all_providers_in_factory(self):
        from zhushou.llm.factory import LLMClientFactory
        available = LLMClientFactory.list_providers()
        for p in self.DOCUMENTED_PROVIDERS:
            assert p in available, f"Provider '{p}' documented but not in factory"

    def test_claude_alias_exists(self):
        from zhushou.llm.factory import LLMClientFactory
        assert "claude" in LLMClientFactory.PROVIDERS

    def test_factory_create_ollama(self):
        from zhushou.llm.factory import LLMClientFactory
        client = LLMClientFactory.create_client("ollama")
        assert client.provider_name == "ollama"

    def test_factory_create_openai(self):
        from zhushou.llm.factory import LLMClientFactory
        client = LLMClientFactory.create_client("openai", api_key="sk-test")
        assert client.provider_name == "openai"

    def test_factory_create_deepseek(self):
        from zhushou.llm.factory import LLMClientFactory
        client = LLMClientFactory.create_client("deepseek", api_key="sk-test")
        assert client.provider_name == "openai"  # deepseek uses OpenAI client

    def test_factory_unknown_provider_raises(self):
        from zhushou.llm.factory import LLMClientFactory
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMClientFactory.create_client("nonexistent_xyz")


# ===========================================================================
# Documented Python API — verify imports and function signatures
# ===========================================================================

class TestDocumentedPythonAPI:
    """Verify all Python API examples from the README work correctly."""

    def test_top_level_imports(self):
        """README: from zhushou import chat, run_pipeline, search_pypi"""
        from zhushou import chat, run_pipeline, search_pypi
        assert callable(chat)
        assert callable(run_pipeline)
        assert callable(search_pypi)

    def test_tools_imports(self):
        """README: from zhushou.tools import TOOLS, dispatch"""
        from zhushou.tools import TOOLS, dispatch
        assert isinstance(TOOLS, list)
        assert callable(dispatch)

    def test_chat_accepts_documented_params(self):
        """README: chat('msg', provider='ollama', model='llama3')"""
        import inspect
        from zhushou.api import chat
        sig = inspect.signature(chat)
        params = list(sig.parameters.keys())
        assert "message" in params
        assert "provider" in params
        assert "model" in params

    def test_run_pipeline_accepts_documented_params(self):
        """README: run_pipeline('request', output_dir='./calc')"""
        import inspect
        from zhushou.api import run_pipeline
        sig = inspect.signature(run_pipeline)
        params = list(sig.parameters.keys())
        assert "request" in params
        assert "output_dir" in params

    def test_search_pypi_accepts_documented_params(self):
        """README: search_pypi('requests')"""
        import inspect
        from zhushou.api import search_pypi
        sig = inspect.signature(search_pypi)
        params = list(sig.parameters.keys())
        assert "query" in params

    def test_toolresult_has_documented_fields(self):
        """README: result.success, result.data"""
        from zhushou.api import ToolResult
        r = ToolResult(success=True, data="test")
        assert hasattr(r, "success")
        assert hasattr(r, "data")
        assert hasattr(r, "error")

    def test_chat_returns_toolresult(self):
        """chat() always returns ToolResult even on failure."""
        from zhushou.api import chat, ToolResult
        result = chat("test", provider="nonexistent_xyz")
        assert isinstance(result, ToolResult)
        assert result.success is False

    def test_run_pipeline_returns_toolresult(self):
        """run_pipeline() always returns ToolResult even on failure."""
        from zhushou.api import run_pipeline, ToolResult
        result = run_pipeline("test", provider="nonexistent_xyz")
        assert isinstance(result, ToolResult)
        assert result.success is False

    def test_search_pypi_returns_toolresult(self):
        """search_pypi() always returns ToolResult."""
        from zhushou.api import search_pypi, ToolResult
        result = search_pypi("requests")
        assert isinstance(result, ToolResult)

    def test_tools_schema_matches_api(self):
        """TOOLS schema tool names map to real dispatch targets."""
        from zhushou.tools import TOOLS, dispatch
        for tool in TOOLS:
            name = tool["function"]["name"]
            # dispatch should not raise ValueError for known tools
            # (it will fail at API level but not at routing level)
            if name == "zhushou_search_pypi":
                result = dispatch(name, {"query": "test"})
                assert isinstance(result, dict)

    def test_proxy_param_in_api_functions(self):
        """Proxy parameter exists in chat() and run_pipeline()."""
        import inspect
        from zhushou.api import chat, run_pipeline
        assert "proxy" in inspect.signature(chat).parameters
        assert "proxy" in inspect.signature(run_pipeline).parameters


# ===========================================================================
# Ollama message sanitization
# ===========================================================================

class TestOllamaSanitizeMessages:
    """Tests for OllamaLLMClient._sanitize_messages()."""

    def _make_client(self):
        from zhushou.llm.ollama_client import OllamaLLMClient
        return OllamaLLMClient()

    def test_plain_messages_unchanged(self):
        client = self._make_client()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = client._sanitize_messages(messages)
        assert len(result) == 3
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}
        assert result[2] == {"role": "assistant", "content": "Hi there"}

    def test_assistant_tool_calls_sanitized(self):
        """String arguments should be deserialized; id/type should be stripped."""
        client = self._make_client()
        messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_0",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "main.py", "content": "print(1)"}',
                        },
                    }
                ],
            }
        ]
        result = client._sanitize_messages(messages)
        assert len(result) == 1
        msg = result[0]
        assert msg["role"] == "assistant"
        tc = msg["tool_calls"][0]
        # id and type should be gone
        assert "id" not in tc
        assert "type" not in tc
        # arguments should be a dict
        assert isinstance(tc["function"]["arguments"], dict)
        assert tc["function"]["arguments"]["path"] == "main.py"
        assert tc["function"]["name"] == "write_file"

    def test_tool_result_messages_sanitized(self):
        """tool_call_id and name should be stripped from tool messages."""
        client = self._make_client()
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_0",
                "name": "write_file",
                "content": "File written: main.py",
            }
        ]
        result = client._sanitize_messages(messages)
        assert len(result) == 1
        msg = result[0]
        assert msg == {"role": "tool", "content": "File written: main.py"}
        assert "tool_call_id" not in msg
        assert "name" not in msg

    def test_mixed_conversation_sanitized(self):
        """Full multi-turn conversation with tool calls round-trips correctly."""
        client = self._make_client()
        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Create a file"},
            {
                "role": "assistant",
                "content": "I'll create it.",
                "tool_calls": [
                    {
                        "id": "call_0",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "x.py", "content": "pass"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_0",
                "name": "write_file",
                "content": "File written: x.py",
            },
            {"role": "assistant", "content": "Done!"},
        ]
        result = client._sanitize_messages(messages)
        assert len(result) == 5
        # system & user unchanged
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        # assistant with tool_calls cleaned
        assert isinstance(result[2]["tool_calls"][0]["function"]["arguments"], dict)
        assert "id" not in result[2]["tool_calls"][0]
        # tool result cleaned
        assert result[3] == {"role": "tool", "content": "File written: x.py"}
        # plain assistant unchanged
        assert result[4] == {"role": "assistant", "content": "Done!"}

    def test_malformed_arguments_handled(self):
        """Invalid JSON in arguments should fall back to empty dict."""
        client = self._make_client()
        messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_0",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": "not valid json {{{",
                        },
                    }
                ],
            }
        ]
        result = client._sanitize_messages(messages)
        tc = result[0]["tool_calls"][0]
        assert tc["function"]["arguments"] == {}


# ===========================================================================
# Tool result dict access
# ===========================================================================

class TestToolResultDictAccess:
    """Verify orchestrator and agent loop correctly extract output from dict results."""

    def test_orchestrator_extracts_dict_output(self):
        """_run_stage_with_tools should put clean output string in tool messages."""
        from unittest.mock import MagicMock
        from zhushou.llm.base import LLMResponse, ToolCallRequest

        # First response: one tool call; second response: done
        tool_call = ToolCallRequest(id="call_0", name="write_file",
                                    arguments='{"path": "a.py", "content": "x"}')
        resp_with_tool = LLMResponse(content="", tool_calls=[tool_call], finish_reason="tool_calls")
        resp_done = LLMResponse(content="All done.", tool_calls=[], finish_reason="stop")

        mock_client = MagicMock()
        mock_client.chat = MagicMock(side_effect=[resp_with_tool, resp_done])

        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(llm_client=mock_client, work_dir=tmpdir)
            # Mock executor to return dict
            orch.executor.execute = MagicMock(
                return_value={"success": True, "output": "File written: a.py"}
            )
            result = orch._run_stage_with_tools(
                system_prompt="test", user_prompt="test", temperature=0.3,
            )

        # Check the tool message that was sent in the 2nd chat() call
        second_call_messages = mock_client.chat.call_args_list[1][1].get(
            "messages", mock_client.chat.call_args_list[1][0][0]
            if mock_client.chat.call_args_list[1][0] else []
        )
        tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        # Content must be clean string, NOT the dict repr
        assert tool_msgs[0]["content"] == "File written: a.py"
        assert "success" not in tool_msgs[0]["content"]


# ===========================================================================
# Pipeline --full flag and FULL_STAGES
# ===========================================================================

class TestPipelineFullFlag:
    """Tests for the --full pipeline flag and FULL_STAGES stage list."""

    def test_stages_all_has_eight(self):
        from zhushou.pipeline.stages import ALL_STAGES
        assert len(ALL_STAGES) == 8

    def test_stages_full_has_ten(self):
        from zhushou.pipeline.stages import FULL_STAGES
        assert len(FULL_STAGES) == 10

    def test_full_stages_starts_with_all_stages(self):
        from zhushou.pipeline.stages import ALL_STAGES, FULL_STAGES
        for i, stage in enumerate(ALL_STAGES):
            assert FULL_STAGES[i].name == stage.name

    def test_full_stages_extra_names(self):
        from zhushou.pipeline.stages import FULL_STAGES
        assert FULL_STAGES[8].name == "Documentation"
        assert FULL_STAGES[9].name == "Packaging"

    def test_pipeline_help_has_full_flag(self):
        r = subprocess.run(
            [sys.executable, "-m", "zhushou", "pipeline", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0
        assert "--full" in r.stdout

    def test_pipeline_full_flag_parses(self):
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "test request", "--full"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.full is True

    def test_pipeline_without_full_defaults_false(self):
        with patch("zhushou.cli._cmd_pipeline") as mock:
            from zhushou.cli import main
            main(["pipeline", "test request"])
            mock.assert_called_once()
            args = mock.call_args[0][0]
            assert args.full is False

    def test_run_pipeline_accepts_full_param(self):
        import inspect
        from zhushou.api import run_pipeline
        assert "full" in inspect.signature(run_pipeline).parameters

    def test_build_user_prompt_stage8(self):
        from zhushou.pipeline.stages import build_user_prompt
        ctx = {"requirements": "req", "architecture": "arch",
               "implementation": "impl"}
        prompt = build_user_prompt(8, "test project", ctx)
        assert "README.md" in prompt
        assert "README_CN.md" in prompt

    def test_build_user_prompt_stage9(self):
        from zhushou.pipeline.stages import build_user_prompt
        ctx = {"requirements": "req", "architecture": "arch",
               "implementation": "impl"}
        prompt = build_user_prompt(9, "test project", ctx)
        assert "pyproject.toml" in prompt
        assert "upload_pypi" in prompt


# ===========================================================================
# Python file validation on write_file / edit_file
# ===========================================================================

class TestWriteFileValidation:
    """Tests for automatic Python file validation in write_file and edit_file."""

    def test_valid_python_no_warnings(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "good.py",
            "content": "def greet(name):\n    return f'Hello, {name}!'\n",
        })
        assert result["success"] is True
        assert "WARNING" not in result["output"]
        assert "File written: good.py" in result["output"]

    def test_syntax_error_detected(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "bad.py",
            "content": "def foo(:\n    pass\n",
        })
        assert result["success"] is True  # file IS written
        assert "SYNTAX ERROR" in result["output"]
        assert "fix them NOW" in result["output"]

    def test_stub_function_detected(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "stub.py",
            "content": "def check_winner(board, player):\n    pass\n",
        })
        assert result["success"] is True
        assert "STUB" in result["output"]
        assert "check_winner" in result["output"]
        assert "write real implementation" in result["output"]

    def test_docstring_plus_pass_detected(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "docstub.py",
            "content": (
                "def process(data):\n"
                '    """Process the data."""\n'
                "    pass\n"
            ),
        })
        assert result["success"] is True
        assert "STUB" in result["output"]
        assert "process" in result["output"]

    def test_real_function_no_warning(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "real.py",
            "content": (
                "def add(a, b):\n"
                "    result = a + b\n"
                "    return result\n"
            ),
        })
        assert result["success"] is True
        assert "WARNING" not in result["output"]

    def test_non_python_file_no_validation(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "readme.md",
            "content": "# Hello\nsome content\n",
        })
        assert result["success"] is True
        assert "WARNING" not in result["output"]

    def test_multiple_stubs_all_reported(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_write_file
        result = _handle_write_file(str(tmp_path), {
            "path": "multi.py",
            "content": (
                "def foo():\n    pass\n\n"
                "def bar():\n    pass\n\n"
                "def baz():\n    pass\n"
            ),
        })
        assert result["success"] is True
        assert result["output"].count("STUB") == 3
        assert "foo" in result["output"]
        assert "bar" in result["output"]
        assert "baz" in result["output"]

    def test_edit_file_validates_python(self, tmp_path):
        from zhushou.executor.builtin_tools import (
            _handle_write_file, _handle_edit_file,
        )
        # Write a valid file first
        _handle_write_file(str(tmp_path), {
            "path": "edit_me.py",
            "content": "def greet():\n    return 'hi'\n",
        })
        # Edit to introduce a stub
        result = _handle_edit_file(str(tmp_path), {
            "path": "edit_me.py",
            "old_text": "    return 'hi'",
            "new_text": "    pass",
        })
        assert result["success"] is True
        assert "STUB" in result["output"]

    def test_validate_python_file_directly(self):
        """Test _validate_python_file function independently."""
        import tempfile
        from zhushou.executor.builtin_tools import _validate_python_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(:\n    pass\n")
            f.flush()
            warnings = _validate_python_file(f.name)
            assert any("SYNTAX ERROR" in w for w in warnings)
            os.unlink(f.name)

    def test_validate_clean_file(self):
        """Clean files produce no warnings."""
        import tempfile
        from zhushou.executor.builtin_tools import _validate_python_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def add(a, b):\n    return a + b\n")
            f.flush()
            warnings = _validate_python_file(f.name)
            assert warnings == []
            os.unlink(f.name)


# ===========================================================================
# scaffold_project tool
# ===========================================================================

class TestScaffoldProject:
    """Tests for the scaffold_project built-in tool."""

    def test_scaffold_creates_package_dir(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "calculator",
            "description": "A simple calculator",
        })
        assert result["success"] is True
        assert (tmp_path / "calculator").is_dir()

    def test_scaffold_creates_all_package_files(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "calculator",
            "description": "A simple calculator",
        })
        expected = ["__init__.py", "__main__.py", "api.py", "cli.py", "tools.py"]
        for f in expected:
            assert (tmp_path / "calculator" / f).is_file(), f"Missing {f}"

    def test_scaffold_creates_tests_dir(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "calculator",
            "description": "A simple calculator",
        })
        assert (tmp_path / "tests" / "__init__.py").is_file()
        assert (tmp_path / "tests" / "conftest.py").is_file()

    def test_scaffold_creates_docs_dir(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "calculator",
            "description": "A simple calculator",
        })
        assert (tmp_path / "docs").is_dir()

    def test_scaffold_substitutes_package_name(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "My application",
        })
        init_content = (tmp_path / "myapp" / "__init__.py").read_text()
        assert "myapp" in init_content
        assert "{{package_name}}" not in init_content

    def test_scaffold_substitutes_description(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "My cool application",
        })
        init_content = (tmp_path / "myapp" / "__init__.py").read_text()
        assert "My cool application" in init_content
        cli_content = (tmp_path / "myapp" / "cli.py").read_text()
        assert "My cool application" in cli_content

    def test_scaffold_cli_has_standard_flags(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        cli_content = (tmp_path / "myapp" / "cli.py").read_text()
        assert "--version" in cli_content
        assert "--verbose" in cli_content
        assert "--json" in cli_content
        assert "--quiet" in cli_content
        assert "--output" in cli_content

    def test_scaffold_api_has_toolresult(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        api_content = (tmp_path / "myapp" / "api.py").read_text()
        assert "class ToolResult" in api_content
        assert "def to_dict" in api_content
        assert "success" in api_content

    def test_scaffold_tools_has_dispatch(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        tools_content = (tmp_path / "myapp" / "tools.py").read_text()
        assert "def dispatch" in tools_content
        assert "TOOLS" in tools_content

    def test_scaffold_conftest_has_sys_path(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        conftest_content = (tmp_path / "tests" / "conftest.py").read_text()
        assert "sys.path" in conftest_content

    def test_scaffold_missing_package_name(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "description": "Test app",
        })
        assert result["success"] is False
        assert "package_name" in result["output"]

    def test_scaffold_missing_description(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
        })
        assert result["success"] is False
        assert "description" in result["output"]

    def test_scaffold_invalid_package_name(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "Invalid-Name",
            "description": "Bad name test",
        })
        assert result["success"] is False
        assert "Invalid" in result["output"]

    def test_scaffold_output_lists_files(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        assert result["success"] is True
        assert "myapp/__init__.py" in result["output"]
        assert "myapp/api.py" in result["output"]
        assert "myapp/cli.py" in result["output"]
        assert "myapp/tools.py" in result["output"]
        assert "tests/conftest.py" in result["output"]

    def test_scaffold_output_has_next_steps(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        assert result["success"] is True
        assert "core.py" in result["output"]
        assert "Next steps" in result["output"]

    def test_scaffold_in_all_tools_registry(self):
        from zhushou.executor.builtin_tools import ALL_TOOLS, TOOL_HANDLERS
        names = {t["function"]["name"] for t in ALL_TOOLS}
        assert "scaffold_project" in names
        assert "scaffold_project" in TOOL_HANDLERS

    def test_scaffold_schema_structure(self):
        from zhushou.executor.builtin_tools import SCAFFOLD_PROJECT_SCHEMA
        func = SCAFFOLD_PROJECT_SCHEMA["function"]
        assert func["name"] == "scaffold_project"
        assert "package_name" in func["parameters"]["properties"]
        assert "description" in func["parameters"]["properties"]
        assert set(func["parameters"]["required"]) == {"package_name", "description"}

    def test_scaffold_main_py_is_static(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        main_content = (tmp_path / "myapp" / "__main__.py").read_text()
        assert "from .cli import main" in main_content
        assert "main()" in main_content

    def test_scaffold_init_exports_toolresult(self, tmp_path):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        _handle_scaffold_project(str(tmp_path), {
            "package_name": "myapp",
            "description": "Test app",
        })
        init_content = (tmp_path / "myapp" / "__init__.py").read_text()
        assert "ToolResult" in init_content
        assert "__version__" in init_content


# ===========================================================================
# scaffold_project — runtime execution tests
# ===========================================================================

class TestScaffoldProjectRuntime:
    """Actually run the generated scaffold code via subprocess to verify
    it produces a working Python package, not just syntactically plausible files."""

    def _scaffold(self, tmp_path, pkg="myapp", desc="Test application"):
        from zhushou.executor.builtin_tools import _handle_scaffold_project
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": pkg,
            "description": desc,
        })
        assert result["success"] is True
        return result

    def _run(self, tmp_path, *args, **kwargs):
        return subprocess.run(
            [sys.executable] + list(args),
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=30,
            **kwargs,
        )

    def test_runtime_import_package(self, tmp_path):
        """Scaffold generates a package that can actually be imported."""
        self._scaffold(tmp_path)
        r = self._run(tmp_path, "-c", "import myapp")
        assert r.returncode == 0, f"Import failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"

    def test_runtime_import_toolresult(self, tmp_path):
        """ToolResult dataclass can be instantiated and to_dict() works."""
        self._scaffold(tmp_path)
        code = (
            "from myapp.api import ToolResult; "
            "r = ToolResult(success=True, data=42); "
            "d = r.to_dict(); "
            "assert d['success'] is True; "
            "assert d['data'] == 42; "
            "assert d['error'] is None; "
            "assert isinstance(d['metadata'], dict); "
            "print('ToolResult OK')"
        )
        r = self._run(tmp_path, "-c", code)
        assert r.returncode == 0, f"ToolResult test failed:\n{r.stderr}"
        assert "ToolResult OK" in r.stdout

    def test_runtime_cli_help(self, tmp_path):
        """Generated CLI --help shows all 5 standard flags."""
        self._scaffold(tmp_path)
        r = self._run(tmp_path, "-m", "myapp", "--help")
        assert r.returncode == 0, f"CLI --help failed:\n{r.stderr}"
        for flag in ["--version", "--verbose", "--json", "--quiet", "--output"]:
            assert flag in r.stdout, f"Missing {flag} in --help output"

    def test_runtime_cli_version(self, tmp_path):
        """Generated CLI -V prints version 0.1.0."""
        self._scaffold(tmp_path)
        r = self._run(tmp_path, "-m", "myapp", "-V")
        assert r.returncode == 0, f"CLI -V failed:\n{r.stderr}"
        assert "0.1.0" in r.stdout

    def test_runtime_import_tools(self, tmp_path):
        """tools.py TOOLS list and dispatch() function are importable."""
        self._scaffold(tmp_path)
        code = (
            "from myapp.tools import TOOLS, dispatch; "
            "assert isinstance(TOOLS, list); "
            "assert callable(dispatch); "
            "print('tools OK')"
        )
        r = self._run(tmp_path, "-c", code)
        assert r.returncode == 0, f"Tools import failed:\n{r.stderr}"
        assert "tools OK" in r.stdout

    def test_runtime_dispatch_unknown_raises(self, tmp_path):
        """dispatch() raises ValueError for unknown tool names."""
        self._scaffold(tmp_path)
        script = tmp_path / "_test_dispatch.py"
        script.write_text(
            "from myapp.tools import dispatch\n"
            "try:\n"
            "    dispatch('nonexistent_tool', {})\n"
            "    raise AssertionError('Should have raised ValueError')\n"
            "except ValueError as e:\n"
            "    assert 'Unknown tool' in str(e)\n"
            "    print('ValueError OK')\n"
        )
        r = self._run(tmp_path, str(script))
        assert r.returncode == 0, f"Dispatch test failed:\n{r.stderr}"
        assert "ValueError OK" in r.stdout

    def test_runtime_init_exports(self, tmp_path):
        """__init__.py exports __version__ and ToolResult correctly."""
        self._scaffold(tmp_path)
        code = (
            "from myapp import __version__, ToolResult; "
            "assert __version__ == '0.1.0'; "
            "assert ToolResult is not None; "
            "r = ToolResult(success=False, error='test'); "
            "assert r.success is False; "
            "assert r.error == 'test'; "
            "print('init exports OK')"
        )
        r = self._run(tmp_path, "-c", code)
        assert r.returncode == 0, f"Init exports failed:\n{r.stderr}"
        assert "init exports OK" in r.stdout

    def test_runtime_conftest_importable(self, tmp_path):
        """tests/conftest.py can be executed without errors."""
        self._scaffold(tmp_path)
        r = self._run(tmp_path, str(tmp_path / "tests" / "conftest.py"))
        assert r.returncode == 0, f"conftest.py failed:\n{r.stderr}"

    def test_runtime_all_py_syntax_valid(self, tmp_path):
        """Every generated .py file passes py_compile."""
        self._scaffold(tmp_path)
        py_files = [
            f"myapp/{f}" for f in
            ["__init__.py", "__main__.py", "api.py", "cli.py", "tools.py"]
        ] + ["tests/conftest.py"]
        for rel_path in py_files:
            abs_path = str(tmp_path / rel_path)
            r = self._run(tmp_path, "-m", "py_compile", abs_path)
            assert r.returncode == 0, (
                f"py_compile failed for {rel_path}:\n{r.stderr}"
            )


# ===========================================================================
# scaffold_project — end-to-end: scaffold + implement + run
# ===========================================================================

class TestScaffoldEndToEnd:
    """Simulate the full Stage 2 -> Stage 4 workflow: scaffold a project,
    add real implementation code (as the LLM would), then verify the
    complete package works — API, CLI, tools dispatch, and pytest."""

    @pytest.fixture(autouse=True)
    def _setup_calculator(self, tmp_path):
        """Scaffold 'calculator' and add real implementation code."""
        from zhushou.executor.builtin_tools import _handle_scaffold_project

        # ── Stage 2: scaffold ──
        result = _handle_scaffold_project(str(tmp_path), {
            "package_name": "calculator",
            "description": "A simple calculator",
        })
        assert result["success"] is True

        # ── Stage 4: add real implementation ──

        # 1. core.py — new file
        (tmp_path / "calculator" / "core.py").write_text(
            '"""Calculator core logic."""\n'
            "\n"
            "\n"
            "def add(a: float, b: float) -> float:\n"
            "    return a + b\n"
            "\n"
            "\n"
            "def subtract(a: float, b: float) -> float:\n"
            "    return a - b\n"
            "\n"
            "\n"
            "def multiply(a: float, b: float) -> float:\n"
            "    return a * b\n"
            "\n"
            "\n"
            "def divide(a: float, b: float) -> float:\n"
            "    if b == 0:\n"
            '        raise ValueError("Cannot divide by zero")\n'
            "    return a / b\n"
        )

        # 2. api.py — replace TODO block with real API functions
        api_path = tmp_path / "calculator" / "api.py"
        api_content = api_path.read_text()
        api_content = api_content.replace(
            "# ---------------------------------------------------------------------------\n"
            "# Add your API wrapper functions below.\n"
            "#\n"
            "# Each function should:\n"
            "#   1. Accept clear parameters\n"
            "#   2. Call core logic from core.py\n"
            "#   3. Return ToolResult(success=True, data=...) on success\n"
            "#   4. Catch exceptions and return ToolResult(success=False, error=str(e))\n"
            "#\n"
            "# Example:\n"
            "#\n"
            "#   def do_something(input_text: str) -> ToolResult:\n"
            "#       try:\n"
            "#           from .core import process\n"
            "#           result = process(input_text)\n"
            "#           return ToolResult(success=True, data=result)\n"
            "#       except Exception as e:\n"
            "#           return ToolResult(success=False, error=str(e))\n"
            "# ---------------------------------------------------------------------------\n",
            "def calculate(operation: str, a: float, b: float) -> ToolResult:\n"
            '    """Perform a calculation."""\n'
            "    try:\n"
            "        from .core import add, subtract, multiply, divide\n"
            "        ops = {'add': add, 'subtract': subtract,\n"
            "               'multiply': multiply, 'divide': divide}\n"
            "        if operation not in ops:\n"
            '            return ToolResult(success=False, error=f"Unknown operation: {operation}")\n'
            "        result = ops[operation](a, b)\n"
            "        return ToolResult(success=True, data=result,\n"
            "                         metadata={'operation': operation})\n"
            "    except Exception as e:\n"
            "        return ToolResult(success=False, error=str(e))\n",
        )
        api_path.write_text(api_content)

        # 3. cli.py — add positional args and dispatch logic
        cli_path = tmp_path / "calculator" / "cli.py"
        cli_content = cli_path.read_text()
        # Replace project-specific args TODO
        cli_content = cli_content.replace(
            "    # ── Project-specific arguments ────────────────────────────────\n"
            "    # TODO: Add your project-specific arguments here.\n"
            "    # Example:\n"
            "    #   parser.add_argument(\"input\", help=\"Input file or value\")\n"
            '    #   parser.add_argument("--format", choices=["csv","json"], default="json")\n',
            '    parser.add_argument("operation", choices=["add", "subtract", "multiply", "divide"],\n'
            '                        help="Math operation to perform")\n'
            '    parser.add_argument("a", type=float, help="First number")\n'
            '    parser.add_argument("b", type=float, help="Second number")\n',
        )
        # Replace dispatch TODO
        cli_content = cli_content.replace(
            "    # ── Dispatch ──────────────────────────────────────────────────\n"
            "    # TODO: Call your core logic or API functions here.\n"
            "    # Example:\n"
            "    #   from .api import do_something\n"
            "    #   result = do_something(args.input)\n"
            "    #   if args.json_output:\n"
            "    #       print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))\n"
            "    #   elif result.success:\n"
            "    #       print(result.data)\n"
            "    #   else:\n"
            '    #       print(f"Error: {result.error}", file=sys.stderr)\n'
            "    #       sys.exit(1)\n"
            "\n"
            "    parser.print_help()\n",
            "    from .api import calculate\n"
            "    result = calculate(args.operation, args.a, args.b)\n"
            "    if args.json_output:\n"
            "        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))\n"
            "    elif result.success:\n"
            "        print(result.data)\n"
            "    else:\n"
            '        print(f"Error: {result.error}", file=sys.stderr)\n'
            "        sys.exit(1)\n",
        )
        cli_path.write_text(cli_content)

        # 4. tools.py — add tool schema and dispatch case
        tools_path = tmp_path / "calculator" / "tools.py"
        tools_content = tools_path.read_text()
        tools_content = tools_content.replace(
            "TOOLS: list[dict[str, Any]] = [\n"
            "    # TODO: Add your tool definitions here.\n"
            "]\n",
            "TOOLS: list[dict[str, Any]] = [\n"
            "    {\n"
            '        "type": "function",\n'
            '        "function": {\n'
            '            "name": "calculator_calculate",\n'
            '            "description": "Perform a math calculation.",\n'
            '            "parameters": {\n'
            '                "type": "object",\n'
            '                "properties": {\n'
            '                    "operation": {\n'
            '                        "type": "string",\n'
            '                        "description": "Math operation.",\n'
            '                        "enum": ["add", "subtract", "multiply", "divide"],\n'
            "                    },\n"
            '                    "a": {"type": "number", "description": "First number."},\n'
            '                    "b": {"type": "number", "description": "Second number."},\n'
            "                },\n"
            '                "required": ["operation", "a", "b"],\n'
            "            },\n"
            "        },\n"
            "    },\n"
            "]\n",
        )
        tools_content = tools_content.replace(
            "    # TODO: Add dispatch cases here.  Example:\n"
            "    #\n"
            '    #   if name == "calculator_do_something":\n'
            "    #       from .api import do_something\n"
            "    #       return do_something(**arguments).to_dict()\n",
            '    if name == "calculator_calculate":\n'
            "        from .api import calculate\n"
            "        return calculate(**arguments).to_dict()\n",
        )
        tools_path.write_text(tools_content)

        # 5. __init__.py — export calculate
        init_path = tmp_path / "calculator" / "__init__.py"
        init_content = init_path.read_text()
        init_content = init_content.replace(
            "from .api import ToolResult  # noqa: F401\n"
            "\n"
            '__all__ = ["__version__", "ToolResult"]\n',
            "from .api import ToolResult, calculate  # noqa: F401\n"
            "\n"
            '__all__ = ["__version__", "ToolResult", "calculate"]\n',
        )
        init_path.write_text(init_content)

        # 6. tests/test_calculator.py — a real test file
        (tmp_path / "tests" / "test_calculator.py").write_text(
            "from calculator.api import ToolResult, calculate\n"
            "\n"
            "\n"
            "class TestCalculate:\n"
            "    def test_add(self):\n"
            "        r = calculate('add', 2, 3)\n"
            "        assert r.success is True\n"
            "        assert r.data == 5\n"
            "\n"
            "    def test_subtract(self):\n"
            "        r = calculate('subtract', 10, 4)\n"
            "        assert r.success is True\n"
            "        assert r.data == 6\n"
            "\n"
            "    def test_multiply(self):\n"
            "        r = calculate('multiply', 3, 7)\n"
            "        assert r.success is True\n"
            "        assert r.data == 21\n"
            "\n"
            "    def test_divide(self):\n"
            "        r = calculate('divide', 10, 2)\n"
            "        assert r.success is True\n"
            "        assert r.data == 5.0\n"
            "\n"
            "    def test_divide_by_zero(self):\n"
            "        r = calculate('divide', 1, 0)\n"
            "        assert r.success is False\n"
            "        assert 'zero' in r.error.lower()\n"
            "\n"
            "    def test_unknown_operation(self):\n"
            "        r = calculate('modulus', 5, 3)\n"
            "        assert r.success is False\n"
            "\n"
            "    def test_returns_toolresult(self):\n"
            "        r = calculate('add', 1, 1)\n"
            "        assert isinstance(r, ToolResult)\n"
            "        d = r.to_dict()\n"
            "        assert 'success' in d\n"
            "        assert 'data' in d\n"
            "        assert 'error' in d\n"
            "        assert 'metadata' in d\n"
        )

        self.tmp_path = tmp_path

    def _run(self, *args):
        return subprocess.run(
            [sys.executable] + list(args),
            cwd=str(self.tmp_path),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_e2e_api_function(self):
        """API function calculate() returns correct ToolResult."""
        code = (
            "from calculator.api import calculate; "
            "r = calculate('add', 2, 3); "
            "assert r.success is True; "
            "assert r.data == 5; "
            "assert r.metadata == {'operation': 'add'}; "
            "r2 = calculate('divide', 1, 0); "
            "assert r2.success is False; "
            "assert 'zero' in r2.error.lower(); "
            "print('API OK')"
        )
        r = self._run("-c", code)
        assert r.returncode == 0, f"API test failed:\n{r.stderr}"
        assert "API OK" in r.stdout

    def test_e2e_cli_execution(self):
        """CLI runs and prints result to stdout."""
        r = self._run("-m", "calculator", "add", "2", "3")
        assert r.returncode == 0, f"CLI failed:\n{r.stderr}"
        assert "5" in r.stdout.strip()

    def test_e2e_cli_json_output(self):
        """CLI --json flag produces valid JSON with correct structure."""
        r = self._run("-m", "calculator", "add", "10", "20", "--json")
        assert r.returncode == 0, f"CLI --json failed:\n{r.stderr}"
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert data["data"] == 30
        assert data["error"] is None
        assert data["metadata"]["operation"] == "add"

    def test_e2e_tool_dispatch(self):
        """tools.dispatch() routes to API and returns dict."""
        code = (
            "from calculator.tools import dispatch; "
            "r = dispatch('calculator_calculate', "
            "{'operation': 'multiply', 'a': 4, 'b': 5}); "
            "assert isinstance(r, dict); "
            "assert r['success'] is True; "
            "assert r['data'] == 20; "
            "print('dispatch OK')"
        )
        r = self._run("-c", code)
        assert r.returncode == 0, f"Dispatch test failed:\n{r.stderr}"
        assert "dispatch OK" in r.stdout

    def test_e2e_tool_dispatch_json_args(self):
        """tools.dispatch() accepts JSON string arguments."""
        code = (
            "import json; "
            "from calculator.tools import dispatch; "
            "args = json.dumps({'operation': 'subtract', 'a': 100, 'b': 37}); "
            "r = dispatch('calculator_calculate', args); "
            "assert r['success'] is True; "
            "assert r['data'] == 63; "
            "print('JSON args OK')"
        )
        r = self._run("-c", code)
        assert r.returncode == 0, f"JSON args dispatch failed:\n{r.stderr}"
        assert "JSON args OK" in r.stdout

    def test_e2e_pytest_runs(self):
        """pytest discovers and passes all tests in the generated project."""
        r = self._run("-m", "pytest", "tests/", "-v")
        assert r.returncode == 0, (
            f"pytest failed in generated project:\n"
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )
        # Verify all 7 test cases passed
        assert "7 passed" in r.stdout or "7 passed" in r.stderr


# ===========================================================================
# Pipeline iterative debug loop
# ===========================================================================

class TestPipelineIterativeDebug:
    """Tests for the iterative debug-until-pass loop in PipelineOrchestrator."""

    # ── _tests_passed() static method ──────────────────────────────────

    def test_tests_passed_detects_all_passed(self):
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._tests_passed(
            "====== 5 passed in 0.3s ======"
        ) is True

    def test_tests_passed_detects_failure(self):
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._tests_passed(
            "====== 3 passed, 2 failed in 0.5s ======"
        ) is False

    def test_tests_passed_empty_string(self):
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._tests_passed("") is False

    def test_tests_passed_zero_failed(self):
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._tests_passed(
            "5 passed, 0 failed"
        ) is True

    def test_tests_passed_error_in_output(self):
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._tests_passed(
            "ERROR collecting tests"
        ) is False

    # ── last_test_output capture from tool results ─────────────────────

    def test_last_test_output_init(self):
        """Orchestrator initializes last_test_output as empty."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        class DummyClient:
            pass

        orch = PipelineOrchestrator(
            llm_client=DummyClient(),
            work_dir="/tmp/test_orch",
        )
        assert orch.last_test_output == ""
        assert orch._total_debug_iterations == 0

    def test_max_total_debug_iterations_constant(self):
        """MAX_TOTAL_DEBUG_ITERATIONS is set to 10."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator.MAX_TOTAL_DEBUG_ITERATIONS == 10

    def test_last_test_output_captured_from_tool(self, tmp_path):
        """When run_command executes a pytest command, its output is captured
        in orchestrator.last_test_output."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        pytest_output = "===== 5 passed in 0.3s ====="

        @dataclass
        class ToolCallRequest:
            name: str = "run_command"
            arguments: str = '{"command": "python -m pytest tests/ -v"}'
            id: str = "call_0"

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        call_count = 0

        class MockClient:
            def chat(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="Running tests...",
                        tool_calls=[ToolCallRequest()],
                    )
                return LLMResponse(content="Done", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )

        # Patch executor to return fake pytest output
        original_execute = orch.executor.execute
        def mock_execute(name, args):
            if name == "run_command":
                return {"success": True, "output": pytest_output}
            return original_execute(name, args)
        orch.executor.execute = mock_execute

        orch._run_stage_with_tools(
            system_prompt="test", user_prompt="test", temperature=0.0,
        )
        assert orch.last_test_output == pytest_output

    def test_last_test_output_not_captured_for_non_pytest(self, tmp_path):
        """run_command for non-pytest commands does NOT set last_test_output."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        @dataclass
        class ToolCallRequest:
            name: str = "run_command"
            arguments: str = '{"command": "ls -la"}'
            id: str = "call_0"

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        call_count = 0

        class MockClient:
            def chat(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="Listing...",
                        tool_calls=[ToolCallRequest()],
                    )
                return LLMResponse(content="Done", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )
        original_execute = orch.executor.execute
        def mock_execute(name, args):
            if name == "run_command":
                return {"success": True, "output": "file1.py\nfile2.py"}
            return original_execute(name, args)
        orch.executor.execute = mock_execute

        orch._run_stage_with_tools(
            system_prompt="test", user_prompt="test", temperature=0.0,
        )
        assert orch.last_test_output == ""

    # ── Debug loop behavior ────────────────────────────────────────────

    def test_debug_loop_skips_when_tests_pass(self, tmp_path):
        """Debug loop is skipped entirely if tests already passed."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        class DummyClient:
            pass

        orch = PipelineOrchestrator(
            llm_client=DummyClient(),
            work_dir=str(tmp_path),
        )
        orch.context["test_output"] = "===== 10 passed in 1.0s ====="
        orch._run_debug_loop("test request", 6, 7)
        assert orch.stats["tests_passed"] == "All passed"
        assert orch._total_debug_iterations == 0

    def test_debug_loop_stops_on_pass(self, tmp_path):
        """Debug loop stops when tests pass on attempt 2."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        @dataclass
        class ToolCallRequest:
            name: str = "run_command"
            arguments: str = '{"command": "python -m pytest tests/ -v"}'
            id: str = "call_0"

        debug_call_count = 0

        class MockClient:
            def chat(self, **kwargs):
                nonlocal debug_call_count
                debug_call_count += 1
                # Odd calls: return tool call; Even calls: return done
                if debug_call_count % 2 == 1:
                    return LLMResponse(
                        content="Fixing...",
                        tool_calls=[ToolCallRequest()],
                    )
                return LLMResponse(content="Done", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )
        orch.context["test_output"] = "2 failed"

        attempt_count = [0]
        original_execute = orch.executor.execute
        def mock_execute(name, args):
            if name == "run_command":
                attempt_count[0] += 1
                if attempt_count[0] >= 2:
                    return {"success": True, "output": "5 passed in 0.3s"}
                return {"success": False, "output": "2 failed, 3 passed"}
            return original_execute(name, args)
        orch.executor.execute = mock_execute

        orch._run_debug_loop("test request", 6, 7)
        assert orch.stats["tests_passed"] == "All passed"
        assert orch._total_debug_iterations == 2

    def test_debug_loop_exhausts_retries(self, tmp_path):
        """Debug loop exhausts MAX_DEBUG_RETRIES when tests never pass."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        @dataclass
        class ToolCallRequest:
            name: str = "run_command"
            arguments: str = '{"command": "python -m pytest tests/ -v"}'
            id: str = "call_0"

        call_count = 0

        class MockClient:
            def chat(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 2 == 1:
                    return LLMResponse(
                        tool_calls=[ToolCallRequest()],
                    )
                return LLMResponse(content="Done", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )
        orch.context["test_output"] = "3 failed"

        original_execute = orch.executor.execute
        def mock_execute(name, args):
            if name == "run_command":
                return {"success": False, "output": "3 failed, 2 passed"}
            return original_execute(name, args)
        orch.executor.execute = mock_execute

        orch._run_debug_loop("test request", 6, 7)
        assert orch.stats["tests_passed"] == "Some failures remain"
        assert orch._total_debug_iterations == orch.MAX_DEBUG_RETRIES

    def test_debug_loop_respects_total_budget(self, tmp_path):
        """Debug loop stops when total budget is exhausted even if
        MAX_DEBUG_RETRIES hasn't been reached."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        class MockClient:
            def chat(self, **kwargs):
                return LLMResponse(content="Done", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )
        orch.context["test_output"] = "3 failed"
        # Pre-exhaust the total budget
        orch._total_debug_iterations = orch.MAX_TOTAL_DEBUG_ITERATIONS

        orch._run_debug_loop("test request", 6, 7)
        # Should not have run any attempts
        assert orch._total_debug_iterations == orch.MAX_TOTAL_DEBUG_ITERATIONS

    # ── Verification -> Debug feedback ─────────────────────────────────

    def test_verify_debug_loop_passes_first_time(self, tmp_path):
        """If verification finds all tests pass, no re-debug needed."""
        from dataclasses import dataclass, field
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        from zhushou.pipeline.stages import ALL_STAGES

        @dataclass
        class LLMResponse:
            content: str = ""
            tool_calls: list = field(default_factory=list)

        @dataclass
        class ToolCallRequest:
            name: str = "run_command"
            arguments: str = '{"command": "python -m pytest tests/ -v"}'
            id: str = "call_0"

        call_count = 0

        class MockClient:
            def chat(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return LLMResponse(
                        content="Verifying...",
                        tool_calls=[ToolCallRequest()],
                    )
                return LLMResponse(content="All good", tool_calls=[])

        orch = PipelineOrchestrator(
            llm_client=MockClient(),
            work_dir=str(tmp_path),
        )
        orch.context["test_output"] = "5 passed"

        original_execute = orch.executor.execute
        def mock_execute(name, args):
            if name == "run_command":
                return {"success": True, "output": "10 passed in 1.0s"}
            return original_execute(name, args)
        orch.executor.execute = mock_execute

        verification_stage = ALL_STAGES[6]
        orch._run_verify_debug_loop(
            "test request", verification_stage, 7, 7,
        )
        assert orch.stats["tests_passed"] == "All passed"
        assert orch._total_debug_iterations == 0


# ===========================================================================
# Small model resilience: timeout, retries, per-file implementation
# ===========================================================================

def _parse_cli_args(argv: list[str]) -> "argparse.Namespace":
    """Parse CLI arguments without executing any command.

    Replicates the parser structure from ``zhushou.cli.main`` so that
    tests can verify flag parsing in-process.
    """
    import argparse as _ap

    from zhushou.cli import _make_common_parser

    common = _make_common_parser()
    parser = _ap.ArgumentParser(prog="zhushou", parents=[common])
    subs = parser.add_subparsers(dest="command")

    chat_p = subs.add_parser("chat", parents=[common])
    chat_p.add_argument("message", nargs="?", default="")

    pipe_p = subs.add_parser("pipeline", parents=[common])
    pipe_p.add_argument("request")
    pipe_p.add_argument("--full", action="store_true")

    subs.add_parser("models", parents=[common])
    subs.add_parser("config", parents=[common])

    return parser.parse_args(argv)


class TestSmallModelResilience:
    """Tests for configurable timeout, increased retries, and per-file
    implementation splitting."""

    # ── --timeout CLI flag ─────────────────────────────────────────────

    def test_timeout_cli_flag_exists(self):
        """--timeout flag appears in pipeline help output."""
        r = subprocess.run(
            [sys.executable, "-m", "zhushou", "pipeline", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert "--timeout" in r.stdout

    def test_timeout_cli_flag_parses(self):
        """--timeout 600 is parsed correctly."""
        args = _parse_cli_args(["pipeline", "test", "--timeout", "600"])
        assert args.timeout == 600

    def test_timeout_default_300(self):
        """Default timeout is 300 when not specified."""
        args = _parse_cli_args(["pipeline", "test"])
        assert args.timeout == 300

    def test_timeout_on_all_subcommands(self):
        """--timeout flag is available on chat and pipeline subcommands."""
        for subcmd in ["chat", "pipeline"]:
            r = subprocess.run(
                [sys.executable, "-m", "zhushou", subcmd, "--help"],
                capture_output=True, text=True, timeout=15,
            )
            assert "--timeout" in r.stdout, f"--timeout missing from {subcmd} help"

    # ── API and client timeout ─────────────────────────────────────────

    def test_run_pipeline_accepts_timeout(self):
        """run_pipeline() accepts timeout parameter."""
        import inspect
        from zhushou.api import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "timeout" in sig.parameters
        assert sig.parameters["timeout"].default == 300

    def test_chat_accepts_timeout(self):
        """chat() accepts timeout parameter."""
        import inspect
        from zhushou.api import chat
        sig = inspect.signature(chat)
        assert "timeout" in sig.parameters
        assert sig.parameters["timeout"].default == 300

    def test_ollama_client_accepts_timeout(self):
        """OllamaLLMClient accepts timeout param and uses it."""
        from zhushou.llm.ollama_client import OllamaLLMClient
        client = OllamaLLMClient(timeout=600)
        assert client._timeout.read == 600.0
        assert client._timeout.connect == 10.0

    def test_ollama_default_timeout(self):
        """Default OllamaLLMClient uses 300s read timeout."""
        from zhushou.llm.ollama_client import OllamaLLMClient
        client = OllamaLLMClient()
        assert client._timeout.read == 300.0

    # ── Retries ────────────────────────────────────────────────────────

    def test_retry_count_increased(self):
        """_MAX_RETRIES is now 5."""
        from zhushou.llm.ollama_client import _MAX_RETRIES
        assert _MAX_RETRIES == 5

    def test_retry_backoff_base_increased(self):
        """_RETRY_BACKOFF_BASE is now 3.0."""
        from zhushou.llm.ollama_client import _RETRY_BACKOFF_BASE
        assert _RETRY_BACKOFF_BASE == 3.0

    # ── Per-file implementation ────────────────────────────────────────

    def test_parse_task_files_file_colon(self):
        """_parse_task_files extracts '- File: path.py' patterns."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        md = (
            "## Task 1\n"
            "- File: calculator/core.py\n"
            "- Description: Core logic\n\n"
            "## Task 2\n"
            "- File: calculator/api.py\n"
            "- Description: API\n"
        )
        files = PipelineOrchestrator._parse_task_files(md)
        assert "calculator/core.py" in files
        assert "calculator/api.py" in files

    def test_parse_task_files_heading(self):
        """_parse_task_files extracts '## Task N: path.py' patterns."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        md = (
            "## Task 1: calculator/core.py\n"
            "Implement the core logic.\n\n"
            "## Task 2: calculator/api.py\n"
            "Implement the API.\n"
        )
        files = PipelineOrchestrator._parse_task_files(md)
        assert "calculator/core.py" in files
        assert "calculator/api.py" in files

    def test_parse_task_files_numbered_list(self):
        """_parse_task_files extracts '1. path.py' patterns."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        md = (
            "1. calculator/core.py\n"
            "2. calculator/api.py\n"
            "3. calculator/cli.py\n"
        )
        files = PipelineOrchestrator._parse_task_files(md)
        assert len(files) == 3
        assert "calculator/cli.py" in files

    def test_parse_task_files_deduplicates(self):
        """_parse_task_files returns unique paths even if repeated."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        md = (
            "- File: calculator/core.py\n"
            "## Task 1: calculator/core.py\n"
            "1. calculator/core.py\n"
        )
        files = PipelineOrchestrator._parse_task_files(md)
        assert files.count("calculator/core.py") == 1

    def test_parse_task_files_empty_returns_empty(self):
        """_parse_task_files returns empty list for non-matching input."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        files = PipelineOrchestrator._parse_task_files("No files here.")
        assert files == []

    def test_build_file_prompt_focused(self):
        """_build_file_prompt mentions only the target file."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        prompt = PipelineOrchestrator._build_file_prompt(
            "calculator/core.py",
            "Build a calculator",
            "Architecture here",
            "Implement add, subtract",
        )
        assert "calculator/core.py" in prompt
        assert "ONLY" in prompt
        assert "NEW file" in prompt  # core.py is not scaffolded

    def test_build_file_prompt_scaffolded(self):
        """_build_file_prompt detects scaffolded files."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        prompt = PipelineOrchestrator._build_file_prompt(
            "calculator/api.py",
            "Build a calculator",
            "Architecture here",
            "Add API functions",
        )
        assert "scaffolded" in prompt.lower()
        assert "read_file" in prompt
        assert "edit_file" in prompt

    def test_extract_task_for_file(self):
        """_extract_task_for_file pulls the right section."""
        from zhushou.pipeline.orchestrator import PipelineOrchestrator
        md = (
            "## Task 1: calculator/core.py\n"
            "Implement add and subtract functions.\n"
            "Key components: add(), subtract()\n\n"
            "## Task 2: calculator/api.py\n"
            "Add API wrappers.\n"
        )
        task = PipelineOrchestrator._extract_task_for_file(
            "calculator/core.py", md,
        )
        assert "add" in task.lower()
        assert "subtract" in task.lower()


# ===========================================================================
# Knowledge Base — Config
# ===========================================================================

class TestKBConfig:
    def test_defaults(self):
        from zhushou.knowledge.kb_config import KBConfig
        cfg = KBConfig()
        assert cfg.chunk_size == 800
        assert cfg.chunk_overlap == 150
        assert cfg.min_chunk_size == 50
        assert cfg.top_k == 10
        assert cfg.embedding_model == "nomic-embed-text"
        assert cfg.ollama_url == "http://localhost:11434"
        assert "kb" in cfg.docs_dir
        assert "kb" in cfg.chroma_dir

    def test_docs_path_property(self):
        from zhushou.knowledge.kb_config import KBConfig
        cfg = KBConfig(docs_dir="/tmp/test_docs")
        assert cfg.docs_path == Path("/tmp/test_docs")

    def test_chroma_path_property(self):
        from zhushou.knowledge.kb_config import KBConfig
        cfg = KBConfig(chroma_dir="/tmp/test_chroma")
        assert cfg.chroma_path == Path("/tmp/test_chroma")

    def test_load_nonexistent_returns_defaults(self):
        from zhushou.knowledge.kb_config import load_kb_config
        cfg = load_kb_config("/tmp/nonexistent_zhushou_kb_config.json")
        assert cfg.chunk_size == 800

    def test_save_and_load_roundtrip(self, tmp_path):
        from zhushou.knowledge.kb_config import KBConfig, save_kb_config, load_kb_config
        cfg = KBConfig(chunk_size=500, top_k=5)
        cfg_path = tmp_path / "kb_config.json"
        save_kb_config(cfg, cfg_path)
        loaded = load_kb_config(cfg_path)
        assert loaded.chunk_size == 500
        assert loaded.top_k == 5


# ===========================================================================
# Knowledge Base — Doc Sources
# ===========================================================================

class TestDocSources:
    def test_doc_sources_is_dict(self):
        from zhushou.knowledge.doc_sources import DOC_SOURCES
        assert isinstance(DOC_SOURCES, dict)
        assert len(DOC_SOURCES) >= 9  # 9 required + extras

    def test_required_frameworks_present(self):
        from zhushou.knowledge.doc_sources import DOC_SOURCES
        required = {"numpy", "pandas", "matplotlib", "scipy", "sympy",
                     "torch", "pyside6", "pyqtgraph", "flask"}
        assert required.issubset(set(DOC_SOURCES.keys()))

    def test_each_source_has_name_and_urls(self):
        from zhushou.knowledge.doc_sources import DOC_SOURCES
        for key, info in DOC_SOURCES.items():
            assert "name" in info, f"{key} missing 'name'"
            assert "urls" in info, f"{key} missing 'urls'"
            assert isinstance(info["urls"], list)
            assert len(info["urls"]) > 0, f"{key} has empty urls"

    def test_list_available_sources(self):
        from zhushou.knowledge.doc_sources import list_available_sources
        sources = list_available_sources()
        assert isinstance(sources, list)
        assert len(sources) >= 9
        for s in sources:
            assert "key" in s
            assert "name" in s

    def test_get_source_known(self):
        from zhushou.knowledge.doc_sources import get_source
        src = get_source("numpy")
        assert src is not None
        assert src["name"] == "NumPy"

    def test_get_source_unknown(self):
        from zhushou.knowledge.doc_sources import get_source
        assert get_source("nonexistent_framework_xyz") is None


# ===========================================================================
# Knowledge Base — Cheatsheets
# ===========================================================================

class TestCheatsheets:
    def test_cheatsheets_dict_not_empty(self):
        from zhushou.knowledge.cheatsheets import CHEATSHEETS
        assert isinstance(CHEATSHEETS, dict)
        assert len(CHEATSHEETS) >= 9

    def test_required_cheatsheets_present(self):
        from zhushou.knowledge.cheatsheets import CHEATSHEETS
        required = {"numpy", "pandas", "matplotlib", "scipy", "sympy",
                     "torch", "pyside6", "pyqtgraph", "flask"}
        assert required.issubset(set(CHEATSHEETS.keys()))

    def test_each_cheatsheet_is_nonempty_string(self):
        from zhushou.knowledge.cheatsheets import CHEATSHEETS
        for name, cs in CHEATSHEETS.items():
            assert isinstance(cs, str), f"{name} cheatsheet is not str"
            assert len(cs) > 100, f"{name} cheatsheet too short"

    def test_get_cheatsheet_known(self):
        from zhushou.knowledge.cheatsheets import get_cheatsheet
        cs = get_cheatsheet("numpy")
        assert cs is not None
        assert "numpy" in cs.lower() or "NumPy" in cs

    def test_get_cheatsheet_unknown(self):
        from zhushou.knowledge.cheatsheets import get_cheatsheet
        assert get_cheatsheet("nonexistent_xyz") is None

    def test_list_cheatsheets(self):
        from zhushou.knowledge.cheatsheets import list_cheatsheets
        names = list_cheatsheets()
        assert isinstance(names, list)
        assert "numpy" in names
        assert names == sorted(names)  # sorted


# ===========================================================================
# Knowledge Base — Chunker (from indexer)
# ===========================================================================

class TestChunker:
    def test_chunk_text_basic(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "A" * 2000
        chunks = KBIndexer._chunk_text(text, 800, 150)
        assert len(chunks) >= 2
        # Each chunk is at most 800 chars
        for c in chunks:
            assert len(c) <= 800

    def test_chunk_text_small_input(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "Hello world"
        chunks = KBIndexer._chunk_text(text, 800, 150)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_chunk_text_empty(self):
        from zhushou.knowledge.indexer import KBIndexer
        chunks = KBIndexer._chunk_text("", 800, 150)
        assert chunks == []

    def test_chunk_overlap(self):
        from zhushou.knowledge.indexer import KBIndexer
        # 1600 chars, chunk_size=800, overlap=150
        # First chunk: 0-800, second start: 800-150=650, chunk: 650-1450, third: 1300-1600
        text = "X" * 1600
        chunks = KBIndexer._chunk_text(text, 800, 150)
        assert len(chunks) >= 2


# ===========================================================================
# Knowledge Base — Language Detection (from indexer)
# ===========================================================================

class TestLanguageDetection:
    def test_english_text(self):
        from zhushou.knowledge.indexer import KBIndexer
        assert KBIndexer._detect_language("Hello world, this is English text.") == "en"

    def test_chinese_text(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "这是一段中文文本，用于测试语言检测功能。" * 5
        assert KBIndexer._detect_language(text) == "zh"

    def test_japanese_text(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "これはテストです。" * 5
        assert KBIndexer._detect_language(text) == "ja"

    def test_korean_text(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "한국어테스트입니다。" * 5
        assert KBIndexer._detect_language(text) == "ko"

    def test_russian_text(self):
        from zhushou.knowledge.indexer import KBIndexer
        text = "Это тестовый текст на русском языке для проверки определения языка." * 3
        assert KBIndexer._detect_language(text) == "ru"


# ===========================================================================
# Knowledge Base — Doc Downloader (unit, no network)
# ===========================================================================

class TestDocDownloader:
    def test_download_unknown_source(self):
        from zhushou.knowledge.doc_manager import DocDownloader
        dl = DocDownloader(docs_dir="/tmp/test_kb_docs_nonexistent")
        saved, errors = dl.download_source("nonexistent_framework_xyz")
        assert saved == 0
        assert len(errors) == 1
        assert "Unknown" in errors[0]

    def test_list_downloaded_empty(self, tmp_path):
        from zhushou.knowledge.doc_manager import DocDownloader
        dl = DocDownloader(docs_dir=tmp_path / "empty_docs")
        result = dl.list_downloaded()
        assert result == []

    def test_list_downloaded_with_files(self, tmp_path):
        from zhushou.knowledge.doc_manager import DocDownloader
        docs_dir = tmp_path / "docs"
        numpy_dir = docs_dir / "numpy"
        numpy_dir.mkdir(parents=True)
        (numpy_dir / "intro.md").write_text("# NumPy Intro", encoding="utf-8")
        dl = DocDownloader(docs_dir=docs_dir)
        result = dl.list_downloaded()
        assert len(result) == 1
        assert result[0]["name"] == "numpy"
        assert result[0]["file_count"] == 1

    def test_convert_to_md_rst(self):
        from zhushou.knowledge.doc_manager import DocDownloader
        content, fname = DocDownloader._convert_to_md("rst content", "doc.rst")
        assert fname == "doc.md"

    def test_convert_to_md_python(self):
        from zhushou.knowledge.doc_manager import DocDownloader
        content, fname = DocDownloader._convert_to_md("print('hi')", "example.py")
        assert fname == "example.md"
        assert "```python" in content

    def test_convert_to_md_already_md(self):
        from zhushou.knowledge.doc_manager import DocDownloader
        content, fname = DocDownloader._convert_to_md("# hello", "readme.md")
        assert fname == "readme.md"
        assert content == "# hello"


# ===========================================================================
# Knowledge Base — KBManager (unit, mocked dependencies)
# ===========================================================================

class TestKBManager:
    def test_init_creates_instance(self):
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig
        cfg = KBConfig(docs_dir="/tmp/test_kb_mgr_docs", chroma_dir="/tmp/test_kb_mgr_chroma")
        mgr = KBManager(cfg)
        assert mgr is not None

    def test_list_sources_returns_list(self):
        from zhushou.knowledge.kb_manager import KBManager
        from zhushou.knowledge.kb_config import KBConfig
        cfg = KBConfig(docs_dir="/tmp/test_kb_mgr_docs2", chroma_dir="/tmp/test_kb_mgr_chroma2")
        mgr = KBManager(cfg)
        sources = mgr.list_sources()
        assert isinstance(sources, list)
        assert len(sources) >= 9
        for s in sources:
            assert "key" in s
            assert "name" in s
            assert "cheatsheet" in s

    def test_get_cheatsheet_delegates(self):
        from zhushou.knowledge.kb_manager import KBManager
        cs = KBManager.get_cheatsheet("numpy")
        assert cs is not None
        assert "NumPy" in cs

    def test_get_cheatsheet_unknown(self):
        from zhushou.knowledge.kb_manager import KBManager
        assert KBManager.get_cheatsheet("nonexistent") is None


# ===========================================================================
# Knowledge Base — KB API functions
# ===========================================================================

class TestKBAPI:
    def test_kb_list_returns_toolresult(self):
        from zhushou.api import kb_list, ToolResult
        result = kb_list()
        assert isinstance(result, ToolResult)
        # Should succeed even if nothing downloaded
        assert result.success is True
        assert isinstance(result.data, list)

    def test_kb_search_returns_toolresult(self):
        from zhushou.api import kb_search, ToolResult
        result = kb_search("test query")
        assert isinstance(result, ToolResult)
        # Success is True even with empty results (no indexed data)
        assert result.success is True


# ===========================================================================
# Function Design — FunctionSpec
# ===========================================================================

class TestFunctionSpec:
    def test_creation_defaults(self):
        from zhushou.pipeline.function_design import FunctionSpec
        spec = FunctionSpec(
            name="mod.func",
            file_path="mod.py",
            signature="func(x: int) -> int",
            docstring="Do something",
        )
        assert spec.name == "mod.func"
        assert spec.dependencies == []
        assert spec.is_class_def is False
        assert spec.implemented is False

    def test_creation_with_deps(self):
        from zhushou.pipeline.function_design import FunctionSpec
        spec = FunctionSpec(
            name="mod.bar",
            file_path="mod.py",
            signature="bar() -> None",
            docstring="Bar",
            dependencies=["mod.foo"],
            is_class_def=False,
        )
        assert spec.dependencies == ["mod.foo"]


# ===========================================================================
# Function Design — FunctionRegistry
# ===========================================================================

class TestFunctionRegistry:
    def _make_specs(self):
        from zhushou.pipeline.function_design import FunctionSpec
        return [
            FunctionSpec(
                name="calc.core.add",
                file_path="calc/core.py",
                signature="add(a: float, b: float) -> float",
                docstring="Add two numbers",
            ),
            FunctionSpec(
                name="calc.core.sub",
                file_path="calc/core.py",
                signature="sub(a: float, b: float) -> float",
                docstring="Subtract",
                dependencies=["calc.core.add"],
            ),
            FunctionSpec(
                name="calc.cli.main",
                file_path="calc/cli.py",
                signature="main() -> None",
                docstring="CLI entry",
            ),
        ]

    def test_register_and_count(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        assert len(reg.functions) == 3

    def test_register_deduplicates(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        specs = self._make_specs()
        reg.register(specs)
        reg.register(specs)  # register again
        assert len(reg.functions) == 3

    def test_mark_implemented(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        reg.mark_implemented("calc.core.add")
        assert reg.functions[0].implemented is True
        assert reg.functions[1].implemented is False

    def test_get_unimplemented_for_file(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        reg.mark_implemented("calc.core.add")
        unimpl = reg.get_unimplemented_for_file("calc/core.py")
        assert len(unimpl) == 1
        assert unimpl[0].name == "calc.core.sub"

    def test_get_implemented_signatures(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        reg.mark_implemented("calc.core.add")
        sigs = reg.get_implemented_signatures("calc/core.py")
        assert "add" in sigs
        assert "sub" not in sigs

    def test_get_dependency_signatures(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        deps = reg.get_dependency_signatures("calc.core.sub")
        assert "add" in deps

    def test_all_implemented_false(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        assert reg.all_implemented() is False

    def test_all_implemented_true(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        for s in reg.functions:
            reg.mark_implemented(s.name)
        assert reg.all_implemented() is True

    def test_file_paths(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        paths = reg.file_paths()
        assert paths == ["calc/core.py", "calc/cli.py"]

    def test_summary(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        reg.mark_implemented("calc.core.add")
        assert reg.summary() == "1/3 functions implemented"

    def test_to_dict_and_from_dict(self):
        from zhushou.pipeline.function_design import FunctionRegistry
        reg = FunctionRegistry()
        reg.register(self._make_specs())
        reg.mark_implemented("calc.core.add")
        data = reg.to_dict()
        reg2 = FunctionRegistry.from_dict(data)
        assert len(reg2.functions) == 3
        assert reg2.functions[0].implemented is True
        assert reg2.summary() == reg.summary()


# ===========================================================================
# Function Design — parse_function_design
# ===========================================================================

class TestParseFunctionDesign:
    SAMPLE_MD = """\
## File: calculator/core.py

### class Calculator
- `__init__(self, precision: int = 10)` -- Initialize calculator
- `add(self, a: float, b: float) -> float` -- Add two numbers
  - depends_on: validate_input

### function validate_input
- `validate_input(value: Any) -> float` -- Validate and convert input

## File: calculator/cli.py

### function main
- `main() -> None` -- CLI entry point
"""

    def test_parses_correct_count(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design(self.SAMPLE_MD)
        assert len(specs) == 4

    def test_file_paths(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design(self.SAMPLE_MD)
        paths = {s.file_path for s in specs}
        assert paths == {"calculator/core.py", "calculator/cli.py"}

    def test_class_method_fq_name(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design(self.SAMPLE_MD)
        init_spec = [s for s in specs if "__init__" in s.name][0]
        assert "Calculator" in init_spec.name
        assert init_spec.is_class_def is True

    def test_dependencies_parsed(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design(self.SAMPLE_MD)
        add_spec = [s for s in specs if "add" in s.name][0]
        assert "validate_input" in add_spec.dependencies

    def test_standalone_function(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design(self.SAMPLE_MD)
        main_spec = [s for s in specs if "main" in s.name][0]
        assert main_spec.file_path == "calculator/cli.py"
        assert main_spec.dependencies == []

    def test_empty_input(self):
        from zhushou.pipeline.function_design import parse_function_design
        specs = parse_function_design("")
        assert specs == []


# ===========================================================================
# Pipeline — Stage Indices and Counts
# ===========================================================================

class TestPipelineStageIndices:
    def test_all_stages_count(self):
        from zhushou.pipeline.stages import ALL_STAGES
        assert len(ALL_STAGES) == 8

    def test_full_stages_count(self):
        from zhushou.pipeline.stages import FULL_STAGES
        assert len(FULL_STAGES) == 10

    def test_function_design_is_stage_3(self):
        from zhushou.pipeline.stages import ALL_STAGES
        assert ALL_STAGES[3].name == "Function Design"

    def test_implementation_is_stage_4(self):
        from zhushou.pipeline.stages import ALL_STAGES
        assert ALL_STAGES[4].name == "Implementation"

    def test_stage_names_ordered(self):
        from zhushou.pipeline.stages import ALL_STAGES
        expected_names = [
            "Requirements Analysis",
            "Architecture Design",
            "Task Breakdown",
            "Function Design",
            "Implementation",
            "Testing",
            "Debugging",
            "Verification",
        ]
        actual_names = [s.name for s in ALL_STAGES]
        assert actual_names == expected_names

    def test_full_stages_includes_doc_packaging(self):
        from zhushou.pipeline.stages import FULL_STAGES
        assert FULL_STAGES[8].name == "Documentation"
        assert FULL_STAGES[9].name == "Packaging"


# ===========================================================================
# Pipeline — build_user_prompt
# ===========================================================================

class TestBuildUserPrompt:
    def test_stage_0_contains_request(self):
        from zhushou.pipeline.stages import build_user_prompt
        p = build_user_prompt(0, "Build a calc", {})
        assert "Build a calc" in p

    def test_stage_3_mentions_function_design(self):
        from zhushou.pipeline.stages import build_user_prompt
        p = build_user_prompt(3, "Build a calc", {"architecture": "arch", "tasks": "tasks"})
        assert "function" in p.lower() or "signature" in p.lower()

    def test_stage_4_includes_function_design_context(self):
        from zhushou.pipeline.stages import build_user_prompt
        ctx = {
            "requirements": "req",
            "architecture": "arch",
            "tasks": "tasks",
            "function_design": "## Function Design here",
        }
        p = build_user_prompt(4, "Build a calc", ctx)
        assert "Function Design" in p

    def test_stage_4_includes_kb_context(self):
        from zhushou.pipeline.stages import build_user_prompt
        ctx = {
            "requirements": "req",
            "architecture": "arch",
            "tasks": "tasks",
            "function_design": "design",
            "kb_context": "## NumPy Reference\nnp.array(...)",
        }
        p = build_user_prompt(4, "Build a calc", ctx)
        assert "NumPy Reference" in p

    def test_stage_9_packaging(self):
        from zhushou.pipeline.stages import build_user_prompt
        p = build_user_prompt(9, "Build a calc", {"requirements": "r", "architecture": "a", "implementation": "i"})
        assert "pyproject.toml" in p


# ===========================================================================
# PersistentMemory — Pipeline Session Helpers
# ===========================================================================

class TestPersistentMemoryPipeline:
    def test_set_and_get_pipeline(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set_pipeline("test_session", {"stage": 3, "data": "hello"})
        result = mem.get_pipeline("test_session")
        assert result == {"stage": 3, "data": "hello"}

    def test_get_pipeline_missing(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        assert mem.get_pipeline("nonexistent") is None

    def test_clear_pipeline(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set_pipeline("sess1", {"x": 1})
        mem.clear_pipeline("sess1")
        assert mem.get_pipeline("sess1") is None

    def test_pipeline_key_namespaced(self, tmp_memory_file):
        from zhushou.memory.persistent import PersistentMemory
        mem = PersistentMemory(path=tmp_memory_file)
        mem.set_pipeline("sess1", {"x": 1})
        # The raw key should be namespaced
        assert mem.get("pipeline:sess1") == {"x": 1}
        assert mem.get("sess1") is None


# ===========================================================================
# Knowledge Base — Constants
# ===========================================================================

class TestKBConstants:
    def test_kb_dir_defined(self):
        from zhushou.utils.constants import KB_DIR, KB_DOCS_DIR, KB_CHROMA_DIR, KB_CONFIG_FILE
        assert "kb" in str(KB_DIR)
        assert "docs" in str(KB_DOCS_DIR)
        assert "chroma" in str(KB_CHROMA_DIR)
        assert "config" in str(KB_CONFIG_FILE)

    def test_kb_paths_under_data_dir(self):
        from zhushou.utils.constants import DATA_DIR, KB_DIR
        assert str(KB_DIR).startswith(str(DATA_DIR))


# ===========================================================================
# Knowledge Base — Package Exports
# ===========================================================================

class TestKBPackageExports:
    def test_kb_init_exports(self):
        from zhushou.knowledge import (
            CHEATSHEETS, DOC_SOURCES, KBConfig, KBManager,
            get_cheatsheet, list_cheatsheets, load_kb_config, save_kb_config,
        )
        assert callable(get_cheatsheet)
        assert callable(list_cheatsheets)
        assert callable(load_kb_config)
        assert callable(save_kb_config)
        assert isinstance(CHEATSHEETS, dict)
        assert isinstance(DOC_SOURCES, dict)
