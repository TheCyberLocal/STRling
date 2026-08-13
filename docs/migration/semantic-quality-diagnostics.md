# Proof-backed semantic quality diagnostics

[← Back to Architecture](../architecture.md)

P12-T04 extends the canonical diagnostic generator with target-neutral quality
diagnostics derived only from normalized Semantic IR and already-certified
foundational and structural facts. It preserves `STRL-SAFETY-0001` through
`STRL-SAFETY-0005` exactly. It does not parse raw regex text, change Semantic
IR, infer target behavior, apply a rewrite, or make a universal performance or
vulnerability claim.

## Stage boundary

Quality proof construction is an implementation-owned substage of canonical
diagnostic generation. The generator continues to receive the exact normalized
program, `SemanticFacts`, `StructuralFacts`, and `SafetyAnalysis`. It first
validates their correspondence, projects the five existing safety findings,
and independently derives only the closed quality proofs below. Safety and
quality evidence share deterministic occurrence ordering and the existing
`Diagnostic` contract, but retain distinct typed provenance.

The dependency direction remains:

```text
normalized Semantic IR
    -> foundational semantic facts
        -> structural facts
            -> safety evidence
                -> canonical diagnostic generation
                    -> safety + proof-backed quality diagnostics
```

Quality proof construction cannot call normalization, safety analysis, target
capability evaluation, portability planning, lowering, serialization, runtime
harnesses, frontends, bindings, product routes, or editor tooling.

## Closed diagnostic inventory

| Code | Severity | Proof condition |
| --- | --- | --- |
| `STRL-QUALITY-0001` | warning | A repetition has bounded maximum zero. Its operand is unreachable and the repetition always contributes the empty match. |
| `STRL-QUALITY-0002` | info | A greedy or lazy repetition has minimum and maximum exactly one. The repetition wrapper cannot change count or backtracking commitment; possessive mode is excluded. |
| `STRL-QUALITY-0003` | warning | A later alternation branch has the exact same canonical semantic shape as an earlier branch when only `NodeId` and `SourceOrigin` are ignored. Capture/reference identities and every semantic field must still agree. |
| `STRL-QUALITY-0004` | warning | One zero-consumption sequence region requires both word-boundary and not-word-boundary at the same input position. Any consuming expression resets the comparison region. |
| `STRL-QUALITY-0005` | warning | One zero-consumption sequence region contains same-direction lookarounds with exact canonical-equivalent bodies and opposite polarity. |
| `STRL-QUALITY-0006` | info | Two explicit members of one character set have a concrete shared Unicode-scalar witness: literal-in-range or range intersection. Symbolic class/property and case-fold guesses are excluded. |
| `STRL-QUALITY-0007` | info | A resolved backreference targets a capture body whose certified maximum consumption is exactly zero. The diagnostic states only that the reference cannot contribute consuming progress when the capture participates. |

Every finding retains a stable code, proof category, primary and contributing
`NodeId` values, typed proof evidence, compiler-policy severity, concise note
and help text, and honest source projection. The primary location is the
smallest available span of the repetition, later duplicate branch, later
contradictory assertion, character set, or backreference. Earlier branches,
assertions, operands, capture definitions, and capture bodies are related
locations when their provenance exists. Character-set member indices and the
concrete overlap witness remain in evidence because set members have no
independent source origin.

## False-positive policy

No diagnostic is emitted for a merely shared leading prefix, unknown leading
consumption, unsupported Unicode-property algebra, case-fold uncertainty,
wildcard exclusions, general language inclusion, general assertion
satisfiability, unused captures, forward or cross-branch references, or a
target-specific runtime behavior. A consuming expression separates assertion
positions. Possessive exact-once repetitions remain silent because commitment
can be observable. Structurally different branches remain distinct even if a
sample input makes them look equivalent.

Diagnostics are descriptive only. They contain no fix, text edit, target
syntax, atomicity recommendation, or semantics-preserving rewrite claim.
P12-T05 owns automated rewrites and must provide separate equivalence proof.

## Certification

Focused fixtures cover every code, source-backed and source-less projection,
stable typed evidence, precise related locations, preservation of all five
safety codes, and adversarial near misses. Fixed-seed generated programs prove
determinism before and after normalization, canonical ordering, input
immutability, and silence whenever proof preconditions are absent. Contract,
architecture, resource-limit, full kernel, shared-corpus, Local, Pull Request,
and Full checks close the task.
