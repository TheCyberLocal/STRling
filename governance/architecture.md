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

## Fitness rule categories

Architecture policy distinguishes placement, dependency, authority, and
transition rules. Placement rules govern where task records and new semantic
components may appear. Dependency rules inspect language imports or structured
references where a reliable parser is available. Authority rules prevent
generated or implementation output from becoming specification input.
Transition rules report current duplication or temporary dependencies without
misrepresenting final-state compliance.

New dependency analyzers MUST resolve the syntax they govern (for example the
Python AST or JSON Schema `$ref` values) and MUST fail closed on malformed
source. Text search may support discovery but is not sufficient evidence for an
enforced import boundary when a language-aware parser is reasonably available.

Rules tighten monotonically. A transition records its exact retirement
condition; activation changes only its status and does not require a new rule
framework. Weakening an enforced boundary requires an explicit breaking
architecture declaration, affected rule or surface identifiers, and evidence
for the replacement or bounded exception.

## Certified current fitness boundaries

Enforced rules now parse Python imports for governance and quality dependency
boundaries, resolve JSON Schema references within specification-owned roots,
bound implementation-derived fixture authority, and inspect newly added Python
or JavaScript-family declarations for semantic implementation islands. These
checks complement generated-input acyclicity and task or top-level placement
rules. Malformed governed source fails closed.

Transitional rules are evaluated and report evidence without becoming false
fatal violations. They currently cover duplicated binding parsers, compilers,
and emitters; implementation-derived shared fixtures; and direct LSP imports of
the Python binding. Their retirement conditions remain attached to the rule
registry, so promotion requires only changing `transitional` to `enforced` once
the stated migration evidence exists.

The binding-to-canonical-core rule remains future-state because no canonical
core exists. It must not block the current repository or be used to claim that
per-binding semantic implementations are already violations. The future rule
activates per binding only after core implementation, adapter migration, legacy
implementation removal, and behavior-preservation certification.
