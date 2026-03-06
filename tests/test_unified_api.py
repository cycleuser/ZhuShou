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
        assert len(ALL_TOOLS) == 11

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
        assert len(defs) == 11

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
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert "0.1.0" in r.stdout

    def test_version_long(self):
        """README: zhushou --version"""
        r = self._run_cli("--version")
        assert r.returncode == 0
        assert "0.1.0" in r.stdout

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
