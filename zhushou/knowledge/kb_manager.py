"""Knowledge base manager — high-level facade for download, index, and search."""

from __future__ import annotations

import logging
from pathlib import Path

from zhushou.knowledge.cheatsheets import CHEATSHEETS, get_cheatsheet
from zhushou.knowledge.doc_manager import DocDownloader
from zhushou.knowledge.doc_sources import DOC_SOURCES, list_available_sources
from zhushou.knowledge.indexer import KBIndexer
from zhushou.knowledge.kb_config import KBConfig
from zhushou.knowledge.retriever import KBRetriever

logger = logging.getLogger(__name__)


class KBManager:
    """Unified facade for the knowledge base subsystem.

    Ties together the downloader, indexer, and retriever.
    ``build_context()`` prefers the built-in cheatsheet when available
    and falls back to full RAG search for richer context.
    """

    def __init__(self, config: KBConfig | None = None) -> None:
        self._config = config or KBConfig()
        self._downloader = DocDownloader(
            docs_dir=self._config.docs_path,
        )
        self._indexer = KBIndexer(self._config)
        self._retriever = KBRetriever(self._config)

    # ── Download ──────────────────────────────────────────────────────

    def download(self, source_name: str) -> tuple[int, list[str]]:
        """Download official docs for *source_name*.

        Returns ``(saved_count, errors)``.
        """
        return self._downloader.download_source(source_name)

    # ── Index ─────────────────────────────────────────────────────────

    def index(self, source_name: str) -> tuple[int, int]:
        """Index downloaded docs for *source_name*.

        Returns ``(total_chunks, files_indexed)``.
        """
        return self._indexer.index_source(source_name)

    # ── Search ────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        collections: list[str] | None = None,
    ) -> list[dict]:
        """Search indexed collections.  Returns list of hit dicts."""
        return self._retriever.search(query, collections)

    def build_context(
        self,
        query: str,
        collections: list[str] | None = None,
        max_chars: int = 6000,
    ) -> str:
        """Build a context string for injection into LLM prompts.

        Strategy:
        1. If *collections* specifies a single source that has a
           built-in cheatsheet, prepend the cheatsheet.
        2. Append RAG search results (if indexed docs are available).
        3. Return combined context trimmed to *max_chars*.
        """
        parts: list[str] = []
        used_chars = 0

        # 1. Cheatsheet(s) for specified collections
        targets = collections or []
        for name in targets:
            cs = get_cheatsheet(name)
            if cs and used_chars + len(cs) < max_chars:
                parts.append(cs)
                used_chars += len(cs)

        # 2. RAG search
        remaining = max_chars - used_chars
        if remaining > 200:
            rag_context = self._retriever.build_context(
                query, collections, max_chars=remaining,
            )
            if rag_context:
                parts.append(rag_context)

        return "\n\n".join(parts) if parts else ""

    # ── Cheatsheet access ─────────────────────────────────────────────

    @staticmethod
    def get_cheatsheet(name: str) -> str | None:
        """Return the built-in cheatsheet for *name*."""
        return get_cheatsheet(name)

    # ── Listing / stats ───────────────────────────────────────────────

    def list_sources(self) -> list[dict]:
        """Return all known sources with download and index status.

        Each entry: ``{"key", "name", "downloaded", "indexed", "cheatsheet"}``.
        """
        downloaded = {d["name"] for d in self._downloader.list_downloaded()}
        indexed_stats = self._indexer.get_stats()
        result: list[dict] = []
        for src in list_available_sources():
            key = src["key"]
            result.append({
                "key": key,
                "name": src["name"],
                "downloaded": key in downloaded,
                "indexed": key in indexed_stats,
                "index_chunks": indexed_stats.get(key, 0),
                "cheatsheet": key in CHEATSHEETS,
            })
        return result

    def list_indexed(self) -> dict[str, int]:
        """Return document counts per indexed collection."""
        return self._indexer.get_stats()
