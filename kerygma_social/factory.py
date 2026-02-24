"""Factory for building a PosseDistributor from SocialConfig or ProjectProfile.

Shared by the social-automation CLI and the kerygma-pipeline orchestrator
to avoid duplicated client construction logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from kerygma_social.bluesky import BlueskyClient, BlueskyConfig
from kerygma_social.config import SocialConfig
from kerygma_social.delivery_log import DeliveryLog
from kerygma_social.discord import DiscordWebhook
from kerygma_social.ghost import GhostClient, GhostConfig
from kerygma_social.mastodon import MastodonClient, MastodonConfig
from kerygma_social.posse import PosseDistributor

if TYPE_CHECKING:
    from kerygma_profiles.registry import ProjectProfile


def build_distributor(
    cfg: SocialConfig,
    delivery_log: DeliveryLog | None = None,
) -> PosseDistributor:
    """Build a PosseDistributor from a SocialConfig.

    Args:
        cfg: Social configuration with platform credentials and live_mode.
        delivery_log: Optional pre-built delivery log. If None, one is
            constructed from cfg.delivery_log_path.

    Returns:
        A fully wired PosseDistributor.
    """
    mastodon = None
    if cfg.mastodon_instance_url:
        mastodon = MastodonClient(
            MastodonConfig(
                instance_url=cfg.mastodon_instance_url,
                access_token=cfg.mastodon_access_token,
                visibility=getattr(cfg, "mastodon_visibility", "public"),
            ),
            live=cfg.live_mode,
        )

    discord = None
    if cfg.discord_webhook_url:
        discord = DiscordWebhook(cfg.discord_webhook_url, live=cfg.live_mode)

    bluesky = None
    if cfg.bluesky_handle:
        bluesky = BlueskyClient(
            BlueskyConfig(handle=cfg.bluesky_handle, app_password=cfg.bluesky_app_password),
            live=cfg.live_mode,
        )

    ghost = None
    if cfg.ghost_api_url:
        ghost = GhostClient(
            GhostConfig(
                admin_api_key=cfg.ghost_admin_api_key,
                api_url=cfg.ghost_api_url,
                newsletter_slug=getattr(cfg, "ghost_newsletter_slug", ""),
            ),
            live=cfg.live_mode,
        )

    if delivery_log is None:
        log_path = Path(cfg.delivery_log_path) if cfg.delivery_log_path else None
        delivery_log = DeliveryLog(log_path)

    return PosseDistributor(
        mastodon_client=mastodon,
        discord_webhook=discord,
        bluesky_client=bluesky,
        ghost_client=ghost,
        delivery_log=delivery_log,
    )


def build_distributor_for_profile(
    profile: ProjectProfile,
    resolve_secret: Callable[[str], str],
    delivery_log: DeliveryLog | None = None,
    live: bool = False,
) -> PosseDistributor:
    """Build a PosseDistributor from a ProjectProfile with resolved credentials.

    Args:
        profile: Project profile containing platform configs with secret refs.
        resolve_secret: Callable that resolves op://, env://, or literal values.
        delivery_log: Optional pre-built delivery log.
        live: Whether to enable live API calls (default: dry-run).

    Returns:
        A fully wired PosseDistributor with profile-specific credentials.
    """
    cfg = SocialConfig.from_profile(profile, resolve_secret)
    cfg.live_mode = live
    return build_distributor(cfg, delivery_log=delivery_log)
