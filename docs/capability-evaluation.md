# Target capability evaluation

[← Back to Architecture](architecture.md)

This contract defines the first target-aware stage in the canonical compiler
kernel. It compares source requirements extracted from normalized Semantic IR
with one immutable, versioned target profile. It does not choose rewrites,
assign a portability status, lower captures, produce diagnostics, or emit regex
syntax. A second use of the same typed evaluator checks requirements extracted
from structured target output after lowering; that post-lowering check is the
final authority for artifact construction.

## Boundary and API

The dependency direction is:

```text
normalized Semantic IR
    + foundational SemanticFacts
    + StructuralFacts
        -> SemanticRequirements
        + TargetProfile
        -> CapabilityEvaluation
```

The pure direct-profile API is:

```rust
evaluate_capabilities(
    &SemanticProgram,
    &SemanticFacts,
    &StructuralFacts,
    &TargetProfile,
) -> Result<CapabilityEvaluation, CapabilityEvaluationErrors>
```

A pure reference-resolution entry point may first resolve a
`TargetProfileReference` from a caller-supplied `TargetProfileSet`, then invoke
the same evaluator. Resolution must verify profile identity, profile revision,
and canonical fingerprint. Neither entry point may consult installed engines,
the filesystem, the environment, a network, a clock, randomness, a frontend, a
binding, or an emitter.

The stage validates canonical Semantic IR, exact program/fact-store identity,
fact-store versions and node coverage, target-profile validity, specification
compatibility, and the profile's canonical reference before extraction or
evaluation. Inputs are borrowed and never mutated.

Callers that need the behavioral description for one capability can use
`resolve_capability_semantic_facts`. It validates the complete profile before
resolving any referenced set, algorithm, or target limit. A missing or malformed
required fact therefore fails closed; an unlisted capability returns the same
explicit unknown represented by the profile's enumerated scope.

## Requirement model

A `SemanticRequirement` is one occurrence identified by the stable `NodeId`
that demands it, a typed `RequirementKind`, and its canonical `CapabilityId`.
Its evidence is structural data, not regex spelling or source traversal
position. Multiple requirements may belong to one node. Requirements are
ordered by node identity, capability identity, and typed requirement value.
Only identical occurrences at the same stable node are deduplicated.

Typed requirement evidence includes:

-   lookbehind body identity and certified `LengthClassification`, including
    certified minimum and finite maximum when present;
-   logical capture identity and whether its ratified semantic name is present;
-   resolved logical capture identity for a backreference;
-   assertion direction and polarity;
-   exact position kind;
-   Unicode-property identity/value and Unicode-domain built-in class kind;
-   repetition mode;
-   case-matching semantics when insensitive matching is required.

No requirement contains target syntax, flags, capture indices, source text, or
rewrite instructions.

## Capability vocabulary and Semantic IR mapping

The certified profile identifiers
`assertions.lookbehind.fixed_length`,
`assertions.lookbehind.variable_length`,
`character_properties.unicode`, `groups.atomic`, and
`repetition.possessive` are reused exactly. The remaining identifiers below are
non-overlapping names for target-sensitive constructs that are already ratified
in Semantic IR. The five governed profiles enumerate the currently certified
set and retain `Unknown` for any unlisted future capability.

| Semantic construct                                                | Capability requirement                                                                                                              | Typed qualification                                                  |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `Lookaround::Ahead`                                               | `assertions.lookahead`                                                                                                              | polarity                                                             |
| fixed-length `Lookaround::Behind`                                 | `assertions.lookbehind.fixed_length`                                                                                                | body and certified fixed length                                      |
| finite-variable, unbounded, or indeterminate `Lookaround::Behind` | `assertions.lookbehind.variable_length`                                                                                             | body, certified length class, minimum, and finite maximum when known |
| named `Capture`                                                   | `groups.named_capture`                                                                                                              | logical capture identity                                             |
| any `Backreference`                                               | `references.backreference`                                                                                                          | resolved logical capture identity                                    |
| Unicode property member                                           | `character_properties.unicode`                                                                                                      | property, optional value, negation                                   |
| Unicode-domain built-in member                                    | `character_classes.unicode`                                                                                                         | class and negation                                                   |
| non-ASCII literal or set member/range                             | `character_semantics.unicode_scalar`                                                                                                | exact Unicode scalar data                                            |
| `Atomic`                                                          | `groups.atomic`                                                                                                                     | none                                                                 |
| possessive `Repeat`                                               | `repetition.possessive`                                                                                                             | none                                                                 |
| lazy `Repeat`                                                     | `repetition.lazy`                                                                                                                   | none                                                                 |
| input/line position                                               | `anchors.input_start`, `anchors.input_end`, `anchors.line_start`, `anchors.line_end`, or `anchors.end_before_final_line_terminator` | exact position kind                                                  |
| word/non-word boundary                                            | `boundaries.word`                                                                                                                   | polarity                                                             |
| insensitive program matching                                      | `matching.case_insensitive` on the root node                                                                                        | global semantic mode                                                 |

