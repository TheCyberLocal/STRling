# STRling Architecture

[← Back to Developer Hub](index.md)

This guide explains the ratified product and compiler architecture in
contributor-facing language. The controlling decisions are
[`governance/product.md`](../governance/product.md) and
[`governance/architecture.md`](../governance/architecture.md).

## Product center

STRling is a portable regex-intent compiler. Its flagship abstraction is
semantic pattern intent, not a particular host binding, regex notation, target
engine, or editor.

Three authoring surface families converge on one semantic compiler path:

-   **Semantic STRling DSL:** the future flagship textual semantic language;
-   **Simply APIs:** idiomatic host-language semantic builders; and
-   **regex frontend/importer:** the existing regex-shaped compatibility source
    dialect.

The current `.strl` grammar belongs to the third family unless later ratified
specification work deliberately extends or reclassifies it.

## Responsibility flow

```text
authoring frontend
    -> canonical semantic representation
    -> semantic analysis
    -> semantic requirement extraction
    -> factual capability evaluation against a versioned target profile
    -> portability planning against a versioned target profile
    -> evidence-only portability explanations
    -> target lowering
    -> target-specific emitter
    -> versioned TargetArtifact
```

This is a responsibility model, not a module diagram. The checked-in
prepublication source, Semantic IR, compile request/result, diagnostic,
analysis, profile, portability, and artifact contracts live under
`spec/contracts/1.0`. The canonical Rust kernel currently implements the path
through certified portability planning, structured target-aware explanations,
pure PCRE2, ECMAScript, and Python `re` lowering stages, and deterministic
standalone PCRE2, ECMAScript, and Python `re` artifact serialization.
Exact-engine execution exists only in isolated repository certification;
product runtime execution and orchestration of those target stages remain
deliberately absent.

**Semantic analysis** owns target-independent validity, facts, safety findings,
and canonical diagnostic explanation. Diagnostic generation preserves the five
certified `STRL-SAFETY` mappings and also owns a closed proof substage for
`STRL-QUALITY` findings: unreachable zero-maximum repetition operands,
non-possessive exact-once wrappers, exact duplicate alternatives,
same-position contradictory boundary or lookaround assertions, explicit
character-set member intersections, and references to proven zero-width
capture bodies. These findings use normalized Semantic IR and certified facts,
not raw-source scanning, target/runtime behavior, general satisfiability,
style-only policy, or rewrite authority. See
[Proof-backed semantic quality diagnostics](migration/semantic-quality-diagnostics.md).

**Semantic requirement extraction** describes which target capabilities the
normalized program demands. **Capability evaluation** compares those
requirements with one exact immutable profile and reports only factual native
support, explicit unavailability, constraint violations, or unknown data. Its
[contract](capability-evaluation.md) preserves missing profile information as
unknown and does not choose rewrites.

**Portability planning** consumes that exact evaluation and chooses native
support, a proven semantics-preserving rewrite plan, or an unsupported result.
Its [canonical contract](portability-planning.md) preserves incomplete evidence
as unresolved outside the final portability vocabulary. Engine capabilities
are version/profile-sensitive, and planning neither applies rewrites nor emits
target syntax. An equivalent rewrite must be bound to the versioned authored
registry, exact strategy fingerprint, exact conformance-evidence fingerprint,
and complete exact-runtime evidence for its applicable profiles. Planning
enumerates only strategies registered as `mandatory_portability`; a
request-only optimization cannot become a target representation decision.

**Certified semantic rewrite actions** are a separate explicit-request stage.
The current action admits only greedy or lazy exact-once repetition wrapper
elision, validates the same normalized program and certified fact stores, and
returns the existing direct body plus proof and removed-wrapper provenance
without mutating Semantic IR. It has no diagnostic, target-policy, lowering,
serialization, runtime, frontend, binding, or product caller. Mandatory
portability strategies cannot cross this boundary, and diagnostics cannot call
it. See the
[semantics-preserving rewrite library](migration/semantics-preserving-rewrite-library.md).

**Portability explanations** consume the immutable Semantic IR and completed
certified plan. They project native, rewrite, unsupported, and unresolved
evidence into canonical structured diagnostics with stable codes, source
origins, affected node identities, profile facts, and proof identities. This
stage does not recompute capabilities or planning, apply a rewrite, lower, emit,
or probe a runtime.

**Lowering** consumes normalized Semantic IR, the exact target profile, and the
completed certified portability plan. `lower_pcre2`, `lower_ecmascript`, and
`lower_python_re` produce closed target operation trees, deterministic capture
slots,
profile-owned option data, requirement resolutions, source/node provenance,
and exact applied-rewrite certification. They reject stale, unsupported,
unresolved, wrong-target, or malformed evidence and never re-run capability
evaluation or planning. Their structured handoff contracts for
[PCRE2](migration/pcre2-target-lowering.md),
[ECMAScript](migration/ecmascript-target-lowering.md), and
[Python `re`](migration/python-re-target-lowering.md) contain no regex
punctuation, escaping, generated spans, emitted pattern, artifact, or runtime
call.

**Emitters** deterministically serialize certified lowering plans; they do not
invent semantic or portability policy. `serialize_pcre2`,
`serialize_ecmascript`, and `serialize_python_re` validate one exact target
plan, apply canonical target
spelling, escaping, grouping, precedence, and flags, copy all already-selected
options and requirement resolutions, build generated UTF-8 spans/source maps,
and validate the final `TargetArtifact`. Their mechanical contracts for
[PCRE2](migration/pcre2-target-serialization.md),
[ECMAScript](migration/ecmascript-target-serialization.md), and
[Python `re`](migration/python-re-target-serialization.md) keep profile-owned
consumer options distinct from pattern syntax. They cannot inspect Semantic
IR, reinterpret target profiles, choose rewrites, run a regex engine, access
ambient state, or serve bindings and product callers.

