# Canonical portability planning

[← Back to Architecture](architecture.md)

This contract defines the canonical portability-planning stage. The stage turns
factual capability results into explicit representation decisions for one exact
target profile. It does not transform Semantic IR, lower captures, serialize a
target pattern, produce diagnostics, or probe a runtime. A separate
evidence-only stage explains the completed plan through canonical diagnostics.

## Boundary and API

The dependency direction is:

```text
normalized Semantic IR
    + foundational SemanticFacts
    + StructuralFacts
    + exact TargetProfile
    + CapabilityEvaluation
        -> canonical portability planning
            + native decision
            + equivalent semantic rewrite plan
            + unsupported decision
            + unresolved planning evidence
        -> target-aware portability explanations
```

The pure API is:

```rust
plan_portability(
    &SemanticProgram,
    &SemanticFacts,
    &StructuralFacts,
    &TargetProfile,
    &CapabilityEvaluation,
) -> Result<PortabilityPlan, PortabilityPlanningErrors>
```

All inputs are borrowed and immutable. The planner requires normalized Semantic
IR and validates that the program, fact stores, requirement set, capability
results, and target profile describe the same contract version, specification
version, canonical program fingerprint, profile identity, profile revision,
engine/runtime identity, and profile fingerprint. Every canonical requirement
must have exactly one matching factual result in the same deterministic order.

The planner consumes capability results exactly as supplied. It never invokes
requirement extraction or capability evaluation, and it never infers capability
support from an engine name. It has no filesystem, environment, network, clock,
randomness, runtime, frontend, binding, LSP, diagnostic presentation, lowering,
or emitter dependency.

## Decision model

`native`, `equivalent_rewrite`, and `unsupported` remain the complete final
portability vocabulary. `Unresolved` is deliberately not added to that enum.
Instead, each requirement has exactly one planning disposition whose payload is
one of:

-   **Native:** the exact capability result is `Supported`. The decision retains
    the semantic requirement, node, target profile, complete capability result,
    constraint facts, and constraint evaluations.
-   **Equivalent rewrite:** native capability is explicitly `Unsupported` or a
    `ConstraintViolation`; one registered strategy applies; every proof
    precondition is satisfied by certified semantic or structural evidence; and
    every replacement semantic requirement is supported for the same target
    profile. The planner records a rewrite plan but does not apply it.
-   **Unsupported:** native capability is explicitly `Unsupported` or a
    `ConstraintViolation`; no registered, fully proved equivalent strategy can
    represent it; and the profile plus closed certified strategy registry provide
    enough negative evidence to conclude non-representability.
-   **Unresolved evidence:** the factual result is `Unknown`, or a potentially
    applicable rewrite has an indeterminate proof or replacement-support
    prerequisite. Unknown profile information is never negative evidence and can
    never be converted to `unsupported`.

Supported native representation takes precedence over rewrite opportunities.
An `Unknown` native result remains unresolved; the planner does not use a
rewrite to conceal incomplete supplied capability evidence.

A semantic node may own several requirements. Each is planned independently,
and success for one requirement cannot conceal rewrite, unsupported, or
unresolved evidence for another requirement on the same node.

## Stable identity and evidence

The program plan records the canonical Semantic IR SHA-256 fingerprint and the
exact immutable `TargetProfileReference`. Requirement occurrences retain their
full typed `SemanticRequirement`, stable `NodeId`, canonical capability identity,
and canonical position in the already ordered capability evaluation. Evidence
never relies on source offsets, traversal addresses, regex spelling, or general
engine identity.

Native evidence is the complete, unchanged `CapabilityResult`. Unsupported and
unresolved decisions retain that same result plus deterministic rewrite-attempt
evidence. This makes later diagnostics able to distinguish explicit profile
unavailability, certified constraint violations, unknown profile data, failed
proof preconditions, and unknown proof preconditions without re-analysis.

## Rewrite-plan contract

A rewrite plan is a target-neutral instruction for a later semantic rewrite or
lowering stage. It contains:

-   a versioned stable strategy identity plus the exact authored registry
    version;
-   the canonical strategy-definition and conformance-evidence SHA-256
    fingerprints;
-   the original requirement and all affected stable semantic nodes;
-   zero or more replacement semantic requirements;
-   structural proof preconditions and a satisfied/failed/indeterminate result
    for each precondition;
-   exact semantic or structural evidence satisfying every successful
    precondition;
-   capability evidence supporting every replacement requirement under the same
    target profile;
-   the exact target profile reference; and
-   deterministic dependencies on other requirement plans, when present.

It contains no emitted fragments, escaping, target flags, capture indices,
engine-specific spelling, source edits, or transformed Semantic IR.

Equivalent rewrite is available only when all proof obligations are satisfied.
Proof inputs may include normalized semantic node kinds, nullability, certified
length, capture/reference relationships, structural overlap, and already
supplied capability results. Source-text heuristics, anecdotal engine behavior,
benchmarks, safety-warning suppression, and apparent equivalence are not proof.

Plans are ordered by the capability evaluation's canonical requirement order.
Affected nodes, replacement requirements, proof conditions, and dependency
identities are each unique and sorted. Dependencies may refer only to existing
plans and must form an acyclic graph. The planner does not assume independent
rewrites commute and does not optimize for the fewest rewrites.

