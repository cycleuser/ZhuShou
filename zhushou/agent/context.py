"""Conversation context management with token-budget awareness."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # LLM client is duck-typed; no concrete import needed

logger = logging.getLogger(__name__)

# ── Heuristic constants ───────────────────────────────────────────────
_CJK_RANGE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef"
    r"\u2e80-\u2eff\u3100-\u312f\u31a0-\u31bf]"
)


class ContextManager:
    """Build and trim the LLM message list so it stays within a token budget.

    Uses a simple character-based heuristic to estimate token counts (no
    external tokeniser required), and can ask the LLM itself to summarise
    older messages when the context window is getting full.
    """

    def __init__(self, max_tokens: int = 32768) -> None:
        self.max_tokens = max_tokens

    # ── Public API ─────────────────────────────────────────────────────

    def build_messages(
        self,
        system_prompt: str,
        conversation: list[dict[str, Any]],
        memory_context: str = "",
    ) -> list[dict[str, Any]]:
        """Construct the messages list sent to the LLM.

        Layout
        ------
        1. System message (always present).
        2. Optional memory-context system message.
        3. Conversation tail, trimmed so the total estimated token count
           stays within *max_tokens*.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        if memory_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant context from long-term memory:\n\n"
                        + memory_context
                    ),
                }
            )

        # Token budget consumed by the fixed prefix
        prefix_tokens = sum(
            self.estimate_tokens(m.get("content", "")) for m in messages
        )
        budget = self.max_tokens - prefix_tokens

        # Walk conversation from newest to oldest, collecting as many
        # messages as fit the remaining budget.
        selected: list[dict[str, Any]] = []
        used = 0
        for msg in reversed(conversation):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            if used + msg_tokens > budget:
                break
            selected.append(msg)
            used += msg_tokens

        selected.reverse()
        messages.extend(selected)
        return messages

    def needs_compaction(self, messages: list[dict[str, Any]]) -> bool:
        """Return *True* when estimated tokens exceed 80 % of *max_tokens*."""
        total = sum(
            self.estimate_tokens(m.get("content", "")) for m in messages
        )
        return total > self.max_tokens * 0.8

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate.

        CJK-heavy text averages ~1 token per 1.5–2 characters (we use /3
        to be conservative).  Latin text averages ~1 token per 4 characters.
        We detect which category dominates and pick the divisor accordingly.
        """
        if not text:
            return 0

        cjk_chars = len(_CJK_RANGE.findall(text))
        total_chars = len(text)

        if total_chars == 0:
            return 0

        cjk_ratio = cjk_chars / total_chars
        divisor = 3 if cjk_ratio > 0.3 else 4
        return max(1, total_chars // divisor)

    async def compact(
        self,
        messages: list[dict[str, Any]],
        llm_client: Any,
    ) -> list[dict[str, Any]]:
        """Summarise older messages via the LLM to free context space.

        Keeps the system message(s) and the most recent messages intact,
        replacing everything in between with a single summary message.

        Parameters
        ----------
        messages:
            The full message list (system + conversation).
        llm_client:
            An object with a ``chat(messages, tools=None)`` method.

        Returns
        -------
        list[dict]
            A compacted message list: [system_msg, summary_msg, …recent].
        """
        if len(messages) <= 4:
            # Nothing meaningful to compact
            return messages

        # Separate system messages from conversation turns
        system_msgs: list[dict[str, Any]] = []
        conv_msgs: list[dict[str, Any]] = []
        for m in messages:
            if m["role"] == "system":
                system_msgs.append(m)
            else:
                conv_msgs.append(m)

        if len(conv_msgs) <= 4:
            return messages

        # Keep the last 4 conversation messages as-is
        older = conv_msgs[:-4]
        recent = conv_msgs[-4:]

        # Ask the LLM to produce a concise summary of the older messages
        summary_request = (
            "Summarise the following conversation concisely, preserving "
            "all important facts, decisions, and context:\n\n"
        )
        for m in older:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            summary_request += f"[{role}]: {content}\n\n"

        summary_messages = [
            {"role": "system", "content": "You are a helpful summariser."},
            {"role": "user", "content": summary_request},
        ]

        try:
            summary_response = llm_client.chat(
                messages=summary_messages, tools=None
            )
            summary_text = getattr(summary_response, "content", "") or str(
                summary_response
            )
        except Exception:
            logger.warning("Compaction LLM call failed; keeping original messages")
            return messages

        summary_msg: dict[str, Any] = {
            "role": "system",
            "content": f"[Conversation summary]\n{summary_text}",
        }

        return system_msgs + [summary_msg] + recent
