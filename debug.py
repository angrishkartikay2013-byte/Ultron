from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "memory" / "ultron_debug.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("ultron")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
        )
    )
    _logger.addHandler(handler)


def info(message: str) -> None:
    _logger.info(message)


def warning(message: str) -> None:
    _logger.warning(message)


def error(message: str) -> None:
    _logger.error(message)


def exception(message: str) -> None:
    _logger.exception(message)


def log_path() -> str:
    return str(LOG_FILE)
