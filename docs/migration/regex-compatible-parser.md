# Canonical regex-compatible parser

## Outcome and authority

The canonical Rust kernel now implements the frozen
`strling.regex-compat@1.0.0` compatibility/import frontend. The parser consumes
one validated, resolved `SourceDocument` and lowers accepted source directly to
target-neutral Semantic IR. The versioned contract under
`spec/frontends/legacy-regex/1.0` remains the syntax authority; historical
TypeScript and Python parsers remain comparison evidence.

This task does not add a CLI, package, binding, editor, import, target, or
artifact-emission surface. It does not infer a target, run a legacy parser, or
introduce a second compiler. P08-T03 continues to own canonical source spans,
provenance, and diagnostic presentation beyond the minimum frontend error
identity and UTF-8 byte offset.

## Canonical API and lowering boundary

The kernel surface is:

```text
strling_kernel::regex_frontend::parse(
    &SourceDocument,
) -> Result<ParsedRegex, RegexFrontendFailure>
```

`parse` validates the source contract, requires frontend identity
`strling.regex-compat` and dialect version `1.0.0`, and requires inline UTF-8
content that has already been resolved. Success returns normalized frontend
flags and a `SemanticProgram`. The frontend calls canonical Semantic IR
validation before returning, so invalid lowered output cannot cross the parser
boundary.

The five global flags lower without target knowledge:

-   `i` selects case-insensitive Semantic IR matching;
-   `m` selects line-relative rather than input-relative anchors;
-   `s` includes line terminators in wildcard matching;
-   `u` selects Unicode shorthand-class domains; and
-   `x` affects frontend layout and comments only.

All accepted syntax lowers structurally. The module has no dependency on target
profiles, emitters, portability planning, bindings, environment variables,
filesystem or network access, command-line behavior, or TypeScript/Python
runtimes.

## Determinism and resource limits

The parser returns the first diagnostic in source order with the exact stable
frontend identity and UTF-8 byte offset frozen in P08-T01. Successful output is
deterministic for identical `SourceDocument` input. The frozen limits are:

| Resource          |           Limit |
| ----------------- | --------------: |
| UTF-8 source size | 1,048,576 bytes |
| Syntactic nesting |      128 levels |
| Capture groups    |          65,535 |
| Quantifier bound  |   4,294,967,295 |

Limit failures are ordinary typed frontend failures rather than panics.
Referenced source content is rejected until canonical orchestration resolves it
to inline content.

## Coverage and historical evidence

Focused Rust tests execute all 30 positive specification-authored fixtures and
all 45 negative fixtures. They assert deterministic successful output, exact
diagnostic identities and byte offsets, flag-to-Semantic-IR mapping, source,
nesting, and capture limits, and no panic across 2,048 deterministic generated
UTF-8 inputs.

A specification-authored correspondence set covers literals, escape/classes,
grouped alternation and lookaround, extended directives, and malformed groups.
The Rust suite executes those five cases from specification authority. A
separate migration-layer test proves that both governed runner corpora contain
exactly the same case identities, sources, and accepted/rejected statuses. The
kernel therefore receives no dependency on historical evidence while its
results cover the complete governed parser corpus.

The differential route review for `parser.parse` is now
`canonical-route-parser-parse@2.0.0`. Its canonical surface is the Rust API
above. Structural output comparison remains intentionally `not_comparable`
with reason `incompatible_surface`: the historical operation returns a
binding-specific AST while the canonical authority returns validated Semantic
IR. `parser.parse_to_artifact` remains `operation_not_exposed`; public artifact
orchestration belongs to later P08 work.

## Verification and certification state

The implementation passes the complete Rust 1.75.0 kernel test suite, focused
fixture and corpus tests, `cargo fmt --check`, warning-denying `cargo check`,
and warning-denying Clippy. Canonical contract mapping and five mutation-aware
parser architecture and correspondence tests also pass.

Native Linux migration-differential certification and checked-baseline renewal
remain pending because the host WSL service cannot create a session
(`Wsl/Service/0x80072747`). An isolated Windows replay preserved the historical
corpus fingerprint but produced a different historical result fingerprint, so
that host-specific observation is deliberately not promoted as the Linux
baseline. The implementation checkpoint is complete; P08-T02 is not ready to
close until the native differential, governed baseline update, aggregate
profiles, and clean-checkout certification pass.
