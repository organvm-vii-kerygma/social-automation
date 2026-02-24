# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`kerygma_social` — the POSSE distribution and social platform automation package for ORGAN-VII (Kerygma). Provides platform clients for Mastodon, Discord, Bluesky, and Ghost, a `PosseDistributor` orchestrator, and a resilience stack (retry, circuit breaker, rate limiter).

## Package Structure

Source is in `kerygma_social/`, installed as the `kerygma_social` package:

### Platform Clients
| Module | Class | Protocol |
|--------|-------|----------|
| `mastodon.py` | `MastodonClient` | REST API via `urllib`. `MastodonConfig` dataclass. `Toot` dataclass for posts. `format_for_mastodon()` helper. |
| `discord.py` | `DiscordWebhook` | Webhook POST. `DiscordEmbed` dataclass for rich embeds. |
| `bluesky.py` | `BlueskyClient` | AT Protocol. `BlueskyConfig`/`BlueskyPost` dataclasses. Session-based auth. |
| `ghost.py` | `GhostClient` | Admin API with JWT auth (`HS256`, `{id}:{secret}` key format). `GhostConfig`/`GhostPost` dataclasses. Optional newsletter targeting. |

### Orchestration & Resilience
| Module | Purpose |
|--------|---------|
| `posse.py` | `PosseDistributor` — central dispatcher. `create_post()` → `syndicate()` flow. `_with_resilience()` wraps calls: rate limiter (outermost) → circuit breaker → retry (innermost). Deduplicates via `DeliveryLog`. Enums: `Platform`, `SyndicationStatus`. Dataclasses: `ContentPost`, `SyndicationRecord`. |
| `circuit_breaker.py` | Three-state machine: CLOSED → OPEN → HALF_OPEN. `CircuitBreakerConfig` (failure_threshold=5, reset_timeout=60s). Raises `CircuitOpenError` when open. |
| `retry.py` | Exponential backoff retry. `RetryConfig` dataclass. |
| `rate_limiter.py` | Token bucket rate limiter. `RateLimiterConfig` dataclass. `acquire(block=True)` blocks until token available. |
| `delivery_log.py` | `DeliveryLog` — persistent JSON log of dispatch attempts. `has_been_delivered(post_id, platform)` for deduplication. `DeliveryRecord` dataclass. |
| `rss_poller.py` | `RssPoller` — polls RSS/Atom feeds via stdlib `xml.etree` and `urllib`. Tracks seen entry IDs in JSON. `parse_feed()` handles both Atom and RSS 2.0. |

### Configuration
| Module | Purpose |
|--------|---------|
| `config.py` | `load_config(path)` → `SocialConfig` dataclass. YAML file + env var overrides (prefix `KERYGMA_`). All platform credentials, `live_mode`, `delivery_log_path`, `rss_feed_url`. |
| `cli.py` | CLI entry point (`social-dispatch`). |

## Development Commands

```bash
# Install (from superproject root or this directory)
pip install -e .[dev]

# Tests
pytest tests/ -v
pytest tests/test_posse.py::TestPosseDistributor::test_syndicate_mastodon -v

# Lint
ruff check kerygma_social/
```

## Key Design Details

- **All clients accept `live=False`** (default). In dry-run mode, API calls return mock responses. Never commit config with `live_mode: true`.
- **Resilience ordering matters**: rate limiter prevents burst → circuit breaker fails fast if service is down → retry handles transient errors. `CircuitOpenError` propagates immediately (not retried).
- **RSS poller is stdlib-only** — uses `urllib.request` and `xml.etree.ElementTree`. No `feedparser` dependency at the package level (feedparser is only needed by the pipeline orchestrator).
- **Delivery log uses atomic writes** — writes to `.tmp` then `os.replace()`.
- **Runtime dependency**: only `pyyaml>=6.0` (for config loading).

## Test Structure

Tests in `tests/` with `fixtures/` directory for test config files:
- `test_mastodon.py`, `test_discord.py`, `test_bluesky.py`, `test_ghost.py` — per-client formatting and dispatch
- `test_posse.py` — PosseDistributor syndication, deduplication, resilience
- `test_circuit_breaker.py` — state transitions, threshold, recovery
- `test_retry.py` — backoff behavior, max retries
- `test_rate_limiter.py` — token bucket, blocking acquire
- `test_delivery_log.py` — persistence, dedup checks
- `test_rss_poller.py` — Atom/RSS parsing, seen tracking
- `test_config.py` — YAML loading, env var overrides

<!-- ORGANVM:AUTO:START -->
## System Context (auto-generated — do not edit)

**Organ:** ORGAN-VII (Marketing) | **Tier:** standard | **Status:** GRADUATED
**Org:** `unknown` | **Repo:** `social-automation`

### Edges
- *No inter-repo edges declared in seed.yaml*

### Siblings in Marketing
`announcement-templates`, `distribution-strategy`, `.github`

### Governance
- *Standard ORGANVM governance applies*

*Last synced: 2026-02-24T01:01:15Z*
<!-- ORGANVM:AUTO:END -->
