# Bounded no-match explanation

## Outcome and authority

P15-T03 defines a reusable, independently versioned explanation result for the
question “why did this semantic pattern not match this subject?” The permanent
contract identity is `strling.no-match-explanation@1.0.0`, owned under
`spec/explanations/no-match/1.0/`.

The result is subordinate to canonical Semantic IR, its exact structured
semantic explanation, and any completed target-plan evidence. It does not
define matching semantics, reinterpret emitted regex, or expose a target
engine’s internal backtracking trace. A useful explanation is accepted only
when bounded canonical evaluation can justify it; uncertainty is data, not a
prompt to invent a narrative.

The clean starting and rollback boundary is
`546df5ff5a7fe355a00c5dc245ad6a5eddec6405`. P15-T01’s semantic explanation
model and P15-T02’s conversion contract are complete at that revision. This
task consumes them without changing either model or beginning P15-T04’s broad
phase certification and product-surface work.

## Inputs and execution identity

The producer accepts:

-   one validated, canonical `SemanticProgram`;
-   the exact corresponding `ExplanationDocument`, target-neutral or carrying
    an already-completed target projection;
-   one UTF-8 subject string;
-   the explicit execution mode `search`; and
-   a complete set of caller limits no larger than the contract ceilings.

`search` examines candidate starts at Unicode-scalar boundaries. It does not
silently mean whole-value validation. Input-start, input-end, line, boundary,
and lookaround nodes retain their zero-width meaning. A later execution mode is
an additive or versioned contract decision, not an undocumented flag.

The result identifies the semantic program and semantic-explanation model by
version and canonical digest. It records only the subject’s SHA-256 digest,
UTF-8 byte length, and Unicode-scalar count; it does not echo subject text.
Subject positions and spans always use half-open UTF-8 byte coordinates and
must fall on scalar boundaries.

## Outcome and evidence dispositions

The match outcome and the quality of its explanation are separate:

-   `matched` means bounded canonical evaluation found a valid match, so there
    is no no-match cause;
-   `no_match` means all relevant candidate starts and paths were exhausted
    within the supported canonical model;
-   `unknown` means a resource guard or semantic/target uncertainty prevented a
    sound match decision; and
-   `unavailable` means completed target evidence says the semantic program is
    unsupported or unresolved for the requested target, so target execution
    cannot be explained as a no-match.

A `no_match` explanation is `proven` only when one localized construct or one
closed set of branch-local blockers is necessary across the complete bounded
failure proof. It is `likely` when no-match itself is established but multiple
defensible blockers exist and the result selects a deterministic high-value
one. `unknown` and `unavailable` outcomes carry corresponding uncertainty or
target-plan evidence, never likely-looking prose. `matched` is
`not_applicable`.

Each finding contains a stable reason code, confidence, evidence class,
semantic node identity, canonical source link, subject position or span, and
structured assertion, branch, repetition, and capture/backreference context
when relevant. The contract contains no localized prose, UI layout, debugger
timeline, or claim about engine-internal evaluation order.

The initial closed reason families are:

-   consuming mismatch: literal, wildcard, and character set;
-   position failure: input, line, word-boundary, and final-line-terminator
    assertions;
-   structure failure: alternation exhausted and repetition minimum unmet;
-   assertion failure: positive lookaround failed or negative lookaround
    matched;
-   state failure: capture unavailable or backreference mismatch;
-   target disposition: unsupported, unresolved, or target semantics unknown;
    and
-   bounded uncertainty: subject, step, depth, branch/state, finding, or
    elapsed-work limit reached, plus semantic evaluation unavailable.

Reason codes classify structured evidence. They do not replace the existing
compiler diagnostic taxonomy and do not imply exhaustive causality.

## Resource contract

The model has hard default ceilings. A caller may request only equal or tighter
limits:

| Guard                      | Default and maximum |
| -------------------------- | ------------------: |
| Subject UTF-8 bytes        |              16,384 |
| Subject Unicode scalars    |               4,096 |
| Evaluation steps           |             100,000 |
| Semantic/evaluation depth  |                 128 |
| Branch or state expansions |               4,096 |
| Retained findings          |                  32 |
| Elapsed work               |              250 ms |

