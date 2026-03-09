"""Rotating disk-log handler configuration.

Mirrors the rotating-log strategy used in Symphony's ``log_file.ex``:
fixed-size log files that rotate automatically so disk usage stays bounded.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_DEFAULT_BACKUP_COUNT = 5
_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_rotating_log(
    log_path: str | Path,
    *,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
    level: int = logging.INFO,
    fmt: str = _DEFAULT_FORMAT,
    logger_name: str | None = None,
) -> logging.Logger:
    """Attach a ``RotatingFileHandler`` to *logger_name* (or root).

    Parameters
    ----------
    log_path:
        Absolute or relative path to the primary log file.  Parent
        directories are created automatically.
    max_bytes:
        Maximum size (in bytes) per log file before rotation.
    backup_count:
        How many rotated files to keep (``*.1``, ``*.2``, ...).
    level:
        Logging level for the handler.
    fmt:
        Format string for log records.
    logger_name:
        Which logger to attach to.  ``None`` means the root logger.

    Returns
    -------
    The configured :class:`logging.Logger` instance.
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=str(path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))

    target_logger = logging.getLogger(logger_name)
    target_logger.addHandler(handler)
    target_logger.setLevel(min(target_logger.level or logging.WARNING, level))

    return target_logger
