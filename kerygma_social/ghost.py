"""Ghost CMS integration module.

Follows the same live/mock pattern as bluesky.py, discord.py, and mastodon.py.
In mock mode, posts are recorded locally without API calls.

Ghost Admin API uses JWT (HS256) authentication — the admin_api_key is
split as {id}:{secret} and signed into a short-lived token.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
import urllib.error
import urllib.request
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GhostConfig:
    admin_api_key: str  # Format: {id}:{secret}
    api_url: str  # e.g. https://your-ghost.com
    newsletter_slug: str = ""


@dataclass
class GhostPost:
    title: str
    html: str
    status: str = "draft"  # "draft" or "published"
    tags: list[str] = field(default_factory=list)
    excerpt: str = ""


class GhostClient:
    """Client for publishing to Ghost via the Admin API."""

    def __init__(self, config: GhostConfig, live: bool = False) -> None:
        self.config = config
        self._live = live
        self._posted: list[dict[str, Any]] = []

    def _build_jwt(self) -> str:
        """Build an HS256 JWT for Ghost Admin API authentication.

        The admin_api_key is "{id}:{secret}" — the id becomes the kid header,
        and the hex-decoded secret is the HMAC signing key.
        """
        parts = self.config.admin_api_key.split(":")
        if len(parts) != 2:
            raise ValueError("Ghost admin_api_key must be in {id}:{secret} format")
        key_id, secret_hex = parts

        # Header
        header = {"alg": "HS256", "typ": "JWT", "kid": key_id}

        # Payload — 5 minute expiry, /admin/ audience
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + 300,
            "aud": "/admin/",
        }

        def _b64(data: bytes) -> str:
            return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        header_b64 = _b64(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())

        signing_input = f"{header_b64}.{payload_b64}"
        secret_bytes = bytes.fromhex(secret_hex)
        signature = hmac.new(secret_bytes, signing_input.encode(), hashlib.sha256).digest()

        return f"{signing_input}.{_b64(signature)}"

    def create_post(self, post: GhostPost) -> dict[str, Any]:
        """Create a post on Ghost (live or mock)."""
        if self._live:
            return self._post_to_api(post)

        result = {
            "id": f"mock-ghost-{len(self._posted) + 1}",
            "title": post.title,
            "status": post.status,
            "url": f"{self.config.api_url}/mock-post-{len(self._posted) + 1}/",
        }
        self._posted.append(result)
        return result

    def _post_to_api(self, post: GhostPost) -> dict[str, Any]:
        """POST to the Ghost Admin API."""
        token = self._build_jwt()  # allow-secret — runtime-generated JWT, not a stored credential
        url = f"{self.config.api_url}/ghost/api/admin/posts/"

        body: dict[str, Any] = {
            "posts": [{
                "title": post.title,
                "html": post.html,
                "status": post.status,
            }],
        }
        if post.tags:
            body["posts"][0]["tags"] = [{"name": t} for t in post.tags]
        if post.excerpt:
            body["posts"][0]["custom_excerpt"] = post.excerpt
        if self.config.newsletter_slug:
            body["posts"][0]["newsletter"] = {"slug": self.config.newsletter_slug}

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Ghost {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._posted.append(result.get("posts", [{}])[0])
                return result.get("posts", [{}])[0]
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ghost API error {exc.code}: {body_text}") from exc

    def format_for_ghost(self, title: str, body: str, canonical_url: str = "") -> GhostPost:
        """Convert pipeline content into a Ghost post with HTML formatting."""
        html_parts = [f"<p>{body}</p>"]
        if canonical_url:
            html_parts.append(f'<p><a href="{canonical_url}">Read the full post</a></p>')
        return GhostPost(
            title=title,
            html="\n".join(html_parts),
            status="draft",
        )

    @property
    def post_count(self) -> int:
        return len(self._posted)
