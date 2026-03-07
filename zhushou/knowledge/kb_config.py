"""Knowledge base configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_KB_DIR = Path.home() / ".zhushou" / "kb"


@dataclass
class KBConfig:
    """Configuration for the knowledge base subsystem."""

    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 800
    chunk_overlap: int = 150
    min_chunk_size: int = 50
    top_k: int = 10
    docs_dir: str = ""
    chroma_dir: str = ""
    ollama_url: str = "http://localhost:11434"

    def __post_init__(self) -> None:
        if not self.docs_dir:
            self.docs_dir = str(_DEFAULT_KB_DIR / "docs")
        if not self.chroma_dir:
            self.chroma_dir = str(_DEFAULT_KB_DIR / "chroma")

    @property
    def docs_path(self) -> Path:
        return Path(self.docs_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir)


def load_kb_config(path: str | Path | None = None) -> KBConfig:
    """Load KB config from JSON, merging with defaults."""
    config_path = Path(path) if path else _DEFAULT_KB_DIR / "config.json"
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Only pass known fields
            known = {f.name for f in KBConfig.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known}
            return KBConfig(**filtered)
        except Exception:
            logger.warning("Failed to load KB config from %s, using defaults", config_path)
    return KBConfig()


def save_kb_config(config: KBConfig, path: str | Path | None = None) -> None:
    """Persist KB config to JSON."""
    config_path = Path(path) if path else _DEFAULT_KB_DIR / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(asdict(config), fh, indent=2, ensure_ascii=False)
