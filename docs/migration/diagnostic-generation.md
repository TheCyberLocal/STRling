# Canonical structured diagnostic generation

## Stage ownership and boundary

Diagnostic generation communicates already-certified target-neutral evidence. It
does not establish safety facts. The pure kernel boundary is conceptually:

```text
generate_diagnostics(
    &SemanticProgram,
    &SemanticFacts,
    &StructuralFacts,
    &SafetyAnalysis,
) -> Result<DiagnosticGeneration, DiagnosticGenerationErrors>
```

`DiagnosticGeneration` retains an evidence-bearing record for every generated
diagnostic and provides the canonically ordered `Diagnostic[]` projection used
by `CompileResult`. The projection conforms to the independently certified
`diagnostic.schema.json`; semantic evidence is not added to that versioned
wire contract through ad hoc fields.

The inputs must describe the same complete normalized Semantic IR program.
Before mapping evidence, the stage validates contract and specification
versions, exact program identity, complete prerequisite stores, safety finding
shape, reachable node references, and referenced structural relationships.

The stage borrows every input and returns independent values. It does not parse
source or regex text, normalize or mutate Semantic IR, derive semantic,
structural, or safety facts, consult a target profile, plan portability, run an
emitter, apply a fix, lower to target syntax, or observe filesystem,
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
semantic safety findings and typed uncertainty
        |
        v
diagnostic generation
        |
        v
