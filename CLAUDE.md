# CLAUDE.md — social-automation

**ORGAN VII** (Marketing) · `organvm-vii-kerygma/social-automation`
**Status:** ACTIVE · **Branch:** `main`

## What This Repo Is

POSSE automation backend: Mastodon API, Discord webhooks, RSS-to-social bridges, scheduling, delivery monitoring, and analytics pipeline

## Stack

**Languages:** Python
**Build:** Python (pip/setuptools)
**Testing:** pytest (likely)

## Directory Structure

```
📁 .github/
📁 docs/
    adr
📁 src/
    __init__.py
    discord.py
    mastodon.py
    posse.py
📁 tests/
    __init__.py
    test_discord.py
    test_mastodon.py
    test_posse.py
  .gitignore
  CHANGELOG.md
  LICENSE
  README.md
  pyproject.toml
  seed.yaml
```

## Key Files

- `README.md` — Project documentation
- `pyproject.toml` — Python project config
- `seed.yaml` — ORGANVM orchestration metadata
- `src/` — Main source code
- `tests/` — Test suite

## Development

```bash
pip install -e .    # Install in development mode
pytest              # Run tests
```

## ORGANVM Context

This repository is part of the **ORGANVM** eight-organ creative-institutional system.
It belongs to **ORGAN VII (Marketing)** under the `organvm-vii-kerygma` GitHub organization.

**Registry:** [`registry-v2.json`](https://github.com/meta-organvm/organvm-corpvs-testamentvm/blob/main/registry-v2.json)
**Corpus:** [`organvm-corpvs-testamentvm`](https://github.com/meta-organvm/organvm-corpvs-testamentvm)
