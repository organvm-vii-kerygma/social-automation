# ADR-001: Initial Architecture and Technology Choices

## Status

Accepted

## Date

2026-02-11

## Context

This repository is part of the organvm eight-organ creative-institutional system. As a documentation-focused project, it needed a structure that supports long-term maintainability and portfolio-quality presentation.

## Decision

We chose a documentation-first approach with Markdown as the primary format, following the organvm repository standards. The project integrates with the cross-organ dependency graph maintained in registry-v2.json and follows the promotion state machine (LOCAL -> CANDIDATE -> PUBLIC_PROCESS -> GRADUATED -> ARCHIVED).

Key choices:
- **Format**: Markdown for universal compatibility and GitHub rendering
- **CI/CD**: Minimal CI (structure validation, link checking)
- **Documentation**: Portfolio-quality README targeting grant reviewers and hiring managers
- **Governance**: Follows ORGAN-IV orchestration rules

## Consequences

### Positive

- Low maintenance overhead for documentation-only projects
- Consistent with system-wide conventions
- CI validates structural integrity automatically

### Negative

- No runtime code means limited automated testing
- Documentation must be manually kept in sync with system changes

## References

- Part of the [organvm eight-organ system](https://github.com/meta-organvm)
