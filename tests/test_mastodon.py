"""Tests for the mastodon module."""
from src.mastodon import MastodonClient, MastodonConfig, Toot

def test_post_toot():
    client = MastodonClient(MastodonConfig(instance_url="https://mastodon.social", access_token="test"))
    toot = Toot(content="Hello Fediverse!")
    result = client.post_toot(toot)
    assert "id" in result
    assert client.post_count == 1

def test_toot_validation():
    valid = Toot(content="Short message")
    assert valid.validate() is True
    empty = Toot(content="")
    assert empty.validate() is False

def test_format_for_mastodon():
    client = MastodonClient(MastodonConfig(instance_url="https://mastodon.social", access_token="test"))
    text = client.format_for_mastodon("New Essay", "https://example.com/essay", ["writing", "organvm"])
    assert "New Essay" in text
    assert "#writing" in text
