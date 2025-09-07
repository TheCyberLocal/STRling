# ADR-002: Grammar and Semantics Alignment

**Status:** Proposed
**Date:** 2025-09-07

## Context

STRling v3 defines both a formal grammar (`dsl.ebnf`) and a normative semantics specification (`semantics.md`).
Historically, projects either (a) treat EBNF as the only source of truth (syntax-only), or (b) allow semantics docs to drift from grammar definitions, creating ambiguity.
For STRling to remain portable and testable across multiple regex engines (PCRE2, ECMAScript, etc.), both grammar and semantics must evolve in lockstep.

## Decision

-   The **EBNF grammar** (`dsl.ebnf`) is the canonical definition of the syntax.
-   The **semantics document** (`semantics.md`) is the canonical definition of behavior and intent.
-   Both artifacts are **normative** and versioned together:

    -   Grammar defines _what is parsable_.
    -   Semantics defines _what parsed constructs mean_ and how emitters must handle them.

-   Features are categorized as **core** (portable across all engines) and **extensions** (engine-specific).
-   Any new feature proposal must include:

    1. EBNF update
    2. Semantics update (including portability rules)
    3. TargetArtifact schema impact assessment

## Consequences

-   ✅ Eliminates drift between grammar and semantics.
-   ✅ Ensures every feature is backed by both parse rules and a behavioral contract.
-   ✅ Clearer validation for emitters and bindings.
-   ⚠️ Slightly higher overhead when evolving the DSL (must touch multiple files).
