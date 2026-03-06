"""Simple conversation message store."""

from __future__ import annotations

from typing import Any


class ConversationManager:
    """In-memory conversation message list with convenience accessors.

    Each message is a plain dict with at least ``role`` and ``content``
    keys, plus an optional ``metadata`` dict for bookkeeping (timestamps,
    token counts, etc.).
    """

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []

    # ── Public API ─────────────────────────────────────────────────────

    def add(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a message to the conversation.

        Parameters
        ----------
        role:
            One of ``"user"``, ``"assistant"``, ``"system"``, ``"tool"``.
        content:
            The message text.
        metadata:
            Optional extra data (e.g. timestamp, token count).
        """
        msg: dict[str, Any] = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata
        self._messages.append(msg)

    def get_recent(self, n: int = 50) -> list[dict[str, Any]]:
        """Return the last *n* messages."""
        return list(self._messages[-n:])

    def get_all(self) -> list[dict[str, Any]]:
        """Return a copy of the full message list."""
        return list(self._messages)

    def clear(self) -> None:
        """Reset the conversation history."""
        self._messages.clear()

    # ── Dunder helpers ─────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._messages)

    def __bool__(self) -> bool:
        return bool(self._messages)

    def __repr__(self) -> str:
        return f"ConversationManager(messages={len(self._messages)})"
