"""Circuit breaker for protecting against cascading failures.

Implements a three-state machine:
  CLOSED  → Normal operation, failures are counted
  OPEN    → Requests fail immediately (service assumed down)
  HALF_OPEN → Trial request allowed to test recovery
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is attempted while circuit is OPEN."""

    def __init__(self, reset_at: float) -> None:
        self.reset_at = reset_at
        super().__init__(f"Circuit is OPEN, resets at {reset_at:.1f}")


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout: float = 60.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    """Circuit breaker that tracks failures and opens when threshold is exceeded."""

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config or CircuitBreakerConfig()
        self._clock = clock or time.monotonic
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = self._clock() - self._last_failure_time
            if elapsed >= self._config.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute func through the circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(
                self._last_failure_time + self._config.reset_timeout
            )

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._config.half_open_max_calls:
                raise CircuitOpenError(
                    self._last_failure_time + self._config.reset_timeout
                )
            self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count += 1

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = self._clock()
        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
