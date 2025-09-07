# ADR 001 — Iron Law of Emitters

**Status:** Proposed  
**Date:** 2025-09-07

## Context

Emitters are the core abstraction that translate internal data structures into serialized outputs (text, JSON, clinical formats). Inconsistent emitter design has caused duplicated logic and unexpected behavior when adding new output formats.

## Decision

Adopt the "Iron Law of Emitters":

-   Each emitter must implement a single, well-documented interface with:

    -   a concise initialization API (config + dependencies),
    -   a single render/emit method that accepts a canonical internal model,
    -   no side effects (emitters return strings/bytes or write to provided streams),
    -   deterministic output for a given model + config.

-   Shared concerns (format helpers, validation, escaping) live in core/ or a shared emitters/utils module.

## Consequences

-   New formats are easier to add and review.
-   Testing is simplified (call render with a model -> assert string/bytes).
-   Performance-sensitive emitters may provide streaming helpers, but must not break the deterministic contract.

## Notes

This ADR sets the shape of emitter interfaces and points to code-level guidelines in docs/emitters.md.
