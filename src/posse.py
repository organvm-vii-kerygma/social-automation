"""POSSE module for Publish (on your) Own Site, Syndicate Everywhere distribution.

Implements the POSSE pattern: content is authored on the canonical site,
then syndicated to external platforms with proper back-links.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
    """Distributes content across platforms following the POSSE pattern."""

    def __init__(self) -> None:
        self._posts: dict[str, ContentPost] = {}

    def create_post(self, post_id: str, title: str, body: str, canonical_url: str, platforms: list[Platform] | None = None) -> ContentPost:
        post = ContentPost(post_id=post_id, title=title, body=body, canonical_url=canonical_url, platforms=platforms or [])
        self._posts[post_id] = post
        return post

    def syndicate(self, post_id: str) -> list[SyndicationRecord]:
        post = self._posts[post_id]
        records: list[SyndicationRecord] = []
        for platform in post.platforms:
            record = SyndicationRecord(platform=platform)
            record.mark_published(f"https://{platform.value}.example.com/{post_id}")
            records.append(record)
        post.syndications = records
        return records

    def get_post(self, post_id: str) -> ContentPost:
        return self._posts[post_id]

    @property
    def total_posts(self) -> int:
        return len(self._posts)
