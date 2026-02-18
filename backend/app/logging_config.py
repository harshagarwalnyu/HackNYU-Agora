"""Centralized logging configuration for Agora backend.
Sets up JSON-formatted logging with DEBUG level throughout.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

from pythonjsonlogger.jsonlogger import JsonFormatter  # type: ignore[attr-defined]


class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter with additional context."""

    def add_fields(
        self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]
    ) -> None:

        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno


def setup_logging(log_level: str = "DEBUG", log_file: str | None = None) -> None:
    """
    Configure application-wide logging with JSON formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to console only.
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    # Respect chosen log level instead of forcing DEBUG
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

    json_formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(logger)s %(module)s %(function)s %(line)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        # Respect chosen log level for file handler as well
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

    logger.debug(
        "Logging configured successfully",
        extra={"log_level": log_level, "log_file": log_file, "handlers": len(logger.handlers)},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def log_exception(
    logger: logging.Logger,
    message: str,
    exception: Exception,
    extra_context: Dict[str, Any] | None = None,
) -> None:
    """
    Standardized exception logging with automatic error type detection.
    
    This utility centralizes the repeated pattern of logging exceptions with
    error type and stringified message, reducing code duplication across the
    backend.

    Args:
        logger: Logger instance to use
        message: Human-readable error message
        exception: The exception that occurred
        extra_context: Additional context fields to log (optional)

    Example:
        try:
            await some_operation()
        except Exception as e:
            log_exception(logger, "Operation failed", e, {"job_id": job_id})
    """
    context = {
        "error": str(exception),
        "error_type": type(exception).__name__,
    }
    if extra_context:
        context.update(extra_context)
    
    logger.error(message, extra=context, exc_info=True)
