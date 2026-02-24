"""Tests for the mastodon module."""
from kerygma_social.mastodon import MastodonClient, MastodonConfig, Toot


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


def test_toot_validation_respects_custom_max_chars():
    """Toot.validate() should respect instance-specific char limits."""
    toot = Toot(content="A" * 600)
    assert toot.validate(max_chars=500) is False
    assert toot.validate(max_chars=1000) is True


def test_post_toot_uses_config_max_chars():
    """MastodonClient.post_toot() should validate against config.max_chars."""
    client = MastodonClient(MastodonConfig(
        instance_url="https://mastodon.social", access_token="test", max_chars=100,
    ))
    short_toot = Toot(content="A" * 50)
    result = client.post_toot(short_toot)
    assert "id" in result

    import pytest
    long_toot = Toot(content="A" * 150)
    with pytest.raises(ValueError, match="character limit"):
        client.post_toot(long_toot)


def test_format_for_mastodon():
    client = MastodonClient(MastodonConfig(instance_url="https://mastodon.social", access_token="test"))
    text = client.format_for_mastodon("New Essay", "https://example.com/essay", ["writing", "organvm"])
    assert "New Essay" in text
    assert "#writing" in text


class TestSplitForThread:
    def test_short_text_returns_single_chunk(self):
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t"))
        result = client.split_for_thread("Short message")
        assert result == ["Short message"]

    def test_long_text_splits_at_word_boundary(self):
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t", max_chars=50))
        text = "This is a fairly long message that should be split into multiple parts"
        chunks = client.split_for_thread(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_thread_numbering_space(self):
        """If thread numbering (e.g. '1/3') is added, chunks must have room for it.
        This test documents the W8 weakness: the current split doesn't reserve space."""
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t", max_chars=50))
        text = "A" * 120  # Forces split
        chunks = client.split_for_thread(text)
        # Verify raw split respects limit (numbering must be added externally)
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_split_preserves_all_content(self):
        """Joining chunks should reconstruct the original content (modulo whitespace)."""
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t", max_chars=30))
        text = "word " * 20
        chunks = client.split_for_thread(text.strip())
        rejoined = " ".join(c.strip() for c in chunks)
        assert rejoined == text.strip()

    def test_unicode_emoji_in_text(self):
        """Emoji characters should not break splitting."""
        client = MastodonClient(MastodonConfig(instance_url="https://m.test", access_token="t", max_chars=50))
        text = "Hello world! " + "🔥" * 30
        chunks = client.split_for_thread(text)
        assert len(chunks) >= 1
        full_text = "".join(chunks)
        assert "🔥" in full_text
