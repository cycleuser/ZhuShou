"""Vector-based semantic memory with ChromaDB backend and numpy fallback.

When ChromaDB is available, embeddings and similarity search are
handled by Chroma.  Otherwise a simple in-memory list with substring
matching is used as a graceful fallback.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

_CHROMA_DIR = Path.home() / ".zhushou" / "chroma"


class VectorMemory:
    """Semantic memory store with pluggable backends.

    Parameters
    ----------
    persist_dir : str | Path | None
        ChromaDB persistence directory (ignored for fallback mode).
    collection_name : str
        ChromaDB collection name.
    """

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str = "zhushou_memory",
    ) -> None:
        self._persist_dir: Path = Path(persist_dir) if persist_dir else _CHROMA_DIR
        self._collection_name: str = collection_name
        self._chroma_client: Any = None
        self._collection: Any = None
        self._fallback_store: list[dict[str, Any]] = []
        self._use_chroma: bool = False
        self._init_backend()

    # ------------------------------------------------------------------
    # Backend initialisation
    # ------------------------------------------------------------------

    def _init_backend(self) -> None:
        """Try to initialise ChromaDB; fall back to in-memory list."""
        try:
            import chromadb  # type: ignore[import-untyped]

            os.makedirs(self._persist_dir, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(self._persist_dir),
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=self._collection_name,
            )
            self._use_chroma = True
        except Exception:
            # ChromaDB not installed or failed to initialise
            self._use_chroma = False
            self._fallback_store = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, text: str, metadata: Optional[dict[str, Any]] = None) -> None:
        """Store a text snippet with optional metadata.

        Parameters
        ----------
        text : str
            The text to store.
        metadata : dict | None
            Arbitrary metadata attached to the entry.
        """
        if not text:
            return

        doc_id = self._make_id(text)

        if self._use_chroma and self._collection is not None:
            meta = metadata or {}
            # ChromaDB requires metadata values to be str/int/float/bool
            safe_meta = {
                k: v for k, v in meta.items()
                if isinstance(v, (str, int, float, bool))
            }
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[safe_meta] if safe_meta else None,
            )
        else:
            # Fallback: simple in-memory list
            entry: dict[str, Any] = {
                "id": doc_id,
                "text": text,
                "metadata": metadata or {},
            }
            # Avoid duplicates
            existing_ids = {e["id"] for e in self._fallback_store}
            if doc_id not in existing_ids:
                self._fallback_store.append(entry)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for texts similar to *query*.

        Returns
        -------
        list[dict]
            Each dict has ``"text"``, ``"metadata"``, and ``"score"`` keys.
        """
        if not query:
            return []

        if self._use_chroma and self._collection is not None:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(top_k, max(self._collection.count(), 1)),
                )
                output: list[dict[str, Any]] = []
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                for i, doc in enumerate(documents):
                    output.append({
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "score": 1.0 - (distances[i] if i < len(distances) else 0.0),
                    })
                return output
            except Exception:
                return []
        else:
            # Fallback: simple substring / word-overlap matching
            return self._fallback_search(query, top_k)

    def clear(self) -> None:
        """Remove all stored entries."""
        if self._use_chroma and self._chroma_client is not None:
            try:
                self._chroma_client.delete_collection(self._collection_name)
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self._collection_name,
                )
            except Exception:
                pass
        self._fallback_store.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fallback_search(
        self, query: str, top_k: int
    ) -> list[dict[str, Any]]:
        """Rank stored entries by simple word-overlap score."""
        query_words = set(query.lower().split())
        if not query_words:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self._fallback_store:
            text: str = entry.get("text", "")
            text_words = set(text.lower().split())
            if not text_words:
                continue
            overlap = len(query_words & text_words)
            score = overlap / max(len(query_words | text_words), 1)
            # Boost exact substring matches
            if query.lower() in text.lower():
                score += 0.5
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, entry in scored[:top_k]:
            results.append({
                "text": entry["text"],
                "metadata": entry.get("metadata", {}),
                "score": round(score, 4),
            })
        return results

    @staticmethod
    def _make_id(text: str) -> str:
        """Generate a deterministic ID for a text snippet."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def __repr__(self) -> str:
        backend = "chroma" if self._use_chroma else "fallback"
        return f"VectorMemory(backend={backend!r})"
