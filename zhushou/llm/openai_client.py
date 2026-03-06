"""OpenAI-compatible LLM client implementation.

Works with OpenAI, DeepSeek, LM Studio, vLLM, and any other provider
that exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from .base import BaseLLMClient, LLMResponse, ModelInfo, TokenUsage, ToolCallRequest
from .model_registry import get_context_window

logger = logging.getLogger(__name__)


def _get_openai():
    """Lazily import the ``openai`` library."""
    try:
        import openai  # noqa: F811
        return openai
    except ImportError:
        raise ImportError(
            "The 'openai' package is required for OpenAILLMClient. "
            "Install it with:  pip install openai"
        )


class OpenAILLMClient(BaseLLMClient):
    """Client for OpenAI and OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        proxy: str = "",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._openai = _get_openai()

        import httpx as _httpx
        http_kwargs: dict[str, Any] = {"trust_env": False}
        if proxy:
            http_kwargs["proxy"] = proxy
        http_client = _httpx.Client(**http_kwargs)

        self._client = self._openai.OpenAI(
            api_key=self._api_key or "not-set",
            base_url=self._base_url,
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
        return "openai"

    @property
    def max_context_tokens(self) -> int:
        # Try the registry first; fall back to a generous default.
        provider_key = self._infer_provider_key()
        ctx = get_context_window(provider_key, self._model)
        return ctx

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

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = self._client.chat.completions.create(**kwargs)
        except self._openai.APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise

        choice = response.choices[0] if response.choices else None
        content = ""
        tool_calls: list[ToolCallRequest] = []
        finish_reason = ""

        if choice:
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or ""

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append(
                        ToolCallRequest(
                            id=tc.id or "",
                            name=tc.function.name or "",
                            arguments=tc.function.arguments or "",
                        )
                    )

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
            )

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

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream = self._client.chat.completions.create(**kwargs)
        except self._openai.APIError as exc:
            logger.error("OpenAI streaming API error: %s", exc)
            raise

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def is_available(self) -> bool:
        try:
            self.list_models()
            return True
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        try:
            response = self._client.models.list()
        except Exception as exc:
            logger.warning("Failed to list OpenAI models: %s", exc)
            return []

        models: list[ModelInfo] = []
        for m in response.data:
            provider_key = self._infer_provider_key()
            ctx = get_context_window(provider_key, m.id)
            models.append(
                ModelInfo(
                    name=m.id,
                    size_gb=0.0,
                    context_window=ctx,
                    provider=self.provider_name,
                )
            )
        return models

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _infer_provider_key(self) -> str:
        """Guess the registry provider key from the base URL."""
        url = self._base_url.lower()
        if "deepseek" in url:
            return "deepseek"
        if "openai" in url:
            return "openai"
        # For LM Studio / vLLM / other local, fall back to openai
        return "openai"
