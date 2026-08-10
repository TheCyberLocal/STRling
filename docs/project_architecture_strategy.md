# Project Architecture & Strategy

[← Back to Developer Hub](index.md)

## Durable direction

STRling develops as one semantic compiler platform with multiple authoring
surfaces, host adapters, target profiles, and tooling consumers. The ratified
[`product architecture`](../governance/product.md) and
[`architecture invariants`](../governance/architecture.md) control this
strategy.

Work proceeds contract first:

1. ratify semantic specifications or versioned contracts;
2. author independent conformance evidence;
3. implement the canonical compiler capability;
4. verify behavior and compatibility;
5. expose it through thin host adapters and shared tooling; and
6. certify target-specific artifacts against versioned profiles.

## Sources of authority

The ratified specification defines semantic behavior. Versioned formal contracts
and delegated specification-authored conformance cases define their declared
scopes. The reference implementation demonstrates conformance and cannot
silently extend those sources.

TypeScript is not the semantic source of truth. The current TypeScript
implementation and its generated fixtures remain transitional compatibility
evidence.

`bindings/python/pyproject.toml` remains an **operational package-version
source** for existing release synchronization. That role grants no semantic or
specification authority.

## Target compiler model

```text
Semantic STRling / Simply / regex import
    -> canonical semantic representation
    -> analysis and portability planning
    -> target lowering and emission
    -> versioned target artifact
```

The target architecture contains one canonical implementation of semantic
meaning. Bindings become adapters that retain idiomatic public APIs,
interoperability, packaging, and error conversion without owning shadow
compilers.

Target engines are independent of host languages. New target support requires a
version-sensitive target profile, deliberate planning/lowering behavior, and an
emitter—not a new host binding.

## Transitional operating model

Until the canonical compiler and contracts exist, the repository preserves
current public APIs and differential behavior:

-   duplicated binding compilers remain active but transitional;
-   TypeScript-generated JSON remains non-normative compatibility evidence;
-   current AST, IR, target schemas, and hint parity remain migration inputs;
-   binding-coupled editor intelligence remains available; and
-   existing target limitations remain recorded rather than normalized into
    permanent product requirements.

Contained migration work may use the existing TypeScript fixture producer and
cross-binding parity tests, but generation never authorizes behavior.

## Delivery stages

1. **Canonical semantic contracts:** define source, Semantic IR, diagnostics,
   compiler request/result, target profile, and target artifact without importing
   accidental choices from one binding.
2. **Reference compiler:** implement ratified contracts in one canonical
   compiler, potentially Rust, while keeping the specification authoritative.
3. **Adapter migration:** move bindings to the stable boundary one at a time and
   retire duplicated semantics only after behavior-preservation certification.
4. **Tooling convergence:** route CLI, LSP, editors, and documentation tooling
   through the same interface.
5. **Target expansion:** add engine support through profiles, planning, lowering,
   emitters, and conformance evidence.

## Release readiness

The canonical `./strling check all` and `./strling certify all` aggregates are
gates. Package publication must also verify installability and smoke behavior
from the actual distribution channel. Compatibility evidence may block a
migration decision, but it does not outrank the controlling specification.
