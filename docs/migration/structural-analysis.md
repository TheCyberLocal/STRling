# Canonical structural semantic analysis

## Stage boundary

Structural analysis is the second pure, target-neutral analysis stage. Its
kernel boundary is conceptually:

```text
analyze_structure(
    &SemanticProgram,
    &SemanticFacts,
) -> Result<StructuralFacts, StructuralAnalysisErrors>
```

The input program must already satisfy the complete `canonical-v1` Semantic IR
contract. The supplied `SemanticFacts` must have been produced for that exact
program by foundational semantic analysis. Structural analysis validates the
program, its certified identity, version correspondence, reachable node set,
and per-node kind correspondence. It rejects invalid or mismatched external
state with structured errors; it never invokes normalization or foundational
analysis implicitly.

The stage borrows both inputs and returns a separate fact store keyed by stable
`NodeId`. It does not mutate Semantic IR or foundational facts. It has no
filesystem, environment, clock, randomness, network, frontend, binding,
protocol-result, diagnostic, target-profile, portability-planner, lowering, or
emitter context.

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
        +---- later safety analysis
        |
        +---- later portability analysis
```

## Fact vocabulary

Every reachable semantic node receives one structural record. The record
contains only facts required by later structural safety and portability work:

-   a symbolic leading-consumption set;
-   one semantic length classification: `fixed(n)`, `finite_variable`,
    `unbounded`, or `indeterminate`;
-   for repetition nodes, finite or unbounded extent plus operand progress as
    `always_consuming`, `potentially_zero_consuming`, or `indeterminate`;
-   for alternations, canonically ordered branch-pair leading overlap; and
-   for sequences, canonically ordered repeated-operand/following-expression
    leading overlap.

Nullability, minimum consumption, maximum consumption, and general consumption
disposition remain owned by `SemanticFacts`. Structural facts refer to those
certified results while composing leading sets and classifying length or
repetition progress. They are not copied into the new node record.

## Leading-consumption abstraction

Leading consumption describes the first semantic input that a node may consume
on a successful path. It is not regex syntax and is not an emitted character
class. A deterministic set contains one or more of these typed possibilities:

-   `empty`, meaning the successful path has no first consumed scalar;
-   an explicit Unicode scalar;
-   one canonical character predicate retaining set negation, literal members,
    scalar ranges, built-in classes, Unicode-property names, and their semantic
    domains;
-   a wildcard retaining its canonical line-terminator policy; or
-   `unknown(reason)` when the canonical information cannot identify the first
    consumer soundly.

Character predicates remain symbolic. Unicode categories are never enumerated,
and ranges are never expanded scalar by scalar. Canonical order is preserved in
the predicate and all unions are deterministically ordered.

Global insensitive case matching is semantic input, but the current canonical
contract does not supply a certified case-fold algebra to this stage. Equal
explicit scalars still prove overlap. Distinct scalar or finite-set membership
under insensitive matching is `unknown`, never guessed disjoint.

### Composition rules

| Semantic node   | Leading-consumption rule                                                                                                                                                                      |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `empty`         | `empty`                                                                                                                                                                                       |
| `literal`       | first Unicode scalar of the canonical nonempty text                                                                                                                                           |
| `wildcard`      | symbolic wildcard with its line-terminator policy                                                                                                                                             |
| `character_set` | one symbolic canonical character predicate                                                                                                                                                    |
| `sequence`      | union child leading sets through every foundationally nullable prefix; stop after a non-nullable child; continue conservatively and add an unknown reason after an unknown-nullability prefix |
| `alternation`   | deterministic union of every branch leading set, retaining unknowns and branch identity                                                                                                       |
| `repeat`        | `empty` when zero repetitions may succeed plus the body leading set when at least one repetition may consume; preserve unknown body/nullability information                                   |
| `position`      | `empty`                                                                                                                                                                                       |
| `capture`       | inherit the body leading set                                                                                                                                                                  |
| `backreference` | `empty` only when foundational bounds prove zero consumption; otherwise conservative `unknown(backreference)`                                                                                 |
| `lookaround`    | outer result is `empty`; analyze the body separately without promoting examined characters to outer consumption                                                                               |
| `atomic`        | inherit the body leading set                                                                                                                                                                  |

If a sequence prefix has unknown nullability, following children may still be
first consumers, but the result retains that uncertainty. Assertions and
lookarounds therefore allow a later sequence child to lead while never making
the assertion body's examined input an enclosing consumed input.

Leading-set growth is bounded deterministically. Crossing the term budget
retains a typed complexity-limit unknown instead of discarding uncertainty or
claiming exactness.

## Length and repetition progress

Length is measured in the same Unicode-scalar unit certified by foundational
analysis. Classification uses only certified minimum, maximum, and consumption
facts:

-   `fixed(n)` when minimum and finite maximum are both exactly `n`;
-   `finite_variable` when a finite maximum is greater than the minimum;
-   `unbounded` when unbounded consumption is proved without an indeterminate
    foundational disposition; and
-   `indeterminate` when conservative foundational information does not prove
    whether the semantic length is actually unbounded.

For each repetition, extent is structural: a bounded `max` is finite and a
semantic `null` maximum is unbounded. Operand progress is:

-   `always_consuming` only when the operand's certified minimum successful
    consumption is strictly positive;
-   `potentially_zero_consuming` when certified nullability or zero-width/
    variable consumption proves a successful zero-consuming path; and
-   `indeterminate` otherwise.

An unbounded repetition over a potentially zero-consuming operand is
representable by those two facts. It is not a vulnerability, warning,
severity, or safety verdict.

## Conservative overlap semantics

`Overlap` has exactly three outcomes:

-   `disjoint`: every represented pair is covered by an exact proof of empty
    intersection;
-   `overlapping`: at least one represented pair has a proved witness or a
    semantically universal intersection; and
-   `unknown`: neither overlap nor disjointness is proved.

`disjoint` is never a default. An unknown term, insensitive-fold comparison,
line-terminator ambiguity, unproved Unicode property relationship, unsupported
built-in-class algebra, or exhausted resource budget prevents a disjoint claim.

Exact proof cases include equal and distinct case-sensitive scalar literals,
scalar membership in positive finite literal/range predicates, intersection of
positive finite predicates, and their corresponding finite disjointness.
Wildcard `include` overlaps a proved nonempty consuming scalar/range predicate;
wildcard pairs overlap. Negated or category-bearing predicates use only locally
provable membership facts; incomplete complement or Unicode-property algebra
returns `unknown`.

Two `empty` possibilities overlap. `empty` and a proved consuming possibility
are disjoint. This retains nullable-branch structure without conflating it with
character consumption.

Alternation relationships enumerate branch pairs in source-index order. A
sequence relationship is recorded when a direct repetition item is immediately
followed by another semantic item; it compares the repeated operand's leading
set with that following expression. Pair derivation has a checked deterministic
budget. Exceeding it returns a structured complexity-limit error rather than an
incorrect partial certainty. No regex-engine backtracking is simulated.

## Applicable variant coverage

All twelve currently ratified Semantic IR variants receive a leading and length
record. Repetition-only progress and extent are present only for `repeat`.
Branch-pair relationships are present only for `alternation`, and repeat/follow
relationships are present only for applicable `sequence` nodes. Capture,
lookaround, and atomic wrapper bodies receive independent complete records.

## Explicit exclusions

This stage does not implement or decide:

-   ReDoS or any other vulnerability classification;
-   safe/unsafe labels, risk severity, or user-facing safety warnings;
-   ambiguity diagnostics or backtracking simulation;
-   target capabilities, engine restrictions, or lookbehind acceptance;
-   portability, native-support, rewrite, or unsupported decisions;
-   optimization or semantics-changing Semantic IR rewrites;
-   diagnostic production or source presentation;
-   target lowering, capture numbering, regex syntax, or emission;
-   parser, grammar, frontend, Simply, binding, LSP, or editor migration;
-   public protocol/schema changes, package versions, or publishing.

Later safety and portability stages may consume these immutable structural
facts alongside the unchanged program and foundational facts. They own every
policy judgment about what a structural condition means.
