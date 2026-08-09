# STRling Documentation — Dedicated Docs and Inline Pedagogy

> **Scope:** This file governs dedicated documentation, inline code pedagogy, structural doc blocks, and synchronous updates to `docs/`. It does NOT define pipeline architecture, test strategy, or contributor workflow beyond documentation obligations.

---

## Documentation Prime Directive

Documentation in STRling exists to **teach the consumer and the developer**. It is not a label layer and it is not optional polish. It is part of the implementation contract.

If a feature is created, changed, or removed, its explanation must be created, changed, or removed in the same turn or PR.

---

## The Zero-Debt Rule

AI agents must identify and update the relevant files in `docs/` whenever a feature, API, behavior, or workflow changes.

### Non-Negotiable Requirements

1. **No code-only feature changes.** If behavior changes, the durable docs must change too.
2. **No stale examples.** If a public API or workflow example becomes outdated, it must be corrected immediately.
3. **No deferred documentation promises.** Do not leave TODOs such as "document later" when the current turn can update the relevant docs.

### Required Targets

-   Update the most relevant spoke documents under `docs/`.
-   Preserve the hub-and-spoke topology rooted at `docs/index.md`.
-   If no existing spoke fits, create or extend the closest authoritative document rather than scattering guidance across unrelated files.

---

## Module Pedagogy Header

Every source file must begin with a **Module Pedagogy** header that explains the file's role in the STRling system.

### Purpose

The header must explain:

-   Where the file sits in the STRling pipeline or support architecture
-   Why the module exists
-   What higher-level contract it owns

### Example

```typescript
/**
 * Module Pedagogy:
 * This module transforms AST nodes into PCRE2-compatible strings.
 * It owns engine-specific escaping and serialization decisions after
 * the compiler has already produced target-agnostic IR.
 */
```

This is a teaching block. It must explain the architectural role of the module, not just restate the filename.

---

## Structural Documentation Tags

All classes, methods, functions, and exported constants must use the language-native documentation format:

-   **TypeScript / JavaScript:** JSDoc
-   **Python:** docstrings
-   **C#:** XML documentation comments
-   **Java / Kotlin:** Javadoc or KDoc
-   **Go:** Go doc comments
-   **Rust:** rustdoc

### Mandatory Structural Fields

Every documented class, method, or function must include the equivalent of:

-   `@description`
-   `@param` for every parameter
-   `@returns` when a value is returned
-   `@throws` for every intentional error path

### Strict Type Requirement

-   Parameter and return documentation must include the strict type expected by the binding.
-   If the language-native format does not use explicit tags, the prose must still name the concrete type.
-   Do not use vague phrases like "value" or "object" when the actual contract is `Pattern`, `IRNode`, `string`, `Flags`, or `TargetArtifact`.

---

## Pedagogical Block Requirement

If a function or method contains more than **3 lines of logic**, it requires a pedagogical documentation block.

### The Block Must Explain

-   Why this approach exists
-   What architectural constraint it satisfies
-   What failure mode or regression it prevents

### The Block Must Not Do

-   Narrate line-by-line mechanics
-   Repeat obvious syntax
-   Replace good naming

Pedagogical comments explain **reasoning**, not keystrokes.

---

## Inline Pedagogy for Complex Logic

Complex blocks such as backtracking control, state-machine transitions, escape handling, normalization passes, IR lowering, and hint generation require inline comments that explain the **architectural reasoning**.

### Good Comment

```typescript
// We normalize adjacent literals here so every emitter can assume compact IR
// and avoid reimplementing concatenation repair logic per target engine.
```

### Bad Comment

```typescript
// Loop through literals and combine them.
```

The first comment teaches the invariant. The second merely labels the syntax.

---

## Documentation Sync Rules

When changing code, agents must ask which durable docs are affected:

-   Public API changed: update the relevant API guide, README examples, and binding docs
-   Parser or compiler behavior changed: update architecture or spec-linked documentation
-   Test or workflow behavior changed: update the relevant testing or contributor docs
-   Tooling output changed: update setup, workflow, or release documentation as appropriate

If the answer is "none," that must be a deliberate conclusion, not an omission.

---

## Anti-Regression Rules

-   **Do not** merge code changes without corresponding `docs/` updates when behavior, public APIs, or workflows changed.
-   **Do not** accept doc blocks that omit parameter or return types.
-   **Do not** use comments to describe trivial operations when the real missing information is architectural intent.
-   **Do not** treat documentation as secondary to implementation. In STRling, documentation is part of the implementation.
-   **Do not** write headers or comments that assume regex expertise when STRling can explain the semantic intent directly.
