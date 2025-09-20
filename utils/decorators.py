"""
Reusable Decorators

Common decorators for error handling, retries, logging, and more.
"""

import time
import functools
import logging
from typing import Any, Callable, Optional, Tuple
from config.settings import Config


def handle_errors(
    default_return=None,
    log_errors: bool = True,
    raise_on_error: bool = False,
    error_message: Optional[str] = None
):
    """
    Decorator for consistent error handling.

    Args:
        default_return: Value to return on error
        log_errors: Whether to log errors
        raise_on_error: Whether to re-raise exceptions
        error_message: Custom error message

    Returns:
        Decorated function

    Examples:
        >>> @handle_errors(default_return=False, log_errors=True)
        ... def risky_function():
        ...     return 1 / 0
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = logging.getLogger(func.__module__)
                    msg = error_message or f"Error in {func.__name__}"
                    logger.error(f"{msg}: {str(e)}", exc_info=True)

                if raise_on_error:
                    raise

                return default_return

        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts (seconds)
        backoff: Backoff multiplier for delays
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function

    Examples:
        >>> @with_retry(max_attempts=3, delay=1.0)
        ... def unstable_network_call():
        ...     return requests.get('https://api.example.com')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

                        # Log retry attempt
                        logger = logging.getLogger(func.__module__)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}: {str(e)}"
                        )
                    else:
                        # Final attempt failed
                        logger = logging.getLogger(func.__module__)
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            # Re-raise the last exception after all attempts failed
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def require_config(*required_keys: str):
    """
    Decorator to ensure required configuration values exist.

    Args:
        *required_keys: Configuration keys that must be present

    Returns:
        Decorated function

    Raises:
        ValueError: If required configuration is missing

    Examples:
        >>> @require_config('DATABASE_PATH', 'SIGNAL_CLI_PATH')
        ... def initialize_service():
        ...     return ServiceClass()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = Config()
            missing = []

            for key in required_keys:
                if not hasattr(config, key) or getattr(config, key) is None:
                    missing.append(key)

            if missing:
                raise ValueError(
                    f"Missing required configuration for {func.__name__}: {', '.join(missing)}"
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator


def log_execution_time(
    log_level: str = "INFO",
    include_args: bool = False
):
    """
    Decorator to log function execution time.

    Args:
        log_level: Log level to use (DEBUG, INFO, WARNING, etc.)
        include_args: Whether to include function arguments in log

    Returns:
        Decorated function

    Examples:
        >>> @log_execution_time(log_level="DEBUG")
        ... def slow_function():
        ...     time.sleep(1)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = time.time()

            # Log function call
            if include_args:
                logger.log(
                    getattr(logging, log_level),
                    f"Starting {func.__name__} with args={args}, kwargs={kwargs}"
                )
            else:
                logger.log(
                    getattr(logging, log_level),
                    f"Starting {func.__name__}"
                )

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                # Log completion
                logger.log(
                    getattr(logging, log_level),
                    f"Completed {func.__name__} in {elapsed:.2f}s"
                )

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Failed {func.__name__} after {elapsed:.2f}s: {str(e)}"
                )
                raise

        return wrapper
    return decorator


def singleton(cls):
    """
    Decorator to make a class a singleton.

    Returns:
        Singleton instance of the class

    Examples:
        >>> @singleton
        ... class DatabaseConnection:
        ...     def __init__(self):
        ...         self.connection = create_connection()
    """
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def validate_input(**validators):
    """
    Decorator to validate function inputs.

    Args:
        **validators: Mapping of parameter names to validator functions

    Returns:
        Decorated function

    Examples:
        >>> from utils.validators import validate_phone_number
        >>> @validate_input(phone=validate_phone_number)
        ... def send_message(phone: str, message: str):
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # Validate specified parameters
            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    is_valid, result = validator(value)

                    if not is_valid:
                        raise ValueError(
                            f"Invalid {param_name} for {func.__name__}: {result}"
                        )

                    # Update with normalized value if provided
                    if result is not None and result != value:
                        bound.arguments[param_name] = result

            return func(*bound.args, **bound.kwargs)

        return wrapper
    return decorator


def async_to_sync(func: Callable) -> Callable:
    """
    Decorator to convert async function to sync.

    Useful for backwards compatibility or testing.

    Returns:
        Synchronous version of the function

    Examples:
        >>> @async_to_sync
        ... async def async_function():
        ...     await asyncio.sleep(1)
        ...     return "done"
    """
    import asyncio

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return wrapper


def cache_result(ttl: int = 300):
    """
    Simple caching decorator with TTL.

    Args:
        ttl: Time to live in seconds (default: 5 minutes)

    Returns:
        Decorated function with caching

    Examples:
        >>> @cache_result(ttl=60)
        ... def expensive_calculation(x):
        ...     return x ** 2
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_time = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            key = str(args) + str(kwargs)

            # Check if cached and not expired
            if key in cache:
                if time.time() - cache_time[key] < ttl:
                    return cache[key]
                else:
                    # Remove expired entry
                    del cache[key]
                    del cache_time[key]

            # Calculate and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = time.time()

            return result

        # Add cache clear method
        wrapper.clear_cache = lambda: (cache.clear(), cache_time.clear())

        return wrapper
    return decorator