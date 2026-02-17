"""Mastodon integration module for federated social publishing.

Handles authentication, post formatting, and interaction tracking
for Mastodon instances in the Fediverse.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
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

    def __init__(self, config: MastodonConfig, live: bool = False) -> None:
        self.config = config
        self._live = live
        self._posted: list[dict[str, Any]] = []

    def _post_to_api(self, toot: Toot) -> dict[str, Any]:
        """Send a toot to the Mastodon API via HTTP POST."""
        url = f"{self.config.instance_url}/api/v1/statuses"
        payload = {
            "status": toot.content,
            "visibility": toot.visibility,
        }
        if toot.spoiler_text:
            payload["spoiler_text"] = toot.spoiler_text
        if toot.media_ids:
            payload["media_ids"] = toot.media_ids
        if toot.in_reply_to:
            payload["in_reply_to_id"] = toot.in_reply_to

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Mastodon API error {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Mastodon connection error: {exc.reason}"
            ) from exc

    def post_toot(self, toot: Toot) -> dict[str, Any]:
        if not toot.validate():
            raise ValueError("Toot content exceeds character limit or is empty")

        if self._live:
            result = self._post_to_api(toot)
            self._posted.append(result)
            return result

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
