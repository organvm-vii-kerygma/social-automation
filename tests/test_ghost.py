"""Tests for the Ghost CMS module."""

import json
from base64 import urlsafe_b64decode

from kerygma_social.ghost import GhostClient, GhostConfig, GhostPost


def _pad_b64(s: str) -> str:
    """Re-add base64 padding stripped by JWT encoding."""
    return s + "=" * (-len(s) % 4)


class TestGhost:
    def _client(self) -> GhostClient:
        return GhostClient(
            GhostConfig(
                admin_api_key="abc123:deadbeef0102030405060708090a0b0c0d0e0f101112131415161718191a1b",
                api_url="https://ghost.example.com",
            )
        )

    def test_jwt_structure(self):
        client = self._client()
        token = client._build_jwt()  # allow-secret — test-generated JWT token
        parts = token.split(".")
        assert len(parts) == 3, "JWT must have 3 dot-separated parts"

        header = json.loads(urlsafe_b64decode(_pad_b64(parts[0])))
        assert header["alg"] == "HS256"
        assert header["typ"] == "JWT"
        assert header["kid"] == "abc123"

        payload = json.loads(urlsafe_b64decode(_pad_b64(parts[1])))
        assert payload["aud"] == "/admin/"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] - payload["iat"] == 300

    def test_jwt_invalid_key_format(self):
        import pytest

        client = GhostClient(
            GhostConfig(admin_api_key="no-colon-here", api_url="https://x.com")
        )
        with pytest.raises(ValueError, match="id.*secret"):
            client._build_jwt()

    def test_mock_post_creation(self):
        client = self._client()
        post = GhostPost(title="Test Post", html="<p>Hello</p>")
        result = client.create_post(post)
        assert "id" in result
        assert result["title"] == "Test Post"
        assert client.post_count == 1

    def test_mock_post_url(self):
        client = self._client()
        result = client.create_post(GhostPost(title="T", html="<p>H</p>"))
        assert result["url"].startswith("https://ghost.example.com/")

    def test_format_for_ghost(self):
        client = self._client()
        post = client.format_for_ghost(
            title="My Essay",
            body="This is the summary.",
            canonical_url="https://example.com/essay",
        )
        assert post.title == "My Essay"
        assert "<p>This is the summary.</p>" in post.html
        assert 'href="https://example.com/essay"' in post.html
        assert post.status == "draft"

    def test_format_for_ghost_no_url(self):
        client = self._client()
        post = client.format_for_ghost(title="T", body="B")
        assert "href" not in post.html

    def test_post_count_increments(self):
        client = self._client()
        assert client.post_count == 0
        client.create_post(GhostPost(title="One", html="<p>1</p>"))
        client.create_post(GhostPost(title="Two", html="<p>2</p>"))
        assert client.post_count == 2

    def test_post_status_preserved(self):
        client = self._client()
        result = client.create_post(
            GhostPost(title="Published", html="<p>Live</p>", status="published")
        )
        assert result["status"] == "published"

    def test_config_defaults(self):
        config = GhostConfig(admin_api_key="a:b", api_url="https://x.com")
        assert config.newsletter_slug == ""
