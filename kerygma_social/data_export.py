"""Generate static data artifacts for social-automation.

Produces:
  data/delivery-log.json   — delivery record schema, status/platform enums, sample record
  data/posse-manifest.json — POSSE pattern, platforms, resilience stack, config

Introspective module: documents its own codebase without running live APIs.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kerygma_social.config import SocialConfig
from kerygma_social.posse import Platform, SyndicationStatus

REPO_ROOT = Path(__file__).parent.parent


def build_delivery_log_schema() -> dict[str, Any]:
    """Document the delivery log record format, status values, and platform enums."""
    fields = [
        {"field": "record_id", "type": "string", "description": "Unique record identifier"},
        {"field": "post_id", "type": "string", "description": "ID of the syndicated post"},
        {"field": "platform", "type": "string", "description": "Target platform name"},
        {"field": "status", "type": "string", "description": "Delivery outcome"},
        {"field": "timestamp", "type": "string", "description": "ISO 8601 timestamp"},
        {"field": "external_url", "type": "string", "description": "URL on target platform"},
        {"field": "error", "type": "string", "description": "Error message if failed"},
        {"field": "metadata", "type": "object", "description": "Additional metadata"},
    ]

    sample_record = {
        "record_id": "essay-001-mastodon",
        "post_id": "essay-001",
        "platform": "mastodon",
        "status": "success",
        "timestamp": "2026-02-24T12:00:00",
        "external_url": "https://mastodon.social/@organvm/123456",
        "error": "",
        "metadata": {},
    }

    return {
        "record_format": "DeliveryRecord",
        "fields": fields,
        "syndication_statuses": [s.value for s in SyndicationStatus],
        "delivery_statuses": ["success", "failure", "skipped"],
        "platforms": [p.value for p in Platform],
        "sample_record": sample_record,
    }


def build_posse_manifest() -> dict[str, Any]:
    """Document the POSSE distribution system: platforms, resilience, config."""
    platforms = []
    platform_details = {
        Platform.MASTODON: {
            "env_vars": [
                "KERYGMA_MASTODON_INSTANCE_URL",
                "KERYGMA_MASTODON_ACCESS_TOKEN",
            ],
            "features": ["threading", "visibility_control", "media_attachments"],
            "module": "kerygma_social.mastodon",
        },
        Platform.DISCORD: {
            "env_vars": ["KERYGMA_DISCORD_WEBHOOK_URL"],
            "features": ["embeds", "color_coding", "fields"],
            "module": "kerygma_social.discord",
        },
        Platform.BLUESKY: {
            "env_vars": [
                "KERYGMA_BLUESKY_HANDLE",
                "KERYGMA_BLUESKY_APP_PASSWORD",
            ],
            "features": ["at_protocol", "word_boundary_truncation"],
            "module": "kerygma_social.bluesky",
        },
        Platform.GHOST: {
            "env_vars": [
                "KERYGMA_GHOST_API_URL",
                "KERYGMA_GHOST_ADMIN_API_KEY",
            ],
            "features": ["html_content", "newsletters", "drafts"],
            "module": "kerygma_social.ghost",
        },
        Platform.RSS: {
            "env_vars": [],
            "features": ["feed_polling"],
            "module": None,
        },
        Platform.TWITTER: {
            "env_vars": [],
            "features": ["deprecated"],
            "module": None,
        },
    }

    for p in Platform:
        details = platform_details[p]
        platforms.append({
            "platform": p.value,
            "env_vars": details["env_vars"],
            "features": details["features"],
            "module": details["module"],
        })

    resilience_stack = [
        {
            "layer": "rate_limiter",
            "module": "kerygma_social.rate_limiter",
            "pattern": "Token bucket",
        },
        {
            "layer": "circuit_breaker",
            "module": "kerygma_social.circuit_breaker",
            "pattern": "Three-state machine (CLOSED -> OPEN -> HALF_OPEN)",
        },
        {
            "layer": "retry",
            "module": "kerygma_social.retry",
            "pattern": "Exponential backoff with jitter",
        },
        {
            "layer": "delivery_log",
            "module": "kerygma_social.delivery_log",
            "pattern": "JSON file-backed persistence with deduplication",
        },
    ]

    config_fields = [f.name for f in dataclasses.fields(SocialConfig)]

    return {
        "pattern": "POSSE (Publish Own Site, Syndicate Everywhere)",
        "description": (
            "Content authored on canonical site, "
            "syndicated to external platforms with back-links"
        ),
        "platforms": platforms,
        "resilience_stack": resilience_stack,
        "rss_polling": {
            "config_key": "rss_feed_url",
            "description": "RSS feed URL for polling new content",
        },
        "config_fields": config_fields,
        "deduplication": {
            "method": "delivery_log.has_been_delivered(post_id, platform)",
            "description": "Skip syndication if post already delivered to platform",
        },
    }


def export_all(output_dir: Path | None = None) -> list[Path]:
    """Generate all data artifacts and return output paths."""
    output_dir = output_dir or REPO_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    # delivery-log.json
    log_schema = build_delivery_log_schema()
    log_path = output_dir / "delivery-log.json"
    log_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organ": "VII",
        "organ_name": "Kerygma",
        "repo": "social-automation",
        **log_schema,
    }
    log_path.write_text(json.dumps(log_data, indent=2) + "\n")
    outputs.append(log_path)

    # posse-manifest.json
    manifest = build_posse_manifest()
    manifest_path = output_dir / "posse-manifest.json"
    manifest_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organ": "VII",
        "organ_name": "Kerygma",
        "repo": "social-automation",
        **manifest,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n")
    outputs.append(manifest_path)

    return outputs


def main() -> None:
    """CLI entry point for data export."""
    paths = export_all()
    for p in paths:
        print(f"Written: {p}")


if __name__ == "__main__":
    main()
