# Canonical compiler contracts

## Status and authority

This directory owns the canonical, machine-readable contracts between STRling
frontends, the future compiler kernel, target backends, adapters, tooling, and
conformance systems. The contracts are normative for their declared serialized
shape and cross-contract invariants. They do not ratify language semantics or
make the unratified Semantic Specification 1.0 draft normative.

The first contract suite has schema version `1.0.0`. Its schemas live under
[`1.0/`](1.0/) and are certified together by
[`CERTIFICATION.md`](CERTIFICATION.md). Semantic specification versions,
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

The suite defines these machine-readable families without selecting an RPC, FFI,
WASM, network, or in-process transport:

| Family                                     | Canonical schema                                                                                                                               |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Source identity, provenance, and spans     | [`source.schema.json`](1.0/source.schema.json)                                                                                                 |
| Target-neutral Semantic IR                 | [`semantic-ir.schema.json`](1.0/semantic-ir.schema.json)                                                                                       |
| Derived target-neutral analysis            | [`analysis.schema.json`](1.0/analysis.schema.json)                                                                                             |
| Structured diagnostics                     | [`diagnostic.schema.json`](1.0/diagnostic.schema.json)                                                                                         |
| Compile request/result                     | [`compile-request.schema.json`](1.0/compile-request.schema.json), [`compile-result.schema.json`](1.0/compile-result.schema.json)               |
| Portability decisions                      | [`portability.schema.json`](1.0/portability.schema.json)                                                                                       |
| Version-aware target profiles              | [`target-profile.schema.json`](1.0/target-profile.schema.json)                                                                                 |
| Deterministic target artifacts             | [`target-artifact.schema.json`](1.0/target-artifact.schema.json)                                                                               |
| Specification-authored cases and authority | [`conformance-case.schema.json`](1.0/conformance-case.schema.json), [`conformance-manifest.schema.json`](1.0/conformance-manifest.schema.json) |

Run `python3 tooling/contract_validation.py` for schema, authored example,
profile, conformance, deterministic serialization, cross-reference, and
controlled-negative validation. This command is a mandatory `check` and
`certify` integrity hardgate.

The same canonical command validates the separately versioned
[`standard-library helper claim contracts`](../stdlib/contracts/README.md),
their evidence correspondence, explicit transition inventory, and controlled
overclaim fixtures. Those claims remain outside compiler protocol and do not
alter any compiler-contract family above.

Legacy schemas under [`../schema/`](../schema/) retain only their existing
compatibility scopes. They are not aliases for these canonical contracts.
