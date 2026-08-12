# Structured PCRE2 target lowering

P10-T01 begins the first concrete target backend at the boundary immediately
after certified portability planning. It lowers normalized Semantic IR and one
exact completed `PortabilityPlan` into a deterministic PCRE2-specific target
representation. It does not serialize a regex string, execute PCRE2, construct
a `TargetArtifact`, migrate a binding, or publish a package.

## Authority and dependency direction

The lowering inputs are immutable:

```text
normalized SemanticProgram
    + exact TargetProfile whose engine is PCRE2
    + complete, self-validating PortabilityPlan for those exact bytes
        -> PCRE2 lowering
            + structured PCRE2 operation tree
            + logical-capture to PCRE2 slot plan
            + target option plan
            + resolved requirement evidence
            + applied-rewrite provenance
```

The stage validates the semantic program, canonical normalization marker,
program fingerprint, contract/specification versions, exact profile reference,
profile compatibility, engine identity, plan self-validation, final status,
requirement dispositions, and rewrite certification before lowering any node.
It consumes capability and planner decisions exactly as supplied. It cannot
extract requirements, evaluate capabilities, plan portability, infer support
from a version string, or use historical emitters as authority.

## Structured target representation

The PCRE2 plan remains pre-serialization data. Each lowered operation retains a
unique, sorted set of contributing Semantic IR `NodeId` values and canonical
source spans. The closed operation vocabulary covers empty, sequence,
alternation, literal, wildcard, character set, repetition, position, capture,
backreference, lookaround, and atomic forms. Target-specific enums record the
chosen wildcard behavior, repetition mode, position, assertion kind, capture
slot, and class-member representation without embedding PCRE2 punctuation or
escaping.

Captures receive deterministic one-based slots in semantic preorder. Named and
unnamed definitions retain their logical `CaptureId`, optional name, semantic
definition node, source evidence, and slot. Backreferences resolve to that
exact definition/slot; unresolved, duplicate, overflowed, or mismatched capture
evidence is a structured failure.

Every profile option is carried with its compile/runtime stage, scalar value,
and required/profile-default selection. UTF, UCP, variable-lookbehind limits,
JIT, matcher API selection, and future runtime configuration remain option
data. They never become pattern text during lowering.

## Planner and rewrite consumption

Only a plan whose final status is `native` or `equivalent_rewrite` may lower.
An `unsupported` plan or unresolved evidence fails before a partial target plan
exists, with a stable target-lowering diagnostic tied to the responsible
semantic node and source span.

Native decisions leave the semantic operation intact. The only admitted
rewrite is `rewrite.atomic_literal.elide.v1`. When selected, lowering removes
the atomic wrapper, lowers its literal body, and records the original/body node
IDs, registry version, strategy fingerprint, conformance fingerprint, proof
identity, and target-profile reference as applied-rewrite provenance. No other
rewrite, heuristic optimizer, safety remediation, or implicit fallback is
recognized. Generated replacement requirements must already have exact
supported evidence in the planner input.

## Explicit support boundary

All current Semantic IR variants have an explicit lowering branch. A branch is
usable only when every requirement attached to its node has a completed native
or certified-rewrite decision. This makes current PCRE2 profile gaps truthful:
unlisted capabilities remain unresolved and cannot be accepted merely because
a historical emitter happened to spell the construct.

Historical Python and TypeScript PCRE2 emitters are compatibility evidence for
construct inventory and later serialization tests. Their escaping, grouping,
lookbehind guards, ReDoS warnings, option assumptions, and output strings do
not define the target IR and are not called by the canonical stage.

## Failure and ownership boundary

Failures use canonical `Diagnostic` values in `target_lowering` phase with
stable codes, target-profile severity authority, affected node identity,
primary/related source locations, and advice identifying the exact stale,
unsupported, unresolved, or malformed evidence. Lowering is all-or-nothing;
there is no partial tree or degraded output.

Architecture fitness must reject target-neutral reverse dependencies, direct
capability/planner recomputation, emitters, pattern text, escaping, generated
spans, `TargetArtifact` construction, filesystem/environment/network/clock/
process/thread/randomness inputs, runtime PCRE2 calls, binding/frontend/editor
dependencies, and host-specific implementation reuse.

P10-T02 now serializes a certified PCRE2 plan through the separate
[`serialize_pcre2` boundary](pcre2-target-serialization.md), selects canonical
PCRE2 syntax and escaping, produces generated spans/source maps, preserves
profile options outside pattern text, and constructs a `TargetArtifact`. P10-T04
will execute real PCRE2 and discharge runtime differential hooks. Those later
tasks must not move policy back into the emitter.
