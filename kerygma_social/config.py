"""Configuration loader for social-automation.

Loads YAML config files with environment variable overrides.
All env vars use the KERYGMA_ prefix.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ENV_PREFIX = "KERYGMA_"


@dataclass
class SocialConfig:
    """Unified configuration for all social-automation components."""
    mastodon_instance_url: str = ""
    mastodon_access_token: str = ""
    mastodon_visibility: str = "public"
    discord_webhook_url: str = ""
    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    ghost_api_url: str = ""
    ghost_admin_api_key: str = ""
    ghost_newsletter_slug: str = ""
    delivery_log_path: str = "delivery_log.json"
    rss_feed_url: str = ""
    live_mode: bool = False


def load_config(path: Path | None = None) -> SocialConfig:
    """Load config from YAML file with env var overrides.

    Env vars override YAML values. Mapping:
      KERYGMA_MASTODON_INSTANCE_URL → mastodon.instance_url
      KERYGMA_MASTODON_ACCESS_TOKEN → mastodon.access_token
      KERYGMA_DISCORD_WEBHOOK_URL → discord.webhook_url
      KERYGMA_BLUESKY_HANDLE → bluesky.handle
      KERYGMA_BLUESKY_APP_PASSWORD → bluesky.app_password
      KERYGMA_GHOST_API_URL → ghost.api_url
      KERYGMA_GHOST_ADMIN_API_KEY → ghost.admin_api_key
      KERYGMA_LIVE_MODE → live_mode
    """
    raw: dict[str, Any] = {}
    if path and path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    mastodon = raw.get("mastodon", {}) if isinstance(raw, dict) else {}
    discord = raw.get("discord", {}) if isinstance(raw, dict) else {}
    bluesky = raw.get("bluesky", {}) if isinstance(raw, dict) else {}
    ghost = raw.get("ghost", {}) if isinstance(raw, dict) else {}

    cfg = SocialConfig(
        mastodon_instance_url=_env_or(
            "MASTODON_INSTANCE_URL",
            mastodon.get("instance_url", ""),
        ),
        mastodon_access_token=_env_or(
            "MASTODON_ACCESS_TOKEN",
            mastodon.get("access_token", ""),
        ),
        mastodon_visibility=mastodon.get("visibility", "public"),
        discord_webhook_url=_env_or(
            "DISCORD_WEBHOOK_URL",
            discord.get("webhook_url", ""),
        ),
        bluesky_handle=_env_or(
            "BLUESKY_HANDLE",
            bluesky.get("handle", ""),
        ),
        bluesky_app_password=_env_or(
            "BLUESKY_APP_PASSWORD",
            bluesky.get("app_password", ""),
        ),
        ghost_api_url=_env_or(
            "GHOST_API_URL",
            ghost.get("api_url", ""),
        ),
        ghost_admin_api_key=_env_or(
            "GHOST_ADMIN_API_KEY",
            ghost.get("admin_api_key", ""),
        ),
        ghost_newsletter_slug=ghost.get("newsletter_slug", ""),
        delivery_log_path=raw.get("delivery_log_path", "delivery_log.json")
        if isinstance(raw, dict) else "delivery_log.json",
        rss_feed_url=raw.get("rss_feed_url", "") if isinstance(raw, dict) else "",
        live_mode=_env_bool("LIVE_MODE", raw.get("live_mode", False) if isinstance(raw, dict) else False),
    )

    return cfg


def _env_or(suffix: str, default: str) -> str:
    return os.environ.get(f"{ENV_PREFIX}{suffix}", default)


def _env_bool(suffix: str, default: bool) -> bool:
    val = os.environ.get(f"{ENV_PREFIX}{suffix}")
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")