## Authored certified rewrite registry

The versioned registry and its schema live under
`spec/portability/equivalence/1.0`. Registry certification validates the schema
shape, the closed reviewed strategy set, obligation and test identities,
evidence path and bytes, and later-executable hook declaration before planning
can select a rewrite. A stale or missing registry, strategy fingerprint,
conformance fingerprint, required test, or proof obligation makes selection or
plan validation fail. Strategy selection is by stable identity after
applicability, so declaration order cannot change the result.

The current `rewrite.atomic_literal.elide.v1` definition has canonical strategy
fingerprint
`52d1a15ffb3becdde9e33f708539395e395eff752741283d90ff8bb1ccb64cc5`.
Its `conformance.atomic_literal_elision.v1` evidence fingerprint is
`5fe61a36f43a50b7ce5f6e2b13f0ac36ded8bda0e6255a66027bcf669a1d3532`.
These identities are part of the selected-plan evidence, not comments or test
metadata.

| Candidate                                                                          | Classification                                      | Boundary                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Elide an atomic wrapper whose body is one literal                                  | Provably semantics-preserving and implementable now | `rewrite.atomic_literal.elide.v1`; requires an `Atomic` node, its exact literal body node, and certified node-kind correspondence. A literal has one fixed consuming path and no internal capture/reference action, so atomic commitment adds no observable semantic behavior. Replacement requirements are empty; requirements independently created by a non-ASCII literal remain independently planned. This is the existing normative `literal_atomicity_redundant` case. |
| Rewrite variable-length lookbehind to a different assertion structure              | Requires additional semantic analysis               | Historical emitters provide prose advice only. General equivalence depends on assertion context, alternatives, captures/references, length, and target assertion semantics not currently proved.                                                                                                                                                                                                                                                                              |
| Convert nested repetition to atomic or possessive form to address a safety warning | Not proven and unavailable                          | Historical raw-source remediation is safety-oriented and can change backtracking, captures, or accepted matches. Safety findings remain independent from portability.                                                                                                                                                                                                                                                                                                         |
| Interchange arbitrary atomic groups and possessive repetitions                     | Requires additional semantic analysis               | Equivalence needs explicit backtracking-choice and capture-effect analysis; current facts do not prove the general case.                                                                                                                                                                                                                                                                                                                                                      |
| Replace a named capture or named backreference with target numbering               | Target-specific lowering concern                    | Logical `CaptureId` preservation, final numbering, capture maps, and target spelling belong to later lowering. The portability planner does not lower captures.                                                                                                                                                                                                                                                                                                               |
| Choose engine flags, anchor spellings, Unicode modes, escaping, or syntax aliases  | Target-specific lowering concern                    | These choices serialize an already certified representation and are not semantic rewrite identities.                                                                                                                                                                                                                                                                                                                                                                          |

Only the first row may participate in `equivalent_rewrite`. The other candidates
remain unavailable even if they would increase an apparent portability score.

## Program aggregation

The program-level status is optional because completeness is required before a
truthful final conclusion. Aggregation uses this exact precedence:

1. If any requirement is unresolved, the program has no final portability
   status. Native, rewrite, and proven unsupported per-requirement evidence is
   still retained.
2. Otherwise, if any requirement is unsupported, the final status is
   `unsupported`.
3. Otherwise, if any requirement uses an equivalent rewrite, the final status is
   `equivalent_rewrite`.
4. Otherwise, including a program with no special target requirements, the
   final status is `native`.

Consequently a mixed unknown/unsupported program does not overclaim either
success or complete failure. A later profile-completion or diagnostic policy may
explain the already retained negative evidence without changing its meaning.

## Target-aware explanations

`explain_portability(&SemanticProgram, &PortabilityPlan)` runs only after plan
validation and exact program-fingerprint correspondence. It emits deterministic
canonical diagnostics for native (`STRL-PORTABILITY-0101`), certified rewrite
(`STRL-PORTABILITY-0102`), unsupported (`STRL-PORTABILITY-0103`), and unresolved
(`STRL-PORTABILITY-0104`) evidence. Locations come from Semantic IR source
origins; advice records capability availability and constraints, affected node
IDs, registry version, strategy and conformance fingerprints, and satisfied or
failed proof identities. Byte-identical explanations for repeated canonical
requirements on the same affected nodes are coalesced deterministically and
retain the exact occurrence count, preventing redundant advisory records from
consuming the compiler's certified diagnostic budget.

The explanation stage treats the plan as authority. Architecture tests prohibit
capability extraction/evaluation, planning, rewrite application, lowering,
emission, runtime probes, target artifacts, bindings, frontends, and ambient
filesystem, environment, clock, process, thread, or randomness dependencies.

## Ownership and exclusions

Portability planning owns representation strategy and proof-backed evidence.
Target lowering later consumes a certified plan and decides how a strategy
becomes transformed target-neutral lowering structures. Emitters later
serialize those structures.

This stage does not own rewrite application, safety remediation, target-specific
diagnostics, capture numbering, target syntax, target artifacts, runtime probing,
parser or grammar behavior, bindings, Simply, or editor/LSP integration.
