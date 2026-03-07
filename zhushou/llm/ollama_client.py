"""Ollama LLM client implementation."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator

import httpx

from .base import BaseLLMClient, LLMResponse, ModelInfo, TokenUsage, ToolCallRequest

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(300.0, connect=10.0)
_MAX_RETRIES = 5
_RETRY_BACKOFF_BASE = 3.0


class OllamaLLMClient(BaseLLMClient):
    """LLM client that communicates with a local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "",
        proxy: str = "",
        timeout: int = 300,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = httpx.Timeout(float(timeout), connect=10.0)
        client_kwargs: dict[str, Any] = {
            "base_url": self._base_url,
            "timeout": self._timeout,
            "trust_env": False,
        }
        if proxy:
            client_kwargs["proxy"] = proxy
        self._client = httpx.Client(**client_kwargs)

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
        return "ollama"

    @property
    def max_context_tokens(self) -> int:
        return 32_768

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
        messages = self._sanitize_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        data = self._request_with_retry("POST", "/api/chat", json_body=payload)

        # Parse assistant message
        msg = data.get("message", {})
        content = msg.get("content", "")

        # Parse tool calls if present
        tool_calls: list[ToolCallRequest] = []
        raw_tool_calls = msg.get("tool_calls", [])
        for idx, tc in enumerate(raw_tool_calls):
            fn = tc.get("function", {})
            tool_calls.append(
                ToolCallRequest(
                    id=f"call_{idx}",
                    name=fn.get("name", ""),
                    arguments=json.dumps(fn.get("arguments", {}))
                    if isinstance(fn.get("arguments"), dict)
                    else str(fn.get("arguments", "")),
                )
            )

        # Parse token usage
        usage_raw = data.get("usage", {})
        # Ollama may report usage at top-level or nested
        prompt_tokens = (
            usage_raw.get("prompt_tokens", 0)
            or data.get("prompt_eval_count", 0)
        )
        completion_tokens = (
            usage_raw.get("completion_tokens", 0)
            or data.get("eval_count", 0)
        )
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        finish_reason = data.get("done_reason", "stop") if data.get("done") else "length"

        return LLMResponse(
            content=content,
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
        messages = self._sanitize_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                with self._client.stream(
                    "POST", "/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            return
                return  # stream ended normally
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Ollama stream attempt %d failed: %s – retrying in %.1fs",
                        attempt + 1,
                        exc,
                        wait,
                    )
                    time.sleep(wait)

        raise ConnectionError(
            f"Ollama streaming failed after {_MAX_RETRIES} retries: {last_exc}"
        )

    def is_available(self) -> bool:
        try:
            resp = self._client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        try:
            resp = self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to list Ollama models: %s", exc)
            return []

        models: list[ModelInfo] = []
        for m in data.get("models", []):
            name = m.get("name", "")
            size_bytes = m.get("size", 0)
            size_gb = round(size_bytes / (1024**3), 2) if size_bytes else 0.0
            models.append(
                ModelInfo(
                    name=name,
                    size_gb=size_gb,
                    context_window=self.max_context_tokens,
                    provider=self.provider_name,
                )
            )
        return models

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sanitize_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI-format tool messages to Ollama-compatible format.

        * Assistant messages with ``tool_calls``: deserialise string
          ``arguments`` to a dict and strip ``id`` / ``type`` wrappers.
        * Tool-role messages: keep only ``role`` and ``content``
          (strip ``tool_call_id`` and ``name``).
        * All other messages pass through unchanged.
        """
        sanitized: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")

            if role == "assistant" and "tool_calls" in msg:
                new_tool_calls: list[dict[str, Any]] = []
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", tc)
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except (json.JSONDecodeError, TypeError):
                            args = {}
                    new_tool_calls.append({
                        "function": {
                            "name": fn.get("name", ""),
                            "arguments": args,
                        }
                    })
                sanitized.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": new_tool_calls,
                })

            elif role == "tool":
                sanitized.append({
                    "role": "tool",
                    "content": msg.get("content", ""),
                })

            else:
                sanitized.append(dict(msg))

        return sanitized

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry + exponential backoff."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._client.request(method, path, json=json_body)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Ollama request %s %s attempt %d failed: %s – retrying in %.1fs",
                        method,
                        path,
                        attempt + 1,
                        exc,
                        wait,
                    )
                    time.sleep(wait)

        raise ConnectionError(
            f"Ollama request {method} {path} failed after {_MAX_RETRIES} retries: {last_exc}"
        )
