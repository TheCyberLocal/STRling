# Semantic STRling Rust parser and canonical formatter

## Outcome and authority

P13-T05 implements the ratified `strling.semantic@1.0.0` source contract as one
pure Rust frontend. The versioned files under
`spec/frontends/semantic/1.0/` remain the grammar, mapping, diagnostic, and
formatting authority. The implementation consumes those inputs; it cannot
rewrite them, derive new authority from its output, infer a target, or duplicate
normalization, analysis, portability, lowering, serialization, or runtime
behavior.

The parser and formatter live in `core/src/semantic_frontend.rs`. They have no
third-party parser dependency and no filesystem, environment, network, binding,
legacy-runtime, target, emitter, package, CLI, or editor dependency. The kernel
adds only explicit `SourceDocument.frontend.id == "strling.semantic"` dispatch
to the same canonical compiler pipeline already used by Semantic IR and the
regex-compatible frontend.

## Locked Rust API

The frontend surface is:

```text
strling_kernel::semantic_frontend::parse(
    &SourceDocument,
) -> Result<ParsedSemantic, SemanticFrontendFailure>

strling_kernel::semantic_frontend::format(
    &ParsedSemantic,
) -> String
```

`ParsedSemantic` exposes the validated canonical `SemanticProgram` and retains
private structured syntax evidence for formatting. The private evidence is
necessary because canonical normalization intentionally sorts/deduplicates set
members, coalesces text, flattens composition, and omits comments. Formatting
from Semantic IR alone would therefore violate the ratified authored-order and
comment-preservation rules.

`SemanticFrontendFailure` separates a stable frontend diagnostic from invalid
`SourceDocument`, unresolved referenced content, and an internal invalid-
semantic-output boundary. `SemanticFrontendErrorCode` covers all 27 frozen
`STRL-DSL-*` identities. Codes 1001-1013 and 3001-3005 use `frontend_parse`;
codes 2001-2009 use `semantic_lowering`. All carry canonical severity, category,
the exact document provenance, and one half-open UTF-8 primary location.

## Streaming parser and first-error rule

The lexer is demand-driven rather than a whole-file prepass. It skips governed
layout, records comments and physical line endings, decodes the closed string
escape set, and reports an error only when the parser reaches that byte. This
preserves the contract's earliest-byte selection: a later lexical defect cannot
mask an earlier structural failure. At one byte, lexical validity wins before
structure and reference/lowering validity.

Tokens retain start/end byte positions and whether required layout preceded
them. The recursive-descent parser follows the 55-production EBNF directly and
has no precedence table, implicit concatenation, transparent groups, or raw-
regex fallback. Unsupported target, module/import, policy, regex, and numeric-
reference forms route to their explicit 300x identities rather than generic
syntax errors.

The parsed syntax tree retains:

-   the required case declaration and one root;
-   authored node and set-member order;
-   decoded strings plus their original token spans;
-   every material construct's first-keyword-through-delimiter span;
-   capture/reference identifier spans; and
-   comments in exact source order for canonical placement.

## Semantic lowering and identities

Lowering allocates material nodes in one-based source preorder as
`node:semantic/n1`, `node:semantic/n2`, and so on. Capture declarations allocate
an independent one-based declaration preorder as `capture:semantic/c1`,
`capture:semantic/c2`, and so on. Each material node receives one source origin
over the exact input document.

A completed-capture table distinguishes unresolved references from forward,
self, and recursive references. Duplicate names reject at the second
declaration. Empty text, scalar cardinality, range order, repeat bounds,
composition arity, and empty sets reject through the frozen semantic-lowering
diagnostics before any partial program enters the compiler.

The resulting pre-normal Semantic IR candidate is passed to the existing
`normalization::normalize`. That sole canonical operation flattens nested
sequence/choice nodes, coalesces adjacent text, canonicalizes set members, and
retains removed identities/origins as derivation evidence. The frontend then
returns the validated canonical program; it owns no competing normalization.

## Resource and robustness boundary

The parser enforces the ratified limits exactly:

| Resource             |            Limit |
| -------------------- | ---------------: |
| UTF-8 source         |  1,048,576 bytes |
| Syntactic nesting    | 128 block levels |
| Material nodes       |           65,535 |
| Capture declarations |           16,384 |
| Set members per set  |           65,535 |
| Identifier           |   64 UTF-8 bytes |
| Integer              |    4,294,967,295 |

The first excess item returns `STRL-DSL-1013`; integer and identifier lexical
limits retain their dedicated 1012/1007 identities. Recursion never exceeds the
governed nesting limit. Deterministic mutation/property tests wrap parsing and
formatting in panic capture across arbitrary Unicode and malformed byte-shaped
Rust strings; no accepted or rejected input may panic.

## Canonical formatting

Formatting is a pure traversal of validated syntax evidence. It emits UTF-8,
LF endings, one final LF, four-space indentation, lowercase keywords, shortest
integers, canonical escapes, opening braces on introducing lines, and closing
braces at the owner indentation. It preserves capture names and authored set
member order.

Comments retain source order, normalize one space after `#` for nonempty text,
and align with the following construct; comments with no following construct
align with the enclosing closing brace or end of file. Blank-line runs collapse
and the required header/case/blank-line/pattern layout is always emitted.

`format` is deterministic and idempotent. Parsing formatted output must preserve
alpha-equivalent canonical semantics, every material capture name, and the same
preorder identity sequence. Only source content and spans may change.

## Verification evidence

Focused Rust tests consume, but never regenerate, all 12 positive and 30
negative specification-authored fixtures. All pass with exact diagnostic code,
phase, category, UTF-8 byte offset and location, material source spans,
identities, comments, Unicode/escape behavior, EOF and reserved/version cases,
and deterministic output.

Separate property tests certify parse-format-parse, format-format, 512 generated
valid programs, exact boundaries for all seven resource families, and 2,048
deterministic arbitrary UTF-8 inputs under panic capture. Nested comment cases
prove following-construct and enclosing-closure alignment remains idempotent.

Kernel orchestration tests prove successful Semantic STRling source traverses
the existing semantic and analysis pipeline and failed source produces one
canonical diagnostic with no partial semantics. Unresolved referenced content
retains the existing protocol failure. Architecture mutations reject
target/emitter/binding/host-I/O dependencies, missing source/Semantic IR
mappings, duplicate parser ownership, and loss of parser, formatter,
normalization, diagnostic, or provenance boundaries.

Exact Rust 1.75.0 formatting, warning-denied Clippy/check, all Rust targets,
canonical contract mapping, public/generated contract integrity, and repository
hygiene pass. Aggregate repository, Local, Pull Request, reproducibility, and
clean-tree closure remain the final certification steps.

Closure requires exact Rust 1.75.0 formatting, warning-denied check and Clippy,
all-target tests, canonical/public/generated contracts, governance,
documentation, repository formatting/lint/hygiene, Local, Pull Request, and a
clean tracked tree. Tutorials, frontend defaults, bindings, package adapters,
and release behavior remain P13-T06 or later work.
