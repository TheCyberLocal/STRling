# Architectural Invariants

## Status

This document defines STRling's target architecture at the level required to
govern migration. It does not prescribe a compiler language, deployment model,
or detailed component layout. The current repository contains duplicated
semantic implementations across bindings and other transitional paths; those
paths are not yet compliant with the target invariants below.

## Target dependency direction

The semantic compilation path MUST follow this conceptual direction:

```text
authoring frontend -> semantic model -> analysis -> portability planning -> target lowering -> emitter
```

Dependencies MUST flow toward stable contracts at each boundary. Later fitness
gates MUST make prohibited reverse or cross-layer dependencies detectable.

## Invariants

### Convergent authoring surfaces

Textual DSL parsing, fluent builders, editor features, and other authoring
surfaces MAY provide different input experiences, but their semantic input MUST
converge on one canonical semantic model. An authoring surface MUST NOT define a
parallel meaning for the same versioned construct.

### One semantic compiler authority

Parsing, normalization, semantic analysis, portability planning, target
lowering, and emission semantics MUST have one canonical implementation. A
reference implementation is subordinate to the specification and contracts; it
does not gain semantic authority merely by being executable.

### Explicit capability planning

Target capability planning MUST be distinct from target serialization.
Planning determines whether a construct has native support, requires a
semantics-preserving rewrite, or is unsupported. An explicitly requested
degraded mode MAY be added only under a versioned contract. Emitters MUST
serialize a deliberate plan rather than silently invent portability behavior.

### Thin host-language adapters

Host-language bindings MUST eventually depend on a stable canonical compiler
interface rather than compiler internals. Adapters MAY own idiomatic public APIs,
data conversion, runtime integration, packaging, and host-specific error
mapping. They MUST NOT own shadow parsers, analyzers, portability planners, or
emitters for canonical STRling semantics.

### Canonical tooling path

Language servers, editor integrations, CLIs, documentation tools, conformance
tools, and other semantic consumers MUST use the canonical compiler interface.
Tooling MUST NOT maintain a shadow compiler or silently reinterpret compiler
results.

### Deterministic contracts

Semantic boundaries MUST carry the versioned inputs needed for deterministic
results, including compiler version, specification version, target profile, and
compiler options. Diagnostics and target artifacts MUST remain traceable to
those inputs.

### Progressive enforcement

Architecture fitness rules MUST tighten as transitional implementations are
replaced. Each gate MUST state its current scope, allowed exceptions, and
evidence. Transitional code MAY be temporarily outside a final-state rule only
through recorded scope or a governed waiver; it MUST NOT be represented as
already compliant.
