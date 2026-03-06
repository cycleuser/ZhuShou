"""Google Gemini LLM client implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from .base import BaseLLMClient, LLMResponse, ModelInfo, TokenUsage, ToolCallRequest

logger = logging.getLogger(__name__)


def _get_genai():
    """Lazily import the ``google.generativeai`` library."""
    try:
        import google.generativeai as genai
        return genai
    except ImportError:
        raise ImportError(
            "The 'google-generativeai' package is required for GeminiLLMClient. "
            "Install it with:  pip install google-generativeai"
        )


def _openai_tools_to_gemini(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI-format tool definitions to Gemini function declarations.

    OpenAI format::

        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "...",
                "parameters": { ... }
            }
        }

    Gemini expects a list of ``FunctionDeclaration``-compatible dicts.
    """
    declarations: list[dict[str, Any]] = []
    for tool in tools:
        fn = tool.get("function", tool)
        declarations.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return declarations


def _openai_messages_to_gemini(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Convert OpenAI-style messages to Gemini format.

    Returns (system_instruction, contents) where *contents* is a list of
    Gemini ``Content``-like dicts with ``role`` and ``parts``.
    """
    system_instruction: str | None = None
    contents: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            if system_instruction:
                system_instruction += "\n\n" + (content or "")
            else:
                system_instruction = content or ""
            continue

        # Gemini uses "user" and "model" roles
        gemini_role = "model" if role == "assistant" else "user"

        if role == "tool":
            # Wrap tool results as function response parts
            contents.append({
                "role": "user",
                "parts": [{
                    "function_response": {
                        "name": msg.get("name", "tool"),
                        "response": {"result": content or ""},
                    }
                }],
            })
            continue

        parts: list[dict[str, Any]] = []
        if content:
            parts.append({"text": content})

        # Handle assistant messages with tool calls
        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                parts.append({
                    "function_call": {
                        "name": fn.get("name", ""),
                        "args": args,
                    }
                })

        if parts:
            contents.append({"role": gemini_role, "parts": parts})

    return system_instruction, contents


class GeminiLLMClient(BaseLLMClient):
    """Client for the Google Gemini generative AI API."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.0-flash",
        proxy: str = "",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._genai = _get_genai()
        if proxy:
            logger.debug(
                "Gemini client does not support custom proxy; "
                "--proxy is ignored for this provider"
            )
        if self._api_key:
            self._genai.configure(api_key=self._api_key)

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
        return "gemini"

    @property
    def max_context_tokens(self) -> int:
        return 1_000_000

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
        system_instruction, contents = _openai_messages_to_gemini(messages)

        generation_config = self._genai.GenerationConfig(temperature=temperature)

        model_kwargs: dict[str, Any] = {"model_name": self._model}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gemini_tools = None
        if tools:
            gemini_tools = _openai_tools_to_gemini(tools)

        gen_model = self._genai.GenerativeModel(**model_kwargs)

        try:
            response = gen_model.generate_content(
                contents,
                generation_config=generation_config,
                tools=gemini_tools,
            )
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            raise

        # Parse response
        content = ""
        tool_calls: list[ToolCallRequest] = []

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    content += part.text
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args_dict = dict(fc.args) if fc.args else {}
                    tool_calls.append(
                        ToolCallRequest(
                            id=f"call_{fc.name}",
                            name=fc.name,
                            arguments=json.dumps(args_dict),
                        )
                    )

        # Token usage
        usage = TokenUsage()
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            prompt_tokens = getattr(um, "prompt_token_count", 0) or 0
            completion_tokens = getattr(um, "candidates_token_count", 0) or 0
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        # Finish reason
        finish_reason = "stop"
        if response.candidates:
            fr = response.candidates[0].finish_reason
            # Gemini uses int enums; map common ones
            _FINISH_MAP = {1: "stop", 2: "length", 3: "safety", 4: "recitation", 5: "other"}
            if isinstance(fr, int):
                finish_reason = _FINISH_MAP.get(fr, "stop")
            elif fr is not None:
                finish_reason = str(fr).lower()

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
        system_instruction, contents = _openai_messages_to_gemini(messages)

        generation_config = self._genai.GenerationConfig(temperature=temperature)

        model_kwargs: dict[str, Any] = {"model_name": self._model}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gemini_tools = None
        if tools:
            gemini_tools = _openai_tools_to_gemini(tools)

        gen_model = self._genai.GenerativeModel(**model_kwargs)

        try:
            response = gen_model.generate_content(
                contents,
                generation_config=generation_config,
                tools=gemini_tools,
                stream=True,
            )
        except Exception as exc:
            logger.error("Gemini streaming error: %s", exc)
            raise

        for chunk in response:
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        yield part.text

    def is_available(self) -> bool:
        try:
            self.list_models()
            return True
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        try:
            models_iter = self._genai.list_models()
            models: list[ModelInfo] = []
            for m in models_iter:
                if "generateContent" in getattr(m, "supported_generation_methods", []):
                    models.append(
                        ModelInfo(
                            name=m.name.replace("models/", "") if hasattr(m, "name") else str(m),
                            size_gb=0.0,
                            context_window=getattr(m, "input_token_limit", self.max_context_tokens) or self.max_context_tokens,
                            provider=self.provider_name,
                        )
                    )
            return models
        except Exception as exc:
            logger.warning("Failed to list Gemini models: %s", exc)
            return []
