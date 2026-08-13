# Native Rust Simply API

## Status and authority

This document locks the P13-T02 implementation boundary. The native Rust
Simply API is an idiomatic construction frontend for
[`strling.simply-builder@1.0.0`](../../spec/frontends/simply/1.0/README.md).
The protocol and canonical compiler contracts remain authoritative. Rust types
and method names are public host ergonomics, not a new semantic specification.

P13-T02 does not alter TypeScript, Python, another binding, a package, the CLI,
the LSP, target behavior, or runtime execution.

## Public construction surface

`SimplyBuilder` owns one versioned construction graph. It accepts an explicit
identity namespace and semantic options, then exposes one method for each of
the protocol's 15 operations: empty, literal, wildcard, character set,
sequence, alternation, transparent group, capture, backreference, position,
lookaround, atomic, repeat, imported node, and imported program.

Operations return opaque immutable value handles. A caller may clone a handle,
but the builder permits one materializing parent only. Every method validates
all arguments before changing builder state, so duplicate steps, invalid keys
or bounds, unresolved or reused values, conflicting imports, and duplicate
capture names fail without partial mutation.

The public surface also provides protocol-shaped semantic options,
character-set members, compile projection, stable failure code/path records,
and owned error collections. It reuses canonical enums and contract types when
they already express the exact protocol value instead of defining parallel
copies.

## Direct canonical representation

The builder stores canonical `Node` candidates directly. Generated identities
are exactly `node:simply/<namespace>/<step>` and
`capture:simply/<namespace>/<capture-key>`. Generated nodes are source-less.
A transparent group keeps the child's identity and adds the deterministic group
identity only to non-semantic derivation provenance.

Imported nodes and programs are already-canonical contract values. Their
identities, origins, and source documents are retained, sources are
deduplicated and ordered by `source_id`, and incompatible contract,
specification, case-matching, identity, name, or source states fail before
mutation.

Finishing consumes the builder. It verifies root ownership, graph completeness,
capture references, imports, and resource limits, then calls the existing
`canonical-v1` normalizer. Conversion to `CompileRequest` adds only requested
outputs, compiler options, and an optional exact target-profile reference and
uses the canonical request validator.

## Compiler delegation and exclusions

The API does not expose another compiler function. Callers pass the generated
`CompileRequest` to the existing crate-root `compile` facade and supply exact
profile evidence there. Compile-through tests compare Simply and direct
semantic requests through that one path for semantic output, diagnostics,
analysis, portability, and target artifacts.

Mechanical architecture checks will reject parser or raw-regex authority,
target syntax/options in builder meaning, emitter/lowering/runtime calls,
filesystem/network/process/environment/clock access, binding/product imports,
direct analysis/planning orchestration, or a shadow semantic node model.

## Certification plan

Authored tests will reproduce all nine positive protocol cases and all 12
stable failure identities, including both import modes. Additional ownership,
cloning, malformed, serialization, fixed-seed determinism, no-panic, and input
immutability tests will exercise host-specific edge cases. Compile-through
tests will prove equal canonical results for representative target-neutral,
native, certified-rewrite, unsupported, and artifact requests.

The enforced `strling-kernel` source snapshot will intentionally add the Simply
module, root re-exports, public types, and method signatures. Rust format,
warning-denied Clippy, all targets, protocol/canonical contracts, public and
generated contracts, architecture mutations, documentation, governance,
migration differential, Local, Pull Request, and clean-tree checks close the
task.
