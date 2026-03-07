"""Collect world context for LLM prompts using ModelSensor."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_world_context(enabled: bool = True) -> str:
    """Return a formatted world-context string for injection into system prompts.

    When *enabled* is ``False`` (user passed ``--no-world``), returns an
    empty string so no extra tokens are consumed.
    """
    if not enabled:
        return ""

    try:
        from modelsensor import ModelSensor

        sensor = ModelSensor()
        time_info = sensor.get_time_info()
        parts = [
            f"Current date/time: {time_info.get('formatted_time', 'unknown')}",
            f"Timezone: {time_info.get('timezone', 'unknown')}",
            f"Weekday: {time_info.get('weekday', 'unknown')}",
        ]
        return "## Current World State\n" + "\n".join(parts)
    except ImportError:
        logger.debug("modelsensor not installed, skipping world context")
        return ""
    except Exception:
        logger.debug("Failed to collect world context", exc_info=True)
        return ""
