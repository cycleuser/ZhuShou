"""Base abstractions for LLM provider clients."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Token usage statistics from an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ModelInfo:
    """Metadata about an available model."""

    name: str = ""
    size_gb: float = 0.0
    context_window: int = 0
    provider: str = ""


@dataclass
class ToolCallRequest:
    """A single tool/function call requested by the model."""

    id: str = ""
    name: str = ""
    arguments: str = ""  # JSON-encoded arguments string


@dataclass
class LLMResponse:
    """Unified response object returned by every provider."""

    content: str = ""
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = ""


# ---------------------------------------------------------------------------
# Abstract base client
# ---------------------------------------------------------------------------

class BaseLLMClient(ABC):
    """Abstract base class that every LLM provider must implement."""

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request and return the full response.

        Parameters
        ----------
        messages:
            A list of message dicts following the OpenAI chat format, e.g.
            ``[{"role": "user", "content": "Hello"}]``.
        temperature:
            Sampling temperature.
        tools:
            Optional list of tool/function definitions in OpenAI format.

        Returns
        -------
        LLMResponse
        """
        ...

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        """Stream a chat completion, yielding content tokens as they arrive.

        Parameters
        ----------
        messages:
            See :meth:`chat`.
        temperature:
            Sampling temperature.
        tools:
            Optional tool definitions (some providers ignore during stream).

        Yields
        ------
        str
            Individual content tokens / chunks.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` when the provider backend is reachable."""
        ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """Return a list of models offered by this provider."""
        ...

    # ------------------------------------------------------------------
    # Abstract properties
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the currently selected model identifier."""
        ...

    @model.setter
    @abstractmethod
    def model(self, value: str) -> None:
        """Set the model identifier."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider name (e.g. ``"ollama"``)."""
        ...

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """Return the maximum context window size in tokens."""
        ...

    # ------------------------------------------------------------------
    # Concrete helpers
    # ------------------------------------------------------------------

    def validate_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate and normalise a message list.

        Raises
        ------
        ValueError
            If messages is empty or a message lacks the required keys.

        Returns
        -------
        list[dict[str, Any]]
            The validated (possibly cleaned-up) message list.
        """
        if not messages:
            raise ValueError("messages must be a non-empty list")

        valid_roles = {"system", "user", "assistant", "tool", "function"}
        cleaned: list[dict[str, Any]] = []

        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message at index {idx} must be a dict, got {type(msg).__name__}")

            role = msg.get("role")
            if role is None:
                raise ValueError(f"Message at index {idx} is missing the 'role' key")
            if role not in valid_roles:
                raise ValueError(
                    f"Message at index {idx} has invalid role '{role}'. "
                    f"Expected one of {valid_roles}"
                )

            # 'content' may legitimately be None for assistant messages with
            # tool_calls, so we only require that the key exists or that the
            # message carries tool_calls.
            if "content" not in msg and "tool_calls" not in msg:
                raise ValueError(
                    f"Message at index {idx} must have either a 'content' or "
                    f"'tool_calls' key"
                )

            cleaned.append(msg)

        return cleaned
