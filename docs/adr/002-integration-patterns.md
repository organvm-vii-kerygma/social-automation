# ADR-002: Cross-Organ Integration and Dependency Patterns

## Status

Accepted

## Date

2026-02-11

## Context

The organvm system enforces a strict dependency flow across organs. This repository must define its integration points within this constraint.

## Decision

This repository participates in the cross-organ dependency graph through documentation and specification sharing. Dependencies are declared in registry-v2.json. Communication is asynchronous through versioned releases and registry state.

## Consequences

### Positive

- No circular dependencies — the graph is validated by CI
- Loose coupling allows independent development
- Registry-driven discovery makes integration explicit

### Negative

- Cross-organ changes require coordinated registry updates

## References

- Dependency validation: validate-dependencies.yml in orchestration-start-here
- Orchestration system: docs/implementation/orchestration-system-v2.md
