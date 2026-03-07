"""Knowledge base retriever — search indexed documents via vector similarity."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from zhushou.knowledge.kb_config import KBConfig

logger = logging.getLogger(__name__)


class KBRetriever:
    """Search indexed knowledge base collections and build context strings.

    If ChromaDB is not available, all search methods return empty results.
    """

    def __init__(self, config: KBConfig) -> None:
        self._config = config
        self._chroma_client: Any = None
        self._chroma_available: bool = False
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore[import-untyped]

            chroma_dir = self._config.chroma_path
            if chroma_dir.is_dir():
                self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
                self._chroma_available = True
        except Exception:
            self._chroma_available = False

    # ── Public API ────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        """Search indexed collections for documents similar to *query*.

        Returns a list of ``{"text", "metadata", "distance"}`` dicts,
        sorted by ascending distance (most relevant first).
        """
        if not self._chroma_available or not query:
            return []

        top_k = top_k or self._config.top_k
        try:
            query_emb = self._embed(query)
        except Exception:
            logger.warning("Failed to embed query")
            return []

        target_collections = collections or self._all_collection_names()
        results: list[dict] = []
        seen_ids: set[str] = set()

        for coll_name in target_collections:
            try:
                coll = self._chroma_client.get_collection(coll_name)
            except Exception:
                continue

            count = coll.count()
            if count == 0:
                continue

            try:
                hits = coll.query(
                    query_embeddings=[query_emb],
                    n_results=min(top_k, count),
                )
            except Exception:
                continue

            documents = hits.get("documents", [[]])[0]
            metadatas = hits.get("metadatas", [[]])[0]
            distances = hits.get("distances", [[]])[0]
            ids = hits.get("ids", [[]])[0]

            for i, doc in enumerate(documents):
                doc_id = ids[i] if i < len(ids) else ""
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                dist = distances[i] if i < len(distances) else 1.0
                if dist > 0.5:
                    continue
                results.append({
                    "text": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": dist,
                })

        results.sort(key=lambda r: r["distance"])
        return results[:top_k]

    def build_context(
        self,
        query: str,
        collections: list[str] | None = None,
        max_chars: int = 6000,
    ) -> str:
        """Search and format results into a markdown context block.

        Includes source attribution for each snippet.
        """
        hits = self.search(query, collections)
        if not hits:
            return ""

        parts: list[str] = []
        total_chars = 0
        for hit in hits:
            text = hit["text"]
            meta = hit.get("metadata", {})
            source = meta.get("source", "unknown")
            filename = meta.get("file", "")
            attribution = f"[{source}/{filename}]" if filename else f"[{source}]"

            snippet = f"{attribution}\n{text}\n"
            if total_chars + len(snippet) > max_chars:
                break
            parts.append(snippet)
            total_chars += len(snippet)

        if not parts:
            return ""

        return "## Relevant Documentation\n\n" + "\n---\n".join(parts)

    def list_collections(self) -> list[str]:
        """Return names of all indexed collections."""
        return self._all_collection_names()

    def get_stats(self) -> dict[str, int]:
        """Return document counts per collection."""
        if not self._chroma_available:
            return {}
        stats: dict[str, int] = {}
        try:
            for coll in self._chroma_client.list_collections():
                stats[coll.name] = coll.count()
        except Exception:
            pass
        return stats

    # ── Internals ─────────────────────────────────────────────────────

    def _all_collection_names(self) -> list[str]:
        if not self._chroma_available:
            return []
        try:
            return [c.name for c in self._chroma_client.list_collections()]
        except Exception:
            return []

    def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector via Ollama."""
        url = f"{self._config.ollama_url}/api/embed"
        payload = {
            "model": self._config.embedding_model,
            "input": text,
        }
        resp = httpx.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        return data.get("embedding", [])
