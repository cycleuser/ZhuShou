"""Knowledge base manager — high-level facade for download, index, and search."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from zhushou.knowledge.cheatsheets import CHEATSHEETS, get_cheatsheet
from zhushou.knowledge.doc_manager import DocDownloader
from zhushou.knowledge.doc_sources import DOC_SOURCES, list_available_sources
from zhushou.knowledge.indexer import KBIndexer
from zhushou.knowledge.kb_config import (
    KBConfig,
    delete_user_kb_entry,
    load_user_kbs,
    sanitize_kb_name,
    save_user_kb,
)
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

        Each entry: ``{"key", "name", "type", "downloaded", "indexed", "cheatsheet"}``.
        Built-in sources have ``type="builtin"``; user-created KBs have ``type="user"``.
        """
        downloaded = {d["name"] for d in self._downloader.list_downloaded()}
        indexed_stats = self._indexer.get_stats()
        result: list[dict] = []

        # Built-in sources
        for src in list_available_sources():
            key = src["key"]
            result.append({
                "key": key,
                "name": src["name"],
                "type": "builtin",
                "downloaded": key in downloaded,
                "indexed": key in indexed_stats,
                "index_chunks": indexed_stats.get(key, 0),
                "cheatsheet": key in CHEATSHEETS,
            })

        # User-created KBs
        user_kbs = load_user_kbs(self._config)
        for internal_name, meta in user_kbs.items():
            result.append({
                "key": internal_name,
                "name": meta.get("display_name", internal_name),
                "type": "user",
                "downloaded": True,
                "indexed": internal_name in indexed_stats,
                "index_chunks": indexed_stats.get(internal_name, 0),
                "cheatsheet": False,
                "file_count": meta.get("file_count", 0),
                "languages": meta.get("languages", []),
                "created": meta.get("created", ""),
            })

        return result

    def list_indexed(self) -> dict[str, int]:
        """Return document counts per indexed collection."""
        return self._indexer.get_stats()

    # ── Web crawling (Huan integration) ────────────────────────────

    def crawl(
        self,
        url: str,
        name: str | None = None,
        max_pages: int = 200,
        prefix: str | None = None,
    ) -> tuple[int, str]:
        """Crawl a website using Huan and auto-index the results.

        Parameters
        ----------
        url : str
            Starting URL to crawl.
        name : str | None
            Source name for the KB collection.  Defaults to the domain.
        max_pages : int
            Maximum pages to save.
        prefix : str | None
            Only follow URLs that start with this prefix.

        Returns
        -------
        tuple[int, str]
            ``(pages_saved, output_dir)``

        Raises
        ------
        ImportError
            If the ``huan`` package is not installed.
        RuntimeError
            If the crawl fails.
        """
        try:
            from huan import archive_site
        except ImportError:
            raise ImportError(
                "huan is required for web crawling.  Install with:  pip install huan"
            )

        from urllib.parse import urlparse

        domain = urlparse(url).netloc.replace(":", "_")
        source_name = name or domain
        output_dir = str(self._config.docs_path / source_name)

        result = archive_site(
            url,
            output_dir=output_dir,
            max_pages=max_pages,
            prefix=prefix,
            extractor="readability",
            metadata=True,
        )

        if not result.success:
            raise RuntimeError(f"Crawl failed: {result.error}")

        pages_saved = result.data.get("pages_saved", 0) if result.data else 0

        # Auto-index the crawled content
        try:
            self.index(source_name)
        except Exception:
            logger.warning("Auto-indexing after crawl failed for %s", source_name)

        return pages_saved, output_dir

    # ── User KB management ─────────────────────────────────────────

    _ALLOWED_SUFFIXES = {".md", ".txt"}

    def upload_files(
        self,
        name: str,
        file_paths: list[str | Path],
        *,
        duplicate_action: str = "skip",
    ) -> dict:
        """Upload markdown/text files to create or extend a user KB.

        Parameters
        ----------
        name : str
            Human-readable display name for the KB.
        file_paths : list[str | Path]
            Paths to ``.md`` / ``.txt`` files.
        duplicate_action : str
            ``"skip"`` (default) or ``"overwrite"`` existing files.

        Returns
        -------
        dict
            ``{"internal_name", "saved", "skipped", "errors"}``.
        """
        internal_name = sanitize_kb_name(name)
        dest_dir = self._config.docs_path / internal_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        saved = 0
        skipped = 0
        errors: list[str] = []

        for fp in file_paths:
            src = Path(fp)
            if not src.is_file():
                errors.append(f"Not a file: {src}")
                continue
            if src.suffix.lower() not in self._ALLOWED_SUFFIXES:
                errors.append(f"Unsupported format: {src.name}")
                continue

            target = dest_dir / src.name
            if target.exists() and duplicate_action == "skip":
                skipped += 1
                continue

            try:
                shutil.copy2(src, target)
                saved += 1
            except Exception as exc:
                errors.append(f"Copy failed for {src.name}: {exc}")

        # Update manifest
        total_files = sum(1 for f in dest_dir.iterdir() if f.is_file())
        save_user_kb(
            self._config, internal_name, name,
            file_count=total_files,
        )

        # Auto-index
        try:
            self._indexer.index_source(internal_name)
        except Exception:
            logger.warning("Auto-indexing after upload failed for %s", internal_name)

        return {
            "internal_name": internal_name,
            "saved": saved,
            "skipped": skipped,
            "errors": errors,
        }

    def import_directory(
        self,
        name: str,
        dir_path: str | Path,
    ) -> dict:
        """Recursively import ``.md`` / ``.txt`` files from a directory.

        Parameters
        ----------
        name : str
            Human-readable display name for the KB.
        dir_path : str | Path
            Source directory to scan.

        Returns
        -------
        dict
            ``{"internal_name", "saved", "errors"}``.
        """
        src_dir = Path(dir_path)
        if not src_dir.is_dir():
            return {"internal_name": "", "saved": 0, "errors": [f"Not a directory: {src_dir}"]}

        internal_name = sanitize_kb_name(name)
        dest_dir = self._config.docs_path / internal_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        saved = 0
        errors: list[str] = []

        for src_file in src_dir.rglob("*"):
            if not src_file.is_file():
                continue
            if src_file.suffix.lower() not in self._ALLOWED_SUFFIXES:
                continue
            # Flatten into dest_dir but keep parent dir prefix to avoid collisions
            relative = src_file.relative_to(src_dir)
            safe_name = str(relative).replace("/", "__").replace("\\", "__")
            target = dest_dir / safe_name
            try:
                shutil.copy2(src_file, target)
                saved += 1
            except Exception as exc:
                errors.append(f"Copy failed for {relative}: {exc}")

        total_files = sum(1 for f in dest_dir.iterdir() if f.is_file())
        save_user_kb(
            self._config, internal_name, name,
            file_count=total_files,
        )

        # Auto-index
        try:
            self._indexer.index_source(internal_name)
        except Exception:
            logger.warning("Auto-indexing after import failed for %s", internal_name)

        return {
            "internal_name": internal_name,
            "saved": saved,
            "errors": errors,
        }

    def list_user_kbs(self) -> list[dict]:
        """Return metadata for all user-created KBs.

        Each entry: ``{"key", "display_name", "created", "file_count", "languages", "indexed"}``.
        """
        indexed_stats = self._indexer.get_stats()
        user_kbs = load_user_kbs(self._config)
        result: list[dict] = []
        for internal_name, meta in user_kbs.items():
            result.append({
                "key": internal_name,
                "display_name": meta.get("display_name", internal_name),
                "created": meta.get("created", ""),
                "file_count": meta.get("file_count", 0),
                "languages": meta.get("languages", []),
                "indexed": internal_name in indexed_stats,
                "index_chunks": indexed_stats.get(internal_name, 0),
            })
        return result

    def delete_user_kb(self, internal_name: str) -> bool:
        """Delete a user KB: remove docs, ChromaDB collection, and manifest entry.

        Returns ``True`` if something was deleted.
        """
        deleted_something = False

        # Remove docs directory
        docs_dir = self._config.docs_path / internal_name
        if docs_dir.is_dir():
            shutil.rmtree(docs_dir)
            deleted_something = True

        # Remove ChromaDB collection
        if self._indexer.delete_collection(internal_name):
            deleted_something = True

        # Remove manifest entry
        if delete_user_kb_entry(self._config, internal_name):
            deleted_something = True

        return deleted_something
