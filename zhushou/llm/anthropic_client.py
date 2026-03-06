"""Anthropic (Claude) LLM client implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from .base import BaseLLMClient, LLMResponse, ModelInfo, TokenUsage, ToolCallRequest

logger = logging.getLogger(__name__)

# Hardcoded model catalogue – Anthropic does not expose a list-models endpoint.
_CLAUDE_MODELS: list[ModelInfo] = [
    ModelInfo(name="claude-sonnet-4-20250514", size_gb=0.0, context_window=200_000, provider="anthropic"),
    ModelInfo(name="claude-3-5-sonnet-20241022", size_gb=0.0, context_window=200_000, provider="anthropic"),
    ModelInfo(name="claude-3-5-haiku-20241022", size_gb=0.0, context_window=200_000, provider="anthropic"),
    ModelInfo(name="claude-3-opus-20240229", size_gb=0.0, context_window=200_000, provider="anthropic"),
    ModelInfo(name="claude-3-haiku-20240307", size_gb=0.0, context_window=200_000, provider="anthropic"),
]


def _get_anthropic():
    """Lazily import the ``anthropic`` library."""
    try:
        import anthropic
        return anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for AnthropicLLMClient. "
            "Install it with:  pip install anthropic"
        )


def _openai_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI-format tool definitions to Anthropic's ``tool_use`` format.

    OpenAI format::

        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "...",
                "parameters": { ... }
            }
        }

    Anthropic format::

        {
            "name": "get_weather",
            "description": "...",
            "input_schema": { ... }
        }
    """
    converted: list[dict[str, Any]] = []
    for tool in tools:
        fn = tool.get("function", tool)
        converted.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return converted


def _openai_messages_to_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Split an OpenAI-style message list into (system_prompt, messages).

    Anthropic requires the system prompt to be passed separately and does
    not allow ``"role": "system"`` inside the messages list.
    """
    system_prompt = ""
    converted: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            # Concatenate multiple system messages if present.
            if system_prompt:
                system_prompt += "\n\n"
            system_prompt += content or ""
            continue

        if role == "tool":
            # Map OpenAI tool-result messages to Anthropic ``tool_result``
            # content blocks.
            converted.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content or "",
                    }
                ],
            })
            continue

        if role == "assistant" and msg.get("tool_calls"):
            # Convert assistant tool_calls to Anthropic ``tool_use`` blocks.
            blocks: list[dict[str, Any]] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "input": args,
                })
            converted.append({"role": "assistant", "content": blocks})
            continue

        # Regular user / assistant message.
        converted.append({"role": role, "content": content or ""})

    return system_prompt, converted


class AnthropicLLMClient(BaseLLMClient):
    """Client for the Anthropic Messages API (Claude models)."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
        proxy: str = "",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._anthropic = _get_anthropic()

        import httpx as _httpx
        http_kwargs: dict[str, Any] = {"trust_env": False}
        if proxy:
            http_kwargs["proxy"] = proxy
        http_client = _httpx.Client(**http_kwargs)

        self._client = self._anthropic.Anthropic(
            api_key=self._api_key or "not-set",
            http_client=http_client,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def max_context_tokens(self) -> int:
        return 200_000

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        messages = self.validate_messages(messages)
        system_prompt, anthropic_messages = _openai_messages_to_anthropic(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 8_192,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = _openai_tools_to_anthropic(tools)

        try:
            response = self._client.messages.create(**kwargs)
        except self._anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise

        # Parse content blocks
        content_parts: list[str] = []
        tool_calls: list[ToolCallRequest] = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCallRequest(
                        id=block.id,
                        name=block.name,
                        arguments=json.dumps(block.input) if isinstance(block.input, dict) else str(block.input),
                    )
                )

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        # Map Anthropic stop reasons to OpenAI-style finish reasons
        finish_reason_map = {
            "end_turn": "stop",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
            "max_tokens": "length",
        }
        finish_reason = finish_reason_map.get(response.stop_reason or "", response.stop_reason or "stop")

        return LLMResponse(
            content="\n".join(content_parts),
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        messages = self.validate_messages(messages)
        system_prompt, anthropic_messages = _openai_messages_to_anthropic(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 8_192,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = _openai_tools_to_anthropic(tools)

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except self._anthropic.APIError as exc:
            logger.error("Anthropic streaming error: %s", exc)
            raise

    def is_available(self) -> bool:
        try:
            # Anthropic has no lightweight ping – attempt a minimal request.
            self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        return list(_CLAUDE_MODELS)
