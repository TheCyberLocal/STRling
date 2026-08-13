# Formal Specification Links

[← Back to Developer Hub](index.md)

## Authority state

The specification identity is **STRling Semantic Specification**. No semantic
specification version is ratified yet. The
[`1.0-draft.1 scope`](../spec/drafts/1.0/README.md) is unratified and
non-normative.

Use the [`Specification Hub`](../spec/README.md) for current classifications and
[`Specification Versioning`](../spec/VERSIONING.md) for compatibility and
ratification rules.

## Current material

-   [`Canonical compiler contracts`](../spec/contracts/README.md) — normative
    serialized shapes and cross-contract invariants for source, Semantic IR,
    diagnostics, compiler protocol, profiles, artifacts, and conformance.
-   [`Contract certification`](../spec/contracts/CERTIFICATION.md) —
    cross-family identity, ordering, versioning, and boundary certification.
-   [`Specification-authored conformance`](../spec/conformance/README.md) —
    draft seed cases and content-addressed authority manifest.
-   [`Semantic STRling frontend 1.0`](../spec/frontends/semantic/1.0/) —
    flagship textual syntax, deterministic Semantic IR mapping, formatting,
    diagnostics, and specification-authored fixtures.
-   [`Target profiles`](../spec/targets/profiles/) — version-aware,
    enumerated-scope engine capability facts.
-   [`Regex-compatible frontend 1.0`](../spec/frontends/legacy-regex/1.0/) —
    normative compatibility/import syntax, limits, frontend diagnostics, and
    specification-authored positive/negative fixtures.
-   [`Simply builder protocol 1.0`](../spec/frontends/simply/1.0/) — normative
    host-neutral construction operations, identities, provenance, validation,
    structured failures, historical dispositions, and exact Semantic
    IR/`CompileRequest` equivalence fixtures.
-   [`Regex frontend grammar`](../spec/grammar/dsl.ebnf) — transitional
    historical compatibility evidence superseded by the versioned frontend.
-   [`Regex frontend semantics`](../spec/grammar/semantics.md) — transitional
    historical behavior/target evidence, not current frontend authority.
-   [`Base TargetArtifact schema`](../spec/schema/base.schema.json) — versioned
    current contract for its declared scope, not the final canonical artifact.
-   [`PCRE2 v1 schema`](../spec/schema/pcre2.v1.schema.json) — versioned current
    PCRE2 contract.
-   [`Conformance fixture schema`](../spec/schema/conformance-fixture.schema.json)
    — fixture shape contract; generated values remain non-normative evidence.
-   [`Feature registry`](../spec/features.json) — transitional implementation and
    capability inventory.
-   [`Standard-library material`](../spec/stdlib/) — preserved capability input
    pending semantic ratification.

## Authority reminder

A ratified versioned specification, expressly normative contract, or delegated
specification-authored conformance set may define behavior. The reference
implementation, TypeScript-generated fixtures, binding agreement, and
documentation cannot silently extend those sources.

Grammar and semantics within a ratified version must evolve according to that
version's rules. The current unversioned regex-frontend documents are not
retroactively a ratified `v3` or `1.0` specification.
