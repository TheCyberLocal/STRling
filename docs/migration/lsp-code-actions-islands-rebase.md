# Canonical LSP code actions and embedded-island rebase

## Outcome and authority

P16-T04 replaces the final STRling language-server dependency on the
transitional Python binding. Code actions become presentation of certified
canonical rewrite evidence, Semantic STRling formatting delegates to the
canonical formatter, and embedded regex-compatible sources are extracted by
one bounded LSP coordinate adapter driven by one governed tooling registry.

The Semantic IR, canonical analyses, diagnostic identities, certified rewrite
registry, Semantic STRling frontend, and source contracts remain authoritative
for meaning and optional rewrites. The island registry is tooling authority for
which host boundaries and literal forms the editor may recognize; it cannot
define STRling syntax, semantics, target behavior, runtime behavior, or binding
APIs. The Python server may validate transport, project coordinates, enforce
limits, and materialize LSP edits, but it may not parse STRling or invent a
replacement.

The clean starting and rollback boundary is
`ee831b1f6c027c37b06da0d7cf571996325e8da8` on `architecture/v4`, the
P16-T03 closure. P16-T04 reuses T02/T03 immutable snapshots, canonical source
identities, UTF-8/UTF-16/UTF-32 projection, bounded subprocess handling,
cancellation, stale-result rejection, and current-result caching.

## Starting-state inventory

The authored server still imports `format_pattern` through
`server/deferred_intelligence.py`. Both LSP island-extractor modules import the
936-line `STRling.core.islands` binding module after mutating `sys.path`.
`test_code_actions.py` imports the binding's heuristic ReDoS detector directly.
Those are the four files covered by the transitional
`lsp-python-binding-semantic-dependency` architecture rule.

The legacy action path recognizes the removed `REDOS_RISK` alias and trusts a
`data.replacements` payload. It proposes atomic and possessive regex text for a
nested repetition without canonical semantic-equivalence evidence. The current
canonical diagnostic is `STRL-SAFETY-0003`; it deliberately has no fix and says
that runtime impact is target-dependent. Renaming the legacy action would
therefore be false certification.

The canonical rewrite library exposes exactly one request-only optional
strategy: `rewrite.repeat_exactly_once.elide.v1`. It proves that a greedy or
lazy repetition with bounds `1..1` may be replaced by its direct body. The
matching quality diagnostic is `STRL-QUALITY-0002`. Possessive mode, mandatory
portability rewrites, ReDoS heuristics, source-less nodes, and every other
candidate remain outside the optional editor-action boundary.

The existing `spec/tooling/island_boundaries.json` lists 17 host languages plus
native `.strl` suffixes and raw boundary regexes. It has no schema, semantic
version, literal-form declarations, escape/interpolation policy, mapping model,
resource contract, ambiguity dispositions, or fingerprint. The binding module
duplicates the entire registry as silent defaults. The Node fixture extractor
falls back to a permissive `parse(...)` regex if the file is absent or malformed.
The current 40 extractor tests pass, while the code-action module has eight
passing binding/registration cases and three expected failures tied to the
retired alias.

## Certified code-action contract

The internal editor-evidence transport gains a versioned, bounded collection of
certified source actions. An action is emitted only after a successful current
Semantic STRling parse and contains:

-   the exact canonical source identity and frontend identity;
-   diagnostic code `STRL-QUALITY-0002` and rewrite strategy identity
    `rewrite.repeat_exactly_once.elide.v1`;
-   semantic-program and strategy-certification fingerprints;
-   removed wrapper and replacement node identities;
-   the complete four-condition canonical proof identity;
-   one half-open UTF-8 wrapper span and one contained direct-body span; and
-   replacement text copied from that exact current inline source.

The Rust projection calls the existing foundational and structural analyses and
`request_semantic_rewrite`; it does not reproduce their predicates. Source edit
materialization additionally requires one unambiguous inline source span for the
wrapper and body, matching source IDs, UTF-8 scalar boundaries, containment,
and preservation of all non-layout source text. Comments or other source text
that would be discarded by wrapper elision make the action unavailable.

