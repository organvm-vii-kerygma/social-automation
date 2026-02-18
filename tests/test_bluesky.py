"""Tests for the Bluesky module."""

from kerygma_social.bluesky import BlueskyClient, BlueskyConfig, BlueskyPost


class TestBluesky:
    def _client(self) -> BlueskyClient:
        return BlueskyClient(BlueskyConfig(handle="test.bsky.social", app_password="test"))

    def test_post_mock(self):
        client = self._client()
        result = client.post(BlueskyPost(text="Hello Bluesky!"))
        assert "uri" in result
        assert client.post_count == 1

    def test_post_validation(self):
        client = self._client()
        import pytest
        with pytest.raises(ValueError):
            client.post(BlueskyPost(text=""))

    def test_format_for_bluesky(self):
        client = self._client()
        text = client.format_for_bluesky("New Essay", "https://example.com/essay")
        assert "New Essay" in text
        assert "https://example.com" in text
        assert len(text) <= 300

    def test_post_count(self):
        client = self._client()
        assert client.post_count == 0
        client.post(BlueskyPost(text="One"))
        client.post(BlueskyPost(text="Two"))
        assert client.post_count == 2

    def test_post_too_long(self):
        client = self._client()
        import pytest
        with pytest.raises(ValueError):
            client.post(BlueskyPost(text="x" * 301))
