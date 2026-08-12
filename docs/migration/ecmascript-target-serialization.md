# Deterministic ECMAScript serialization and Node certification

P11-T02 owns the mechanical boundary from one validated
`EcmascriptLoweringPlan` to one canonical `TargetArtifact`, followed by a
separate, controlled certification of those artifacts against one exact
Node/V8 runtime. Serialization does not inspect Semantic IR, evaluate target
capabilities, choose rewrites, execute JavaScript, migrate bindings, or expose
a product runtime. Certification observes artifacts; it cannot repair or
reinterpret them.

## Authority and dependency direction

The serializer consumes only the completed target plan produced by P11-T01:

```text
validated EcmascriptLoweringPlan
    -> deterministic ECMAScript serializer
        + RegExp pattern source
        + canonical pattern flags
        + profile-declared compile/runtime options
        + resolved requirements
        + generated-to-semantic/source mappings
        + emission diagnostics
    -> validated TargetArtifact
```

The [ECMAScript 2024 RegExp grammar and execution
semantics](https://tc39.es/ecma262/2024/multipage/text-processing.html) are the
normative syntax and matching authority. In particular, Pattern, Assertion,
Quantifier, AtomEscape, GroupSpecifier, CharacterClassEscape, RegExp
initialization, RegExpBuiltinExec, MakeMatchIndicesIndexPairArray,
Canonicalize, and WordCharacters govern spelling and observation. The PCRE2
serializer and historical JavaScript bindings are compatibility evidence only.

The serializer validates the complete lowering plan before writing output and
validates the constructed artifact before returning it. Contract and
specification versions, semantic-program fingerprint, exact profile reference,
portability status, capture table, requirement order, rewrite evidence, and
operation provenance remain upstream facts.

## Pattern flags and the artifact contract

ECMAScript global case behavior cannot be expressed by the ES2024 pattern
grammar, and ES2024 does not provide PCRE2-style scoped modifiers. A valid
artifact therefore needs pattern flags in addition to pattern source. The
existing `TargetArtifact` has profile-owned `engine_options`, but those options
have immutable profile-declared values and cannot represent per-program `i`
intent. P11-T02 adds an optional, canonical `flags` array to `EmittedPattern`.
The addition is backward compatible: existing PCRE2 JSON omits the field and
retains its bytes and fingerprint, while ECMAScript artifacts emit it.

The ECMAScript serializer emits flags in canonical `RegExp.prototype.flags`
order. The current plan can produce only `u` or `iu`: `u` materializes the
required `ecmascript.unicode_mode` option, and `i` materializes insensitive
case intent. The artifact still copies the profile-owned Unicode option into
`engine_options`; the flag is its exact constructor spelling, not a second
policy decision. `g`, `d`, `m`, `s`, `v`, and `y` are never inferred into a
product artifact. Certification may use explicitly declared observational
`d` or iteration `g` modes in an isolated run and records those additions
separately from the artifact flags.

## Canonical syntax and precedence

Serialization favors one reviewable form over minimal text:

-   alternations use an explicit noncapturing group and preserve branch order;
-   sequences concatenate already-delimited children in order;
-   every repetition operand uses an explicit noncapturing group before the
    canonical `*`, `+`, `?`, `{m}`, `{m,}`, or `{m,n}` spelling and optional lazy
    suffix;
-   named captures use `(?<name>...)`, unnamed captures use `(...)`, and
    backreferences use the lowering plan's unambiguous named or decimal form;
-   lookahead and lookbehind use their exact positive or negative assertion
    forms; and
-   include-line-terminators wildcard uses `[\\s\\S]`, while the ordinary
    wildcard uses `.`, so no global `s` flag broadens unrelated nodes.

Input start uses `^` without `m`. Strict input end uses a terminal negative
lookahead. ECMAScript `$` without `m` recognizes only strict input end, so
`end_before_final_line_terminator` uses an explicit CRLF-aware lookahead that
accepts strict end or the position before one final LF, CR, CRLF, U+2028, or
U+2029 sequence. Line-start and line-end behavior is spelled with explicit
zero-width alternatives over the four ECMAScript LineTerminator code points
rather than enabling global `m`.
Word and non-word boundaries retain ECMAScript `\\b` and `\\B` behavior under
the artifact's exact `u`/`i` flags.

## Escaping and character sets

Pattern-source escaping is independent from JavaScript string-literal
escaping. Regex metacharacters and solidus are escaped; NUL, controls, the four
line terminators, and ambiguity-prone characters use stable lowercase hex or
Unicode escapes; ordinary printable Unicode scalars remain UTF-8 text. Class
members use a separate escape table for `]`, `-`, `^`, backslash, controls,
and range endpoints. Capture and Unicode-property identifiers are syntax data,
not escapable literals, and malformed values fail closed.

ASCII built-ins use exact explicit sets for digit, word, and ASCII whitespace,
so global `i` cannot widen them through Unicode case folding. Unicode digit and
whitespace use their ECMAScript property-escape spellings. Unicode word uses a
fixed property union matching the canonical Unicode word contract rather than
ECMAScript's ASCII-oriented `\\w`. Mixed positive and negative members are
serialized through deterministic one-scalar alternatives and assertions when
one bracket class cannot preserve the set algebra. The serializer does not
introduce `v`-mode class algebra; `v` behavior is observed only in explicitly
separate runtime cases because the governed profile requires `u`.

## Artifact projection, provenance, and failures

Every plan option is copied with its exact ID, stage, and value. Requirement
identities, native or exact rewrite resolution, portability status, and exact
target reference are projected without recomputation. Each operation records
its half-open generated UTF-8 byte range and retained semantic/source
provenance. Equal generated spans coalesce sorted unique evidence so empty and
rewritten operations remain representable.

The pure stage has no filesystem, environment, network, clock, process,
thread, randomness, Node, V8, binding, frontend, editor, or product input.
Stable `STRL-ECMASCRIPT_EMIT` diagnostics cover malformed plans, capture or
property syntax, ECMAScript numeric/syntax bounds, output resource limits,
invalid flag materialization, and invalid constructed artifacts. No partial
artifact is returned.

## Exact Node/V8 certification

Runtime evidence is controlled by a Python orchestrator and a fixed JavaScript
harness. The governed runtime is Node.js `v22.23.2` on Linux x64 with upstream
V8 `12.4.254.21` and exact process-reported identity
`12.4.254.21-node.56`, the current maintained Node 22 release within the
repository's `>=22,<23` toolchain constraint when this task was scoped. The orchestrator
accepts only `STRLING_NODE_22_BINARY`. Node publishes SHA-256 evidence for the
Linux x64 archive, so the governed pin records that official archive hash plus
the extracted `bin/node` hash derived from the verified archive. The
orchestrator verifies the executable hash, exact Node and V8 versions,
operating system, and architecture, and returns `unavailable` rather than
substituting another host runtime.

The harness receives bounded JSON on standard input and returns canonical JSON
on standard output. It has no network, package-manager, module-resolution,
filesystem-write, clock, randomness, worker, or child-process authority. Its
fingerprint covers the executable bytes, Node/V8/platform identity, target
profile, harness source, runtime corpus, artifact source and flags, declared
observational flags, invocation mode, limits, and repeat count.

Corpus cases cover successful and failed construction; match/non-match;
UTF-16 code-unit spans; named and numbered captures; unmatched captures;
lookahead and both lookbehind directions; strict input and line anchors over
LF, CR, CRLF, U+2028, and U+2029; sensitive/insensitive matching; Unicode
scalars, properties, `u`, and separately declared `v` observations; invalid
and duplicate flags; exact error class; zero-length single and repeated
execution; and the certified atomic-literal rewrite. Negative cases retain
their governed expectation even when an unpinned newer Node would accept a
different extension.

At least two complete runs must produce identical semantic projections and a
stable `certification-result-v1` digest. The operation is registered in Full
and Release profiles only. Missing or mismatched exact runtime evidence is
`unavailable`; malformed configuration is `incomplete`; an observed semantic
mismatch is `failed`. Local and Pull Request profiles continue to test the
serializer and harness protocol without claiming exact runtime certification.

## Architecture and deferred ownership

Architecture fitness enforces a one-way
`ecmascript_lowering -> ecmascript_serialization` dependency and prohibits
PCRE2 reuse, capability or rewrite-policy recomputation, profile
reinterpretation, runtime execution inside Rust serialization, ambient input,
target-neutral reverse dependencies, and direct product/kernel callers. The
runtime orchestrator may execute only the exact configured Node binary and
fixed harness; the harness may consume only declared artifacts and cases.

Public compiler orchestration, bindings, package APIs, cross-engine
conformance, Python target work, broad fuzzing, performance budgets, release
notes, version changes, tags, publication, and registry upload remain later
ordered work.
