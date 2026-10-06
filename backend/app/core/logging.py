import logging
import sys
from loguru import logger
from app.core.config import settings


class InterceptHandler(logging.Handler):
    """Intercept standard Python logging messages and route to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure structured logging using Loguru."""
    # Remove default loguru handler
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Add console stream handler
    logger.add(
        sys.stdout,
        colorize=True,
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
    )

    # Intercept standard library loggers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy.engine", "gunicorn", "gunicorn.error", "gunicorn.access"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False
