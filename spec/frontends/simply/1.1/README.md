# Simply builder protocol 1.1

## Authority and compatibility

This directory is the normative, backward-compatible minor revision of
`strling.simply-builder`. It inherits every operation, option, identity,
provenance, ownership, validation, error, and compilation rule from
[`1.0.0`](../1.0/README.md) and adds one operation:
`stdlib_helper`.

Protocol `1.0.0` remains immutable and accepted by the Rust transport. A
`1.0.0` request cannot use `stdlib_helper`; that operation is available only
when `protocol_version` is `1.1.0`. Responses echo the accepted request
protocol version.

## Standard-library operation

`stdlib_helper` records a governed helper ID and a scalar parameter map. It
materializes a canonical Semantic IR value by delegating to the sole Rust
standard-library implementation selected by
[`registry.json`](../../../stdlib/registry/1.0/registry.json). The operation does
not carry regex, generated Semantic IR, target output, runtime objects, or host
validation behavior.

Unknown helper IDs fail with `STRL-SIMPLY-0010` at
`arguments.helper_id`. Parameters not declared by the selected registry
signature fail with `STRL-SIMPLY-0001` at the exact parameter path. The
result is an ordinary immutable, single-parent Simply value and may be composed
with every inherited operation.

TypeScript and Python Preview adapters expose this protocol as serializers.
Their generated convenience wrappers record only helper identity and
parameters. All construction, normalization, analysis, planning, lowering,
and compilation remains in the canonical Rust path.

## Files and certification

-   `protocol.json` is the complete 16-operation machine registry.
-   `builder-request.schema.json` and `adapter-response.schema.json` define
    the exact 1.1 transport shapes.
-   `case.schema.json` defines the 1.1 standard-library extension evidence.
-   `fixtures/positive.json` covers all eight registry variants.
-   `fixtures/negative.json` covers unknown helper and invalid parameter
    failures.
-   `fixtures/manifest.json` binds the complete authored input set.

`python3 tooling/simply_contract.py` certifies both immutable 1.0 and additive
1.1 contracts. Rust convergence tests prove that every accepted helper
selection reaches the canonical implementation and converges with the
generated Semantic DSL form.
