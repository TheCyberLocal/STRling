# Canonical LSP completion, navigation, and semantic-token rebase

## Outcome and authority

P16-T03 replaces the remaining completion, structural-navigation, and
semantic-token dependencies on `STRling.core.intelligence` with editor evidence
derived by the canonical Rust frontends, Semantic IR identities and origins,
and governed Semantic STRling, Simply, and standard-library catalogs. The LSP
remains a presentation adapter. It cannot recognize STRling syntax, invent a
capture scope, assign semantic identity, or treat a generated compatibility
registry as language authority.

The normative inputs are the Semantic STRling 1.0 grammar and language
catalog, the regex-compatible frontend 1.0 contract, Semantic IR and source
contracts, Simply 1.1 protocol, and canonical stdlib registry 1.0. The Rust
frontend implementations consume those authorities; they do not replace them.
The editor projection added by this task is non-normative implementation data
and cannot create language, target, runtime, binding, or package semantics.

The clean starting and rollback boundary is
`fadcc60f2e8b4fcd9f3c70d83aa0117f0ba8f7a1` on `architecture/v4`, the
P16-T02 closure. P16-T03 reuses T02's immutable document snapshots, canonical
source identity, UTF-8/UTF-16/UTF-32 position projection, bounded subprocess
handling, cancellation, cache identity, stale-result rejection, close cleanup,
and service-failure isolation.

## Starting-state inventory

The authored server still imports four relevant functions from the Python
binding through `server/deferred_intelligence.py`:
`get_completion_items`, `tokenize_pattern`, `extract_document_symbols`, and
`find_registry_definition`. The same deferred module also contains the
formatter function, which is not owned by this task.

Current completion is not contextual. A `.` trigger inside any cached island
returns every entry from the generated `spec/stdlib/registry.json` projection.
It does not inspect the frontend, parse state, cursor prefix, replacement
range, capture scope, Simply operation, target/profile option, or semantic
possibility. A host expression such as `s.` is normally outside an island and
therefore receives no items despite the handler's member-access description.

Semantic tokens come from a hand-written character scanner in the Python
binding. The scanner independently recognizes regex punctuation, group names,
backreferences, escapes, quantifiers, anchors, and comments. It does not reuse
either canonical frontend parser, the current canonical result, source
identity, negotiated position encoding, snapshot version, cancellation, or
stale-result checks.

Document symbols come from another raw-text Python scanner. It reparses group
headers and nesting, fabricates alternation-branch names from source substrings,
tolerates unbalanced input independently of canonical diagnostics, and has no
canonical node or capture identity. Definition extracts a word at the cursor
and performs keyword-alias lookup in the generated compatibility registry. It
does not resolve capture declarations/backreferences or expose references.

The existing owned tests cover five pure scanner examples, three registry
lookups, two document-symbol handlers, and three definition handlers. They do
not freeze completion handlers, completion context or ranking, token legend or
wire ranges, capture definition/reference identity, formatter round trips,
Unicode/multiline token projection, version invalidation, cancellation, or
resource bounds.

## Canonical editor-evidence boundary

The Rust kernel gains one internal editor-evidence projection and a bounded
source-tree executable dedicated to that projection. It reuses the exact
Semantic STRling and regex-compatible frontend token/syntax implementations;
it does not introduce a third parser. The serialized transport is an internal
versioned implementation contract for the LSP and its tests, not a new
normative or public compiler contract. P16-T05 owns deciding how that executable
and its metadata are assembled and distributed in the VSIX.

For one exact source, explicit frontend, and optional cursor byte offset, the
projection may return:

-   frontend-owned lexical tokens with half-open UTF-8 byte spans;
-   successful syntax/Semantic IR node and capture identities with exact origins;
-   hierarchical document symbols whose identities and ranges come from that
    syntax and Semantic IR;
-   capture declaration/reference links using canonical `capture_id` values; and
-   parser-context completion candidates and one exact replacement span.

