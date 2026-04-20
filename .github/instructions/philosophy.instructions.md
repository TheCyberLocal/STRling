# STRling Philosophy — Fluent Abstraction Over Raw Regex

> **Scope:** This file governs API design, interface naming, and the semantic intent of every user-facing surface. It does NOT cover pipeline internals, test strategy, or contributor workflow.

---

## Prime Directive

STRling exists to **abstract the cryptic nature of raw regex into a readable, semantic, object-oriented interface**. Every design decision must serve this goal.

Raw regex is technical debt the moment it appears in application code. STRling treats regex as **software** — composable, type-safe, and self-documenting — not as an opaque string.

---

## Non-Negotiable Constraints

1. **No Raw Regex in the Public API.** Users must never be required to write, read, or debug native regex syntax to use STRling. The compiled output is an implementation detail, not a user-facing surface.
2. **Fluent Readability Over Brevity.** Method names must describe **intent**, not regex mechanics. Prefer `simply.lookBehind(...)` over any shorthand that leaks engine notation like `(?<=...)`.
3. **Intent-First Naming.** Every public method, class, and parameter name must be understandable to a developer who has never seen a regex character class. Names like `digit()`, `oneOrMore()`, `capture()`, and `anyOf()` are correct. Names that mirror regex tokens (`star()`, `qmark()`, `pipe()`) are forbidden.
4. **Composition Over Concatenation.** Patterns are built from reusable, composable building blocks — not by string-gluing regex fragments. The Simply API's chainable `Pattern` objects enforce this structurally.
5. **Type Safety as a Design Tool.** IDE autocomplete and compile-time checks must catch errors before runtime. The API surface should make invalid patterns unrepresentable where possible.

---

## The Simply API Contract

The Simply API is the **primary fluent interface** for constructing patterns programmatically. It wraps AST nodes in chainable `Pattern` objects so developers compose intent without touching the IR or regex output directly.

### Design Rules

- Every `Pattern` method maps to a meaningful pattern concept, not a regex syntax trick.
- Method chains read as near-English descriptions of matching intent.
- The compiled regex string is never the return type of a builder method; it is only produced by an explicit `compile()` or `emit()` terminal operation.

### Example: Phone Number

```typescript
import { simply as s } from "@strling-lang/strling";

s.digit(3).then("-").then(s.digit(3)).then("-").then(s.digit(4));
```

This reads as intent. The equivalent raw regex `\d{3}-\d{3}-\d{4}` does not.

---

## Anti-Regression Rules

- **Do not** introduce public API methods whose names require knowledge of regex syntax to understand.
- **Do not** accept raw regex strings as parameters in the fluent API unless explicitly gated behind an `unsafe` or `raw` escape hatch that is clearly documented as an advanced opt-in.
- **Do not** surface compiled regex output in error messages when a semantic explanation is available. Users should see "Expected a digit quantifier" not "Expected \d{n}".
- **Do not** document STRling features by showing the regex output first. Always lead with the fluent API form; show the compiled output only as a secondary reference.

---

## Readability Litmus Test

Before merging any public API change, apply this check:

> _Can a junior developer who has never written a regex read this pattern chain and understand what it matches?_

If the answer is no, the API surface needs revision.
