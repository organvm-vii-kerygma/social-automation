"""POSSE module for Publish (on your) Own Site, Syndicate Everywhere distribution.

Implements the POSSE pattern: content is authored on the canonical site,
then syndicated to external platforms with proper back-links.

Integrates resilience layers: retry, circuit breaker, rate limiter,
and delivery log persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from kerygma_social.bluesky import BlueskyClient
    from kerygma_social.circuit_breaker import CircuitBreaker
    from kerygma_social.delivery_log import DeliveryLog
    from kerygma_social.discord import DiscordWebhook
    from kerygma_social.mastodon import MastodonClient
    from kerygma_social.rate_limiter import RateLimiter
    from kerygma_social.retry import RetryConfig


class Platform(Enum):
    MASTODON = "mastodon"
    DISCORD = "discord"
    BLUESKY = "bluesky"
    RSS = "rss"
    TWITTER = "twitter"


class SyndicationStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SyndicationRecord:
    platform: Platform
    status: SyndicationStatus = SyndicationStatus.PENDING
    external_url: str | None = None
    published_at: datetime | None = None
    error: str | None = None

    def mark_published(self, url: str) -> None:
        self.status = SyndicationStatus.PUBLISHED
        self.external_url = url
        self.published_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        self.status = SyndicationStatus.FAILED
        self.error = error


@dataclass
class ContentPost:
    post_id: str
    title: str
    body: str
    canonical_url: str
    platforms: list[Platform] = field(default_factory=list)
    syndications: list[SyndicationRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_platform(self, platform: Platform) -> None:
        if platform not in self.platforms:
            self.platforms.append(platform)

    def get_syndication(self, platform: Platform) -> SyndicationRecord | None:
        return next((s for s in self.syndications if s.platform == platform), None)


class PosseDistributor:
    """Distributes content across platforms following the POSSE pattern.

    Supports optional resilience layers:
    - retry_config: Exponential backoff on transient failures
    - circuit_breakers: Per-platform circuit breakers
    - rate_limiter: Shared rate limiter across platforms
    - delivery_log: Persistent record of all dispatch attempts
    """

    def __init__(
        self,
        mastodon_client: MastodonClient | None = None,
        discord_webhook: DiscordWebhook | None = None,
        bluesky_client: BlueskyClient | None = None,
        retry_config: RetryConfig | None = None,
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
        rate_limiter: RateLimiter | None = None,
        delivery_log: DeliveryLog | None = None,
    ) -> None:
        self._posts: dict[str, ContentPost] = {}
        self._mastodon = mastodon_client
        self._discord = discord_webhook
        self._bluesky = bluesky_client
        self._retry_config = retry_config
        self._circuit_breakers = circuit_breakers or {}
        self._rate_limiter = rate_limiter
        self._delivery_log = delivery_log

    def create_post(
        self,
        post_id: str,
        title: str,
        body: str,
        canonical_url: str,
        platforms: list[Platform] | None = None,
    ) -> ContentPost:
        post = ContentPost(
            post_id=post_id, title=title, body=body,
            canonical_url=canonical_url, platforms=platforms or [],
        )
        self._posts[post_id] = post
        return post

    def _with_resilience(
        self,
        platform: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Wrap a syndication call with rate limiter, circuit breaker, and retry.

        Ordering: rate limiter (outermost) → circuit breaker (fail-fast) → retry → API call.
        Retry wraps only the raw API call so CircuitOpenError propagates immediately
        instead of being retried pointlessly.
        """
        # Rate limiter (outermost)
        if self._rate_limiter:
            self._rate_limiter.acquire(block=True)

        # Circuit breaker (fail-fast before retry)
        cb = self._circuit_breakers.get(platform)
        if cb:
            # Let CircuitOpenError propagate immediately — no retry around it
            def _retryable() -> Any:
                return func(*args, **kwargs)

            if self._retry_config:
                from kerygma_social.retry import retry
                return cb.call(retry, _retryable, self._retry_config)
            return cb.call(func, *args, **kwargs)

        # No circuit breaker — retry wraps raw call
        if self._retry_config:
            from kerygma_social.retry import retry
            return retry(func, self._retry_config, None, *args, **kwargs)

        return func(*args, **kwargs)

    def _log_delivery(
        self, post_id: str, platform: str, record: SyndicationRecord,
    ) -> None:
        if not self._delivery_log:
            return
        from kerygma_social.delivery_log import DeliveryRecord
        self._delivery_log.append(DeliveryRecord(
            record_id=f"{post_id}-{platform}",
            post_id=post_id,
            platform=platform,
            status="success" if record.status == SyndicationStatus.PUBLISHED else "failure",
            external_url=record.external_url or "",
            error=record.error or "",
        ))

    def _syndicate_mastodon(self, post: ContentPost) -> SyndicationRecord:
        from kerygma_social.mastodon import Toot

        record = SyndicationRecord(platform=Platform.MASTODON)
        text = self._mastodon.format_for_mastodon(post.title, post.canonical_url)
        toot = Toot(content=text)
        try:
            result = self._with_resilience(
                "mastodon", self._mastodon.post_toot, toot,
            )
            url = result.get("url", f"https://mastodon.example.com/{post.post_id}")
            record.mark_published(url)
        except Exception as exc:
            record.mark_failed(str(exc))
        return record

    def _syndicate_discord(self, post: ContentPost) -> SyndicationRecord:
        from kerygma_social.discord import DiscordEmbed

        record = SyndicationRecord(platform=Platform.DISCORD)
        embed = DiscordEmbed(
            title=post.title,
            description=post.body[:200],
            url=post.canonical_url,
        )
        try:
            result = self._with_resilience(
                "discord", self._discord.send_embed, embed,
            )
            url = result.get("url", f"https://discord.example.com/{post.post_id}")
            record.mark_published(url)
        except Exception as exc:
            record.mark_failed(str(exc))
        return record

    def _syndicate_bluesky(self, post: ContentPost) -> SyndicationRecord:
        from kerygma_social.bluesky import BlueskyPost

        record = SyndicationRecord(platform=Platform.BLUESKY)
        text = self._bluesky.format_for_bluesky(post.title, post.canonical_url)
        bsky_post = BlueskyPost(text=text)
        try:
            result = self._with_resilience(
                "bluesky", self._bluesky.post, bsky_post,
            )
            url = result.get("uri", f"at://bluesky.example.com/{post.post_id}")
            record.mark_published(url)
        except Exception as exc:
            record.mark_failed(str(exc))
        return record

    def syndicate(self, post_id: str) -> list[SyndicationRecord]:
        post = self._posts[post_id]
        records: list[SyndicationRecord] = []

        for platform in post.platforms:
            # Deduplication: skip if already delivered successfully
            if self._delivery_log and self._delivery_log.has_been_delivered(post_id, platform.value):
                record = SyndicationRecord(platform=platform)
                record.status = SyndicationStatus.SKIPPED
                record.error = "Already delivered (dedup)"
                records.append(record)
                continue

            if platform == Platform.MASTODON and self._mastodon is not None:
                record = self._syndicate_mastodon(post)
            elif platform == Platform.DISCORD and self._discord is not None:
                record = self._syndicate_discord(post)
            elif platform == Platform.BLUESKY and self._bluesky is not None:
                record = self._syndicate_bluesky(post)
            else:
                record = SyndicationRecord(platform=platform)
                record.status = SyndicationStatus.SKIPPED
                record.error = f"No client configured for {platform.value}"
            records.append(record)
            self._log_delivery(post_id, platform.value, record)

        post.syndications = records
        return records

    def get_post(self, post_id: str) -> ContentPost:
        return self._posts[post_id]

    @property
    def total_posts(self) -> int:
        return len(self._posts)
