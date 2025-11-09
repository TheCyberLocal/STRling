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
- **Portability**: New target engines can be added without changing the parser or IR
- **Testability**: Each phase can be tested independently
- **Maintainability**: Changes to one phase don't cascade to others

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

- New output formats are easier to add and review
- Testing is simplified: call render with a model → assert string/bytes
- Performance-sensitive emitters may provide streaming helpers without breaking the deterministic contract

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

- **EBNF Grammar** is the canonical definition of **syntax** (what is parsable)
- **Semantics Document** is the canonical definition of **behavior** (what parsed constructs mean)
- Both artifacts are versioned together and are equally authoritative

### Feature Categorization

- **Core features**: Portable across all supported regex engines
- **Extension features**: Engine-specific, clearly documented as such

### Any New Feature Must Include

1. EBNF grammar update in `spec/grammar/dsl.ebnf`
2. Semantics update in `spec/grammar/semantics.md` (including portability rules)
3. Impact assessment on target artifact schemas in `spec/schema/`

### Benefits

- ✅ Eliminates drift between grammar and semantics
- ✅ Ensures every feature is backed by both parse rules and behavioral contracts
- ✅ Provides clear validation criteria for emitters and bindings
- ⚠️ Requires coordination when evolving the DSL (must touch multiple files)

See the [Formal Language Specification](spec_links.md) for links to all specification artifacts.

---

## Separation of Concerns

STRling maintains a clear separation between components:

- **Specification** (`spec/`): Formal grammar, semantics, and schemas
- **Core** (`core/`): Language-agnostic compiler and IR
- **Emitters** (`emitters/`): Target-specific code generators
- **Bindings** (`bindings/`): Language-specific APIs and convenience wrappers
- **Tests** (`tests/`): Validation and verification

### Benefits

- Changes to one component don't cascade unnecessarily
- Each component can be understood independently
- Testing can be targeted and efficient

---

## Design Decisions Archive

For historical context on architectural decisions, see the archived ADR (Architecture Decision Records) that informed these principles. The principles documented here represent the current, authoritative design philosophy.