Completion expectation recording is part of the existing Rust parser control
flow. It may expose terminals the parser can legally consume at the cursor and
completed capture names already available to a reference. It may not duplicate
the grammar as an LSP-side state machine. The implementation catalog of
Semantic STRling keywords is cross-checked exactly against
`language.json`; Simply operations and option values come from protocol 1.1;
helper identities, parameters, descriptions, examples, and binding spellings
come from the canonical stdlib registry, never the generated LSP projection.

Malformed or incomplete text may retain bounded lexical tokens and parser
expectations up to the canonical failure point. It cannot produce a resolved
symbol, definition, reference, or semantic identity that the frontend did not
establish. Service absence, malformed transport, timeout, stale source, or
resource exhaustion returns no editor result and is logged separately; it is
never converted into a completion, token, or navigation guess.

## Completion contract

Completion uses the exact current snapshot and maps the negotiated LSP cursor
to a canonical UTF-8 byte offset before requesting evidence. The replacement
range is the frontend-owned current token or zero-width insertion point. Items
outside that range are never rewritten.

Semantic STRling candidates are limited to parser-expected terminals,
context-valid catalog values, and completed capture names when the grammar
expects a reference identifier. Regex-compatible candidates are limited to
frontend-declared directives, flags, escapes, and already resolvable capture
references where the canonical frontend can prove the context. A raw regex
island does not receive stdlib helper names because helper identifiers are not
regex syntax.

Simply and stdlib candidates are exposed only through an already-recognized
host builder/member boundary retained by the existing compatibility adapter.
This task may map the recognized binding spelling to canonical Simply
operation/helper metadata, but it cannot add or broaden host-language island or
call extraction; P16-T04 owns that grammar. Target/profile candidates are
offered only in an explicit configuration or protocol field whose catalog is
already governed. Filename or installed-engine inference is forbidden.

Ranking is deterministic:

1. exact parser-expected fixed terminals;
2. in-scope canonical capture identities;
3. canonical Simply operations and stdlib helpers valid at the recognized
   boundary;
4. explicit governed option/profile values.

Within a tier, items sort by stable canonical identity and label. Prefix
filtering is case-sensitive for Semantic STRling syntax and follows the
declared binding spelling for host helpers. Every item carries a stable data
identity, detail/source authority, plain text or explicitly tested snippet,
and exact replacement edit. The response is complete and capped at 256 items.

## Navigation and symbol contract

Document symbols come only from successfully resolved canonical syntax and
Semantic IR. They retain canonical node/capture identities as data, use exact
current-source ranges, and form their hierarchy from real child relationships.
The adapter does not invent alternation labels, close unfinished groups, or
name source substrings. An incomplete document may therefore have fewer or no
symbols rather than a speculative tree.

Definition on a backreference resolves by canonical `capture_id` to its current
declaration. References resolve every current-source declaration/reference
node sharing that identity and honor the LSP `includeDeclaration` flag.
Unknown, duplicate, forward, failed, stale, or source-less identities return no
location. Locations never survive an edit solely because byte offsets happen
to match; the current source identity and snapshot must match.

Stdlib definition resolves a canonical helper identity to the authored
`spec/stdlib/registry/1.0/registry.json` declaration. Generated compatibility
aliases may be accepted only after their canonical binding-spelling metadata
resolves one unambiguous helper. Simply operation definition similarly points
to the authored protocol declaration. Arbitrary word-under-cursor lookup and
trigger-keyword aliases are retired.

Formatter stability is proven with the canonical Semantic STRling formatter:
parse-format-parse must preserve semantic alpha equivalence and deterministic
node/capture relationships. Source hashes and byte ranges are expected to
change after formatting; navigation recomputes against the new canonical
source identity rather than pretending identity means offset stability.

## Semantic-token contract

The existing client-visible legend order remains stable for compatibility:

1. `string`
2. `number`
3. `operator`
4. `regexp`
5. `keyword`
6. `function`
7. `variable`
8. `comment`

There are no token modifiers in this task. Token classes and UTF-8 spans come
from the exact frontend lexer/syntax projection. Capture declarations use
`function`; resolved references use `variable`; Semantic STRling terminals and
directives use `keyword`; strings and numeric bounds use their corresponding
classes; regex-compatible constructs use frontend-owned operator/regexp
classes; comments use `comment`.

