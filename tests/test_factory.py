"""Tests for the distributor factory, including profile-based construction."""

from kerygma_social.config import SocialConfig
from kerygma_social.factory import build_distributor, build_distributor_for_profile
from kerygma_social.posse import PosseDistributor


class TestBuildDistributor:
    def test_build_with_empty_config(self):
        cfg = SocialConfig()
        dist = build_distributor(cfg)
        assert isinstance(dist, PosseDistributor)

    def test_build_with_mastodon(self):
        cfg = SocialConfig(
            mastodon_instance_url="https://mastodon.social",
            mastodon_access_token="test-token",
        )
        dist = build_distributor(cfg)
        assert isinstance(dist, PosseDistributor)
        assert dist._mastodon is not None

    def test_build_with_discord(self):
        cfg = SocialConfig(discord_webhook_url="https://discord.com/api/webhooks/test")
        dist = build_distributor(cfg)
        assert dist._discord is not None


class TestBuildDistributorForProfile:
    def _make_profile(self, platforms=None):
        """Create a minimal ProjectProfile-like object for testing."""
        from kerygma_profiles.registry import ProjectProfile
        return ProjectProfile(
            profile_id="test",
            display_name="Test Profile",
            organ=None,
            repos=["test-repo"],
            voice={"tone": "neutral"},
            platforms=platforms or {},
            channels=[],
            calendar_events=[],
        )

    def test_build_from_profile_empty(self):
        profile = self._make_profile()
        dist = build_distributor_for_profile(
            profile, resolve_secret=lambda v: v,
        )
        assert isinstance(dist, PosseDistributor)

    def test_build_from_profile_with_mastodon(self):
        profile = self._make_profile(platforms={
            "mastodon": {
                "instance_url": "https://mastodon.social",
                "access_token": "mock-token",
                "visibility": "public",
            },
        })
        dist = build_distributor_for_profile(
            profile, resolve_secret=lambda v: v,
        )
        assert dist._mastodon is not None

    def test_secrets_are_resolved(self):
        profile = self._make_profile(platforms={
            "mastodon": {
                "instance_url": "https://mastodon.social",
                "access_token": "op://vault/item/field",
                "visibility": "public",
            },
        })
        resolved_values = []

        def mock_resolve(val):
            resolved_values.append(val)
            if val.startswith("op://"):
                return "resolved-token"
            return val

        dist = build_distributor_for_profile(
            profile, resolve_secret=mock_resolve,
        )
        assert "op://vault/item/field" in resolved_values
        assert dist._mastodon is not None

    def test_live_mode_propagates(self):
        profile = self._make_profile(platforms={
            "mastodon": {
                "instance_url": "https://mastodon.social",
                "access_token": "token",
                "visibility": "public",
            },
        })
        dist = build_distributor_for_profile(
            profile, resolve_secret=lambda v: v, live=False,
        )
        # In dry-run, the mastodon client should exist but not make real calls
        assert dist._mastodon is not None

    def test_from_profile_classmethod(self):
        """Test SocialConfig.from_profile directly."""
        profile = self._make_profile(platforms={
            "mastodon": {
                "instance_url": "https://mastodon.social",
                "access_token": "secret-ref",
                "visibility": "unlisted",
            },
            "discord": {"webhook_url": "https://discord.com/webhook"},
        })
        cfg = SocialConfig.from_profile(profile, resolve=lambda v: f"resolved:{v}")
        assert cfg.mastodon_instance_url == "https://mastodon.social"
        assert cfg.mastodon_access_token == "resolved:secret-ref"
        assert cfg.mastodon_visibility == "unlisted"
        assert cfg.discord_webhook_url == "resolved:https://discord.com/webhook"
