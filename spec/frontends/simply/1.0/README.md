# Simply builder protocol 1.0

## Authority and destination

This directory defines the specification-owned interchange contract for
STRling Simply builders. It owns construction behavior only. Canonical semantic
meaning remains in [`semantic-ir.schema.json`](../../../contracts/1.0/semantic-ir.schema.json),
normalization remains in the Rust kernel, and compilation remains in
[`compile-request.schema.json`](../../../contracts/1.0/compile-request.schema.json).

```text
idiomatic host builder
        |
builder-request.schema.json
        |
deterministic construction projection
        v
source-less or import-composed Semantic IR
        |
canonical-v1 Rust normalization
        v
CompileRequest
```

The protocol cannot carry raw regex, emitted target syntax, engine option
names, runtime objects, callbacks, or an implicit target. An explicit target
profile is compiler routing data and is permitted only in the `compile`
projection alongside requested portability or artifact output.

## Files

-   [`protocol.json`](protocol.json) is the machine-authoritative closed
    operation, option, identity, provenance, ownership, validation, error, and
    historical-compatibility registry.
-   [`protocol.schema.json`](protocol.schema.json) validates that registry.
-   [`builder-request.schema.json`](builder-request.schema.json) defines the
    host-neutral operation graph and exact compiler projection.
-   [`case.schema.json`](case.schema.json) defines positive equivalence and
    controlled-negative evidence.
-   [`fixtures/positive.json`](fixtures/positive.json) covers all 15 operations,
    semantic options, identities, imports, provenance, and target-profile routing.
-   [`fixtures/negative.json`](fixtures/negative.json) covers every stable
    `STRL-SIMPLY` failure code.
-   [`fixtures/manifest.json`](fixtures/manifest.json) binds the complete authored
    input set and case counts.

Run `python3 tooling/simply_contract.py` for schema, registry, projection,
coverage, negative, and fingerprint certification. The same suite is part of
`python3 tooling/contract_validation.py`.

Run
`cargo test --manifest-path core/Cargo.toml --test simply_builder_contract --locked`
to prove every expected Semantic IR program is canonical under the existing
Rust normalizer and every expected `CompileRequest` validates in the kernel.

## Identity, ownership, and provenance

Generated node IDs are
`node:simply/<identity_namespace>/<step_id>`. Generated capture IDs are
`capture:simply/<identity_namespace>/<capture_key>`. They are stable request
identities, not positions, indexes, host object addresses, target capture
numbers, or content hashes.

Builder values are immutable and have one materializing parent. Reusing an
equal subtree requires constructing another value with another identity. A
transparent `group` adds its deterministic removed identity to non-semantic
origin metadata while leaving the child identity intact.

Generated nodes have no source spans. `import_node` and `import_program`
preserve canonical identities, origins, and source documents. Imported sources
are deduplicated and ordered by `source_id`. Mixed provenance is accepted only
when versions and semantic options agree, all identities are unique, and every
span resolves against an embedded source.

## Operations and options

The closed operation inventory is `empty`, `literal`, `wildcard`,
`character_set`, `sequence`, `alternation`, `group`, `capture`,
`backreference`, `position`, `lookaround`, `atomic`, `repeat`, `import_node`,
and `import_program`. Unknown operations are unsupported rather than extension
points.

Unicode scalar values are the fixed text model. Program case matching,
built-in character-class domain, and wildcard line-terminator treatment are
explicit semantic options. Repetition mode, positions, and lookaround
direction/polarity are explicit operation arguments. JSON `null` is the only
unbounded repetition maximum; finite zero retains its canonical meaning.

## Validation and failure model

Validation order is fixed as decode, graph, projection, normalization,
semantic, then CompileRequest. A failure yields stable structured code/path
data and no partially mutated value, Semantic IR, or request. Host adapters may
translate those records into idiomatic result or exception containers but may
not replace the stable identity with formatted prose.

Historical TypeScript, Python, Rust, and other bindings remain compatibility
evidence. Their dispositions are recorded in `protocol.json`; they cannot
override this protocol or canonical contracts.
