# Canonical Simply builder protocol

## Status and boundary

This document records the specification-owned design boundary for the Simply
builder protocol. It is a frontend construction contract into canonical
Semantic IR and `CompileRequest`, not a new syntax tree, compiler, target
emitter, runtime API, or host-language implementation.

Canonical contracts and the Rust kernel remain authoritative. Historical
TypeScript, Python, Rust, and other binding implementations are compatibility
evidence only. No host-specific constructor, callable-object trick, exception
message, target convenience, or emitted pattern becomes semantic precedent.

## Locked operation inventory

The version 1.0 request will admit exactly these construction operations:

| Operation        | Canonical destination                                                        |
| ---------------- | ---------------------------------------------------------------------------- |
| `empty`          | `Node::Empty`                                                                |
| `literal`        | nonempty `Node::Literal`; empty text becomes `Node::Empty`                   |
| `wildcard`       | `Node::Wildcard` with explicit effective line-terminator treatment           |
| `character_set`  | `Node::CharacterSet` with canonical literal/range/builtin/property members   |
| `sequence`       | ordered `Node::Sequence`, normalized by canonical-v1                         |
| `alternation`    | ordered `Node::Alternation`, normalized by canonical-v1                      |
| `group`          | transparent one-child sequence candidate removed by canonical normalization  |
| `capture`        | `Node::Capture` with a logical capture identity and optional unique name     |
| `backreference`  | `Node::Backreference` resolved by logical capture identity                   |
| `position`       | one explicit canonical anchor or boundary position                           |
| `lookaround`     | `Node::Lookaround` with explicit direction and polarity                      |
| `atomic`         | `Node::Atomic`                                                               |
| `repeat`         | `Node::Repeat` with nonnegative bounds and greedy/lazy/possessive mode       |
| `import_node`    | a prebuilt canonical node plus any required declared source documents        |
| `import_program` | a prebuilt canonical Semantic IR program whose root and sources are composed |

Operation values are immutable. A value may be materialized once into the
result tree; callers that need two equal subtrees construct two values with two
identities. This avoids object aliasing and duplicate Semantic IR identities
while remaining idiomatic in each host adapter.

## Identity and provenance

Every request supplies one stable namespace and every operation supplies one
stable step key. Materializing builder operations derive node identities as
`node:simply/<namespace>/<step-key>`. Capture declarations derive logical
identities as `capture:simply/<namespace>/<capture-key>`; backreferences use the
capture key, never a host object, source position, or target capture number.

Generated builder nodes have no source span. Imported canonical nodes and
programs preserve their identities and origins. Their sources are merged by
`source_id` in deterministic order and must match the request's contract and
specification versions. A mixed-provenance program is valid only when every
span resolves to an embedded source, imported identities remain unique, and
semantic options agree. Identity and origin metadata remain excluded from
semantic equality.

## Semantic options and compiler routing

Builder semantic options are target-neutral intent:

-   Unicode scalar values are the fixed text model;
-   `case_matching` is program-level semantic intent;
-   built-in character classes select an ASCII or Unicode domain;
-   wildcards select whether line terminators are included; and
-   repetition mode and every position/lookaround property are explicit on the
    operation that owns them.

Requested outputs, a target-profile reference, diagnostic policy, partial
semantics, and resource limits belong to the generated `CompileRequest`. They
do not alter builder meaning. Raw regex, emitted target fragments, engine flag
letters, runtime objects, host callbacks, target option names, and implicit
engine selection are not protocol values.

## Validation and errors

Validation is deterministic and non-mutating:

1. decode the versioned request and reject unknown fields;
2. validate step order, references, single materialization, identities, and
   arguments;
3. project a source-less or import-composed Semantic IR candidate;
4. run the existing canonical Rust normalizer;
5. validate canonical semantic identities, captures, references, and origins;
6. construct and validate the exact `CompileRequest`.

Failures retain stable builder error identities for invalid arguments or
bounds, duplicate identities or capture names, unresolved values or captures,
reused values, incompatible imports, invalid provenance, unsupported
constructs, and resource limits. Host adapters may translate those structured
failures into idiomatic result or exception types but may not replace their
identity with prose. A failure produces no partially mutated builder value,
Semantic IR program, or compile request.

## Historical compatibility dispositions

The protocol will record the existing migration taxonomy for historical Simply
evidence:

-   literal escaping and empty-literal intent are preserved semantically;
-   immutable composition and readable host helpers remain adapter ergonomics;
-   `max=0` as an unbounded sentinel is intentionally corrected to explicit JSON
    `null`, because canonical zero is a real finite maximum;
-   host guards against repeating named captures and Python duplication of
    numbered captures are unsupported host quirks rather than semantics;
-   direct `toString`, `compileNode`, `toRegExp`, `exec`, and PCRE2 convenience
    routes remain separately governed compatibility obligations and must route
    through `CompileRequest` plus a target profile when later adapters migrate;
    and
-   formatted `STRlingError` prose is presentation, not failure identity.

## Certification plan

The protocol registry, three schemas, positive and negative fixture documents,
and checked manifest will be certified together. Positive cases will cover all
operations, option modes, imports, source-less and mixed provenance, captures,
Unicode, and compiler routing. Negative cases will cover invalid bounds,
duplicate names and identities, unresolved references, value reuse,
incompatible imports, invalid mixed provenance, unsupported constructs, target
leakage, and missing required target profiles.

A certification-only projector will reproduce each authored Semantic IR
candidate. A Rust integration test will feed those candidates to the existing
canonical normalizer and compare the exact expected normalized program and
validated `CompileRequest`. Architecture mutations will prove the contract and
validator cannot acquire binding, target, runtime, product, raw-regex,
subprocess, or second-compiler authority.

## Implemented contract evidence

Protocol `1.0.0` now provides the closed machine registry, three schemas, nine
positive equivalence cases, 13 controlled-negative cases, and a seven-input
content-addressed manifest. Its certification fingerprint is
`sha256:245bd1aa0745db78258f5c5f27e023d4bd07ffbc3814bfd751e577192a034740`.

The specification projector validates the construction graph and deterministically
produces each authored Semantic IR program and `CompileRequest`. The Rust
contract proof binds all seven JSON artifacts, proves every positive program is
already canonical under `canonical-v1`, validates each exact request, and
confirms complete stable-error coverage. Controlled mutations reject operation
inventory drift, stale manifest bytes, raw/target field widening, missing
historical evidence, changed failure identities, runtime/process dependencies,
and expanded frontend authority. The canonical kernel fixture hardgate now
accounts for 107 files, including all seven Simply artifacts.

## Completion certification

P13-T01 closes from clean review commit
`1d35c309acf2e3c6188bfae3b253d8951240b638`. All Rust targets,
warning-denied Clippy, 498 tooling tests, canonical/core/public/generated
contracts, formatters and linters, governance, security, documentation
integrity across 150 files, patch integrity, and the reviewed three-run
migration differential pass. The migration baseline remains
`sha256:c6552f544b307f7ca9bb01c52fd79ea4c046248fcd03dedf57fb501b570aa0d0`
and the canonical boundary remains
`sha256:2f58ec3fe3e9f1c4498a40b43c5a44eeb386e15973ae0cef7b4aaa47ab2998ed`.
Local passes 26/26 from a clean tree with no failures, waivers, unavailable
operations, or incomplete operations.

P13-T02 may now implement the native Rust Simply API as an idiomatic thin
construction layer over protocol `1.0.0` and the canonical kernel. It must not
create a host AST authority, second semantic model, second compiler, hidden
target syntax, or runtime execution route.
