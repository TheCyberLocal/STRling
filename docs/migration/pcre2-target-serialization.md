# Deterministic PCRE2 serialization and artifacts

P10-T02 owns the mechanical boundary from one validated
`Pcre2LoweringPlan` to one canonical `TargetArtifact`. It serializes the
already-selected PCRE2 operation tree, records generated provenance, and
projects the already-selected profile options and requirement resolutions. It
does not inspect Semantic IR, evaluate capabilities, choose rewrites, execute
PCRE2, migrate bindings, or publish packages.

## Authority and dependency direction

The only semantic input to serialization is the completed target plan:

```text
validated Pcre2LoweringPlan
    -> deterministic PCRE2 serializer
        + UTF-8 regex pattern text
        + all profile-declared compile/runtime option values
        + resolved requirement records
        + generated-to-semantic/source mappings
        + emission diagnostics
    -> validated TargetArtifact
```

The serializer first validates the lowering plan. Contract and specification
versions, semantic-program fingerprint, exact profile reference, portability
status, capture table, requirement order, rewrite evidence, and operation-tree
provenance therefore remain facts decided upstream. Serialization cannot call
requirement extraction, capability evaluation, portability planning, or target
lowering, and it cannot infer support from an engine-version string.

## Pattern syntax and precedence

Serialization uses a deliberately canonical, mechanically reviewable PCRE2
spelling:

- alternations are enclosed in noncapturing groups and retain branch order;
- sequences concatenate their already-grouped children in order;
- every repetition operand is enclosed in a noncapturing group before the
  canonical `*`, `+`, `?`, `{m}`, `{m,}`, or `{m,n}` spelling and the optional
  lazy or possessive suffix;
- named and unnamed captures use PCRE2 capture syntax, while backreferences use
  unambiguous absolute slot syntax from the lowering capture table;
- lookarounds, anchors, boundaries, and atomic groups use their exact PCRE2
  constructs; and
- insensitive matching and wildcard inclusion of line terminators use scoped
  PCRE2 option groups because `i` and `s` are genuine pattern-level PCRE2
  semantics. They are not substitutes for profile-owned runtime options.

This grouping rule favors a single deterministic form over minimal text. It
prevents parent context from changing the serialization of an operation and
keeps quantifier and alternation precedence explicit.

## Escaping and character sets

Literal serialization escapes every PCRE2 metacharacter, backslash, ASCII
pattern whitespace, `#`, NUL, and other control scalars. Short documented
escapes are used for tab, line feed, carriage return, form feed, and vertical
tab; other controls use lowercase `\\x{...}` code-point spelling. Printable
non-ASCII Unicode scalars remain UTF-8 text.

Inside ordinary character classes, class metacharacters and ambiguity-prone
range endpoints are escaped independently from pattern literals. Unicode
built-ins use `\\d`, `\\w`, and `\\s` under the profile-declared UCP option;
Unicode properties use `\\p{property}` or `\\p{property=value}` and their
negated forms. ASCII built-ins use explicit ASCII atoms under a scoped
case-sensitive group so global insensitive matching cannot widen them through
Unicode case folding. Mixed sets that cannot be represented by one bracket
class use a deterministic one-scalar alternation, with a negative assertion
and dot-all scalar for outer complementation.

Property and capture-name text is syntax data, not an escapable literal.
Current canonical support accepts the specification's ASCII identifier form
and fails closed with a stable emission diagnostic for other names rather than
emitting ambiguous or invalid PCRE2 syntax. Later profile-governed expansion
may admit the wider Unicode name vocabulary documented by PCRE2.

## Options and artifact projection

`TargetArtifact.pattern.encoding` remains `utf-8`, as required by the
canonical artifact contract. Every option already present in the lowering
plan is copied to `engine_options` with its exact ID, compile/runtime stage, and
JSON scalar value in canonical order, including profile-default selections.
In particular, `pcre2.utf` and `pcre2.ucp` remain separate compile options.
The serializer never prefixes the pattern with `(*UTF)` or `(*UCP)` and never
uses an invented Unicode inline modifier.

The current PCRE2 profiles do not declare code-unit library width,
newline/BSR overrides, JIT policy, or match-context settings. Serialization
does not fabricate them. If a later exact profile declares such obligations,
the lowering plan and artifact carry them as separate options; direct runtime
work must reject or explicitly certify any consumer configuration that the
selected profile does not describe. UTF-16 and UTF-32 consumers must therefore
wait for exact profile data instead of reinterpreting this UTF-8 artifact.

Requirement identities project by their zero-padded canonical ordinal,
capability identity, completed status, and a stable native or exact rewrite
resolution code. No unsupported or unresolved requirement can reach this
stage.

## Provenance, determinism, and failures

Each target operation contributes its half-open UTF-8 byte range and retained
semantic node/source provenance. Identical generated spans are coalesced by
unioning sorted unique references, which makes empty and rewritten operations
representable without duplicate source-map keys. The final source map is
sorted by generated span and validates against the emitted pattern text.

The stage is pure and all-or-nothing. It has no filesystem, environment,
network, clock, process, thread, randomness, runtime PCRE2, binding, frontend,
or editor input. Stable emission diagnostics cover malformed target plans,
invalid capture/property identifiers, PCRE2 syntax bounds, output resource
limits, and an invalid constructed artifact. The PCRE2 quantifier and capture
limits are syntax validity checks, not new portability policy.

Focused tests will cover every operation and option shape, exact escaping,
grouping and precedence, UTF-8 generated spans, empty-span coalescing,
deterministic JSON/fingerprints, input immutability, controlled invalid plans,
and generated mutations. Architecture fitness must enforce a one-way
target-lowering-to-serialization dependency and forbid policy recomputation,
runtime execution, ambient state, product callers, and target-neutral reverse
dependencies.

P10-T03 owns advanced and version-sensitive feature proof against exact
profiles. P10-T04 owns real-PCRE2 execution, pathological and sanitizer
certification, and performance budgets. Neither later task may move semantic or
portability decisions into serialization.
