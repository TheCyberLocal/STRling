# Architectural Invariants

## Status and scope

This is a ratified architecture decision. It assigns conceptual responsibility
and dependency direction without prescribing contract fields, process
boundaries, module layout, deployment, or implementation language.

The [`product architecture`](product.md) defines STRling's identity and authoring
hierarchy. The [`authority hierarchy`](authority.md) keeps the normative
specification above every implementation. Current duplicated semantic paths are
transitional, not examples of the desired architecture.

## Permanent conceptual architecture

```text
AUTHORING SURFACES
    Semantic STRling DSL
    Simply APIs
    Regex frontend / importer
            |
            v
    Canonical semantic representation
            |
            v
    Semantic analysis
    Portability planning
            |
            v
    Target lowering
            |
            v
    Target-specific emitters
            |
            v
    Versioned target artifacts

HOST-LANGUAGE ADAPTERS
    expose the same compiler capability
    without reimplementing semantics

TOOLING
    CLI / LSP / editor integrations
    consume the same canonical compiler
```

Every semantic path converges before analysis and target planning. Dependencies
flow toward stable versioned contracts. Later fitness gates must detect
prohibited reverse dependencies and new semantic implementation islands without
falsely rejecting recorded transitional code.

## Authoring responsibilities

### Semantic STRling DSL

Semantic STRling is the flagship textual frontend for semantic pattern intent.
Its `strling.semantic@1.0.0` source dialect, formatting, diagnostics, and
deterministic mapping to canonical Semantic IR are ratified. A later parser will
implement that contract; it cannot define or extend the language by accepting
additional input.

Semantic STRling does not mean “whatever the current `.strl` parser accepts,”
and its ratified keyword-and-block syntax is deliberately distinct from target
regex spelling and the regex-compatible import frontend.

### Simply APIs

Simply is a first-class semantic frontend. Each host ecosystem may expose an
idiomatic public API, but equivalent operations lower to the same canonical
semantic representation and meaning.

Simply must not define independent behavior, use direct target-regex emission as
its semantic implementation, contain a shadow compiler, or assume that PCRE2
output executes in every host runtime. Current public Simply APIs remain
compatibility obligations until a separately authorized migration changes them.

### Regex frontend and importer

The existing regex-shaped grammar is the low-level **regex frontend** and a
regex-compatible **source dialect**. It remains valuable for compatibility,
migration, and import. Accepted behavior remains compatibility evidence until a
versioned specification decision retains, revises, or rejects it.

This frontend is not the final Semantic STRling DSL and does not define the
product's semantic ceiling. Target-like input must still enter the canonical
semantic path. Raw regex is not prohibited internally: import and target output
are necessary. The prohibition is treating raw target syntax as the semantic
public abstraction.

## Canonical compiler responsibilities

### Frontend normalization

Each authoring surface owns source-specific parsing, source validation, and
source mapping at its boundary. The canonical compiler authority owns shared
normalization so equivalent inputs have one meaning. Frontend-specific syntax
does not create parallel semantics.

### Canonical semantic representation

All authoring surfaces converge on one target-independent semantic
representation consumed by shared analysis and planning. This decision defines
no fields, serialization, ownership, or required split between a source model
and Semantic IR. Current per-binding AST and IR structures are not the final
canonical model.

### Semantic analysis

Semantic analysis owns target-independent validity, diagnostics, safety
findings, and explanations that can be established before target selection.
Results remain traceable to semantic input and specification version.

### Portability planning

The portability planner compares analyzed requirements with a selected,
versioned target profile and deliberately chooses native support, a
semantics-preserving rewrite, or an unsupported result. Degraded output exists
only under a versioned contract and explicit caller request. Silent semantic
degradation is forbidden.

### Target profiles

A target profile describes relevant semantics and capabilities of a target
engine version, runtime edition, and material options. Capabilities are
version/profile-sensitive facts, not timeless booleans. A profile is subordinate
to the semantic specification and cannot redefine STRling meaning. Exact profile
identity and schema are later contract work.

### Target lowering

Target lowering turns an analyzed semantic program and portability plan into a
target-specific emission plan. It owns deliberate target rewrites and must not
depend on a host adapter's runtime implementation.

### Emitters

An emitter deterministically serializes an already selected target plan. It may
own target escaping, syntax selection, and serialization mechanics. It must not
invent meaning, portability policy, unsupported fallbacks, or safety decisions.

### TargetArtifact

Compilation produces a versioned TargetArtifact for the selected profile. It
must ultimately be traceable to compiler version, specification version, target
profile, options, semantic result, diagnostics, and emitted material as the
future contract defines. Current schema fields are not ratified as the final
artifact contract by this decision.

## Host-language adapters

