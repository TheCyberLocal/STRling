# Canonical standard-library semantics

## Scope and starting contract

P14-T03 begins from clean commit
`9a70a2bc1aa6ad95168585c8871b547e5d7531d5` and canonical registry version
`1.0.0`, fingerprint
`sha256:07065e1cb66d3277e4f482df0d9cf91c94be0417e05f1b157f15658ae504a382`.
The governed denominator is five helpers, eight construction variants, forty
audited edge cases, five target profiles, and five `lexical_shape` guarantees.
There are no registry entries with `semantic` guarantee level, so this task
must add zero semantic validators and zero semantic-validation diagnostic
codes.

The task owns canonical Rust Semantic IR/builder implementations, authored
form-equivalence contracts, exhaustive boundary evidence, and target
portability. P14-T04 retains broad public helper exposure across Simply,
Semantic DSL documentation, bindings, adapters, and generated reference
surfaces.

## Compatibility constraint

Four helpers deliberately emit a target-engine digit class. ECMAScript treats
that shorthand as ASCII, PCRE2 with the certified UCP profiles and Python
string patterns treat it as Unicode, and Python bytes patterns treat it as
ASCII. Replacing the class with either the existing `ascii` or `unicode`
Semantic IR domain would change at least one supported target.

P14-T03 therefore adds one explicit `target_native` built-in character domain.
It is a target-neutral declaration of an audited compatibility policy, not raw
target syntax and not a semantic-validity claim. Capability evaluation,
lowering, and serialization remain in their existing stages. Existing
`ascii` and `unicode` meanings do not change.

## Planned implementation

The canonical registry will resolve each of the eight variants to an authored
Semantic IR program, canonical Semantic STRling source, and a crate-private
Rust builder identity. The Rust module will construct those programs through
the existing `SimplyBuilder`, normalize through the existing canonical path,
and expose no binding or package surface in this task.

Tests will prove deterministic construction, selector fallbacks, Semantic
IR/Simply/DSL alpha-equivalence, complete positive and negative boundaries,
known semantic false positives, known standards false negatives, empty and
malformed values, oversized inputs, Unicode behavior, cross-engine artifact
execution, and exact non-strengthening of all five lexical contracts.
