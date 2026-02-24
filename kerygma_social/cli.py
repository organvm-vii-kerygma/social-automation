"""CLI entry point for social-automation.

Usage:
    social-dispatch dispatch --title TITLE --url URL [--platforms mastodon,discord,bluesky]
    social-dispatch poll-rss
    social-dispatch log [--failures]
    social-dispatch status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kerygma_social.config import load_config, SocialConfig
from kerygma_social.factory import build_distributor
from kerygma_social.posse import Platform
from kerygma_social.delivery_log import DeliveryLog


def cmd_dispatch(cfg: SocialConfig, title: str, url: str, platforms: list[str]) -> None:
    dist = build_distributor(cfg)
    platform_list = [Platform(p) for p in platforms]
    post = dist.create_post("cli-dispatch", title, "", url, platform_list)
    records = dist.syndicate("cli-dispatch")

    for r in records:
        status = r.status.value
        print(f"  [{status.upper()}] {r.platform.value}: {r.external_url or r.error or 'N/A'}")


def cmd_poll_rss(cfg: SocialConfig) -> None:
    if not cfg.rss_feed_url:
        print("No rss_feed_url configured.", file=sys.stderr)
        sys.exit(1)

    from kerygma_social.rss_poller import RssPoller
    poller = RssPoller(feed_url=cfg.rss_feed_url)
    entries = poller.poll()
    print(f"Found {len(entries)} new entries.")
    for entry in entries:
        print(f"  - {entry.title}: {entry.url}")


def cmd_log(cfg: SocialConfig, failures_only: bool) -> None:
    log_path = Path(cfg.delivery_log_path) if cfg.delivery_log_path else None
    log = DeliveryLog(log_path)
    records = log.get_failures() if failures_only else log.all_records
    print(f"{'Failures' if failures_only else 'All records'}: {len(records)}")
    for r in records:
        print(f"  [{r.status}] {r.platform} / {r.post_id}: {r.external_url or r.error}")


def cmd_status(cfg: SocialConfig) -> None:
    print(f"Live mode: {cfg.live_mode}")
    print(f"Mastodon: {'configured' if cfg.mastodon_instance_url else 'not configured'}")
    print(f"Discord:  {'configured' if cfg.discord_webhook_url else 'not configured'}")
    print(f"Bluesky:  {'configured' if cfg.bluesky_handle else 'not configured'}")
    print(f"RSS feed: {cfg.rss_feed_url or 'not configured'}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="social-dispatch", description="Social automation CLI")
    parser.add_argument("--config", type=Path, default=None, help="Config YAML file")
    sub = parser.add_subparsers(dest="command")

    dispatch_p = sub.add_parser("dispatch", help="Dispatch content to platforms")
    dispatch_p.add_argument("--title", required=True)
    dispatch_p.add_argument("--url", required=True)
    dispatch_p.add_argument("--platforms", default="mastodon,discord",
                            help="Comma-separated platform list")

    sub.add_parser("poll-rss", help="Poll RSS feed for new entries")

    log_p = sub.add_parser("log", help="View delivery log")
    log_p.add_argument("--failures", action="store_true")

    sub.add_parser("status", help="Show configuration status")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return

    cfg = load_config(args.config)

    if args.command == "dispatch":
        platforms = [p.strip() for p in args.platforms.split(",")]
        cmd_dispatch(cfg, args.title, args.url, platforms)
    elif args.command == "poll-rss":
        cmd_poll_rss(cfg)
    elif args.command == "log":
        cmd_log(cfg, args.failures)
    elif args.command == "status":
        cmd_status(cfg)


if __name__ == "__main__":
    main()