The LSP adapter validates, sorts, and projects tokens into the negotiated
position encoding, splits multiline evidence into legal per-line tokens, and
delta-encodes a non-overlapping stream. Host-island tokens use the existing
virtual-to-host coordinate mirror without changing extraction. Tokens are
bounded at 16,384 per document; symbols at 4,096; capture locations at 16,384;
and all editor responses share T02's 1 MiB source, 256-island, and five-second
document budgets.

Only full semantic-token responses are supported in P16-T03. The server does
not advertise delta responses until a separately tested result identity and
edit protocol exist.

## Lifecycle, compatibility, and task boundary

Completion, definition, references, symbols, and semantic tokens read the same
immutable snapshot as diagnostics and hover. A request for a version, content,
frontend, encoding, target profile, or generation other than the current one
returns no result. In-flight editor projection is cancellable; late completion
is discarded. Cache keys include canonical source identity, explicit frontend,
projection version, and cursor offset where applicable. Caching cannot change
candidate order or reuse locations across source identities.

P16-T03 intentionally changes legacy results where they contradict canonical
evidence: global registry completions disappear from regex text; speculative
symbols disappear on unresolved syntax; generated-registry keyword aliases no
longer navigate; tokens follow frontend syntax and negotiated encoding; and
capture navigation is added only for resolved identities.

This task does not:

-   change Semantic STRling, regex-compatible, Semantic IR, Simply, stdlib,
    diagnostic, target, or runtime semantics;
-   modify a normative specification, generated stdlib projection, or binding
    API;
-   redesign document formatting or retain the Python formatter as accepted
    evidence;
-   add or rebase code actions;
-   add, broaden, or certify embedded-language/island extraction;
-   edit generated `tooling/lsp-server/dist/**`; or
-   package or distribute the editor executable, bridge modules, metadata, or
    kernel in the VSIX.

## Verification and rollback

CP2 freezes parser-context completion fixtures, canonical registry/Simply
catalog fingerprints, successful and malformed lexical cases, symbol and
capture identity graphs, definition/reference goldens, formatter
parse-format-parse properties, the token legend, UTF-8/16/32 and multiline
wire cases, host projection, lifecycle mutations, and resource limits before
implementation.

The closed CP2 denominator contains 65 uniquely named cases: 21 completion
contexts, 13 navigation/identity cases, eight semantic-token streams, three
formatter recomputation cases, three host-projection cases, and 17 lifecycle
and service mutations. Its canonical JSON fingerprint is
`sha256:b1d5be9de0b0a9e7664e3ea63e99960e0f810875c4291db213452dd956ec276f`.
The harness pins raw hashes for the regex dialect and grammar, Semantic
STRling language catalog, Simply 1.1 protocol, and canonical stdlib registry;
it also checks the stdlib registry's own declared fingerprint. Exact counts,
unique identifiers, catalog equality, byte-bound ranges, all eight token
classes, and an explicit evidence-shrink mutation make denominator loss or
authority drift fail closed. These are authored acceptance expectations, not
claims that the editor projection already exists.

CP3 adds the smallest Rust projection and Python adapter needed to pass that
evidence, removes the four replaced binding-intelligence imports, and proves
focused Rust/LSP/architecture behavior. CP4 runs the complete owned LSP suite,
canonical frontend/formatter tests, affected Rust all-target tests, public and
generated checks, migration differential, formatting/static analysis,
governance, and Local, Pull Request, and Full profiles as safely available.

Rollback is the complete P16-T03 diff back to
`fadcc60f2e8b4fcd9f3c70d83aa0117f0ba8f7a1`. It does not revert P16-T02's
canonical diagnostics/hover bridge or restore deprecated diagnostic aliases.
Closure records exact candidate sources and ranking, navigation identity rules,
token legend and range counts, removed duplicate logic, verification evidence,
environment limitations, final commit, and readiness for P16-T04.
