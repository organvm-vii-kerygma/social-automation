"""Mastodon integration module for federated social publishing.

Handles authentication, post formatting, and interaction tracking
for Mastodon instances in the Fediverse.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MastodonConfig:
    instance_url: str
    access_token: str
    visibility: str = "public"
    max_chars: int = 500


@dataclass
class Toot:
    content: str
    visibility: str = "public"
    spoiler_text: str = ""
    media_ids: list[str] = field(default_factory=list)
    in_reply_to: str | None = None

    def validate(self) -> bool:
        return 0 < len(self.content) <= 500


class MastodonClient:
    """Client for publishing and interacting with Mastodon."""

    def __init__(self, config: MastodonConfig) -> None:
        self.config = config
        self._posted: list[dict[str, Any]] = []

    def post_toot(self, toot: Toot) -> dict[str, Any]:
        if not toot.validate():
            raise ValueError("Toot content exceeds character limit or is empty")
        result = {
            "id": f"toot-{len(self._posted) + 1:06d}",
            "content": toot.content,
            "url": f"{self.config.instance_url}/@user/{len(self._posted) + 1}",
            "visibility": toot.visibility,
        }
        self._posted.append(result)
        return result

    def format_for_mastodon(self, title: str, url: str, tags: list[str] | None = None) -> str:
        parts = [title, "", url]
        if tags:
            hashtags = " ".join(f"#{t}" for t in tags)
            parts.append("")
            parts.append(hashtags)
        text = "\n".join(parts)
        return text[:self.config.max_chars]

    @property
    def post_count(self) -> int:
        return len(self._posted)
