# STRling Architectural Principles

[← Back to Developer Hub](index.md)

This document details STRling's foundational design decisions and architectural principles that ensure consistency, reliability, and maintainability across the entire project.

---

## The Parse → Compile (IR) → Emit Pipeline

STRling follows a classic compiler architecture with three distinct phases:

1. **Parse**: Transform user input (STRling DSL) into an Abstract Syntax Tree (AST)
2. **Compile (IR)**: Convert the AST into an Intermediate Representation (IR) that is target-agnostic
3. **Emit**: Generate target-specific output (PCRE2, ECMAScript, etc.) from the IR

This separation ensures:

-   **Portability**: New target engines can be added without changing the parser or IR
-   **Testability**: Each phase can be tested independently
-   **Maintainability**: Changes to one phase don't cascade to others

---

## The Iron Law of Emitters

**Principle**: Every emitter must implement a predictable, testable interface with no side effects.

Emitters are the core abstraction that translate STRling's internal representation into serialized outputs (text, JSON, regex patterns). To ensure consistency and prevent duplicated logic, all emitters must adhere to the "Iron Law":

### Requirements

1. **Single, well-documented interface** with:

    - Concise initialization API (config + dependencies)
    - Single render/emit method accepting a canonical internal model
    - No side effects (emitters return strings/bytes or write to provided streams)
    - Deterministic output for a given model + config

2. **Shared concerns** (format helpers, validation, escaping) live in `core/` or `emitters/utils/` — not duplicated in each emitter

### Benefits

-   New output formats are easier to add and review
-   Testing is simplified: call render with a model → assert string/bytes
-   Performance-sensitive emitters may provide streaming helpers without breaking the deterministic contract

### Example Structure

**Python:**

```python
class PCRE2Emitter:
    def __init__(self, config: EmitterConfig):
        self.config = config

    def emit(self, model: IRModel) -> str:
        # Deterministic transformation
        return self._render(model)
```

**JavaScript:**

```typescript
class PCRE2Emitter {
    constructor(config: EmitterConfig) {
        this.config = config;
    }

    emit(model: IRModel): string {
        // Deterministic transformation
        return this._render(model);
    }
}
```

---

## Grammar and Semantics Alignment

**Principle**: The EBNF grammar and semantics specification are both normative and must evolve in lockstep.

STRling defines both a formal grammar (`spec/grammar/dsl.ebnf`) and normative semantics (`spec/grammar/semantics.md`). For STRling to remain portable and testable across multiple regex engines (PCRE2, ECMAScript, etc.), both must be kept synchronized.

### The Contract

-   **EBNF Grammar** is the canonical definition of **syntax** (what is parsable)
-   **Semantics Document** is the canonical definition of **behavior** (what parsed constructs mean)
-   Both artifacts are versioned together and are equally authoritative

### Feature Categorization

-   **Core features**: Portable across all supported regex engines
-   **Extension features**: Engine-specific, clearly documented as such

### Any New Feature Must Include

1. EBNF grammar update in `spec/grammar/dsl.ebnf`
2. Semantics update in `spec/grammar/semantics.md` (including portability rules)
3. Impact assessment on target artifact schemas in `spec/schema/`

### Benefits

-   ✅ Eliminates drift between grammar and semantics
-   ✅ Ensures every feature is backed by both parse rules and behavioral contracts
-   ✅ Provides clear validation criteria for emitters and bindings
-   ⚠️ Requires coordination when evolving the DSL (must touch multiple files)

See the Formal Language Specification (via Developer Hub) for links to all specification artifacts.

---

## Separation of Concerns

STRling maintains a clear separation between components:

-   **Specification** (`spec/`): Formal grammar, semantics, and schemas
-   **Core** (`core/`): Language-agnostic compiler and IR
-   **Emitters** (`emitters/`): Target-specific code generators
-   **Bindings** (`bindings/`): Language-specific APIs and convenience wrappers
-   **Tests** (`tests/`): Validation and verification

### Benefits

-   Changes to one component don't cascade unnecessarily
-   Each component can be understood independently
-   Testing can be targeted and efficient

---

## Design Decisions Archive

For historical context on architectural decisions, see the archived ADR (Architecture Decision Records) that informed these principles. The principles documented here represent the current, authoritative design philosophy.

---

## Real-Time Diagnostics Architecture

STRling's real-time diagnostics feature introduces a small, explicit architecture that complements the existing compiler pipeline. The model is intentionally binding-agnostic and focuses on a clear contract between interactive editors and the parser runtime.

The execution flow is:

-   **Editor → LSP Server → CLI Server → Parser**

1. **Editor**: Any text editor with LSP support (VS Code, Neovim, etc.) sends document changes and receives diagnostics and code actions.
2. **LSP Server**: Implements the Language Server Protocol, converts text edits into diagnostic requests, formats `to_lsp_diagnostic()` output, and provides code-actions where applicable.
3. **CLI Server**: A small, language-neutral service (invoked by the LSP server or bindings) that marshals input to the parser and normalizes responses into a diagnostic contract.
4. **Parser**: The authoritative parser that produces `STRlingParseError` objects and machine-readable diagnostics.

Key design constraints and guarantees:

-   **Binding-agnostic contract**: The CLI Server exposes a stable, versioned contract that every binding (Python, JavaScript, other) can call. The contract returns structured diagnostics and optional fix suggestions.
-   **Idempotence**: Diagnostic responses are deterministic for a given document state.
-   **Partial parsing**: The parser supports incremental checks for fast, near-real-time feedback.
-   **Security**: No sensitive information is returned in diagnostics; error hints are limited to the pattern content and suggested remediation.

