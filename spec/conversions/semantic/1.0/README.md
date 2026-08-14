# Semantic conversion result 1.0

## Authority and identity

This directory is the normative serialized-result contract for
`strling.semantic-conversion@1.0.0`. It governs conversion evidence from
validated canonical Semantic IR to either `strling.semantic@1.0.0` text or a
direct-operation `strling.simply-builder@1.0.0` request. The Semantic IR and
destination frontend contracts remain authoritative for semantics and output
syntax.

[`conversion-result.schema.json`](conversion-result.schema.json) closes the
wire shape. The authored `examples/` and `invalid/` corpora are part of this
contract's certification evidence; examples illustrate the contract and do
not create language semantics. [`destination-domain.json`](destination-domain.json)
exhaustively maps all twelve canonical node kinds and four character-set member
kinds to each destination and records the only destination-specific limits.

## Status and proof rules

-   `exact` requires executable output, `proven` normalized semantic alpha
    equivalence, and identical source/reconstructed fingerprints. Exact output
    may record only non-semantic loss, such as omission of unavailable source
    comments.
-   `partial` requires executable output and at least one explicit loss,
    approximation, or manual decision. It can never claim proven equivalence.
-   `unsupported` has no output or mappings, uses `not_applicable` equivalence,
    and records every discovered blocking construct.

The proof method is
`normalized_semantic_alpha_equivalence@1.0.0`. It alpha-renames generated node
and capture identities and excludes source/origin evidence. It retains capture
names, semantic options, all node and set-member values, topology, and order.
Equal emitted text or equal target regex is not proof.

## Destination invariants

Semantic STRling output is UTF-8 text whose recorded digest and half-open byte
spans correspond exactly. An exact result reparses through the existing
Semantic STRling frontend and satisfies the proof rule. Invalid or missing
capture names may be replaced only in a `partial` result with both a named
substitution issue and a manual decision. Forward, self, and recursive
backreferences are unsupported for this textual destination.

Simply output is a complete 1.0.0 BuilderRequest. It contains only direct
construction operations, requests only `semantic`, and omits `target_profile`.
It never uses `import_node`, `import_program`, or `stdlib_helper`. An exact
result replays through the existing Simply frontend and satisfies the same
proof rule.

Node and capture mappings are sorted by canonical source identity. Explanation
links and target annotations are optional evidence and must correspond to the
same source-program digest. They cannot change output or conversion status.
The fixed `semantic_ir_only` comment policy means raw source is not consulted
and comments are never recovered or emitted.
