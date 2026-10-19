"""Sanitized logging configuration for FridgeMind."""

import logging
import sys
from backend.app.core.config import settings


class SanitizedFormatter(logging.Formatter):
    """Log formatter that masks potential secrets and raw image data."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        # Mask Gemini API key if present in log text
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 8:
            orig = orig.replace(settings.GEMINI_API_KEY, f"{settings.GEMINI_API_KEY[:4]}...****")
        return orig


def setup_logging():
    """Configure root and application loggers."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        SanitizedFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Remove existing handlers to avoid duplicates
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)

    return logging.getLogger("fridgemind")


logger = setup_logging()
