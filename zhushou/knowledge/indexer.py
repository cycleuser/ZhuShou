"""Knowledge base indexer — chunk, embed, and store documents."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from zhushou.knowledge.kb_config import KBConfig

logger = logging.getLogger(__name__)


class KBIndexer:
    """Chunk documents and store them in a ChromaDB collection.

    Chunking parameters (size, overlap, min) and the embedding model
    are read from *config*.  The chunking algorithm and metadata format
    are compatible with GangDan.
    """

    def __init__(self, config: KBConfig) -> None:
        self._config = config
        self._chroma_client: Any = None
        self._chroma_available: bool = False
        self._init_chroma()

    # ── ChromaDB initialisation ───────────────────────────────────────

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore[import-untyped]

            chroma_dir = self._config.chroma_path
            os.makedirs(chroma_dir, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
            self._chroma_available = True
        except Exception:
            self._chroma_available = False
            logger.info("ChromaDB not available — indexing disabled")

    # ── Public API ────────────────────────────────────────────────────

    def index_source(self, source_name: str) -> tuple[int, int]:
        """Index all ``.md`` / ``.txt`` files for *source_name*.

        Returns ``(total_chunks, files_indexed)``.
        """
        if not self._chroma_available:
            logger.warning("ChromaDB not available, cannot index")
            return 0, 0

        source_dir = self._config.docs_path / source_name
        if not source_dir.is_dir():
            logger.warning("Source directory not found: %s", source_dir)
            return 0, 0

        files = [
            f for f in source_dir.iterdir()
            if f.is_file() and f.suffix in (".md", ".txt")
        ]
        if not files:
            return 0, 0

        collection = self._chroma_client.get_or_create_collection(
            name=source_name,
            metadata={"hnsw:space": "cosine"},
        )

        total_chunks = 0
        files_indexed = 0

        for filepath in files:
            try:
                content = filepath.read_text(encoding="utf-8")
            except Exception:
                logger.warning("Failed to read %s", filepath)
                continue

            doc_lang = self._detect_language(content)
            chunks = self._chunk_text(
                content,
                self._config.chunk_size,
                self._config.chunk_overlap,
            )

            documents: list[str] = []
            embeddings: list[list[float]] = []
            metadatas: list[dict] = []
            ids: list[str] = []

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < self._config.min_chunk_size:
                    continue
                try:
                    emb = self._embed(chunk)
                except Exception:
                    logger.warning("Embedding failed for chunk %d of %s", i, filepath.name)
                    continue

                doc_id = hashlib.md5(f"{filepath.name}_{i}".encode()).hexdigest()
                documents.append(chunk)
                embeddings.append(emb)
                metadatas.append({
                    "source": source_name,
                    "file": filepath.name,
                    "chunk": i,
                    "language": doc_lang,
                })
                ids.append(doc_id)

            if documents:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                total_chunks += len(documents)
                files_indexed += 1
                logger.info(
                    "Indexed %s/%s: %d chunks",
                    source_name, filepath.name, len(documents),
                )

        return total_chunks, files_indexed

    def list_collections(self) -> list[str]:
        """Return names of all indexed collections."""
        if not self._chroma_available:
            return []
        try:
            return [c.name for c in self._chroma_client.list_collections()]
        except Exception:
            return []

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

    def delete_collection(self, name: str) -> bool:
        """Delete a ChromaDB collection by *name*.

        Returns ``True`` if the collection was found and deleted.
        """
        if not self._chroma_available:
            return False
        try:
            self._chroma_client.delete_collection(name)
            return True
        except Exception:
            logger.warning("Failed to delete collection %s", name)
            return False

    # ── Text chunking (GangDan-compatible) ────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split *text* into overlapping chunks.

        Algorithm matches GangDan's ``_chunk_text``: character-based
        sliding window with configurable size and overlap.
        """
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks

    # ── Embedding via Ollama ──────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text* via Ollama."""
        url = f"{self._config.ollama_url}/api/embed"
        payload = {
            "model": self._config.embedding_model,
            "input": text,
        }
        resp = httpx.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        # Ollama /api/embed returns {"embeddings": [[...], ...]}
        embeddings = data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        # Fallback for older Ollama versions
        return data.get("embedding", [])

    # ── Language detection ────────────────────────────────────────────

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect document language from the first 500 characters.

        Uses Unicode character ranges.  Returns ISO 639-1 code.
        """
        sample = text[:500]
        counts: dict[str, int] = {"zh": 0, "ja": 0, "ko": 0, "ru": 0}
        for ch in sample:
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF:
                counts["zh"] += 1
            elif 0x3040 <= cp <= 0x30FF:
                counts["ja"] += 1
            elif 0xAC00 <= cp <= 0xD7AF:
                counts["ko"] += 1
            elif 0x0400 <= cp <= 0x04FF:
                counts["ru"] += 1

        if counts["zh"] > 10:
            return "zh"
        if counts["ja"] > 5:
            return "ja"
        if counts["ko"] > 5:
            return "ko"
        if counts["ru"] > 10:
            return "ru"
        return "en"
