# Canonical Observation Comparison and Discrepancy Taxonomy

## Purpose and authority

This comparison layer converts immutable historical observations into factual,
traceable comparison evidence. It does not modify a source observation, define
STRling semantics, or make historical agreement normative.

```text
Normative Specification
        |
        v
Canonical Semantic Contracts / Rust Kernel
        |
        v
Migration Decisions

Historical TypeScript Evidence ----\
Historical Python Evidence ---------+--> Comparison Evidence
Other future observations ----------/
```

The repository authority hierarchy in
[`governance/authority.md`](../../governance/authority.md) controls every
migration interpretation. Historical consensus is evidence of historical
consensus. Historical divergence is evidence of historical divergence. Neither
selects the correct behavior, and no count or majority of implementations can
override specification or canonical-contract authority.

## Independently versioned contracts

The machine-readable contract is
[`tooling/migration_comparison_contract.json`](../../tooling/migration_comparison_contract.json).
Its initial identities are independent of runner protocol `1.0.0`, observation
schema `1.1.0`, and both runner versions.

| Concern                   | Version | Meaning                                                                     |
| ------------------------- | ------- | --------------------------------------------------------------------------- |
| Comparison schema         | `1.0.0` | Projection-pair facts, comparability, relationship, and stable differences |
| Projection schema         | `1.0.0` | Provenance-bearing derived representation of one validated observation     |
| Normalization rules       | `1.0.0` | Exact ordered set of permitted representation-only transformations         |
| Comparator implementation | `1.0.0` | Deterministic pairing and field-difference implementation identity          |
| Discrepancy taxonomy      | `1.0.0` | Governed migration-disposition meanings and evidence requirements          |

A version change is explicit in every derived artifact. In particular, a later
taxonomy version cannot silently reinterpret an earlier classification.

## Four separate layers

1. A **raw observation** is immutable runner evidence. Its runner,
   implementation, request, surface, schema, and outcome remain independently
   fingerprinted and retrievable.
2. A **comparison projection** is derived from one validated raw observation.
   It records the source observation identity, runner and implementation
   identity, corpus and case identity, request, operation, surface, projection
   versions, normalization rule IDs, and projection fingerprint.
3. A **comparison result** states only the factual relationship between two
   projections. It does not claim which side is correct.
4. A **migration disposition** interprets comparison evidence only when a
   replacement relationship and sufficient governing authority exist.

Peer-to-peer historical comparisons have disposition applicability
`not_applicable` and a null disposition. They must not be forced into any of the
four substantive migration categories.

## Faithful comparability and pairing

Pairing uses exact stable identities rather than operation-name similarity. A
pair must share the cross-runner case identity derived by the existing
cross-runner contract from case ID, conceptual operation, input, options, and
cross-corpus version. It must also have the same request semantics and one of
the exact TypeScript/Python surface correspondences locked in the comparison
contract. A reused name, similar operation, or approximate input is not a pair.

The current contract can faithfully compare exact historical outcome shapes on
the 12 already certified shared cases. It can also represent a missing
counterpart, unsupported operation, or incompatible surface without fabricating
a counterpart. No current canonical-kernel frontend, parser AST, emitter, or
Simply observation adapter exists, so this task does not invent one.

Comparability is `comparable` or `not_comparable`. A not-comparable result has
one of these stable reasons:

-   `operation_not_exposed` or `unsupported_operation`;
-   `incompatible_surface`;
-   `missing_counterpart`;
-   `insufficient_semantic_correspondence`.

Not-comparable is a structural fact, not automatically a discrepancy.
Comparable results relate the projections as `equivalent_observation` or
`differing_observation`; other results use `not_comparable`.

## Projection and normalization lock

The sole normalization rule is `select-semantic-outcome@1.0.0`. It compares the
complete outcome object while moving the runner-owned observation envelope into
projection provenance. This can remove implementation, runner, surface, and
request identity noise from the compared value without losing those fields or
allowing two differently sourced projections to share an identity.

The rule preserves the exact status and the complete success evidence, legacy
failure, or unsupported reason. It may not hide or rewrite an unsupported or
failure outcome. Unknown, repeated, out-of-order, or version-incompatible rules
are rejected. A zero-normalization projection is allowed for validation and
certification and retains the entire validated raw observation as its compared
value.

No rule normalizes array order, object meaning, capture numbering, diagnostics,
emitted text, flags, AST or semantic-node shape, source positions, warning or
error content, target options, or outcome status. Differing names or structures
inside historical evidence remain differences unless later proof supports a
separately versioned normalization rule.

## Stable field differences

Differing observations carry deterministic JSON-Pointer paths. Each record has
left and right presence/value evidence and one of `value_mismatch`,
`type_mismatch`, `left_missing`, or `right_missing`. Object keys are traversed
in canonical order and arrays in source order. Multiple differences are never
collapsed into prose.

Success/success, success/failure, and failure/failure are comparable when the
pairing contract holds. Any comparison involving `unsupported` is
not-comparable; unsupported remains distinct from historical failure.

## Governed disposition taxonomy

The taxonomy has exactly four substantive identities:

-   `preserved_behavior`: demonstrated replacement behavior retains the
    explicitly scoped historical semantics. Historical peer agreement is not
    replacement evidence.
-   `intentional_specification_correction`: a meaningful difference is accepted
    because an identified normative specification, canonical contract, or
    ratified architecture rule requires or justifies the correction. A runner
    merely looking wrong is insufficient.
-   `unsupported_legacy_behavior`: observed historical behavior is intentionally
    outside an identified supported-scope contract, retired extension, or
    authoritative replacement boundary. Incomplete implementation is
    insufficient.
-   `unresolved_discrepancy`: a meaningful difference lacks the correspondence,
    replacement evidence, semantic clarity, or authority needed for another
    disposition. Uncertainty defaults here.

Every substantive classification carries comparison identity, affected
operation and surfaces, exact difference paths, authority kind and reference,
evidence identities, explanation, limitations, and unresolved questions.
Preservation additionally names its scope; correction names the corrected rule;
unsupported behavior names the governing scope boundary. Classification never
mutates comparison evidence, and supersession uses explicit prior
classification identities.

## Explicit exclusions

This work does not execute or gate the complete migration corpus, change a
historical runner contract, reinterpret existing observations, add a canonical
frontend comparison surface, decide unresolved historical differences, or
change TypeScript, Python, Rust-kernel, Semantic IR, diagnostic, safety,
portability, target, package, version, or publication behavior.

No existing STRling runtime/compiler behavior intentionally changed.
