"""Loguru logging configuration for the application."""

import logging
import sys
from types import FrameType

from loguru import logger

from app.config import LOG_LEVEL


class InterceptHandler(logging.Handler):
    """Route stdlib logging records through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        current: FrameType | None = logging.currentframe()
        depth = 2
        while current is not None and current.f_code.co_filename == logging.__file__:
            current = current.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging() -> None:
    """Configure loguru and intercept stdlib loggers (e.g. uvicorn)."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.handlers = [InterceptHandler()]
        stdlib_logger.propagate = False


__all__ = ["configure_logging", "logger"]
