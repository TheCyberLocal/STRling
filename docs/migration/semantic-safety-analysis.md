# Canonical semantic safety analysis

## Threat model and stage boundary

Semantic safety analysis identifies target-neutral structures that can enable
non-progress or competing match paths in regex execution models that support
backtracking. It produces risk evidence, not an engine simulation, universal
vulnerability verdict, exploitability claim, severity, diagnostic, or rewrite.

The pure kernel boundary is conceptually:

```text
analyze_safety(
    &SemanticProgram,
    &SemanticFacts,
    &StructuralFacts,
) -> Result<SafetyAnalysis, SafetyAnalysisErrors>
```

The program must already satisfy the complete `canonical-v1` Semantic IR
contract. Foundational and structural facts must be complete stores produced
for that exact program. The stage validates contract and specification
versions, the canonical program identity, reachable node coverage, structural
record shape, and every evidence reference before returning a result.

The stage borrows its inputs and returns an independent result. It does not
normalize, parse regex source, derive foundational or structural facts, mutate
Semantic IR, consult a target profile, produce diagnostics, plan portability,
rewrite expressions, lower to target syntax, emit regex, or observe filesystem,
environment, network, time, process, thread, or randomness state.

The canonical responsibility flow is:

```text
normalized Semantic IR
        |
        v
foundational semantic facts
        |
        v
structural analysis facts
        |
        v
semantic safety findings and uncertainty
```

## Result and evidence model

`SafetyAnalysis` contains two deterministically ordered collections:

-   positive `SafetyFinding` values backed by a complete structural proof; and
-   `SafetyUncertainty` values recording an applicable conclusion that could
    not be proved because certified input remained indeterminate.

A finding has a stable machine-readable code, domain category, primary
semantic `NodeId`, sorted and deduplicated contributing node identities, typed
evidence, and a structural proof status. English prose is not finding identity,
and diagnostic severity is not part of the model.

Relationship evidence identifies the owning semantic node, relationship kind,
and participating node identities. Alternation evidence additionally retains
the canonical branch indexes; repetition/follower evidence retains the
canonical sequence indexes. Nested-repetition evidence retains the complete
stable-node path from outer repetition to inner repetition. Traversal indexes,
allocation addresses, source text, and emitted syntax are never evidence
identities.

Every returned evidence reference must resolve to a reachable semantic node and
to the applicable certified structural record. Malformed evidence is a
whole-stage invariant error, never a partially exposed result.

## Stable positive finding codes and proof conditions

### `unbounded_nullable_repetition`

Produce this finding exactly when a semantic `repeat` has certified structural
extent `unbounded` and its operand progress is
`potentially_zero_consuming`. Evidence names the repetition and operand and
retains both classifications. An always-consuming or indeterminate operand
does not satisfy this proof.

This proves an unbounded repetition without guaranteed progress. It does not
prove nontermination or catastrophic backtracking in every target engine.

### `unbounded_indeterminate_progress`

Produce this finding exactly when a semantic `repeat` has certified structural
extent `unbounded` and its operand progress is `indeterminate`. Evidence names
the repetition and operand and records the foundationally conservative
classification.

This code deliberately distinguishes missing progress proof from a proved
zero-consuming path.

### `nested_repetition_overlap`

Produce this finding for an outer/inner repetition pair only when all of the
following are proved:

1.  the outer repetition admits an unbounded number of iterations;
2.  outer and inner repetition semantics permit backtracking rather than
    declaring the applicable repetition possessive;
3.  the inner repetition admits more than one count;
4.  the inner operand has certified always-consuming progress;
5.  its certified leading consumption contains a concrete consuming
    self-witness rather than only `empty` or `unknown`; and
6.  the inner repetition is reachable from the outer operand only through
    consumption-transparent capture wrappers or one selected alternation
    branch, without crossing a sequence, lookaround, or atomic barrier.

