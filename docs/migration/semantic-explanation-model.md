# Canonical semantic explanation model

## Scope and authority

P15-T01 defines one deterministic, structured explanation model over canonical
Semantic IR. The model is an independently versioned data contract. It does not
revise the STRling Semantic Specification, the certified compiler contract
suite under `spec/contracts/1.0`, or any target artifact.

The implementation consumes evidence already produced by the canonical
pipeline:

```text
normalized Semantic IR
        + foundational semantic facts
        + structural facts
        + safety findings and uncertainties
        + evidence-bearing diagnostics
        |
        v
target-neutral semantic explanation
        + exact capability evaluation and portability plan (optional)
        |
        v
target-aware semantic explanation
```

It never derives meaning from emitted regex, target syntax, raw source-text
heuristics, runtime probes, or presentation prose. Source text is relevant only
through canonical source identities and node origins. Source-less Semantic IR
is therefore fully explainable.

## Version and transport boundary

The first model version is `1.0.0`, governed by
`spec/explanations/semantic/1.0/explanation.schema.json`. Explanation-model,
compiler-contract, semantic-specification, source-dialect, and target-profile
versions remain separate identities.

The model is not added to `CompileResult` 1.0. The Rust kernel exposes the
typed explanation producer for later reusable transports, while existing
compiler requests and results remain byte-for-byte contract compatible. A
future transport addition must follow its own versioned public-contract task.

## Closed entity model

An explanation document contains both structured rendering forms:

-   a concise projection with program-level facts, entity counts, uncertainty
    counts, and optional target status; and
-   detailed entities for the program, every semantic node, capture/reference
    relationships, structural evidence, safety findings, diagnostics/advice,
    uncertainties, and optional target planning.

Detailed node entities retain stable node identity, canonical source spans and
derived-node provenance when available, semantic construct data, foundational
nullability/length/consumption facts, and structural facts. The semantic
construct vocabulary covers empty, sequence, alternation, literal, wildcard,
character set, repetition, position assertion, capture, backreference,
lookaround, and atomic nodes. Options and modes are represented as typed data,
not English labels.

Every evidence-bearing item declares exactly one evidence class:

-   `semantic_fact` for target-independent canonical meaning or analysis;
-   `target_plan` for exact capability or portability-planning evidence;
-   `diagnostic_advice` for diagnostic or advisory policy; or
-   `uncertainty` when the available canonical evidence is incomplete.

Unknown nullability, structural overlap, capability support, constraint facts,
and rewrite proof state remain explicit unknowns. No renderer or explanation
producer may coerce unknown to supported, unsupported, safe, unsafe, or proven.

## Determinism and correspondence

The producer validates that every supplied fact store, finding, diagnostic,
capability evaluation, and plan belongs to the exact canonical semantic
program and specification version. Target-aware projection additionally
requires the evaluation and plan to identify the same target profile and to
agree on every embedded capability result. Mismatch is a whole-operation
structured error, never a partial explanation.

Collections use their certified canonical order: stable node and capture IDs,
diagnostic result order, safety value order, and requirement-plan order.
Repeated production from identical inputs must serialize byte identically.
Equivalent frontends are compared after the contract-defined alpha projection
that removes frontend-specific stable IDs and optional source provenance; their
remaining explanation structure must agree.

## Rendering boundary

The canonical model contains typed entities, codes, relations, counts, and
evidence. It contains no UI layout, Markdown hierarchy, localization policy,
or engine-derived narrative. Concise and detailed text renderings are generated
non-normative fixtures used only to prove that the structured model is
renderable and deterministic. Structured JSON remains authoritative when text
and data disagree.

## Implemented Rust projection

The public `strling_kernel::explanation` module implements model `1.0.0` as
closed Serde types. `explain_semantics` validates exact Semantic IR,
foundational, structural, safety, and diagnostic-generation correspondence
before projecting every reachable node in stable identity order. The
diagnostic-generation object retains the exact private semantic-program
identity, so diagnostics from a different program are rejected even when that
program deliberately reuses the same stable node IDs.
`explain_target` accepts only a target-neutral explanation plus a completed
capability evaluation and portability plan whose versions, semantic digest,
profile, order, and embedded capability results agree exactly.

The internal target-neutral pipeline retains the structured explanation next
to its existing diagnostics, and the target-aware pipeline retains the target
projection next to its completed evaluation and plan. Neither object is added
to the immutable `CompileResult` 1.0 projection.

Portability diagnostics currently expose contract diagnostics without stable
semantic-node provenance. The target explanation therefore leaves its
target-local diagnostic array empty instead of guessing node identity from
message prose or source spans. Completed per-requirement target decisions,
constraints, rewrites, unsupported outcomes, and unresolved outcomes remain
fully represented by evidence-bearing plan entities. A later provenance-aware
diagnostic transport may populate that array without changing target-plan
semantics.

The Rust public-contract extractor now snapshots the explanation module,
functions, constants, enums, and structs as an additive `strling-kernel`
surface. Architecture fitness rules reject stage reruns, frontend or target
syntax dependencies, runtime I/O, emitted-pattern inference, and why-no-match
scope inside the projection.

## Non-goals

P15-T01 does not:

-   implement whyNoMatch execution tracing or inspect a subject string;
-   migrate Semantic IR to Semantic DSL or Simply;
-   parse or reinterpret raw regex source;
-   apply rewrites, lower targets, serialize artifacts, or run target engines;
-   change semantic meaning, diagnostics, capability evaluation, portability
    planning, target profiles, or existing compiler protocol shapes; or
-   add binding, CLI, LSP, editor, or product-specific presentation surfaces.

## Acceptance evidence

Completion requires schema-positive and controlled-invalid fixtures; Rust type
and serialization correspondence; complete node/taxonomy coverage; source-less
and provenance-bearing cases; semantic/regex/Simply frontend convergence;
target-profile sensitivity with invariant target-neutral sections; diagnostic,
safety, uncertainty, capability, and portability consistency; repeated-byte
determinism; generated non-normative text fixtures; architecture and public
contract hardgates; Local and Pull Request profiles; and a clean tree.

## Certification and P15-T02 handoff

P15-T01 closes with semantic-explanation model `1.0.0`, four evidence classes,
all 12 Semantic IR node kinds, one authoritative positive fixture, three
controlled-invalid fixtures, and two generated non-normative text views. Rust
all-target tests, focused explanation/property/frontend tests, all 591 tooling
tests, architecture/governance checks, the selected Rust public contract, and
the three-run migration differential pass. The final differential retains 44
observations, no determinism mismatch, no blocking canonical replacement, and
full-corpus fingerprint
`sha256:feedb6435b8b61ae6a004484feca0f0b23b6e578234f8ffc8daeca9eb0f04300`.

Local and Pull Request profiles pass every executable task-owned hardgate. The
repository-wide public-contract and generated-artifact operations retain the
inherited missing-Go limitation, and unavailable format/lint/typecheck/test
leaves retain the workstation's missing or incompatible declared toolchains.
The explanation-specific public/generated checks and direct Rust/tooling gates
pass, so no task-owned defect is carried forward.

P15-T02 may use the authoritative structured model to explain exact, partial,
or unsupported migration from canonical Semantic IR into Semantic DSL and
Simply. It must prove equivalence after reparsing or reconstruction, preserve
explicit unknown/loss states, and never convert directly from historical regex
text or treat the generated explanation renderings as semantic authority.
Bounded whyNoMatch tracing remains owned by P15-T03.