The LSP handler reads only the current immutable compiled snapshot and its
matching editor evidence. A client diagnostic authorizes display only when its
canonical code, source identity, exact projected range, and requested range all
match the action. Empty client diagnostic lists, cached diagnostics from older
versions, source hash changes, missing evidence, malformed proof data,
overlapping edits, ambiguous island projection, timeout, cancellation, and
resource exhaustion return no action. There is no fallback to the prior
per-URI diagnostic cache.

Actions are deterministic and unapplied. The server emits one
`refactor.rewrite` action per certified wrapper, attaches the exact matching
canonical diagnostic, and materializes one source edit only while the immutable
snapshot remains current. The validated editor evidence retains the canonical
strategy and proof identity even where the local LSP data model cannot serialize
custom action data or versioned document changes. No action is preferred.

No quick fix is emitted for `STRL-SAFETY-0003`, any other safety or quality
diagnostic, regex-compatible source, host island, mandatory portability
strategy, target-dependent suggestion, or heuristic text replacement.

## Canonical formatting contract

Successful native `*.semantic.strling` documents may return the exact output of
`semantic_frontend::format`. The LSP emits at most one full-document edit when
that output differs from the current source. Parse failure, stale identity,
service failure, and unchanged output return no edits.

There is no canonical formatter for the regex-compatible frontend. Native
`*.strl` files and all embedded host islands therefore return no formatting
edits in P16-T04. The binding formatter is retired rather than accepted as a
second formatting authority. Formatter determinism and parse-format-parse
semantic preservation remain proved by the canonical frontend property suite.

## Governed island-boundary registry

`spec/tooling/island_boundaries.json` remains the single tooling-owned registry
path so existing consumers do not gain a competing source. P16-T04 gives it a
closed `1.0.0` contract and schema. Its ordered host entries declare stable
language and boundary IDs, suffixes, boundary expressions, comment/string
scanner profile, supported literal-form IDs, frontend identity, raw/processed
content policy, interpolation and escape disposition, newline behavior,
coordinate model, target/profile policy, resource limits, unsupported cases,
and a deterministic registry fingerprint.

The registry covers native `.strl` routing plus 17 existing host IDs: Python,
TypeScript/JavaScript, Rust, Java, C, C++, C#, F#, Go, Kotlin, Swift, Dart, PHP,
Ruby, Perl, Lua, and R. Every suffix and boundary spelling in the existing
registry is inventoried; retention as an accepted island still depends on a
supported literal form and exact mapping proof. Registry loading is fail-closed:
missing, malformed, unsupported-version, duplicate, unsorted, unknown-scanner,
invalid-regex, fingerprint-drift, or over-limit data yields no islands and an
explicit service error. There are no built-in boundary dictionaries and no
permissive Node fallback.

The canonical extraction implementation lives with the authored LSP server as
a tooling/source-coordinate adapter. The top-level compatibility import
delegates to it and contains no algorithm or binding bootstrap. The historical
binding module is not a canonical LSP source and is no longer reachable from
the server or its acceptance tests; changing that binding's independent public
compatibility status is outside this internal editor task. The Node fixture
consumer reads the same governed registry and fails rather than broadening its
match when the registry is unavailable.

## Literal and source-mapping policy

An accepted island is always a regex-compatible STRling source document with
authored content and explicit derived host provenance. The virtual content is
bounded and maps monotonically to one exact host literal content range. Every
virtual line start and Unicode scalar boundary maps to a host position; inverse
mapping is defined only inside that range. Projection into UTF-8, UTF-16, or
UTF-32 happens after this host-scalar mapping.

P16-T04 accepts only declared literal forms for which the registry and scanner
can prove that the virtual text presented to STRling is the host string value
without guessing. Plain quoted forms are accepted only when their content has
no processed escape or interpolation marker. Declared raw forms may preserve
backslashes when the host form makes them literal and its delimiter/newline
rules are exact. Multiline forms are accepted only when every physical newline
and first-line rule has a one-to-one mapping.

