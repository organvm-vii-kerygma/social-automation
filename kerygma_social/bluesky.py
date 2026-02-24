"""Bluesky (AT Protocol) integration module.

Follows the same live/mock pattern as mastodon.py and discord.py.
In mock mode, posts are recorded locally without API calls.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class BlueskyConfig:
    handle: str
    app_password: str
    service_url: str = "https://bsky.social"
    max_chars: int = 300


@dataclass
class BlueskyPost:
    text: str
    reply_to: dict[str, Any] | None = None

    def validate(self) -> bool:
        return 0 < len(self.text) <= 300


class BlueskyClient:
    """Client for posting to Bluesky via the AT Protocol."""

    def __init__(self, config: BlueskyConfig, live: bool = False) -> None:
        self.config = config
        self._live = live
        self._posted: list[dict[str, Any]] = []
        self._session: dict[str, Any] | None = None

    def _create_session(self) -> dict[str, Any]:
        """Authenticate and create an AT Protocol session."""
        url = f"{self.config.service_url}/xrpc/com.atproto.server.createSession"
        payload = {
            "identifier": self.config.handle,
            "password": self.config.app_password,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self._session = json.loads(resp.read().decode("utf-8"))
                return self._session
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Bluesky auth error {exc.code}: {body}") from exc

    def _post_to_api(self, post: BlueskyPost) -> dict[str, Any]:
        """Create a post via the AT Protocol."""
        if not self._session:
            self._create_session()

        url = f"{self.config.service_url}/xrpc/com.atproto.repo.createRecord"
        record: dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": post.text,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        if post.reply_to:
            record["reply"] = post.reply_to

        payload = {
            "repo": self._session["did"],  # type: ignore[index]
            "collection": "app.bsky.feed.post",
            "record": record,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._session['accessJwt']}",  # type: ignore[index]
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Bluesky API error {exc.code}: {body}") from exc

    def post(self, post: BlueskyPost) -> dict[str, Any]:
        """Post to Bluesky (live or mock)."""
        if not post.validate():
            raise ValueError("Post text exceeds character limit or is empty")

        if self._live:
            result = self._post_to_api(post)
            self._posted.append(result)
            return result

        result = {
            "uri": f"at://did:plc:mock/app.bsky.feed.post/{len(self._posted) + 1}",
            "cid": f"mock-cid-{len(self._posted) + 1}",
            "text": post.text,
        }
        self._posted.append(result)
        return result

    def format_for_bluesky(self, title: str, url: str) -> str:
        """Format content for Bluesky's character limit, truncating at word boundary."""
        text = f"{title}\n\n{url}"
        limit = self.config.max_chars
        if len(text) <= limit:
            return text
        # Reserve space for ellipsis
        trunc_at = text.rfind(" ", 0, limit - 3)
        if trunc_at <= 0:
            trunc_at = limit - 3
        return text[:trunc_at].rstrip() + "..."

    @property
    def post_count(self) -> int:
        return len(self._posted)
