"""Centralized application logging configuration."""

import logging


def configure_logging(log_level: str) -> None:
    """Configure useful console logging without exposing application secrets."""
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported log level: {log_level}")

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
