"""Retry helpers with exponential backoff."""

import logging
import time
from functools import wraps
from typing import Callable, Optional, Tuple, Type, Union

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    predicate: Optional[Callable[[Exception], bool]] = None,
) -> Callable:
    """Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exceptions: Tuple of exception types to catch.
        predicate: Optional callable that receives the exception and returns
            True if the call should be retried. If None, all matching exceptions
            are retried.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[BaseException] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # pylint: disable=broad-except
                    last_exception = exc
                    if attempt == max_retries:
                        raise

                    if predicate is not None and not predicate(exc):
                        raise

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            # Should never reach here, but keeps mypy happy.
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


def is_transient_google_error(exc: BaseException) -> bool:
    """Return True for Google API errors that are safe to retry."""
    # HttpError with a 5xx status or rate-limit status should be retried.
    status = getattr(exc, "resp", None) and getattr(exc.resp, "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    # Connection/timeout errors from underlying transport.
    if "Connection" in type(exc).__name__ or "Timeout" in type(exc).__name__:
        return True
    return False


def is_transient_llm_error(exc: BaseException) -> bool:
    """Return True for LLM errors that are safe to retry."""
    # OpenAI/Anthropic rate limits and server errors.
    if hasattr(exc, "status_code"):
        return exc.status_code in (429, 500, 502, 503)
    error_type = type(exc).__name__.lower()
    return "ratelimit" in error_type or "apierror" in error_type or "timeout" in error_type
