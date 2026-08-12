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

The remaining gap is authority. The current registry is a Rust constant and a
selected plan contains structural proof objects but no authored registry
version or evidence fingerprint. That makes proof staleness invisible. Public
portability output supplies stable status and reason codes, but no structured
human-readable explanation tied to source evidence.

## P09-T05 contract

The task will add one versioned, schema-validated registry under
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

Target-aware portability explanations are generated only after factual
capability evaluation and planning. They use canonical diagnostics to explain
native availability, the certified equivalent rewrite, explicit unsupported
evidence, or unresolved knowledge. Where Semantic IR has provenance, the
diagnostic identifies the affected node's primary source span and related
rewrite-node evidence. Advice carries stable capability, constraint, profile,
strategy, registry, proof, and evidence identities. No target-neutral safety
diagnostic depends on a profile or planner.

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