**Exact-engine certification** is a separate tooling boundary. Full and
Release may invoke fixed offline harnesses with explicitly supplied,
cryptographically pinned runtimes. Missing or mismatched engines are
`unavailable`, never substituted. Certification observes emitted syntax,
flags, spans, captures, failures, and repeat determinism; it does not become a
kernel or product execution route.

The specification-owned shared cross-engine corpus fixes one explicit
five-profile denominator and derives expected semantics, diagnostics, matches,
logical captures, support, and applicability only from its content-addressed
case manifest. A repository-only Rust example projects Semantic IR through the
public canonical stages without process or runtime access. An isolated Python
controller owns exact PCRE2, Node/V8, and CPython process/ABI interaction,
coordinate normalization, and checked raw-observation evidence. The corpus
does not vote across engines, learn expectations from emitted text, or expose a
product execution API; subsequent portability-matrix work classifies any
observed differences without rewriting the authored expectations.

The initial portability matrix is a derived evidence-only layer downstream of
that checked observation artifact. Its repository controller revalidates the
complete corpus, profile, runtime, and observation identities; compares every
executed normalized result with the authored expectation and peer profiles;
classifies native, certified-rewrite, unsupported, not-applicable, and
unresolved evidence; and generates one machine-authoritative JSON artifact plus
a human-readable projection. It cannot execute runtimes, inspect emitted
pattern spelling, vote across implementations, change an owning contract, or
enter product/public paths. Full and Release run it only after exact target and
shared-corpus certification, and any unresolved result blocks readiness. See
[Initial cross-engine portability matrix](migration/initial-portability-matrix.md).

## Simply

Simply is first-class semantic authoring. APIs may remain idiomatic in Rust,
TypeScript, Python, Java, C#, and other hosts, but equivalent operations must
serialize the same closed, ordered
[`strling.simply-builder@1.0.0`](../spec/frontends/simply/1.0/README.md)
construction graph and project to the same canonical Semantic IR and
`CompileRequest`.

The protocol fixes all 15 operations, Unicode/text and character-domain
options, repetition modes, deterministic node/capture identities, immutable
single-parent values, source-less generated provenance, imported provenance,
validation order, and stable structured failures. Target profiles and compiler
options are explicit request routing, never builder semantics. Raw regex,
emitted target syntax, implicit engines, runtime objects, and callbacks cannot
cross this boundary.

The specification-owned projector and authored fixtures are certification
evidence, not a second semantic implementation: every expected program must
validate as canonical in the Rust kernel, and every expected request must pass
the canonical compiler contract. Host adapters may translate stable failures
into idiomatic containers but may not replace their code/path identity with
formatted prose.

Existing public helpers, including direct target convenience methods, remain
compatibility obligations. They are not proof that Simply's permanent
implementation should bypass the canonical compiler, and this architecture does
not redesign them. Historical maximum-zero, repeated-capture, numbered-capture,
and formatted-exception behavior is explicitly dispositioned by the protocol
rather than silently promoted into authority.

## Host adapters and targets

A host adapter exposes compiler capability in a programming ecosystem. A target
profile describes the regex/runtime semantics to compile for. These are
orthogonal:

| Host adapters                                            | Target engines                                               |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| Rust, TypeScript, Python, Java, C#                       | PCRE2, ECMAScript, Python `re`                               |
| Own idiomatic APIs, conversion, packaging, error mapping | Own version-sensitive runtime facts and target serialization |
| Must not reimplement semantics                           | Must not redefine STRling semantic intent                    |

The Rust canonical core is the prepublication reference implementation. It does
not become the specification. TypeScript and Python behavior remain
compatibility evidence, not semantic authority.

## Tooling

The CLI, LSP, editor integrations, documentation tools, and conformance tools
consume the same canonical compiler interface. They may own transport,
presentation, caching, and source projection, but not shadow semantic
implementations.

The root `./strling compile` command is a deterministic JSON transport for
`CompileRequest` and `CompileResult`. It delegates to the Rust kernel and owns
only standard-input/output, argument, target-profile file, and exit-status
handling. The kernel selects source syntax only from the explicit
`SourceDocument.frontend` identity; it currently dispatches
`strling.regex-compat@1.0.0` to the one governed compatibility parser. Neither
the shell nor the Rust transport binary parses regex syntax, selects a default
frontend or target, lowers targets, or emits artifacts.

## Current versus target state

Current per-binding parsers, compilers, validators, ASTs, IRs, diagnostics, and
emitters are transitional. So are TypeScript-derived shared fixtures, shallow
representation models, incomplete target capability tables, and direct
LSP-to-binding semantic dependencies.

These paths remain available until their replacements exist and public behavior
is preserved under the certified migration obligations. Their presence does not
change the permanent dependency direction.

## Specification relationship

The [`engineering authority hierarchy`](../governance/authority.md) places a
ratified versioned specification and expressly normative contracts above the
reference implementation, tests, compatibility evidence, and explanatory
documentation.

There is no ratified Semantic STRling flagship language specification version
yet. [`1.0-draft.1`](../spec/drafts/1.0/README.md) remains a non-normative scope
scaffold. The frozen `strling.regex-compat@1.0.0` grammar is a governed
compatibility/import frontend contract and must not be presented as the
flagship authoring language.