canonically ordered structured diagnostics
```

## Identity and evidence records

English prose is never diagnostic identity. The stable contract identity is
the diagnostic code, phase, category, and occurrence. Each generation record
also retains:

-   the primary semantic `NodeId`;
-   sorted and deduplicated contributing `NodeId` values;
-   the certified structural relationship identity when the finding has one;
-   the complete typed `SafetyEvidence`; and
-   the selected primary and related source spans, when provenance exists.

These values are used to validate evidence integrity, deduplicate equivalent
findings, derive occurrence order, and project locations. Traversal indexes,
hash-map order, allocation identity, process-local counters, prose, and source
text are not identities. Certified branch and sequence indexes remain evidence
because the structural model defines them as canonical relationship identity.

The certified diagnostic contract represents `occurrence` as a numeric
ordinal. The generator first deduplicates by the complete stable finding value,
then sorts occurrence keys by diagnostic code, primary node identity,
contributing node identities, and typed evidence value. It assigns contiguous
zero-based ordinals only after that stable sort. The ordinal is therefore
stable for identical semantic input and certified evidence, independent of
traversal or collection iteration. No hash, random value, clock, or unstable
counter is used.

Final contract diagnostics use the normative ordering from `PROTOCOL.md`:
located diagnostics first; source identity, start, end, phase order, severity
order, code, and occurrence; then location-free diagnostics by the remaining
keys. Related locations preserve the deterministic explanatory role order
defined below. Exact duplicate spans in the same explanatory role are removed.

## Stable safety diagnostic mapping

Every currently certified positive safety finding has exactly one mapping:

| Safety finding                         | Diagnostic code       | Severity  |
| -------------------------------------- | --------------------- | --------- |
| `unbounded_nullable_repetition`        | `STRL-SAFETY-0001`    | `warning` |
| `unbounded_indeterminate_progress`     | `STRL-SAFETY-0002`    | `info`    |
| `nested_repetition_overlap`            | `STRL-SAFETY-0003`    | `warning` |
| `repeated_alternation_overlap`         | `STRL-SAFETY-0004`    | `warning` |
| `repetition_follower_overlap`          | `STRL-SAFETY-0005`    | `warning` |

All five diagnostics use phase `semantic_analysis`, category `safety`, and
severity basis `compiler_policy`. The namespace and numeric allocation are
external diagnostic identities; they are deliberately not raw serialization
of the internal safety enum.

Messages state only what certified evidence proves. They describe unbounded
repetition without guaranteed progress or a proved structural competition.
They do not claim nontermination, catastrophic backtracking, denial of service,
universal vulnerability, exploitability, runtime complexity, or behavior of a
specific engine.

## Severity and confidence policy

Finding identity, evidence confidence, diagnostic severity, and target policy
are independent dimensions:

-   finding identity names the certified structural condition;
-   proof status and typed evidence state what semantic analysis established;
-   diagnostic severity communicates the default target-neutral action level;
    and
-   a later target-aware stage may add separate target capability or
    portability diagnostics under its own identity and severity authority.

A `warning` marks a proved nullable-progress or overlap structure that merits
attention but does not assert target runtime impact. The indeterminate-progress
finding is `info`: the unbounded extent is proved, while guaranteed operand
progress is not. This lower severity distinguishes missing progress proof from
proved nullable progress without discarding the certified finding.

Severity is not exploitability confidence. No target-neutral safety diagnostic
is a normative compile error, and generated safety diagnostics do not change a
successful `CompileResult` into failure.

## Source projection

All locations remain zero-based, half-open UTF-8 byte spans copied from
canonical `SourceOrigin` values. The generator never constructs a range by
merging discontiguous spans and never converts to lines, columns, Unicode
scalars, or UTF-16.

For a node with multiple source spans, the primary span is the smallest honest
span by byte length, with source identity, start, and end as deterministic
tie-breakers. Remaining spans are retained as related context rather than
merged. Within one evidence role, spans retain canonical source/start/end
order. A node without source provenance remains valid evidence and does not
cause a location to be fabricated.

The finding-specific projection is:

-   repetition progress: repetition primary; operand related as the progress
    cause when its location differs;
-   nested repetition: outer repetition primary; inner repetition related as
    the competing nested repetition, with its operand as additional context
    when separately located;
-   repeated alternation: enclosing repeated region primary; left and right
    overlapping branches related in canonical branch-index order;
-   repetition/follower competition: repetition primary; follower related as
    the competing input consumer, with the repeated operand as context when
    separately located.

If the primary node has no span, the diagnostic is location-free. Related
locations may still be emitted for contributing nodes that have provenance.
The generator does not promote a related span into the primary location because
doing so would misattribute finding ownership.

## Advice and remediation boundary

Advice is structured with the certified `note` and `help` kinds. Notes explain
the proof boundary, especially that runtime impact depends on execution policy
and input. Help may propose only conceptual actions:

-   require semantic progress before unbounded repetition;
-   make progress evidence explicit when it is currently indeterminate;
-   remove ambiguous nested repeated partitions;
-   narrow overlapping repeated alternatives; or
-   separate repeated content from follower input that competes for the same
    leading characters.

Generated safety diagnostics contain no `Fix`, `TextEdit`, replacement text,
or executable semantic transformation. They do not emit atomic-group or
possessive-quantifier syntax and do not recommend such behavior
unconditionally. Advice may note that a later target-aware stage can consider
engine-supported atomic or possessive behavior only after it proves semantic
equivalence. When no accurate generic help exists, help is omitted rather than
guessed.

## Typed uncertainty policy

Current `SafetyUncertainty` values do not generate compiler diagnostics. An
unknown overlap, unsupported Unicode-property algebra, saturated leading set,
indeterminate comparison, or nullable-only relationship is not promoted to a
positive safety warning or informational diagnostic.

This signal-over-noise default preserves typed uncertainty in `SafetyAnalysis`
for later policy without presenting absence of proof as proved risk. If a later
contract deliberately exposes uncertainty, it must use diagnostic codes
distinct from `STRL-SAFETY-0001` through `STRL-SAFETY-0005`, state the unknown
reason, and define its own deterministic severity policy.

## Deferred target-aware diagnostics

This stage does not decide whether a target engine backtracks, whether a target
supports atomic or possessive behavior, whether a semantics-preserving rewrite
exists, whether a pattern is portable, or whether operational context makes a
finding exploitable. It does not produce target capability, portability,
lowering, emission, parser, binding, Simply, or editor diagnostics.

Target-aware semantic capability modeling may later consume target-neutral
requirements and immutable target profiles. It must preserve this stage's
finding identity and evidence rather than changing safety proof conditions or
reusing safety codes for target decisions.
