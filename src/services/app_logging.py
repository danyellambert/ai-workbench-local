from __future__ import annotations

import logging
import os


_LOGGING_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Configure process-wide logging once for app/runtime modules."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    resolved_level_name = str(level or os.getenv("APP_LOG_LEVEL", "INFO")).strip().upper() or "INFO"
    resolved_level = getattr(logging, resolved_level_name, logging.INFO)
    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)