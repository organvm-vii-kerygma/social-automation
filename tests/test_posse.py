"""Tests for the posse module."""
import pytest
from kerygma_social.posse import PosseDistributor, Platform, SyndicationStatus
from kerygma_social.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError
from kerygma_social.rate_limiter import RateLimiter, RateLimiterConfig
from kerygma_social.retry import RetryConfig


def test_create_post():
    dist = PosseDistributor()
    post = dist.create_post("P001", "Launch Day", "We are live", "https://example.com/launch", [Platform.MASTODON])
    assert post.post_id == "P001"
    assert Platform.MASTODON in post.platforms


def test_syndicate_without_clients_marks_skipped():
    """Without configured clients, unknown platforms get SKIPPED (not PUBLISHED)."""
    dist = PosseDistributor()
    dist.create_post("P001", "Test", "Body", "https://example.com", [Platform.MASTODON, Platform.DISCORD])
    records = dist.syndicate("P001")
    assert len(records) == 2
    assert all(r.status == SyndicationStatus.SKIPPED for r in records)


def test_syndication_with_no_client_has_error_message():
    dist = PosseDistributor()
    dist.create_post("P001", "Test", "Body", "https://example.com", [Platform.MASTODON])
    records = dist.syndicate("P001")
    assert records[0].error == "No client configured for mastodon"


# --- T1: Resilience integration tests ---


class _MockClient:
    """Minimal mock that tracks calls and can be set to fail."""
    def __init__(self, fail_times: int = 0):
        self.calls = 0
        self._fail_times = fail_times

    def do_action(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise RuntimeError(f"Transient failure #{self.calls}")
        return {"url": "https://mock.example.com/posted"}


class TestWithResilience:
    def test_retry_succeeds_after_transient_failures(self):
        """Retry wraps the API call — transient failures are retried."""
        mock = _MockClient(fail_times=2)
        dist = PosseDistributor(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.001, jitter=False),
        )
        result = dist._with_resilience("test", mock.do_action)
        assert result == {"url": "https://mock.example.com/posted"}
        assert mock.calls == 3

    def test_circuit_breaker_propagates_immediately(self):
        """CircuitOpenError is NOT retried — it propagates immediately."""
        clock_val = [0.0]
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, reset_timeout=60.0),
            clock=lambda: clock_val[0],
        )
        # Trip the circuit
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass

        dist = PosseDistributor(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.001, jitter=False),
            circuit_breakers={"test": cb},
        )
        with pytest.raises(CircuitOpenError):
            dist._with_resilience("test", lambda: None)

    def test_rate_limiter_acquired_before_call(self):
        """Rate limiter is consumed before the actual API call."""
        acquired = []
        clock_val = [0.0]

        class TrackingLimiter(RateLimiter):
            def acquire(self, tokens=1.0, block=True):
                acquired.append(True)
                return super().acquire(tokens, block)

        limiter = TrackingLimiter(
            RateLimiterConfig(tokens_per_second=100.0, max_tokens=100.0),
            clock=lambda: clock_val[0],
        )
        dist = PosseDistributor(rate_limiter=limiter)
        dist._with_resilience("test", lambda: "ok")
        assert len(acquired) == 1

    def test_delivery_log_records_failure(self):
        """Failed syndication should be recorded in delivery log."""
        from kerygma_social.delivery_log import DeliveryLog
        from kerygma_social.mastodon import MastodonClient, MastodonConfig

        log = DeliveryLog()
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t"))

        dist = PosseDistributor(mastodon_client=client, delivery_log=log)
        dist.create_post("P002", "Test", "Body", "https://example.com", [Platform.MASTODON])
        records = dist.syndicate("P002")

        assert log.total_records == 1
        assert records[0].status == SyndicationStatus.PUBLISHED

    def test_resilience_all_layers_together(self):
        """Full stack: rate limiter + circuit breaker + retry — successful call."""
        mock = _MockClient(fail_times=1)
        clock_val = [0.0]
        limiter = RateLimiter(
            RateLimiterConfig(tokens_per_second=100.0, max_tokens=100.0),
            clock=lambda: clock_val[0],
        )
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=5, reset_timeout=60.0),
            clock=lambda: clock_val[0],
        )
        dist = PosseDistributor(
            retry_config=RetryConfig(max_attempts=3, base_delay=0.001, jitter=False),
            circuit_breakers={"test": cb},
            rate_limiter=limiter,
        )
        result = dist._with_resilience("test", mock.do_action)
        assert result == {"url": "https://mock.example.com/posted"}
        assert mock.calls == 2
