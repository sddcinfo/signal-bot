"""
Centralized Logging Setup

Provides consistent logging configuration across all modules.
"""

import logging
import sys
from typing import Optional
from pathlib import Path
import os
from config.settings import Config


# Cache for loggers
_loggers = {}


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    propagate: bool = False,
    debug_override: bool = False
) -> logging.Logger:
    """
    Setup and return a configured logger instance.

    This function creates a logger with both console and file handlers,
    using consistent formatting across the application.

    Args:
        name: Logger name (typically __name__ from calling module)
        log_file: Optional log file path (defaults to service-specific file)
        level: Log level (defaults to Config.LOG_LEVEL)
        format_string: Custom format string (defaults to Config.LOG_FORMAT)
        propagate: Whether to propagate to parent logger

    Returns:
        Configured logger instance

    Examples:
        >>> logger = setup_logger(__name__)
        >>> logger = setup_logger('MyService', log_file='myservice.log')
    """
    # Return cached logger if exists
    if name in _loggers:
        return _loggers[name]

    config = Config()

    # Determine log level (debug override takes precedence)
    if debug_override:
        log_level = logging.DEBUG
    elif level:
        log_level = getattr(logging, level.upper())
    else:
        # Check environment variable first, then config
        env_level = os.environ.get('LOG_LEVEL', config.LOG_LEVEL)
        log_level = getattr(logging, env_level.upper())

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = propagate

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        format_string or config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log file specified)
    if log_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not setup file logging to {log_file}: {e}")

    # Suppress noisy third-party loggers
    _suppress_noisy_loggers()

    # Cache the logger
    _loggers[name] = logger

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.

    This is a convenience function that returns a cached logger if it exists,
    or creates a new one with default settings.

    Args:
        name: Logger name

    Returns:
        Logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello, world!")
    """
    if name in _loggers:
        return _loggers[name]

    return setup_logger(name)


def _suppress_noisy_loggers():
    """Suppress verbose third-party library loggers."""
    noisy_loggers = [
        'urllib3',
        'requests',
        'httpx',
        'httpcore',
        'google',
        'openai',
        'anthropic',
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def set_log_level(level: str, logger_name: Optional[str] = None):
    """
    Change log level for a specific logger or all loggers.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Optional specific logger name (changes all if None)

    Examples:
        >>> set_log_level('DEBUG')  # Set all to DEBUG
        >>> set_log_level('ERROR', 'MyService')  # Set specific logger
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if logger_name:
        if logger_name in _loggers:
            logger = _loggers[logger_name]
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)
    else:
        # Update all cached loggers
        for logger in _loggers.values():
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)


def get_log_context(
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    message_id: Optional[str] = None
) -> dict:
    """
    Create a log context dictionary for structured logging.

    Args:
        user_id: Optional user UUID
        group_id: Optional group ID
        message_id: Optional message ID

    Returns:
        Context dictionary for logging

    Examples:
        >>> ctx = get_log_context(user_id="abc123")
        >>> logger.info("Processing message", extra=ctx)
    """
    context = {}

    if user_id:
        context['user_id'] = user_id
    if group_id:
        context['group_id'] = group_id
    if message_id:
        context['message_id'] = message_id

    return {'context': context} if context else {}


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for adding context to log messages.

    This adapter automatically includes context information in all log messages.

    Examples:
        >>> logger = get_logger(__name__)
        >>> adapted = LoggerAdapter(logger, {'user_id': 'abc123'})
        >>> adapted.info("User action")  # Will include user_id in log
    """

    def process(self, msg, kwargs):
        """Add context to log message."""
        if 'context' in self.extra:
            # Format context as key=value pairs
            context_str = ' '.join(
                f"{k}={v}" for k, v in self.extra['context'].items()
            )
            return f"[{context_str}] {msg}", kwargs
        return msg, kwargs