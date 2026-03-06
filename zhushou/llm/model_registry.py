"""Model registry with context windows and pricing information."""

from __future__ import annotations

from typing import Any

from .base import TokenUsage

# ---------------------------------------------------------------------------
# Registry: provider -> model -> { context_window, input_cost_per_1m, output_cost_per_1m }
#
# Costs are expressed in USD per 1 000 000 tokens.
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, dict[str, dict[str, Any]]] = {
    "openai": {
        "gpt-4o": {
            "context_window": 128_000,
            "input_cost_per_1m": 2.50,
            "output_cost_per_1m": 10.00,
        },
        "gpt-4o-mini": {
            "context_window": 128_000,
            "input_cost_per_1m": 0.15,
            "output_cost_per_1m": 0.60,
        },
        "gpt-4-turbo": {
            "context_window": 128_000,
            "input_cost_per_1m": 10.00,
            "output_cost_per_1m": 30.00,
        },
        "gpt-4": {
            "context_window": 8_192,
            "input_cost_per_1m": 30.00,
            "output_cost_per_1m": 60.00,
        },
        "gpt-3.5-turbo": {
            "context_window": 16_385,
            "input_cost_per_1m": 0.50,
            "output_cost_per_1m": 1.50,
        },
        "o1": {
            "context_window": 200_000,
            "input_cost_per_1m": 15.00,
            "output_cost_per_1m": 60.00,
        },
        "o1-mini": {
            "context_window": 128_000,
            "input_cost_per_1m": 3.00,
            "output_cost_per_1m": 12.00,
        },
        "o3-mini": {
            "context_window": 200_000,
            "input_cost_per_1m": 1.10,
            "output_cost_per_1m": 4.40,
        },
    },
    "anthropic": {
        "claude-sonnet-4-20250514": {
            "context_window": 200_000,
            "input_cost_per_1m": 3.00,
            "output_cost_per_1m": 15.00,
        },
        "claude-3-5-sonnet-20241022": {
            "context_window": 200_000,
            "input_cost_per_1m": 3.00,
            "output_cost_per_1m": 15.00,
        },
        "claude-3-5-haiku-20241022": {
            "context_window": 200_000,
            "input_cost_per_1m": 0.80,
            "output_cost_per_1m": 4.00,
        },
        "claude-3-opus-20240229": {
            "context_window": 200_000,
            "input_cost_per_1m": 15.00,
            "output_cost_per_1m": 75.00,
        },
        "claude-3-haiku-20240307": {
            "context_window": 200_000,
            "input_cost_per_1m": 0.25,
            "output_cost_per_1m": 1.25,
        },
    },
    "deepseek": {
        "deepseek-chat": {
            "context_window": 64_000,
            "input_cost_per_1m": 0.14,
            "output_cost_per_1m": 0.28,
        },
        "deepseek-coder": {
            "context_window": 64_000,
            "input_cost_per_1m": 0.14,
            "output_cost_per_1m": 0.28,
        },
        "deepseek-reasoner": {
            "context_window": 64_000,
            "input_cost_per_1m": 0.55,
            "output_cost_per_1m": 2.19,
        },
    },
    "gemini": {
        "gemini-2.0-flash": {
            "context_window": 1_000_000,
            "input_cost_per_1m": 0.10,
            "output_cost_per_1m": 0.40,
        },
        "gemini-2.0-flash-lite": {
            "context_window": 1_000_000,
            "input_cost_per_1m": 0.075,
            "output_cost_per_1m": 0.30,
        },
        "gemini-1.5-pro": {
            "context_window": 2_000_000,
            "input_cost_per_1m": 1.25,
            "output_cost_per_1m": 5.00,
        },
        "gemini-1.5-flash": {
            "context_window": 1_000_000,
            "input_cost_per_1m": 0.075,
            "output_cost_per_1m": 0.30,
        },
    },
    "ollama": {
        # Local models – no API cost; context varies per model, use defaults.
    },
}


def get_context_window(provider: str, model: str) -> int:
    """Look up the context window size for a given provider and model.

    Falls back to sensible defaults when the model is not found in the
    registry.

    Parameters
    ----------
    provider:
        Provider key (e.g. ``"openai"``, ``"anthropic"``).
    model:
        Model identifier (e.g. ``"gpt-4o"``).

    Returns
    -------
    int
        Context window size in tokens.
    """
    provider_models = MODEL_REGISTRY.get(provider, {})
    info = provider_models.get(model)
    if info is not None:
        return int(info["context_window"])

    # Try a fuzzy prefix match (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
    for registered_model, info in provider_models.items():
        if model.startswith(registered_model) or registered_model.startswith(model):
            return int(info["context_window"])

    # Provider-level defaults
    _PROVIDER_DEFAULTS: dict[str, int] = {
        "openai": 128_000,
        "anthropic": 200_000,
        "deepseek": 64_000,
        "gemini": 1_000_000,
        "ollama": 32_768,
        "lmstudio": 32_768,
        "vllm": 32_768,
    }
    return _PROVIDER_DEFAULTS.get(provider, 4_096)


def get_cost(provider: str, model: str, usage: TokenUsage) -> float:
    """Calculate the estimated cost in USD for a given usage.

    Parameters
    ----------
    provider:
        Provider key.
    model:
        Model identifier.
    usage:
        Token usage from the LLM response.

    Returns
    -------
    float
        Estimated cost in USD.  Returns ``0.0`` for local / unpriced models.
    """
    provider_models = MODEL_REGISTRY.get(provider, {})
    info = provider_models.get(model)

    # Fuzzy prefix match
    if info is None:
        for registered_model, candidate in provider_models.items():
            if model.startswith(registered_model) or registered_model.startswith(model):
                info = candidate
                break

    if info is None:
        return 0.0

    input_cost = (usage.prompt_tokens / 1_000_000) * info.get("input_cost_per_1m", 0.0)
    output_cost = (usage.completion_tokens / 1_000_000) * info.get("output_cost_per_1m", 0.0)
    return round(input_cost + output_cost, 6)
