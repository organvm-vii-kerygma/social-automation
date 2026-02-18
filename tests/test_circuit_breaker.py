"""Tests for the circuit breaker module."""

import pytest
from kerygma_social.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
)


class TestCircuitBreaker:
    def _clock(self, time: float = 0.0):
        """Create a controllable clock."""
        state = {"now": time}

        def clock():
            return state["now"]

        def advance(dt: float):
            state["now"] += dt

        return clock, advance

    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_success_keeps_closed(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=3),
            clock=clock,
        )
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_calls(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, reset_timeout=60.0),
            clock=clock,
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        with pytest.raises(CircuitOpenError):
            cb.call(lambda: 42)

    def test_transitions_to_half_open(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, reset_timeout=10.0),
            clock=clock,
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        advance(11.0)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, reset_timeout=10.0),
            clock=clock,
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        advance(11.0)
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, reset_timeout=10.0),
            clock=clock,
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        advance(11.0)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail again")))
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        clock, advance = self._clock()
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1),
            clock=clock,
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.failure_count == 1

        cb.call(lambda: "ok")
        assert cb.failure_count == 0
