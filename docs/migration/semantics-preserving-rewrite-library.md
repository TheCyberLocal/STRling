# Semantics-preserving rewrite library

[← Back to Architecture](../architecture.md)

P12-T05 turns the existing equivalence registry into a deliberately closed
rewrite library. Registration means semantic equivalence is supported by exact
proof obligations, counterexamples, and every applicable initial runtime. It
does not mean that a rewrite is generally faster, safer, or suitable for
automatic application.

## Locked strategy inventory

The task admits exactly two strategies:

| Strategy | Kind | Certified input | Transformation |
| --- | --- | --- | --- |
| `rewrite.atomic_literal.elide.v1` | mandatory portability | An atomic node whose direct body is a literal | Lower the direct literal body without the unsupported atomic wrapper. |
| `rewrite.repeat_exactly_once.elide.v1` | optional optimization | A repeat node with minimum one, bounded maximum one, and greedy or lazy mode | Offer the direct body as a request-only replacement for the count-neutral wrapper. |

Atomic-literal elision remains selected only when an exact target profile lacks
the original atomic capability and the existing portability proof succeeds.
Exact-once repetition elision has no portability requirement and therefore can
never enter target planning automatically. A consumer must explicitly request
that strategy for one stable node identity and receive a certified action; the
core does not silently mutate the program.

## Proof and registration boundary

Every registry entry must author its stable ID, application kind, exact
Semantic IR shape, preconditions, invariants, excluded states, transformation,
capability effects, target applicability, proof method, provenance behavior,
explanation, conformance evidence, and execution evidence. Registration fails
closed when any evidence file is absent or stale, a required test or profile is
missing, an execution vector is not associated with the strategy, an authored
precondition is widened, or an implementation strategy is not represented
exactly once.

Optional exact-once evidence must preserve accepted language, match span and
value, capture participation and values, alternative priority, zero-length
behavior, Unicode/case options, and diagnostics. Dedicated vectors execute on
PCRE2 10.42, PCRE2 10.43, ECMAScript 2024, Python `re` 3.11 str, and Python
`re` 3.11 bytes. Runtime corpora remain evidence, never semantic authority.

The requested action retains the removed wrapper identity and origin as
evidence and keeps the direct body and its provenance unchanged. It describes
the replacement but does not fabricate source text, a text edit, target
syntax, or an automatically mutated program.

## Rejected candidates

Possessive `{1}` is excluded because commitment can prevent backtracking into
the repeated body. Zero-count repetition removal is excluded because captures
inside the unreachable body remain part of the program's capture contract.
Duplicate-alternative removal is excluded pending a complete match-priority and
capture-path proof. General atomic or possessive insertion/elision is excluded
because backtracking choices may be observable. Character-set overlap cleanup
is excluded because a diagnostic witness is not a complete normalization proof
for Unicode, case-folding, member provenance, or negation.

No safety or quality diagnostic is rewrite authority. In particular,
`STRL-QUALITY-0002` may explain an exact-once wrapper, but only the independent
registry proof and an explicit rewrite request can produce the optional
action.

## Certification

Certification requires registry/schema and fingerprint completeness,
deterministic unit and property tests, adversarial rejected candidates,
unmodified inputs, stable request/action evidence, exact execution on every
applicable initial profile, unchanged shared-corpus and portability-matrix
semantics, all Rust and tooling checks, migration review, Local/Pull
Request/Full profiles, and a clean final commit.
