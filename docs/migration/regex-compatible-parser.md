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

The blocking `./strling migration-differential` command executes that focused
Rust correspondence test before launching either historical runner. A missing
Rust toolchain, failed canonical case, or nonzero test process therefore blocks
the same differential gate that owns the route review and baseline.

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

Native Linux migration-differential certification passes across all 44 source
observations and three repeated runs with zero determinism mismatches and zero
blocking replacement discrepancies. The gate executes the focused canonical
Rust parser route before both historical runners. The renewed checked baseline
is
`sha256:e52a2b48c01b214cf74a9aee967a55817637b11f5c68666a14a59799227dd845`;
the certified result is
`sha256:e8d610c1fd0ddac973507774f2a98f2a69be62504ec4b94ea8fec9d5ce77e01e`.
The historical peer result remains the P07-certified
`sha256:06a2e2d095f89ba2fdfb13ffc950e1290b920d558605ab176bd4d08887dfba97`.

The local and pull-request profiles execute the renewed differential and every
P08-T02 operation successfully. Their aggregate status retains one pre-existing
repository-lint failure in earlier migration/reference files outside this
task's diff. Pull-request certification additionally records the existing Ruby
Bundler mismatch and unavailable Swift executable. No profile policy, baseline,
or finding was weakened or reported as passing. P08-T02 is therefore `READY
WITH RECORDED CARRY-FORWARD`; P08-T03 owns canonical provenance, source spans,
and diagnostic integration.
