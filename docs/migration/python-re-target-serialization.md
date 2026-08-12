# Deterministic Python `re` serialization and CPython certification

P11-T04 owns the mechanical boundary from one validated
`PythonReLoweringPlan` to one canonical `TargetArtifact`, followed by a
separate controlled certification of emitted artifacts against an exact
CPython 3.11 runtime. Serialization does not inspect Semantic IR, evaluate
capabilities, choose rewrites, execute Python, migrate the historical Python
binding, or expose a product runtime. Certification observes artifacts and
cannot repair or reinterpret them.

## Authority and dependency direction

The serializer consumes only the completed target plan produced by P11-T03:

```text
validated PythonReLoweringPlan
    -> deterministic Python re serializer
        + regex pattern source
        + canonical re flags
        + profile-declared pattern-kind option
        + resolved requirements
        + generated-to-semantic/source mappings
        + emission diagnostics
    -> validated TargetArtifact
```

The [Python 3.11 `re` documentation](https://docs.python.org/3.11/library/re.html)
is the normative syntax and matching authority. The
[CPython 3.11.15 release](https://www.python.org/downloads/release/python-31115/)
is the exact maintained patch release selected for runtime evidence. Its
official XZ source archive has SHA-256
`272179ddd9a2e41a0fc8e42e33dfbdca0b3711aa5abf372d3f2d51543d09b625`.
The PCRE2 and ECMAScript implementations and the historical Python binding are
compatibility evidence only and are prohibited implementation dependencies.

The serializer validates the complete lowering plan before emitting and
validates the resulting artifact before returning it. Contract and
specification versions, semantic-program fingerprint, exact profile
reference, portability status, capture table, requirements, rewrite evidence,
pattern kind, options, and provenance remain upstream facts.

## Pattern representation, flags, and options

`TargetArtifact.pattern.text` contains Python regular-expression source, not a
Python source-code string or bytes literal. The existing UTF-8 artifact
contract remains unchanged. `str` plans may retain printable Unicode scalar
text; `bytes` plans are already restricted by lowering to ASCII pattern
semantics and emit ASCII regex source which the harness materializes as bytes.

Global case intent is the only current artifact flag: insensitive plans emit
the canonical one-element `i` array and sensitive plans emit no flags. The
harness maps `i` to `re.IGNORECASE`. It never infers `A`, `L`, `M`, `S`, `U`,
or `X`. The required `python.pattern_kind` value remains separately copied as
a runtime-stage engine option. Because target-profile options are immutable,
the existing `profile:python-re/3.11` continues to govern `str` and a separate
`profile:python-re/3.11-bytes` companion governs `bytes`; serializers accept
only the exact fingerprints of those two profiles. Scoped Python modifiers
used inside pattern text preserve individual wildcard, anchor, or
character-domain semantics; they are syntax projection, not new profile
policy.

## Canonical syntax and precedence

Serialization favors one reviewable form over minimal text:

- alternations use an explicit noncapturing group and preserve branch order;
- sequences concatenate already-delimited children in order;
- every repetition operand uses a noncapturing group followed by canonical
  `*`, `+`, `?`, `{m}`, `{m,}`, or `{m,n}` spelling and an optional lazy `?` or
  possessive `+` suffix;
- named captures and references use `(?P<name>...)` and `(?P=name)`; unnamed
  captures use `(...)` and unambiguous decimal references;
- lookahead, fixed lookbehind, and atomic groups use their Python 3.11 forms;
  and
- include-line-terminators wildcard uses `(?s:.)`, while the excluding form
  uses an explicit line-terminator complement, so no global dot-all mode leaks.

Input start and strict input end use `\A` and `\Z`. Line-start and line-end use
scoped Python multiline assertions, `(?m:^)` and `(?m:$)`, whose target-native
line boundary is LF; CR, CRLF, U+2028, and U+2029 do not acquire broader
cross-target meaning. End-before-one-final-LF uses Python `$`. Word and
non-word boundaries retain `\b` and `\B` under the exact pattern kind and case
flag.

## Escaping and character domains

Regex-source escaping is independent from Python string-literal escaping.
Metacharacters and backslash are escaped; NUL, controls, DEL, line separators,
ASCII whitespace, and `#` use stable hex or Unicode escapes so emitted source
is safe even in verbose/comment-sensitive contexts. Printable Unicode scalars
remain UTF-8 text for `str`. Class endpoints have a separate escape table and
bytes emission rejects any non-ASCII scalar if a malformed plan crosses the
lowering boundary.

Character-set members serialize as deterministic one-scalar predicates.
ASCII built-ins use scoped ASCII semantics for `str`, Unicode built-ins use
scoped Unicode semantics, and bytes use Python's bytes-domain built-ins.
Positive unions use ordered noncapturing alternatives. An outer-negated set
uses a bounded negative lookahead over that union followed by one dot-all
scalar, preserving mixed positive and negative members without global flags or
ambiguous bracket algebra. Python-unsupported Unicode property members fail
closed if injected into a malformed lowering plan.

## Artifact projection, provenance, and failures

Every plan option is copied with its exact ID, stage, and value. Requirement
identities, native or exact rewrite resolution, portability status, and target
reference are projected without recomputation. Each operation records its
half-open generated UTF-8 byte range and retained semantic/source provenance;
equal spans coalesce sorted unique evidence.

The pure stage has no filesystem, environment, network, clock, process,
thread, randomness, CPython, binding, frontend, editor, or product input.
Stable `STRL-PYTHON_RE_EMIT` diagnostics cover malformed plans, captures,
unsupported property syntax, bytes/scalar violations, quantifier or output
bounds, flag materialization, and invalid constructed artifacts. Failure is
all-or-nothing.

## Exact CPython execution certification

Runtime evidence is controlled by a host Python orchestrator and a fixed
Python harness executed only by the configured target binary. The selected
runtime is a local Linux x86-64 build of official CPython 3.11.15 source,
configured without `ensurepip`. The orchestrator accepts only
`STRLING_CPYTHON_311_BINARY`, verifies the official source archive digest,
the derived executable digest, exact `3.11.15` implementation and ABI identity,
Linux x86-64 platform, profile, corpus, and harness fingerprints, and returns
`unavailable` rather than substituting host Python 3.12 or Windows Python 3.13.

The harness receives bounded JSON on standard input and returns canonical JSON
on standard output. It imports only Python standard-library modules, reads no
files, writes no files, performs no network access, and starts no child
processes. String subjects are JSON text; bytes subjects are exact hex. It
reports compile outcomes, all bounded `finditer` observations, code-point or
byte spans, numbered and named captures, unmatched captures, and runtime
identity.

The governed corpus covers positive and negative matches, spans, named and
numbered captures, lookahead and fixed lookbehind, strict and line anchors over
all relevant newline forms, Unicode and case behavior, bytes, native atomic
and possessive syntax introduced in 3.11, zero-length iteration, compile
errors, and certified rewrites. A negative runtime-identity probe proves that
newer local CPython behavior cannot leak into the 3.11 target profile. At least
two complete target runs must produce identical semantic projections and one
stable `certification-result-v1` digest.

The runtime operation is registered in Full and Release profiles only. Missing
or mismatched exact runtime evidence is `unavailable`; malformed configuration
is `incomplete`; a semantic discrepancy is `failed`. Local and Pull Request
continue to exercise serializer, protocol, and architecture tests without
claiming exact target-runtime execution.

## Architecture and deferred ownership

Architecture fitness enforces one-way
`python_re_lowering -> python_re_serialization` dependency and prohibits peer
serializer reuse, capability or rewrite-policy recomputation, profile
reinterpretation, runtime execution inside Rust serialization, ambient input,
target-neutral reverse dependencies, and direct product/kernel callers. The
orchestrator may execute only the exact configured CPython binary and fixed
harness.

Public compiler orchestration, bindings, package APIs, cross-engine
conformance, broad fuzzing and performance budgets, release notes, version
changes, tags, publication, and registry upload remain later ordered work.
