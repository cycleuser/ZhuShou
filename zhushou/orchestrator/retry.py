"""Exponential-backoff retry delay calculation.

Pure function with no external dependencies -- mirrors the retry logic
in Symphony's ``orchestrator.ex`` (lines 829-831).

    delay = min(base_ms * 2^(attempt - 1), max_ms)

The exponent is capped at 10 (i.e. 1024x the base) to prevent overflow
when *attempt* values grow large during prolonged failure scenarios.
"""

from __future__ import annotations

_MAX_EXPONENT = 10  # 2^10 = 1024


def retry_delay(
    attempt: int,
    base_ms: int = 10_000,
    max_ms: int = 300_000,
) -> int:
    """Return the backoff delay in milliseconds for *attempt* (1-based).

    >>> retry_delay(1)
    10000
    >>> retry_delay(2)
    20000
    >>> retry_delay(5)
    160000
    >>> retry_delay(20)          # capped at max_ms
    300000
    >>> retry_delay(1, base_ms=5000, max_ms=60000)
    5000
    """
    if attempt < 1:
        attempt = 1
    exponent = min(attempt - 1, _MAX_EXPONENT)
    delay = base_ms * (1 << exponent)
    return min(delay, max_ms)


def retry_delay_seconds(
    attempt: int,
    base_ms: int = 10_000,
    max_ms: int = 300_000,
) -> float:
    """Convenience wrapper returning seconds as a ``float``."""
    return retry_delay(attempt, base_ms, max_ms) / 1000.0
