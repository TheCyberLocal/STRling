# Canonical compiler contracts

## Status and authority

This directory owns the canonical, machine-readable contracts between STRling
frontends, the future compiler kernel, target backends, adapters, tooling, and
conformance systems. The contracts are normative for their declared serialized
shape and cross-contract invariants. They do not ratify language semantics or
make the unratified Semantic Specification 1.0 draft normative.

The first contract suite has schema version `1.0.0`. Its schemas live under
[`1.0/`](1.0/) as they are established. Semantic specification versions,
compiler releases, source-dialect versions, target-profile versions, and this
schema version are independent identities.

Read [`INVARIANTS.md`](INVARIANTS.md) before changing or implementing any
contract in this directory.

## Canonical flow

```text
SourceDocument or constructed semantic input
        |
frontend-specific parser or builder representation
        |
semantic lowering
        v
Semantic IR
        |
diagnostics and derived analysis keyed by stable node identity
        |
versioned target profile and portability plan
        v
TargetArtifact
```

There is deliberately no universal syntax AST contract. Textual frontends may
retain different parse representations, and Simply may construct semantic
structures directly. Every frontend converges on Semantic IR before shared
analysis, planning, lowering, or emission.

## Contract families

The suite defines these families without selecting an RPC, FFI, WASM, network,
or in-process transport:

-   source identity, provenance, and spans;
-   target-neutral Semantic IR and derived-analysis attachment;
-   structured diagnostics;
-   compile request and result;
-   version-aware target profiles and portability decisions;
-   deterministic target artifacts; and
-   specification-authored conformance cases.

Legacy schemas under [`../schema/`](../schema/) retain only their existing
compatibility scopes. They are not aliases for these canonical contracts.
