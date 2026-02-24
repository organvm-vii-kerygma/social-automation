"""Exponential backoff retry with jitter for resilient API calls.

Wraps callables with configurable retry logic: max attempts,
base delay, exponential multiplier, and random jitter.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (RuntimeError, OSError, ConnectionError)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts: {last_error}")


def retry(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    sleep_func: Callable[[float], None] | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute func with exponential backoff retry.

    Args:
        func: Callable to execute.
        config: Retry configuration. Uses defaults if None.
        sleep_func: Sleep function (injectable for testing). Defaults to time.sleep.
        *args, **kwargs: Passed to func.

    Returns:
        The return value of func on success.

    Raises:
        RetryError: If all attempts fail.
    """
    cfg = config or RetryConfig()
    do_sleep = sleep_func or time.sleep
    last_exc: Exception | None = None

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except cfg.retryable_exceptions as exc:
            last_exc = exc
            if attempt == cfg.max_attempts:
                break
        except Exception:
            raise

        delay = min(cfg.base_delay * (cfg.multiplier ** (attempt - 1)), cfg.max_delay)
        if cfg.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        do_sleep(delay)

    raise RetryError(cfg.max_attempts, last_exc)  # type: ignore[arg-type]
