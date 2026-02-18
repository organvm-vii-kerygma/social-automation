"""Tests for the retry module."""

import pytest
from kerygma_social.retry import retry, RetryConfig, RetryError


class TestRetry:
    def test_succeeds_first_try(self):
        result = retry(lambda: 42, RetryConfig(max_attempts=3))
        assert result == 42

    def test_succeeds_after_failures(self):
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("transient")
            return "ok"

        result = retry(flaky, RetryConfig(max_attempts=3), sleep_func=lambda _: None)
        assert result == "ok"
        assert len(attempts) == 3

    def test_exhausts_retries(self):
        def always_fail():
            raise RuntimeError("permanent")

        with pytest.raises(RetryError) as exc_info:
            retry(always_fail, RetryConfig(max_attempts=2), sleep_func=lambda _: None)
        assert exc_info.value.attempts == 2

    def test_sleep_is_called(self):
        sleeps = []

        def fail_once():
            if not sleeps:
                raise RuntimeError("first")
            return "ok"

        def fake_sleep(t):
            sleeps.append(t)

        retry(fail_once, RetryConfig(max_attempts=2, jitter=False), sleep_func=fake_sleep)
        assert len(sleeps) == 1
        assert sleeps[0] == 1.0  # base_delay

    def test_exponential_backoff(self):
        sleeps = []
        call_count = [0]

        def always_fail():
            call_count[0] += 1
            raise RuntimeError("fail")

        with pytest.raises(RetryError):
            retry(
                always_fail,
                RetryConfig(max_attempts=4, base_delay=1.0, multiplier=2.0, jitter=False),
                sleep_func=lambda t: sleeps.append(t),
            )
        # Delays: 1.0, 2.0, 4.0 (3 sleeps for 4 attempts)
        assert len(sleeps) == 3
        assert sleeps[0] == 1.0
        assert sleeps[1] == 2.0
        assert sleeps[2] == 4.0

    def test_max_delay_cap(self):
        sleeps = []

        def always_fail():
            raise RuntimeError("fail")

        with pytest.raises(RetryError):
            retry(
                always_fail,
                RetryConfig(max_attempts=5, base_delay=10.0, max_delay=15.0, jitter=False),
                sleep_func=lambda t: sleeps.append(t),
            )
        assert all(s <= 15.0 for s in sleeps)

    def test_passes_args(self):
        def add(a, b):
            return a + b

        result = retry(add, RetryConfig(max_attempts=1), None, 3, b=4)
        assert result == 7

    def test_retry_error_contains_last_error(self):
        def fail():
            raise ValueError("specific error")

        with pytest.raises(RetryError) as exc_info:
            retry(fail, RetryConfig(max_attempts=1), sleep_func=lambda _: None)
        assert isinstance(exc_info.value.last_error, ValueError)
        assert "specific error" in str(exc_info.value.last_error)
