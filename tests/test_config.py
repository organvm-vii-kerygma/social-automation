"""Tests for the config module."""

from pathlib import Path

from kerygma_social.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


class TestConfig:
    def test_load_from_yaml(self):
        cfg = load_config(FIXTURES / "sample_config.yaml")
        assert cfg.mastodon_instance_url == "https://mastodon.test"
        assert cfg.mastodon_access_token == "test-token"
        assert cfg.discord_webhook_url == "https://discord.com/api/webhooks/test"
        assert cfg.bluesky_handle == "test.bsky.social"
        assert cfg.live_mode is False

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("KERYGMA_MASTODON_INSTANCE_URL", "https://env.mastodon")
        cfg = load_config(FIXTURES / "sample_config.yaml")
        assert cfg.mastodon_instance_url == "https://env.mastodon"

    def test_env_bool(self, monkeypatch):
        monkeypatch.setenv("KERYGMA_LIVE_MODE", "true")
        cfg = load_config()
        assert cfg.live_mode is True

    def test_default_config(self):
        cfg = load_config()
        assert cfg.mastodon_instance_url == ""
        assert cfg.live_mode is False
        assert cfg.delivery_log_path == "delivery_log.json"

    def test_missing_file(self):
        cfg = load_config(Path("/nonexistent/config.yaml"))
        assert cfg.mastodon_instance_url == ""
