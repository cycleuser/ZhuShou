"""Persistent configuration manager for ZhuShou.

Stores user preferences (Python interpreter, LLM provider/model, etc.)
in ``~/.zhushou/config.json``.  CLI arguments always override stored values.
"""

from __future__ import annotations

import json
import logging
import os
from argparse import Namespace
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path.home() / ".zhushou" / "config.json"

# Defaults used when neither CLI arg nor config file provides a value
_DEFAULTS: dict[str, Any] = {
    "python_path": "",
    "provider": "ollama",
    "model": "",
    "api_key": "",
    "base_url": "",
    "proxy": "",
    "timeout": 300,
}


@dataclass
class ZhuShouConfig:
    """Central configuration store.

    Load order:  config.json → CLI args override non-None values.
    """

    python_path: str = ""
    provider: str = "ollama"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    proxy: str = ""
    timeout: int = 300
    first_run_complete: bool = False
    version: int = 1

    # ── I/O ────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str | Path | None = None) -> ZhuShouConfig:
        """Load config from JSON file, falling back to defaults."""
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                known = {f.name for f in cls.__dataclass_fields__.values()}
                filtered = {k: v for k, v in data.items() if k in known}
                return cls(**filtered)
            except Exception:
                logger.warning("Failed to load config from %s, using defaults", config_path)
        return cls()

    def save(self, path: str | Path | None = None) -> None:
        """Persist config to JSON atomically (write .tmp then rename)."""
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = config_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(asdict(self), fh, indent=2, ensure_ascii=False)
            tmp_path.replace(config_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    # ── Merging with CLI args ──────────────────────────────────────

    def resolve(self, args: Namespace) -> Namespace:
        """Merge stored config into CLI *args*.

        CLI args with non-None values take precedence.  For args that
        are ``None`` (meaning the user didn't supply them on the command
        line), fill in from the stored config, falling back to built-in
        defaults.

        Returns the mutated *args* namespace for convenience.
        """
        mapping = {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "proxy": self.proxy,
            "timeout": self.timeout,
        }

        for attr, config_val in mapping.items():
            cli_val = getattr(args, attr, None)
            if cli_val is None:
                # CLI didn't set it → use config value, or built-in default
                final = config_val if config_val else _DEFAULTS.get(attr, "")
                setattr(args, attr, final)

        # Python path: not a CLI arg, but used by pipeline
        if not getattr(args, "python_path", None):
            if self.python_path:
                args.python_path = self.python_path

        return args

    # ── Mutation helpers ───────────────────────────────────────────

    def update(self, path: str | Path | None = None, **kwargs: Any) -> None:
        """Update specific fields and save."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save(path)

    @property
    def is_first_run(self) -> bool:
        """True when setup wizard hasn't been completed yet."""
        return not self.first_run_complete

    @property
    def config_path(self) -> Path:
        return _DEFAULT_CONFIG_PATH

    # ── Display ────────────────────────────────────────────────────

    def to_display_dict(self) -> dict[str, Any]:
        """Return a dict suitable for showing to the user (hides sensitive fields)."""
        d = asdict(self)
        if d.get("api_key"):
            key = d["api_key"]
            d["api_key"] = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
        return d


# ── Module-level convenience functions ─────────────────────────────


def load_config(path: str | Path | None = None) -> ZhuShouConfig:
    """Load config from the default or specified path."""
    return ZhuShouConfig.load(path)


def save_config(config: ZhuShouConfig, path: str | Path | None = None) -> None:
    """Save config to the default or specified path."""
    config.save(path)