A host-language adapter answers: “From which programming ecosystem can I invoke
STRling?” Rust, TypeScript, Python, Java, and C# are host examples. A target
engine answers: “For which regex/runtime semantics should STRling compile?”
PCRE2, ECMAScript, and Python `re` are target examples.

Adapters may own idiomatic Simply and compiler-call APIs, host type conversion,
serialization, packaging, interoperability, host error conversion, and runtime
helpers that explicitly identify executable artifacts. They must not own
canonical parsing, normalization, semantic analysis, portability planning,
target lowering, or emission semantics.

The adapter count is never a target-engine count. A future canonical compiler
may be written in Rust; Rust would be the reference implementation language, not
the specification and not a target by implication.

### Stable interop boundary

Host adapters invoke the canonical compiler through independently versioned,
serialized or opaque boundaries that expose canonical contract data rather than
reference-implementation layout. The initial native and WebAssembly boundary is
[`strling.interop` 1.0](../spec/interop/1.0/README.md): compact UTF-8 JSON over
fixed C/WASM buffer primitives. `CompileRequest`, `CompileResult`, supplied
target profiles, diagnostics, and Simply protocols keep their own authority and
version identities.

The reference interop bridge is an adapter under `bindings/`; it depends on the
public kernel facade and may own narrowly reviewed raw-memory handling, panic
containment, serialization, and generated headers. It must not expose Rust
layout, link callers to internal kernel modules, select targets implicitly, or
contain parsing, semantic validation, planning, lowering, emission, or runtime
execution. The unsafe-free kernel does not absorb FFI pointer handling.

## Tooling

The CLI, LSP, editors, documentation tools, and conformance tools consume the
same canonical compiler interface. They may own transport, presentation,
caching, source projection, and editor protocol behavior. They must not maintain
shadow compilers or reinterpret canonical results. Binding-coupled tooling
remains transitional until the canonical interface and source/diagnostic
contracts exist.

## Determinism and traceability

Identical semantic input, compiler version, specification version, target
profile, and compiler options must produce deterministic semantic results,
diagnostics, plans, and artifacts. Permitted nondeterministic metadata must be
specified and isolated.

Compiler, specification, source-dialect, profile, artifact, host-package, and
implementation versions have different responsibilities. Equal version numbers
never imply compatibility.

## Explicit decisions

| Question                                                            | Decision                                                                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| What is STRling?                                                    | A portable semantic regex compiler platform.                                                            |
| What is the flagship abstraction?                                   | Semantic intent through multiple authoring surfaces.                                                    |
| Is raw regex forbidden internally?                                  | No. Import and target output are required; raw target syntax is not the semantic public abstraction.    |
| Is the current regex-shaped grammar the final Semantic STRling DSL? | No. It is the compatibility/import frontend unless ratified work reclassifies it.                       |
| Is Simply normative?                                                | No. It is a first-class frontend conforming to the specification and canonical semantic representation. |
| Is TypeScript authoritative?                                        | No. Historical behavior is compatibility evidence.                                                      |
| Is Rust authoritative?                                              | No. A future Rust core may be the subordinate reference implementation.                                 |
| Are bindings compiler implementations?                              | Not in the target architecture; current independent implementations are transitional.                   |
| Are engine capabilities timeless booleans?                          | No. Support is version/profile-sensitive.                                                               |

## Transitional architecture

These current structures remain permitted but are not the desired architecture:

-   the regex-shaped textual frontend;
-   duplicated parsers, ASTs, IRs, validators, compilers, diagnostics, planners,
    and emitters across bindings;
-   TypeScript-derived fixtures and historical outputs;
-   shallow AST/IR and artifact models predating canonical contracts;
-   target limitations and feature tables not yet expressed by versioned
    profiles; and
-   tooling coupled to binding implementations.

Their preservation, rewrite, or retirement follows the certified matrix, donor
inventory, public contracts, and transition rules. A transition is not compliant
until replacement and behavior-preservation evidence exists.

## Progressive enforcement

Fitness rules tighten monotonically as transitions are replaced. Each gate
states scope, exceptions, and retirement or activation evidence. Current rules
cover governance dependency direction, generated-input acyclicity,
implementation-derived fixture authority, task placement, specification schema
references, and new semantic islands.

Transitional rules report duplicated binding compilers, implementation-derived
fixtures, and direct LSP-to-Python coupling. The binding-to-canonical-core rule
remains future-state until the interface and adapter migrations exist.

Text search may support documentation discovery, but dependency enforcement uses
structured or language-aware analysis where reasonably available. Weakening an
enforced boundary requires a breaking architecture declaration and replacement
evidence.

## Deliberate non-decisions

Later work decides canonical source, Semantic IR, diagnostics, compiler
request/result, target profile, and TargetArtifact contracts. The versioned
native/WASM interop boundary is now selected, but this document still does not
select a general RPC service boundary, define additional backends, redesign
Simply, migrate individual host packages, or implement Semantic STRling parsing.
