"""ZhuShou token usage tracker.

Records per-model token usage across a session and persists
cumulative stats to ``~/.zhushou/usage.json``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_USAGE_PATH = Path.home() / ".zhushou" / "usage.json"

# ── Cost-per-token lookup (USD) ───────────────────────────────────
# Approximate pricing per 1 K tokens (input / output).
# Updated values should be placed in a model_registry module; these
# serve as reasonable defaults.
_COST_TABLE: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
    # DeepSeek
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-coder": {"input": 0.00014, "output": 0.00028},
    # Gemini
    "gemini-pro": {"input": 0.00025, "output": 0.0005},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    # Ollama / local — free
    "local": {"input": 0.0, "output": 0.0},
}


class TokenTracker:
    """Accumulate and persist token usage across a session.

    Parameters
    ----------
    usage_path : str | Path | None
        Override the default ``~/.zhushou/usage.json`` path.
    """

    def __init__(self, usage_path: str | Path | None = None) -> None:
        self._usage_path: Path = Path(usage_path) if usage_path else _DEFAULT_USAGE_PATH
        self._session_records: list[dict[str, Any]] = []
        self._total_prompt: int = 0
        self._total_completion: int = 0
        self._total_cost: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Record a single LLM call's token usage.

        Parameters
        ----------
        provider : str
            LLM provider name (``"openai"``, ``"ollama"``, etc.).
        model : str
            Model identifier.
        prompt_tokens : int
            Number of tokens in the prompt.
        completion_tokens : int
            Number of tokens in the completion.
        """
        cost = self._estimate_cost(provider, model, prompt_tokens, completion_tokens)

        self._total_prompt += prompt_tokens
        self._total_completion += completion_tokens
        self._total_cost += cost

        self._session_records.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": round(cost, 6),
        })

    def get_session_stats(self) -> dict[str, Any]:
        """Return aggregated stats for the current session.

        Returns
        -------
        dict
            Keys: ``prompt_tokens``, ``completion_tokens``,
            ``total_tokens``, ``estimated_cost``, ``calls``,
            ``provider``, ``model``.
        """
        # Determine dominant provider/model from records
        provider = "unknown"
        model = "unknown"
        if self._session_records:
            last = self._session_records[-1]
            provider = last.get("provider", "unknown")
            model = last.get("model", "unknown")

        return {
            "prompt_tokens": self._total_prompt,
            "completion_tokens": self._total_completion,
            "total_tokens": self._total_prompt + self._total_completion,
            "estimated_cost": round(self._total_cost, 6),
            "calls": len(self._session_records),
            "provider": provider,
            "model": model,
        }

    def save(self) -> None:
        """Persist cumulative usage data to ``~/.zhushou/usage.json``.

        Appends current session records to any existing file data.
        """
        existing: list[dict[str, Any]] = []
        if self._usage_path.is_file():
            try:
                with open(self._usage_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    existing = data if isinstance(data, list) else data.get("records", [])
            except (json.JSONDecodeError, OSError):
                existing = []

        combined = existing + self._session_records

        os.makedirs(self._usage_path.parent, exist_ok=True)
        tmp_path = self._usage_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(combined, fh, indent=2, ensure_ascii=False)
            tmp_path.replace(self._usage_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_cost(
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate cost in USD for a single call.

        Uses the ``_COST_TABLE`` lookup.  Local / Ollama models are
        treated as free.
        """
        if provider.lower() == "ollama":
            return 0.0

        # Try exact model match first, then prefix match
        rates = _COST_TABLE.get(model)
        if rates is None:
            for key in _COST_TABLE:
                if model.startswith(key) or key.startswith(model):
                    rates = _COST_TABLE[key]
                    break

        if rates is None:
            return 0.0

        input_cost = (prompt_tokens / 1000.0) * rates.get("input", 0.0)
        output_cost = (completion_tokens / 1000.0) * rates.get("output", 0.0)
        return input_cost + output_cost

    def __repr__(self) -> str:
        stats = self.get_session_stats()
        return (
            f"TokenTracker(calls={stats['calls']}, "
            f"tokens={stats['total_tokens']}, "
            f"cost=${stats['estimated_cost']:.4f})"
        )
