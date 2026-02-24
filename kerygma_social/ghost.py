"""Ghost CMS integration module.

Follows the same live/mock pattern as bluesky.py, discord.py, and mastodon.py.
In mock mode, posts are recorded locally without API calls.

Ghost Admin API uses JWT (HS256) authentication — the admin_api_key is
split as {id}:{secret} and signed into a short-lived token.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from kerygma_social.ghost_jwt import build_ghost_jwt


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
        """Build an HS256 JWT for Ghost Admin API authentication."""
        return build_ghost_jwt(self.config.admin_api_key)

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