Responsibility split:

-   The **Parser** remains the source of truth for syntax and semantics.
-   The **CLI Server** normalizes parser output and enforces the binding-agnostic diagnostic schema.
-   The **LSP Server** handles editor protocol concerns, UI-level formatting, and context-sensitive code-actions.

This architecture ensures that editor integrations can be built rapidly while maintaining a single, testable source of truth for diagnostics and suggestions.

---

## The Simply API (Fluent Builder Pattern)

The **Simply API** provides a type-safe, object-oriented alternative to the raw DSL string syntax for constructing regex patterns programmatically. Rather than writing regex as text, developers compose patterns using chainable method calls that directly map to the Intermediate Representation (IR).

### Why Simply?

Regular expressions are notoriously difficult to read and maintain. The Simply API addresses this by:

-   **Hiding Raw Regex**: Users never write cryptic character sequences like `(?<=\d{3})` directly
-   **Providing Type Safety**: IDE autocomplete and compile-time checks catch errors before runtime
-   **Enabling Composition**: Complex patterns are built from simple, reusable building blocks
-   **Improving Readability**: Method names like `digit()`, `oneOrMore()`, and `capture()` are self-documenting

### Semantic Intent

The Simply API is designed as a **semantic abstraction layer**. Each method call represents a meaningful pattern concept, not a regex syntax trick. This makes patterns accessible to developers who may not be regex experts.

### DSL vs. Simply: A Comparison

The following examples demonstrate equivalent patterns using both approaches:

**Example 1: Matching a Phone Number**

```
DSL String:
\d{3}-\d{3}-\d{4}

Simply API (TypeScript):
import { simply as s } from '@strling-lang/strling';

s.digit(3)
 .then('-')
 .then(s.digit(3))
 .then('-')
 .then(s.digit(4));
```

**Example 2: Matching an Email Local Part**

```
DSL String:
[A-Za-z0-9._%+-]+

Simply API (TypeScript):
import { simply as s } from '@strling-lang/strling';

s.anyOf(
    s.letter(),
    s.digit(),
    '.', '_', '%', '+', '-'
).oneOrMore();
```

**Example 3: Capturing with Named Groups**

```
DSL String:
(?<area>\d{3})-(?<exchange>\d{3})-(?<line>\d{4})

Simply API (TypeScript):
import { simply as s } from '@strling-lang/strling';

s.capture('area', s.digit(3))
 .then('-')
 .then(s.capture('exchange', s.digit(3)))
 .then('-')
 .then(s.capture('line', s.digit(4)));
```

### Mapping to IR Nodes

Every Simply API method corresponds directly to an IR node type. This 1:1 mapping ensures predictable, auditable output:

| Simply Method     | IR Node Type | Description                         |
| ----------------- | ------------ | ----------------------------------- |
| `s.lit('text')`   | `Lit`        | Literal character sequence          |
| `s.digit()`       | `CharClass`  | Digit character class (`\d`)        |
| `s.letter()`      | `CharClass`  | Letter character class (`[A-Za-z]`) |
| `s.anyOf(...)`    | `Alt`        | Alternation (OR)                    |
| `s.merge(...)`    | `Seq`        | Sequence concatenation              |
| `s.capture(name)` | `Group`      | Named capturing group               |
| `s.group(...)`    | `Group`      | Non-capturing group                 |
| `.oneOrMore()`    | `Quant`      | Quantifier with min=1, max=∞        |
| `.zeroOrMore()`   | `Quant`      | Quantifier with min=0, max=∞        |
| `.optional()`     | `Quant`      | Quantifier with min=0, max=1        |
| `.repeat(n,m)`    | `Quant`      | Quantifier with explicit bounds     |

### The Pattern Class

At the heart of the Simply API is the `Pattern` class. Each method returns a new `Pattern` instance, enabling fluent chaining:

```typescript
// Pattern class provides chainable modifiers
const pattern = s
    .digit() // Returns Pattern wrapping CharClass node
    .oneOrMore() // Returns Pattern wrapping Quant node
    .lazy(); // Returns Pattern with lazy quantification
```

The `Pattern` class also exposes compilation methods:

-   `pattern.compile()` → Returns the compiled IR
-   `pattern.toPCRE2()` → Emits a PCRE2-compatible regex string
-   `pattern.toJS()` → Emits an ECMAScript-compatible regex string

### Error Handling

The Simply API uses `STRlingError` exceptions with instructional messages. When an invalid pattern is constructed, the error explains both what went wrong and how to fix it:

```typescript
try {
    s.capture("name", s.digit()).capture("name", s.letter()); // Duplicate name!
} catch (e) {
    // STRlingError: Duplicate named capture group 'name'.
    // Each capture group must have a unique name within a pattern.
}
```

### Best Practices

1. **Compose Small Patterns**: Build complex patterns from simple, tested components
2. **Use Named Captures**: Prefer `capture('name', ...)` over anonymous groups for clarity
3. **Chain Readably**: Break long chains across multiple lines for readability
4. **Avoid Raw Regex**: If you find yourself thinking in regex syntax, step back and use Simply methods

---

## Related Documentation

-   **[Project Architecture & Strategy](project_architecture_strategy.md)**: Binding SSOT rules, diagnostics flow, and release strategy.
-   **[Developer Hub](index.md)**: Return to the central documentation hub
