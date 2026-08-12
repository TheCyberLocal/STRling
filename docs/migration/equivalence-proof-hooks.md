# Evidence-bearing rewrite equivalence and portability explanations

P09-T05 closes the existing portability-planning layer by making its one
semantics-preserving rewrite claim reproducibly certified and explainable. It
does not add another rewrite, apply a transformation, lower Semantic IR, emit
target syntax, probe a runtime, migrate a binding, or publish a package.

## Existing boundary

The canonical planner already distinguishes native, equivalent rewrite,
unsupported, and unresolved evidence. Its only registered strategy is
`rewrite.atomic_literal.elide.v1`: an atomic node whose direct body is a
certified literal may omit atomicity because a literal has no internal choice
point for atomicity to prune. The planner already requires exact program,
analysis, capability-evaluation, and target-profile correspondence.

P09-T05 replaces the prior Rust-constant authority with authored evidence. A
selected plan now contains its registry version, strategy fingerprint, and
conformance-evidence fingerprint, so missing or stale proof authority is a hard
certification failure. Public portability output keeps its stable status and
reason codes and gains canonical structured explanations tied to source and
proof evidence.

## P09-T05 contract

The implementation adds one versioned, schema-validated registry under
`spec/portability/equivalence/1.0`. Each strategy definition owns its stable
identity, applicable Semantic IR shape, preconditions, semantic invariants,
unsupported conditions, explanation, proof method, required property and
conformance evidence, and later-executable runtime hook. The registry remains
target-neutral; exact target-profile evidence only determines whether the
original or any generated requirement is available.

A selected `SemanticRewritePlan` must carry the exact registry version,
canonical strategy fingerprint, and conformance-evidence fingerprint. Planning
and self-validation fail if authored evidence is missing, malformed, stale, or
does not identify the selected strategy. Existing satisfied structural proof,
replacement support, target-profile correspondence, dependency, and canonical
ordering requirements remain mandatory.

The only admitted strategy, `rewrite.atomic_literal.elide.v1`, has canonical
strategy fingerprint
`52d1a15ffb3becdde9e33f708539395e395eff752741283d90ff8bb1ccb64cc5`.
Its `conformance.atomic_literal_elision.v1` evidence fingerprint is
`5fe61a36f43a50b7ce5f6e2b13f0ac36ded8bda0e6255a66027bcf669a1d3532`.
The evidence suite contains four semantic cases and six profile expectations;
unknown profile evidence stays unresolved and cannot be concealed by a
rewrite.

Target-aware portability explanations are generated only after factual
capability evaluation and planning. They use canonical diagnostics to explain
native availability, the certified equivalent rewrite, explicit unsupported
evidence, or unresolved knowledge. Where Semantic IR has provenance, the
diagnostic identifies the affected node's primary source span and related
rewrite-node evidence. Advice carries stable capability, constraint, profile,
strategy, registry, proof, and evidence identities. No target-neutral safety
diagnostic depends on a profile or planner.

The compiler contract fixture
`compile-request/equivalence-explanation.json` records the public projection for
an atomic literal targeting ECMAScript 2024. Its exact result includes both
affected Semantic IR node IDs, the primary and related source spans, stable
`STRL-PORTABILITY-0102` code, registry `1.0.0`, and both certification
fingerprints. Architecture fitness checks enforce that the explanation stage is
evidence-only.

## Explicit exclusions

-   No possessive, lookbehind, capture, flag, optimizer, or safety rewrite is
    added.
-   No rewrite is applied and no target artifact becomes available.
-   No emitted fragment, engine spelling, runtime observation, filesystem
    state, clock, randomness, frontend, binding, or editor dependency enters
    equivalence certification.
-   Canonical compile, portability, diagnostic, and target-profile schemas keep
    their current shapes; the registry has its own versioned schema.
-   Publication and release actions remain prohibited.
