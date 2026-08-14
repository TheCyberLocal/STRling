# STRling CLI transport contract 1.0

## Status and authority

This directory defines the normative machine-readable transport envelope for
the STRling command-line interface, version `1.0.0`. Its authority is limited
to CLI response shape, command identity, and transport status. It does not
define Semantic STRling or regex-compatible syntax, Semantic IR, diagnostics,
portability, target behavior, explanation meaning, conversion meaning, or
Simply construction behavior.

The referenced versioned contracts remain authoritative for every embedded
value. A CLI implementation must return those values without reinterpretation.
Human-readable rendering is non-normative.

## Response families

`compile`, `import`, and JSON `check` return the canonical `CompileResult` 1.0
object directly. The existing `simply` compatibility command returns its
versioned Simply adapter response directly. Those objects are not wrapped or
reversioned by this contract.

[`cli-response.schema.json`](cli-response.schema.json) defines the remaining
closed response families:

-   completed or compile-failed semantic explanation, with optional bounded
    no-match evidence on a completed explanation;
-   completed or compile-failed semantic migration, where exact, partial, and
    unsupported remain properties of the embedded canonical conversion result;
-   target-profile listing as immutable profile references; and
-   target-profile inspection as one exact authored profile plus its computed
    immutable reference.

Every envelope carries `cli_contract_version = 1.0.0`, a closed command
identity, and a transport status where applicable. A compile-failed envelope
contains the exact request and failed result but no fabricated explanation or
conversion. Explicit null placeholders are forbidden.

## Determinism and privacy

JSON output is canonical field-order serialization of the typed Rust response,
encoded as UTF-8 and followed by one newline. Arrays retain the canonical order
of their owning contracts. Target lists use immutable profile-reference order.
Unknown fields are rejected.

No-match responses may contain the canonical subject digest, byte/scalar
counts, bounded findings, and reached-limit evidence. They never contain the
raw subject. CLI envelopes do not add source text, emitted target text,
diagnostic prose, or human explanation outside their referenced canonical
objects.

## Process contract

The command tree, input selection, human/JSON stream policy, exit taxonomy,
output-file safety, compatibility dispositions, and verification obligations
are frozen by the P16-T01 migration record and the non-normative certification
manifest under `tests/cli/1.0`. Those operational fixtures test this contract;
they do not outrank it.

Breaking an existing response alternative, required field, command identity,
or referenced contract requires a new CLI contract version. An additive
command or optional evidence field requires public-contract review and must
remain unambiguous under the existing alternatives.
