"""Factory for creating LLM clients by provider name."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseLLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider descriptor: (module_path, class_name, default_kwargs_override)
# Using strings so we can do lazy imports and avoid hard dependencies.
# ---------------------------------------------------------------------------

_PROVIDER_DESCRIPTORS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "ollama": (
        "zhushou.llm.ollama_client",
        "OllamaLLMClient",
        {},
    ),
    "openai": (
        "zhushou.llm.openai_client",
        "OpenAILLMClient",
        {},
    ),
    "anthropic": (
        "zhushou.llm.anthropic_client",
        "AnthropicLLMClient",
        {},
    ),
    "gemini": (
        "zhushou.llm.gemini_client",
        "GeminiLLMClient",
        {},
    ),
    # Aliases – same implementation classes, different default kwargs
    "deepseek": (
        "zhushou.llm.openai_client",
        "OpenAILLMClient",
        {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    ),
    "claude": (
        "zhushou.llm.anthropic_client",
        "AnthropicLLMClient",
        {},
    ),
    "lmstudio": (
        "zhushou.llm.openai_client",
        "OpenAILLMClient",
        {"base_url": "http://localhost:1234/v1", "model": "local-model"},
    ),
    "vllm": (
        "zhushou.llm.openai_client",
        "OpenAILLMClient",
        {"base_url": "http://localhost:8000/v1", "model": "local-model"},
    ),
}


def _lazy_import(module_path: str, class_name: str) -> type[BaseLLMClient]:
    """Import a class by fully-qualified module path."""
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls  # type: ignore[return-value]


class LLMClientFactory:
    """Factory that instantiates LLM clients by provider name.

    Usage::

        client = LLMClientFactory.create_client("ollama", model="llama3")
        client = LLMClientFactory.create_client("openai", api_key="sk-...")
        client = LLMClientFactory.create_client("deepseek", api_key="sk-...")
    """

    # Expose the mapping for introspection / documentation.
    PROVIDERS: dict[str, str] = {
        name: desc[1] for name, desc in _PROVIDER_DESCRIPTORS.items()
    }

    @classmethod
    def create_client(cls, provider: str, **kwargs: Any) -> BaseLLMClient:
        """Create and return an LLM client for the given *provider*.

        Parameters
        ----------
        provider:
            One of the registered provider keys (e.g. ``"ollama"``,
            ``"openai"``, ``"deepseek"``).
        **kwargs:
            Additional keyword arguments forwarded to the client constructor.
            These override the default kwargs for the provider.

        Raises
        ------
        ValueError
            If *provider* is not recognised.
        ImportError
            If the required optional dependency for the provider is not
            installed.
        """
        provider_key = provider.lower().strip()
        descriptor = _PROVIDER_DESCRIPTORS.get(provider_key)

        if descriptor is None:
            available = ", ".join(sorted(_PROVIDER_DESCRIPTORS))
            raise ValueError(
                f"Unknown LLM provider '{provider}'. "
                f"Available providers: {available}"
            )

        module_path, class_name, default_kwargs = descriptor

        # Merge: default_kwargs are overridden by caller kwargs
        merged_kwargs = {**default_kwargs, **kwargs}

        client_cls = _lazy_import(module_path, class_name)
        logger.debug(
            "Creating %s client (provider=%s) with kwargs=%s",
            class_name,
            provider_key,
            {k: ("***" if "key" in k.lower() else v) for k, v in merged_kwargs.items()},
        )
        return client_cls(**merged_kwargs)

    @classmethod
    def auto_detect(cls) -> list[BaseLLMClient]:
        """Probe common local providers and return those that are available.

        Currently probes:

        * Ollama at ``http://localhost:11434``
        * LM Studio at ``http://localhost:1234``
        * vLLM at ``http://localhost:8000``

        Returns
        -------
        list[BaseLLMClient]
            A (possibly empty) list of available clients.
        """
        available: list[BaseLLMClient] = []

        # Probe local providers that don't need API keys
        local_providers = ["ollama", "lmstudio", "vllm"]
        for provider_name in local_providers:
            try:
                client = cls.create_client(provider_name)
                if client.is_available():
                    logger.info("Auto-detected available provider: %s", provider_name)
                    available.append(client)
            except Exception as exc:
                logger.debug("Provider %s not available: %s", provider_name, exc)

        return available

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return a sorted list of all registered provider keys."""
        return sorted(_PROVIDER_DESCRIPTORS)