The adapter refuses processed escapes, interpolation, concatenation,
expressions, heredocs or forms not declared by the registry, invalid encodings,
delimiter ambiguity, unterminated strings/comments, CR transformations,
language-specific initial-newline elision, and any construct whose runtime
string cannot be proven from the bounded scanner. Refusal is an intentional
source-safety correction, not a claim that the host language or STRling source
is invalid.

The scanner remains deliberately lexical and bounded. It skips only registry-
declared comment and literal regions and recognizes only registry-declared
boundary/literal pairs. It is not a general host parser, name resolver, macro
expander, type checker, or binding API validator. Boundary spellings indicate
editor extraction candidates, not proof that a host call resolves to STRling at
runtime.

## Resource, determinism, and task boundaries

Extraction shares the 1 MiB document, 256-island, and five-second document
budgets already enforced by the LSP. Registry counts, boundary-expression
length, delimiter length, raw-delimiter length, comment nesting, literal scan,
and mapping entries receive explicit finite ceilings. A limit breach fails the
document operation without returning partial semantic evidence. Islands are
ordered by host start and boundary registry order; overlapping candidates are
refused rather than selected by accident.

This task does not change Semantic STRling, regex-compatible, Semantic IR,
diagnostic, rewrite, target, runtime, stdlib, Simply, binding, or package
semantics. It does not certify a generic host parser, decode arbitrary host
escapes, add Semantic STRling host islands, introduce target inference, edit
generated `dist/**`, or package the kernel/editor executable and registry in the
VSIX. P16-T05 owns assembly and distribution.

## Verification and rollback

CP2 freezes a closed manifest for action proof identity and refusal, canonical
formatting, all registry hosts/boundaries/literal forms, Unicode and multiline
coordinate algebra, escape/interpolation/ambiguity refusal, malformed registry
mutations, lifecycle invalidation, limits, and Node-consumer fail-closed
behavior. Its counts and fingerprint are acceptance evidence, not an
implementation claim.

The closed denominator contains 108 uniquely named cases: 18 action
authorization/refusal cases, six formatter cases, 36 literal forms, 18 island
refusal sources, eight source-mapping cases, 14 registry mutations, and eight
lifecycle/service cases. Eighteen route contracts cover native `.strl` plus 17
hosts, 35 normalized suffixes, and 47 boundary spellings. The manifest pins the
Semantic language, certified rewrite registry, source contract, and diagnostic
contract; its canonical fingerprint is
`sha256:42869a311689fc057d07614156c66da78c6efe2c794f43ef352052f075d9f554`.
Six integrity tests enforce exact counts and unique IDs, catalog fingerprints,
the sole optional-action identity and four proof conditions, every literal
form's identity-only mapping policy, the closed refusal/mutation/lifecycle
dimensions, resource ceilings, and shrinkage detection.

CP3 implements only enough Rust evidence, Python LSP adaptation, registry
validation, extraction, and consumer changes to pass that denominator. CP4
runs the complete LSP, Rust, tooling, public/generated, migration differential,
architecture, static-analysis, formatting, governance, and Local/Pull
Request/Full profile checks with exact environment limitations recorded.

The CP3 implementation retains the `1.0.0` editor evidence contract and bumps
only the editor projection to `1.1.0`. Its governed island registry fingerprint
is `sha256:f263465d9a49eb76aed8205d7fe72bec59cee2e7e7886651af4e8a60f82344c2`.
The complete authored LSP suite passes 544 tests; the focused Rust editor and
Semantic frontend suites pass 17 tests; the closed island suite passes 84
tests; schema, Node syntax, architecture, static-analysis suppression,
governance, formatting, and diff checks pass. Pytest cache writes remain an
inherited managed-workspace limitation and do not change test results.

Rollback is the complete P16-T04 diff back to
`ee831b1f6c027c37b06da0d7cf571996325e8da8`. Rollback does not restore the
non-canonical diagnostic alias as authority, modify T02/T03 canonical editor
features, or discard later unrelated commits.
