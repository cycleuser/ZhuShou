"""Document downloader — fetch official docs from GitHub raw URLs."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import httpx

from zhushou.knowledge.doc_sources import DOC_SOURCES

logger = logging.getLogger(__name__)


class DocDownloader:
    """Download framework documentation from registered URLs.

    Files are stored as UTF-8 Markdown in ``docs_dir/{source_name}/*.md``.
    Non-Markdown formats (.rst, .py, .ipynb, .html) are converted on the fly.
    """

    def __init__(self, docs_dir: Path | str, proxy: str = "") -> None:
        self._docs_dir = Path(docs_dir)
        self._proxy = proxy or None

    # ── Public API ────────────────────────────────────────────────────

    def download_source(self, source_name: str) -> tuple[int, list[str]]:
        """Download all docs for *source_name*.

        Returns ``(saved_count, errors)`` where *errors* is a list of
        error description strings (empty on full success).
        """
        source = DOC_SOURCES.get(source_name)
        if not source:
            return 0, [f"Unknown source: {source_name}"]

        dest_dir = self._docs_dir / source_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        saved = 0
        errors: list[str] = []
        transport = None
        if self._proxy:
            transport = httpx.HTTPTransport(proxy=self._proxy)

        with httpx.Client(
            follow_redirects=True,
            timeout=60.0,
            transport=transport,
        ) as client:
            for url in source["urls"]:
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    content = resp.text
                    filename = url.rsplit("/", 1)[-1]
                    content, filename = self._convert_to_md(content, filename)
                    out_path = dest_dir / filename
                    out_path.write_text(content, encoding="utf-8")
                    saved += 1
                    logger.info("Saved %s -> %s", url, out_path)
                except Exception as exc:
                    msg = f"Failed to download {url}: {exc}"
                    logger.warning(msg)
                    errors.append(msg)

        return saved, errors

    def list_downloaded(self) -> list[dict]:
        """Return info about downloaded sources.

        Each entry: ``{"name": ..., "file_count": ..., "files": [...]}``.
        """
        result: list[dict] = []
        if not self._docs_dir.is_dir():
            return result
        for entry in sorted(self._docs_dir.iterdir()):
            if entry.is_dir():
                files = [
                    f.name for f in entry.iterdir()
                    if f.is_file() and f.suffix in (".md", ".txt")
                ]
                if files:
                    result.append({
                        "name": entry.name,
                        "file_count": len(files),
                        "files": sorted(files),
                    })
        return result

    # ── Format conversion ─────────────────────────────────────────────

    @staticmethod
    def _convert_to_md(content: str, filename: str) -> tuple[str, str]:
        """Convert non-Markdown formats to Markdown.

        Returns ``(converted_content, new_filename)``.
        """
        if filename.endswith(".rst"):
            filename = re.sub(r"\.rst$", ".md", filename)
            # Minimal RST -> MD: strip directives, keep content
        elif filename.endswith(".py") or filename.endswith(".ipynb"):
            content = f"```python\n{content}\n```"
            filename = re.sub(r"\.(py|ipynb)$", ".md", filename)
        elif filename.endswith(".html"):
            filename = re.sub(r"\.html$", ".md", filename)
        elif not filename.endswith((".md", ".txt")):
            filename = filename + ".md"
        return content, filename