The following constructs add no target requirement by themselves: `Empty`,
`Sequence`, `Alternation`, ASCII-only nonempty `Literal`, `Wildcard`,
ASCII literal/range and ASCII-domain character-set members, greedy repetition,
unnamed capture, and positive/negative polarity independent of its assertion or
boundary. Their children can still add requirements. Unicode scalar
requirements remain semantic data; no target encoding mode or emitted flag is
invented for them.

The profiles nevertheless enumerate `character_classes.wildcard` and bind it
to `wildcard_exclusions` plus `matching_unit`. Wildcard has no source-side
requirement by itself, but target lowering classifies each structured emitted
wildcard and adds that capability to the final artifact requirement union.

## Post-lowering evaluation

Each target lowerer exhaustively classifies its closed operation vocabulary.
Structural nodes contribute no capability; capability-bearing nodes produce the
same typed `SemanticRequirement` evidence used here. Canonical reconciliation
removes only a matching natively implemented source occurrence, appends every
other emitted requirement deterministically, and evaluates the appended set
against the exact profile and selected options. Unsupported, unsatisfied,
unknown, malformed, or over-limit results prevent artifact construction.

Plan validation repeats the target-tree classification. Adding or mutating a
capability-bearing operation without updating its requirement evidence is thus
rejected before serialization. Final regex text is never parsed to reconstruct
requirements.

Logical capture identity remains independent of target numbering. An unnamed
capture does not require a particular target capture spelling; named captures
and backreference semantics do. Final numbering belongs to target lowering.

## Factual outcomes and evidence

Each extracted requirement produces exactly one `CapabilityResult` containing:

-   the stable semantic node identity and complete typed requirement;
-   the immutable `TargetProfileReference`, including profile identity,
    revision, and fingerprint;
-   the capability record found, or explicit evidence that it was absent;
-   the semantic sets, algorithms, and limits resolved through that capability's
    validated references;
-   every relevant typed constraint check and its semantic, structural, or
    profile-option evidence; and
-   one factual disposition.

The factual disposition vocabulary is:

-   `Supported`: the exact profile proves native support and all constraints are
    satisfied;
-   `Unsupported`: the exact profile explicitly declares the capability
    unavailable;
-   `ConstraintViolation`: the capability exists, but a typed requirement fact
    contradicts at least one certified constraint;
-   `Unknown`: the capability is absent, a constraint lacks comparable evidence,
    or the available facts are otherwise insufficient.

These are not portability decisions. In particular, `Unsupported` here does
not preclude a later semantics-preserving rewrite, and no result is converted
to `native`, `equivalent_rewrite`, or portability `unsupported` by this stage.

## Lookup and constraint rules

Capabilities are found by exact `CapabilityId` in the profile's validated,
unique, sorted capability list. Absence is always `Unknown`; the evaluator must
never infer `not listed -> false`.

Availability and constraints are evaluated as follows:

1. `available` with no constraints and every required semantic fact resolved is
   `Supported`.
2. `unavailable` is `Unsupported`.
3. A missing capability is `Unknown`.
4. For `constrained`, each constraint is evaluated structurally. Any violated
   constraint makes the result `ConstraintViolation`; otherwise any
   indeterminate constraint makes it `Unknown`; only all-satisfied constraints
   make it `Supported`.

`equals`, `at_most`, and `at_least` compare same-typed scalars identified by
the constraint identity and reject unit mismatches. `one_of` compares the typed
requirement scalar with the declared set. `requires_option` is satisfied only
when the exact option exists in the validated supplied profile with the
certified selection and value; it does not inspect emitted flags or runtime
state. A missing requirement fact, incomparable scalar, unknown structural
length, or absent target-context value is indeterminate, not a violation.

For lookbehind, the evaluator consumes the body node's certified structural
length and foundational consumption bounds. It never recomputes length. Fixed
length selects the fixed-length capability. Finite variable length selects the
variable-length capability and supplies its certified maximum in characters to
`bounded_maximum`. Unbounded and indeterminate bodies select the variable-length
capability but cannot satisfy a finite maximum constraint.

The profile, including its engine/runtime versions and profile revision, is the
complete target authority. No engine-name defaults are permitted. Consequently
the same semantic requirements can be `Unsupported` under the authored PCRE2
10.42 profile and constrained under PCRE2 10.43 without changing Semantic IR.
Likewise, two `available` capabilities may resolve to different semantic facts;
the `Supported` disposition means the profile fact is present and usable, not
that STRling lowering has already established cross-engine equivalence.

## Ownership and exclusions

Requirement extraction owns the target-neutral description of demanded
meaning. Capability evaluation owns factual comparison with a supplied profile.
Portability planning will later consume these facts and decide whether native
support, an equivalent rewrite, or failure is appropriate.

This stage does not own rewrite planning, target-specific diagnostics,
remediation, target lowering, capture numbering, engine options planning, regex
serialization, parser or grammar behavior, bindings, Simply, or editor/LSP
integration.
