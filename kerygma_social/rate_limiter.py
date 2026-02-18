"""Token bucket rate limiter for social API calls.

Prevents exceeding platform rate limits by controlling the
rate of outgoing requests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


class RateLimitExceeded(Exception):
    """Raised when rate limit would be exceeded and blocking is disabled."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after:.1f}s")


@dataclass
class RateLimiterConfig:
    """Token bucket configuration."""
    tokens_per_second: float = 1.0
    max_tokens: float = 10.0
    initial_tokens: float | None = None  # Defaults to max_tokens


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        config: RateLimiterConfig | None = None,
        clock: Callable[[], float] | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        cfg = config or RateLimiterConfig()
        self._rate = cfg.tokens_per_second
        self._max = cfg.max_tokens
        self._tokens = cfg.initial_tokens if cfg.initial_tokens is not None else cfg.max_tokens
        self._clock = clock or time.monotonic
        self._sleep = sleep_func or time.sleep
        self._last_refill = self._clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        self._tokens = min(self._max, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def acquire(self, tokens: float = 1.0, block: bool = True) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.
            block: If True, sleep until tokens are available.
                   If False, raise RateLimitExceeded.

        Returns:
            True if tokens were acquired.
        """
        self._refill()

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True

        if not block:
            deficit = tokens - self._tokens
            retry_after = deficit / self._rate
            raise RateLimitExceeded(retry_after)

        # Block until enough tokens
        deficit = tokens - self._tokens
        wait_time = deficit / self._rate
        self._sleep(wait_time)
        self._refill()
        self._tokens -= tokens
        return True

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._tokens
