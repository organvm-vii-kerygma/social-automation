[![ORGAN-VII: Kerygma](https://img.shields.io/badge/ORGAN--VII-Kerygma-6a1b9a?style=flat-square)](https://github.com/organvm-vii-kerygma)
[![POSSE](https://img.shields.io/badge/POSSE-Publish%20Own%20Site%2C%20Syndicate%20Elsewhere-blueviolet?style=flat-square)]()
[![Mastodon](https://img.shields.io/badge/Mastodon-API%20integrated-6364FF?style=flat-square&logo=mastodon&logoColor=white)]()
[![Discord](https://img.shields.io/badge/Discord-Webhooks%20live-5865F2?style=flat-square&logo=discord&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-6a1b9a?style=flat-square)]()

# Social Automation

**Backend automation infrastructure for POSSE content distribution -- API integrations, scheduling logic, rate limiting, retry policies, delivery monitoring, and analytics collection for the eight-organ creative-institutional system.**

Social Automation is the execution engine behind ORGAN-VII (Kerygma), the marketing and distribution organ of the [organvm](https://github.com/organvm-vii-kerygma) ecosystem. Where [announcement-templates](https://github.com/organvm-vii-kerygma/announcement-templates) defines *what* to say and [distribution-strategy](https://github.com/organvm-vii-kerygma/distribution-strategy) defines *when and to whom*, this repository defines *how* -- the technical infrastructure that moves content from composition to delivery across every distribution channel.

The system implements the POSSE (Publish on Own Site, Syndicate Elsewhere) principle as operational infrastructure. Primary content lives on the ORGAN-V Jekyll/GitHub Pages site. This repository ensures that every publication event triggers a coordinated, reliable, monitored distribution cascade across Mastodon, Discord, and future channels -- without manual intervention, without missed posts, and without silent failures.

Content distribution at the scale of an eight-organ system is not a simple API call. It is a pipeline with failure modes at every stage: rate limits, network timeouts, API deprecations, format rejections, webhook delivery failures, and scheduling conflicts. This repository treats distribution as an engineering problem deserving the same rigor applied to any production system: retry policies with exponential backoff, circuit breakers for degraded services, delivery confirmation with receipt tracking, and comprehensive error reporting.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [POSSE Implementation](#posse-implementation)
- [Channel Integrations](#channel-integrations)
- [Scheduling Infrastructure](#scheduling-infrastructure)
- [Error Handling and Resilience](#error-handling-and-resilience)
- [Monitoring and Delivery Confirmation](#monitoring-and-delivery-confirmation)
- [Analytics Pipeline](#analytics-pipeline)
- [Configuration](#configuration)
- [Connection to ORGAN-IV Workflows](#connection-to-organ-iv-workflows)
- [Security and Credential Management](#security-and-credential-management)
- [Metrics and Tracking](#metrics-and-tracking)
- [Cross-Organ Dependencies](#cross-organ-dependencies)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Author and Contact](#author-and-contact)

---

## Overview

Social Automation bridges the gap between content creation and audience delivery. In the organvm system, content flows through a defined pipeline:

1. **Creation** -- ORGAN-V essays, ORGAN-I/II/III repository updates, ORGAN-VI community events generate publication events.
2. **Templating** -- [announcement-templates](https://github.com/organvm-vii-kerygma/announcement-templates) transforms events into platform-specific content with variable interpolation and quality checklists.
3. **Scheduling** -- This repository's scheduler determines optimal dispatch timing based on the content calendar, audience engagement patterns, and platform-specific best practices.
4. **Dispatch** -- Channel-specific adapters format and transmit content via platform APIs and webhooks.
5. **Confirmation** -- Delivery monitors verify successful receipt and log results.
6. **Analytics** -- Engagement metrics are collected, aggregated, and reported back to the orchestration hub.

This repository owns stages 3-6. It is the operational core that turns strategic intent into measurable distribution outcomes.

### What Makes This Different

Most social media automation tools optimize for volume -- schedule as many posts as possible across as many platforms as possible. This system optimizes for **signal integrity**. Every dispatched message is:

- **Verified** against the source event (no stale or contradictory information reaches audiences)
- **Timed** according to strategic calendaring (not just "best time to post" algorithms, but alignment with grant cycles, conference seasons, and audience attention patterns)
- **Monitored** for delivery success (a failed webhook is not a silent failure -- it triggers retry logic and, if unresolvable, alerts for manual intervention)
- **Measured** for actual impact (engagement metrics flow back to inform future distribution decisions)

---

## Architecture

The system is organized into five subsystems that form a linear pipeline with feedback loops:

```
  ┌──────────────────────────────────────────────────────────────┐
  │                    EVENT INGESTION                            │
  │  GitHub webhooks  |  RSS polling  |  Manual triggers          │
  └──────────────┬───────────────────────────────────────────────┘
                 │
  ┌──────────────▼───────────────────────────────────────────────┐
  │                    SCHEDULING ENGINE                          │
  │  Calendar alignment  |  Rate limiting  |  Priority queue      │
  └──────────────┬───────────────────────────────────────────────┘
                 │
  ┌──────────────▼───────────────────────────────────────────────┐
  │                    DISPATCH ADAPTERS                          │
  │  Mastodon API  |  Discord webhooks  |  RSS bridges            │
  └──────────────┬───────────────────────────────────────────────┘
                 │
  ┌──────────────▼───────────────────────────────────────────────┐
  │                    DELIVERY MONITOR                           │
  │  Receipt verification  |  Retry logic  |  Alerting            │
  └──────────────┬───────────────────────────────────────────────┘
                 │
  ┌──────────────▼───────────────────────────────────────────────┐
  │                    ANALYTICS COLLECTOR                        │
  │  Engagement metrics  |  Aggregation  |  Reporting             │
  └──────────────────────────────────────────────────────────────┘
                 │
                 └──────────► ORGAN-IV Orchestration Hub (feedback)
```

### Event Ingestion

The ingestion layer accepts publication events from three sources:

- **GitHub Webhooks:** Repository events (push to main, release creation, README deployment) trigger distribution workflows. The ORGAN-IV `distribute-content.yml` workflow sends structured event payloads to this system.
- **RSS Polling:** The ORGAN-V Jekyll site publishes an Atom feed. The RSS poller checks for new entries on a configurable interval (default: 15 minutes) and generates essay publication events.
- **Manual Triggers:** The workflow dispatch interface allows manual event creation for announcements that do not originate from automated sources (partnership announcements, milestone celebrations, ad-hoc promotions).

### Scheduling Engine

The scheduler transforms raw events into timed dispatch jobs. It considers:

- **Content calendar:** Preferred posting times from [distribution-strategy](https://github.com/organvm-vii-kerygma/distribution-strategy). Different announcement types have different optimal windows (essay promotions within 24 hours of publication; community event invitations 7 days before the event).
- **Rate limits:** Per-platform dispatch rate limits prevent API throttling. Mastodon: maximum 30 API calls per 5-minute window. Discord webhooks: maximum 30 requests per minute per webhook.
- **Priority queue:** High-priority announcements (system milestones, breaking changes) preempt lower-priority items in the queue. Priority levels: CRITICAL (immediate), HIGH (within 1 hour), NORMAL (next optimal window), LOW (batch with next digest).
- **Deduplication:** The scheduler detects and suppresses duplicate events (e.g., multiple pushes to the same repository within a short window) to prevent announcement spam.

### Dispatch Adapters

Each distribution channel has a dedicated adapter that handles platform-specific formatting, API authentication, and transmission:

- **Mastodon Adapter:** Uses the Mastodon REST API (v1) for status creation. Handles thread posting (sequential status creation with `in_reply_to_id` chaining), media uploads for images and diagrams, and visibility settings (public, unlisted, followers-only). Implements OAuth 2.0 authentication with token refresh.
- **Discord Adapter:** Uses Discord webhook endpoints for message delivery. Constructs embed objects with organ-specific colors, structured fields, and footer attribution. Supports multiple webhook URLs for channel routing (announcements, releases, community-events, general).
- **RSS Bridge:** Generates and updates syndication feeds that third-party services can consume. Maintains an outbound Atom feed of all announcements for subscribers who prefer feed readers.

### Delivery Monitor

Every dispatched message is tracked through delivery confirmation:

- **Receipt Verification:** After dispatch, the monitor polls the platform API to confirm the message exists and is publicly visible. Mastodon: verifies status exists via GET `/api/v1/statuses/:id`. Discord: verifies message exists via webhook response (HTTP 204 for success).
- **Retry Logic:** Failed dispatches enter a retry queue with exponential backoff. Retry schedule: immediate retry, then 1 minute, 5 minutes, 15 minutes, 1 hour, 6 hours. Maximum 6 retries before escalation.
- **Circuit Breaker:** If a platform's error rate exceeds a threshold (default: 50% of requests failing over a 10-minute window), the circuit breaker opens and halts all dispatches to that platform. The breaker enters a half-open state after a cooldown period (default: 30 minutes), allowing a single test request. If the test succeeds, normal dispatch resumes; if it fails, the breaker remains open for another cooldown cycle.
- **Alerting:** Unresolvable failures (all retries exhausted, circuit breaker open for extended period) trigger alerts via GitHub Issues in the orchestration-start-here repository, ensuring human attention for persistent problems.

### Analytics Collector

Engagement data flows back from distribution channels to inform strategy:

- **Mastodon Metrics:** Boosts, favorites, replies, and click-through rates (via UTM parameter tracking on canonical URLs).
- **Discord Metrics:** Reactions, thread replies, and link clicks (approximated via Discord's limited analytics).
- **Aggregation:** Raw metrics are aggregated into per-announcement, per-channel, per-organ, and per-audience-segment summaries.
- **Reporting:** Weekly analytics reports are generated and stored in the orchestration hub. Reports include: top-performing announcements, channel comparison, audience segment engagement, and trend analysis.

---

## POSSE Implementation

POSSE (Publish on Own Site, Syndicate Elsewhere) is not just a distribution strategy -- it is an ownership strategy. By publishing canonical content on infrastructure the organvm system controls (GitHub Pages, own-domain Jekyll site) and syndicating copies to third-party platforms, the system maintains control over its content regardless of platform policy changes, algorithm shifts, or service shutdowns.

### The POSSE Flow

```
ORGAN-V Jekyll Site (canonical)
        │
        ├──► Atom RSS Feed
        │         │
        │         └──► RSS Poller (this repo)
        │                   │
        │                   └──► Scheduling Engine
        │                              │
        ├──► Mastodon (syndicated copy with canonical link)
        ├──► Discord (syndicated copy with canonical link)
        └──► Future channels (LinkedIn, newsletter, etc.)
```

Every syndicated copy includes a canonical URL pointing back to the ORGAN-V site. This ensures:

1. **Search engine authority** accrues to the canonical site, not to third-party platforms.
2. **Link permanence** -- if a Mastodon instance goes down, the canonical URL remains valid.
3. **Content versioning** -- corrections and updates happen at the canonical source; syndicated copies can reference the canonical URL for the latest version.
4. **Analytics consolidation** -- all click-through traffic arrives at the canonical site, providing a single measurement point.

### Canonical URL Structure

The ORGAN-V Jekyll site at `https://organvm-v-logos.github.io/public-process/` publishes essays with URLs following the pattern:

```
/essays/meta-system/01-why-orchestrate-everything.html
/essays/meta-system/02-governance-without-bureaucracy.html
```

Syndicated copies always link to these canonical URLs with UTM parameters for source tracking:

```
?utm_source=mastodon&utm_medium=social&utm_campaign=essay-01
?utm_source=discord&utm_medium=social&utm_campaign=essay-01
```

---

## Channel Integrations

### Mastodon API Integration

The Mastodon adapter implements the following API operations:

| Operation | Endpoint | Method | Purpose |
|-----------|----------|--------|---------|
| Post status | `/api/v1/statuses` | POST | Create a new toot |
| Post thread | `/api/v1/statuses` (chained) | POST | Create threaded replies |
| Upload media | `/api/v2/media` | POST | Attach images/diagrams |
| Verify status | `/api/v1/statuses/:id` | GET | Confirm delivery |
| Get notifications | `/api/v1/notifications` | GET | Collect engagement data |

**Authentication:** OAuth 2.0 bearer token stored as a GitHub Actions secret (`MASTODON_ACCESS_TOKEN`). Token scope: `read write push`.

**Rate Limiting:** Mastodon instances enforce a rate limit of 300 API calls per 5-minute window. The adapter maintains a sliding window counter and queues requests that would exceed the limit.

**Thread Posting Algorithm:** For multi-post threads (essay promotions, launch announcements), the adapter posts sequentially with a 2-second delay between posts. Each subsequent post includes the `in_reply_to_id` of the previous post to maintain thread structure. If any post in the thread fails, the adapter logs the partial thread and retries only the failed and subsequent posts.

### Discord Webhook Integration

The Discord adapter uses webhook endpoints (not bot accounts) for simplicity and security:

| Operation | Mechanism | Purpose |
|-----------|-----------|---------|
| Send message | POST to webhook URL | Deliver announcement |
| Send embed | POST with embed payload | Rich-formatted announcement |
| Confirm delivery | HTTP 204 response | Verify receipt |

**Webhook Configuration:** Separate webhook URLs for different channels allow routing announcements to appropriate Discord channels. Webhook URLs are stored as GitHub Actions secrets (`DISCORD_WEBHOOK_ANNOUNCEMENTS`, `DISCORD_WEBHOOK_RELEASES`, `DISCORD_WEBHOOK_COMMUNITY`).

**Embed Construction:** Discord embeds are constructed programmatically from template output:

```json
{
  "embeds": [{
    "title": "New Essay: Why Orchestrate Everything",
    "description": "A 5,063-word exploration of why creative systems need governance...",
    "url": "https://organvm-v-logos.github.io/public-process/essays/meta-system/01-why-orchestrate-everything.html",
    "color": 6954906,
    "fields": [
      { "name": "Organ", "value": "V (Logos)", "inline": true },
      { "name": "Word Count", "value": "5,063", "inline": true },
      { "name": "Reading Time", "value": "~20 min", "inline": true }
    ],
    "footer": { "text": "ORGAN-VII Kerygma | organvm distribution" }
  }]
}
```

### RSS-to-Social Bridge

The RSS bridge monitors the ORGAN-V Atom feed and generates distribution events for new entries:

- **Polling interval:** Every 15 minutes (configurable via `RSS_POLL_INTERVAL` environment variable).
- **Deduplication:** Maintains a local state file tracking processed entry GUIDs. Only new entries trigger distribution events.
- **Feed URL:** `https://organvm-v-logos.github.io/public-process/feed.xml`
- **Entry parsing:** Extracts title, summary, canonical URL, publication date, and content hash for each new entry.

---

## Error Handling and Resilience

### Retry Policy

All dispatches use a graduated retry strategy:

| Attempt | Delay | Behavior |
|---------|-------|----------|
| 1 | Immediate | Retry same request |
| 2 | 1 minute | Retry with fresh auth token |
| 3 | 5 minutes | Retry with exponential backoff |
| 4 | 15 minutes | Retry, log warning |
| 5 | 1 hour | Retry, elevate to error |
| 6 | 6 hours | Final retry, create alert issue |

After 6 failed attempts, the dispatch is marked as permanently failed and a GitHub Issue is created in `organvm-iv-taxis/orchestration-start-here` with full error context (HTTP status codes, response bodies, timestamps, retry history).

### Circuit Breaker States

```
CLOSED (normal operation)
    │
    ▼  error rate > 50% over 10 min
OPEN (all requests blocked)
    │
    ▼  30 min cooldown
HALF-OPEN (single test request)
    │
    ├──► success → CLOSED
    └──► failure → OPEN (restart cooldown)
```

### Fallback Strategies

When a primary channel is unavailable:

- **Mastodon down:** Queue all Mastodon dispatches for later delivery. Increase Discord posting frequency to compensate. Log the outage for analytics adjustment.
- **Discord down:** Queue Discord dispatches. Mastodon continues normally. Create an alert issue.
- **Both down:** Queue all dispatches. Create a CRITICAL alert issue. Manual intervention required before queue processing resumes.
- **RSS feed unavailable:** Fall back to GitHub webhook events for essay detection. Log feed outage for investigation.

---

## Monitoring and Delivery Confirmation

### Delivery Dashboard

The monitoring system maintains a real-time view of distribution health:

- **Queue depth:** Number of pending dispatches per channel and priority level.
- **Delivery rate:** Successful dispatches per hour, per channel.
- **Error rate:** Failed dispatches per hour, per channel, with error categorization.
- **Circuit breaker status:** Current state of each channel's circuit breaker.
- **Last successful dispatch:** Timestamp of the most recent confirmed delivery per channel.

### Health Check Endpoints

Automated health checks run on a 5-minute interval:

- **Mastodon connectivity:** Verify API access with a lightweight GET request.
- **Discord webhook validity:** Verify webhook URL returns expected response headers.
- **RSS feed availability:** Verify feed URL returns valid Atom XML.
- **Scheduling engine:** Verify the scheduler process is running and processing queue items.

---

## Analytics Pipeline

### Data Collection

Engagement metrics are collected at configurable intervals (default: daily):

| Metric | Source | Collection Method |
|--------|--------|-------------------|
| Boosts | Mastodon | API polling: `GET /api/v1/statuses/:id` |
| Favorites | Mastodon | API polling: same endpoint |
| Replies | Mastodon | Notification stream filtering |
| Reactions | Discord | Not available via webhooks (manual tracking) |
| Click-throughs | Jekyll site | UTM parameter analysis in site analytics |
| RSS subscribers | Feed server | Subscriber count from feed analytics |

### Aggregation and Reporting

Raw metrics are aggregated into structured reports:

- **Per-announcement report:** engagement across all channels for a single announcement.
- **Per-channel report:** aggregate engagement for a single channel over a time period.
- **Per-organ report:** engagement with announcements related to each organ.
- **Trend report:** week-over-week and month-over-month engagement trends.

Reports are stored as JSON artifacts in the orchestration hub and referenced by the [distribution-strategy](https://github.com/organvm-vii-kerygma/distribution-strategy) repository for strategic planning.

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MASTODON_INSTANCE_URL` | Mastodon server base URL | -- (required) |
| `MASTODON_ACCESS_TOKEN` | OAuth bearer token | -- (required) |
| `DISCORD_WEBHOOK_ANNOUNCEMENTS` | Webhook URL for announcements channel | -- (required) |
| `DISCORD_WEBHOOK_RELEASES` | Webhook URL for releases channel | -- (optional) |
| `DISCORD_WEBHOOK_COMMUNITY` | Webhook URL for community channel | -- (optional) |
| `RSS_FEED_URL` | ORGAN-V Atom feed URL | `https://organvm-v-logos.github.io/public-process/feed.xml` |
| `RSS_POLL_INTERVAL` | Polling interval in minutes | `15` |
| `RETRY_MAX_ATTEMPTS` | Maximum retry attempts | `6` |
| `CIRCUIT_BREAKER_THRESHOLD` | Error rate to trigger breaker | `0.5` |
| `CIRCUIT_BREAKER_COOLDOWN` | Cooldown period in minutes | `30` |

### GitHub Actions Secrets

All sensitive credentials are stored as GitHub Actions secrets, never in code or configuration files:

- `MASTODON_ACCESS_TOKEN` -- Mastodon API authentication
- `DISCORD_WEBHOOK_*` -- Discord webhook URLs (treated as secrets because they grant posting access)

---

## Connection to ORGAN-IV Workflows

This repository's automation integrates directly with the ORGAN-IV orchestration hub's `distribute-content.yml` workflow. The workflow:

1. Receives a `workflow_dispatch` trigger with content payload (announcement text, target channels, priority).
2. Invokes the Mastodon and Discord dispatch adapters defined in this repository.
3. Collects delivery confirmations (HTTP 200 from Mastodon, HTTP 204 from Discord).
4. Reports results back to the workflow caller.

The integration was verified live during system launch (2026-02-11): Mastodon returned HTTP 200 and Discord returned HTTP 204 for the launch announcement, confirming end-to-end POSSE delivery.

---

## Security and Credential Management

- **No credentials in code.** All API tokens and webhook URLs are stored as GitHub Actions secrets or environment variables injected at runtime.
- **Token rotation.** Mastodon access tokens should be rotated quarterly. A reminder is included in the maintenance calendar.
- **Webhook URL protection.** Discord webhook URLs are treated as secrets because anyone with the URL can post to the channel.
- **Audit logging.** All dispatch attempts (successful and failed) are logged with timestamps, target channels, and HTTP response codes. Logs are retained for 90 days.
- **Principle of least privilege.** The Mastodon token has only the scopes required for posting and reading engagement metrics (`read write push`). No admin or moderation scopes.

---

## Metrics and Tracking

Distribution effectiveness is measured across four dimensions:

- **Delivery reliability:** Percentage of dispatches that succeed on first attempt (target: 95%+).
- **Delivery latency:** Time from event ingestion to confirmed delivery (target: under 5 minutes for HIGH priority, under 24 hours for NORMAL).
- **Engagement rate:** Average engagement (boosts + favorites + replies) per announcement (tracked per channel and per audience segment).
- **System uptime:** Percentage of time all channels are in CLOSED (healthy) circuit breaker state (target: 99%+).

---

## Cross-Organ Dependencies

| Dependency | Direction | Purpose |
|-----------|-----------|---------|
| ORGAN-IV orchestration-start-here | VII consumes IV | distribute-content.yml triggers dispatches |
| ORGAN-IV orchestration-start-here | VII reports to IV | Analytics and delivery logs flow to orchestration hub |
| ORGAN-V public-process | VII monitors V | RSS feed polling for essay publication events |
| announcement-templates | VII internal | Templates provide formatted content for dispatch |
| distribution-strategy | VII internal | Calendar and audience data inform scheduling |
| registry-v2.json | VII consumes IV | Repository metadata for template interpolation |

---

## Roadmap

- **Phase 1 (Current):** Mastodon + Discord integration via GitHub Actions workflows. Manual trigger capability. Basic delivery monitoring.
- **Phase 2:** RSS polling automation. Automated essay promotion pipeline. Engagement analytics collection.
- **Phase 3:** LinkedIn API integration. Email newsletter dispatch (via Buttondown or similar). Advanced scheduling with audience engagement pattern analysis.
- **Phase 4:** Self-hosted monitoring dashboard. Historical analytics database. A/B testing for announcement formats.

---

## Contributing

Contributions to the automation infrastructure should be proposed via issue before implementation. Key areas for contribution:

- **New channel adapters** -- integration specs for additional platforms (Bluesky, LinkedIn, Buttondown).
- **Analytics enhancements** -- richer engagement metrics, visualization dashboards, trend detection.
- **Resilience improvements** -- better retry strategies, smarter circuit breaker tuning, chaos testing.

See [CONTRIBUTING.md](https://github.com/organvm-vii-kerygma/.github/blob/main/CONTRIBUTING.md) for general contribution guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for full text.

---

## Author and Contact

**4444J99** -- [@4444J99](https://github.com/4444J99)

Part of the [organvm](https://github.com/meta-organvm) eight-organ creative-institutional system.
ORGAN-VII (Kerygma) -- Marketing, Distribution, and Audience Building.
