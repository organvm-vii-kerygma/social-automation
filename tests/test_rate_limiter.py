"""Tests for the rate limiter module."""

import pytest
from kerygma_social.rate_limiter import RateLimiter, RateLimiterConfig, RateLimitExceeded


class TestRateLimiter:
    def _clock(self, start: float = 0.0):
        state = {"now": start}

        def clock():
            return state["now"]

        def advance(dt: float):
            state["now"] += dt

        return clock, advance

    def test_acquire_within_limit(self):
        clock, advance = self._clock()
        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=10.0, max_tokens=10.0),
            clock=clock, sleep_func=lambda _: None,
        )
        assert rl.acquire(tokens=1.0) is True

    def test_acquire_depletes_tokens(self):
        clock, advance = self._clock()
        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=1.0, max_tokens=3.0),
            clock=clock, sleep_func=lambda _: None,
        )
        assert rl.acquire(1.0)
        assert rl.acquire(1.0)
        assert rl.acquire(1.0)
        # Now depleted
        with pytest.raises(RateLimitExceeded):
            rl.acquire(1.0, block=False)

    def test_tokens_refill_over_time(self):
        clock, advance = self._clock()
        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=1.0, max_tokens=5.0, initial_tokens=0.0),
            clock=clock, sleep_func=lambda _: None,
        )
        with pytest.raises(RateLimitExceeded):
            rl.acquire(1.0, block=False)

        advance(2.0)
        assert rl.acquire(1.0)

    def test_max_tokens_cap(self):
        clock, advance = self._clock()
        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=100.0, max_tokens=5.0),
            clock=clock, sleep_func=lambda _: None,
        )
        advance(100.0)
        assert rl.available_tokens <= 5.0

    def test_blocking_acquire(self):
        sleeps = []
        clock, advance = self._clock()

        def fake_sleep(t):
            sleeps.append(t)
            advance(t)

        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=1.0, max_tokens=1.0, initial_tokens=0.0),
            clock=clock, sleep_func=fake_sleep,
        )
        assert rl.acquire(1.0, block=True)
        assert len(sleeps) == 1
        assert sleeps[0] == pytest.approx(1.0)

    def test_rate_limit_exceeded_has_retry_after(self):
        clock, advance = self._clock()
        rl = RateLimiter(
            RateLimiterConfig(tokens_per_second=1.0, max_tokens=1.0, initial_tokens=0.0),
            clock=clock, sleep_func=lambda _: None,
        )
        with pytest.raises(RateLimitExceeded) as exc_info:
            rl.acquire(1.0, block=False)
        assert exc_info.value.retry_after > 0