The transparent path proves that two adjacent outer iterations can compete
with one inner repetition matching the same repeated operand units. A fixed
inner count, potentially-zero-consuming or indeterminate operand, unknown-only
leading set, possessive repetition, or atomic/assertion/sequence barrier does
not satisfy the proof. Applicable unknown progress or leading evidence is
preserved as typed uncertainty.

Safety traversal still enters capture, lookaround, and atomic bodies so a
nested pair wholly inside such a wrapper is analyzed. A wrapper is only a
barrier between an outer repetition and a candidate inner repetition when its
semantics prevent the inner match from contributing to the outer consumed
partition.

### `repeated_alternation_overlap`

Produce this finding for a branch pair only when all of the following are
proved:

1.  an enclosing non-possessive repetition can execute the repeated region at
    least twice;
2.  the alternation is inside that repeated region without an intervening
    atomic or lookaround barrier;
3.  its certified branch-pair relationship is `overlapping`; and
4.  at least one branch is foundationally always consuming, so the certified
    overlap cannot have been established solely from two `empty` leading
    possibilities.

Evidence preserves the repetition, alternation, both branch identities, branch
indexes, and the exact structural relationship reference. Each proved branch
pair is a separate deterministic finding. `Disjoint` produces no finding;
`Unknown` and nullable-only overlap produce typed uncertainty.

### `repetition_follower_overlap`

Produce this finding only when all of the following are proved:

1.  a certified repetition/follower relationship exists on a sequence;
2.  the repetition admits at least two possible counts and is not possessive;
3.  the repeated operand is certified always consuming, preventing an
    `empty`/`empty` relationship from masquerading as input competition; and
4.  the certified relationship is `overlapping`.

Evidence preserves the sequence, repetition, operand, immediate follower,
sequence indexes, extent, count bounds, and the exact structural relationship
reference. A fixed-count, zero-count, or possessive repetition does not meet
the competition precondition. `Disjoint` produces no finding and `Unknown`
produces typed uncertainty. A nullable follower may still qualify when the
certified overlap proves a consuming relationship with the always-consuming
operand.

## Uncertainty rules

Unknown is neither safe nor unsafe and never coerces to overlapping or
disjoint. Typed uncertainty is recorded only for an otherwise applicable
safety question, including:

-   foundationally indeterminate nested or follower progress;
-   unknown-only nested leading consumption, including backreferences;
-   saturated leading sets;
-   unknown branch or follower relationships caused by case folding,
    Unicode/property algebra, wildcard exclusions, unknown leading
    consumption, or overlap comparison exhaustion; and
-   a branch relationship whose positive overlap might be empty-only because
    neither branch proves mandatory consumption.

The stage does not emit a user-facing warning for uncertainty. Later policy may
decide whether and how to present it, together with target information.

## Determinism and complexity bounds

Safety analysis reuses the certified structural depth and relationship limits.
It performs one deterministic semantic traversal, reads already-materialized
structural relationships, and never constructs an independent branch-pair or
character-set cross product.

The implementation will additionally bound visited semantic nodes, positive
findings, uncertainty records, and evidence-path length. Exceeding a node,
finding, or uncertainty budget is a structured whole-stage error because
silently truncating positive evidence would be unsound. Evidence-path depth is
bounded by the shared semantic/structural nesting limit. All output collections
use canonical identity/value ordering; input order is retained only where it is
itself certified evidence such as branch and sequence indexes.

## What this analyzer does not prove

A positive finding proves only the documented semantic structure. It does not
by itself prove:

-   universal regex vulnerability or denial-of-service exploitability;
-   catastrophic, exponential, polynomial, or any other runtime complexity;
-   behavior of PCRE2, ECMAScript, Python, or another target engine;
-   attacker control, rejecting suffixes, input size, resource exhaustion, or
    operational impact;
-   a user-facing severity, warning message, remediation, or safe rewrite; or
-   portability, target support, lowering, or emitted-pattern behavior.

The historical emitter checks remain non-normative compatibility evidence.
They may inform a comparison corpus, but their broad `REDOS_RISK` warning and
source/legacy-IR shape tests cannot define canonical semantic findings.