Every node visit, candidate start, character comparison, assertion attempt,
capture transition, repetition transition, and branch/state expansion charges
an explicit logical counter. The elapsed guard uses a monotonic clock only as a
fail-safe; elapsed duration is not serialized. A reached guard returns
`unknown` with the configured ceiling, deterministic logical counts, and the
reached-limit code. It never returns a partial proof as `proven` or `likely`.

Unbounded repetitions are bounded by subject progress, the semantic depth
ceiling, and logical step/state ceilings. Zero-width repetition is detected
explicitly so it cannot loop. Output retention is bounded independently from
search work.

## Semantic coverage and conservative unknowns

The evaluator operates on canonical nodes, not source syntax. Case-sensitive
Unicode literals, scalar ranges, ASCII built-in classes, wildcard behavior,
input anchors, alternation, bounded or progress-bounded repetition, ordinary
captures/backreferences, and supported lookaround are evaluated directly.

Target-native classes, arbitrary Unicode properties, target-sensitive case
folding or boundary rules, target-dependent line terminators, unsupported
atomic/possessive interactions, forward/self/recursive capture topology, and
capture effects inside assertions receive a result only when the exact
canonical and completed target evidence is sufficient. Otherwise the whole
decision is `unknown` or `unavailable`. A target-aware semantic explanation
whose plan is unsupported or unresolved prevents a fabricated no-match claim.

This conservative boundary is intentional. Returning `unknown` is correct when
the repository has not ratified or encoded the fact required to distinguish a
match from a no-match.

## Determinism and correspondence

The producer rejects malformed Semantic IR, a mismatched semantic explanation,
invalid limits, stale target identity, or non-boundary subject spans as a
structured whole-operation error. It never repairs inputs.

Candidate starts, alternatives, repetition counts, findings, and context paths
have a canonical order. Logical work counters and all serialized output are
deterministic. Repeated evaluation of the same supported input and limits must
serialize byte-identically. Normal certification cases use enough elapsed
headroom that the monotonic fail-safe cannot choose their semantic outcome;
elapsed exhaustion has its own controlled resource case.

Equivalent Semantic STRling, Simply, regex-import, and source-less Semantic IR
programs are compared after the established alpha projection that removes
frontend-specific stable identities and optional provenance. Subject outcome,
reason family, confidence, context shape, and logical work disposition must
then agree.

## Architecture boundary

The intended Rust surface is a public `no_match_explanation` module containing
closed version, input-limit, outcome, finding, context, work-report, error, and
document types plus one pure `explain_no_match` producer. The module may consume
only canonical Semantic IR, its exact structured explanation, source identity,
target-plan identity, canonical hashing/validation, and a monotonic fail-safe
clock.

It cannot parse a frontend, import raw regex, convert authoring syntax, rerun
semantic or target planning, lower or emit a target artifact, execute a target
engine, inspect emitted patterns, read files or networks, call bindings, or
contain CLI/LSP/editor/Regex Lab presentation. Representative engine execution
belongs in certification and is compared with the structured result; it is not
the explanation algorithm.

## Verification and handoff boundary

Before implementation, CP2 freezes the closed schema, reason taxonomy,
positive matched/proven/likely/unknown/unavailable examples, isolated invalid
fixtures, mutation evidence, and a corpus spanning literals, classes, anchors,
alternation, repetition, lookaround, captures/backreferences, Unicode,
multiple blockers, target disposition, malformed correspondence, and every
resource guard.

CP3 implements the smallest canonical evaluator and proves no-panic bounded
work, sound disposition rules, source/subject correspondence, alpha-projected
frontend convergence, and repeated-byte determinism. CP4 cross-checks
representative supported results against a governed real target, certifies
unsupported target behavior and architecture/public surfaces, renews the
migration differential, and runs Local/Pull Request/Full profiles.

Task closure records model version and fingerprint, exact ceilings, reason and
disposition counts, target limitations, resource results, final SHA, and
P15-T04 readiness. Building an interactive trace viewer, Regex Lab Evaluate
flow, debugger controls, localization, binding adapters, CLI/LSP commands, or
engine-specific backtracking narrative is explicitly out of scope.
