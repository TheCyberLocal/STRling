# Legacy TypeScript Reference Runner

## Authority and purpose

The legacy TypeScript reference runner is isolated migration tooling that answers
one question: what did the governed historical TypeScript implementation do for
this exact request?

**A legacy observation records historical implementation behavior. It does not
establish required STRling semantics.**

The authority relationship is one-way and intentionally disconnected:

```text
Normative Specification
        |
        v
Canonical Rust Kernel

Legacy TypeScript Runner
        |
        v
Historical Evidence Only
```

The runner cannot define, generate, or amend the normative specification,
canonical contracts, Semantic IR, target profiles, target capabilities,
portability decisions, compiler diagnostics, or Rust-kernel behavior. The Rust
kernel and published bindings cannot depend on the runner. Historical defects
are recorded without correction and do not create compatibility obligations.

## Legacy surface inventory

The governed implementation is `bindings/typescript`, built from its checked-in
TypeScript sources with the dependency graph locked by
`bindings/typescript/package-lock.json`.

| Concern                      | Existing legacy surface                                                                                              | Observable behavior                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parser                       | `src/STRling/core/parser.ts`: `parse`, `parseToArtifact`, and `ParseError`                                           | `[Flags, Node]`, the serializable artifact projection, accepted/rejected status, AST shape, flags, positions, source text, hints, and thrown errors                        |
| Compiler                     | `src/STRling/core/compiler.ts`: `Compiler.compile` and `Compiler.compileWithMetadata`                                | normalized legacy IR and the sorted `features_used` metadata projection                                                                                                    |
| Emitter                      | `src/STRling/emitters/pcre2.ts`: `emit` and `emitWithDiagnostics`                                                    | exact PCRE2 text, inline flags, warning objects, configured depth failures, and compilation errors                                                                         |
| Package root                 | `src/index.ts`: `parse`, `parseToArtifact`, `ParseError`, `Compiler`, and `simply`                                   | package-root return and failure shapes without changing the exported package surface                                                                                       |
| Simply API                   | `src/STRling/simply/pattern.ts`, `src/STRling/compiler.ts`: `lit`, `Pattern.toString`, `compileNode`, and `toRegExp` | literal-pattern construction, string conversion, target selection, flag handling, `RegExp` projection, and thrown API failures                                             |
| Diagnostics                  | `src/STRling/core/errors.ts` and `src/STRling/core/hint_engine.ts`                                                   | `STRlingParseError` message/position/text/hint/formatted form, `STRlingCompilationError` code/engine/message, and `STRlingWarning` code/message                            |
| Directives and preprocessing | parser `_parseDirectives` and cursor free-spacing handling                                                           | leading `%flags` for `i`, `m`, `s`, `u`, and `x`; leading blank/comment removal; extended-mode whitespace/comments; malformed, unknown, and late directives as implemented |
| Target and options           | PCRE2 emitter plus `compileNode`                                                                                     | the sole legacy target identifier `pcre2`, emitter `maxDepth`, and legacy string/object flag handling                                                                      |

The package manifest advertises package, `./core`, `./emitters/pcre2`, and
`./simply` entrypoints. Existing public-surface evidence records that the
subpath declarations do not match the declaration-build layout. The runner
loads freshly compiled governed modules by their actual build paths; it does not
repair or reinterpret the advertised package paths.

The TypeScript package uses `tsc` and Jest/`ts-jest`. Existing evidence
includes the TypeScript unit and end-to-end suites, `tests/spec`
implementation-derived fixtures, the focused pathological emitter corpus at
`tests/conformance/inputs/emitter_edges/pathological.json`, the migration donor
inventory, the compatibility-preservation matrix, public-surface snapshots, and
the older `tooling/js_to_json_ast` TypeScript-oracle generator. The older
generator remains transitional evidence and is not reused as a protocol or
authority.

## Observation operations

Protocol version `1.0.0` reserves these stable operation identifiers and exact
legacy call surfaces:

| Operation                             | Expected legacy surface                         |
| ------------------------------------- | ----------------------------------------------- |
| `parser.parse`                        | `typescript.core.parser.parse`                  |
| `parser.parse_to_artifact`            | `typescript.core.parser.parseToArtifact`        |
| `compiler.compile`                    | `typescript.core.Compiler.compile`              |
| `compiler.compile_with_metadata`      | `typescript.core.Compiler.compileWithMetadata`  |
| `emitter.pcre2.emit`                  | `typescript.emitters.pcre2.emit`                |
| `emitter.pcre2.emit_with_diagnostics` | `typescript.emitters.pcre2.emitWithDiagnostics` |
| `api.root.parse`                      | `typescript.package-root.parse`                 |
| `api.root.parse_to_artifact`          | `typescript.package-root.parseToArtifact`       |
| `api.simply.literal_to_string`        | `typescript.simply.Pattern.toString`            |
| `api.simply.compile_node`             | `typescript.simply.compileNode`                 |
| `api.simply.to_regexp`                | `typescript.simply.toRegExp`                    |

Source operations own a UTF-8 JavaScript string named `source`. Simply
operations own a literal string named `literal`; options own only the target,
flags, or emitter depth accepted by the selected legacy call. A request must
name the expected surface so accidental routing changes fail at the protocol
boundary.

The runner owns only the observation envelope, validation, stable projection,
identity, canonical serialization, and process containment. AST and IR
projections call the existing `toDict()` methods. Exact emitted strings and
legacy messages are retained. The projection may omit prototypes, functions,
symbols, and stack traces, but it cannot rename nodes, classify behavior, or
normalize a semantic difference.

## Contract and failure semantics

A request contains a protocol version, operation, operation-specific input,
operation-specific options, and expected legacy surface. An observation
contains an independently versioned schema and protocol, implementation and
request identities, the operation and surface, and exactly one outcome:
`success` evidence or `legacy_failure` evidence.

Malformed JSON, a malformed request, an unknown operation, a surface mismatch,
or inability to build/load the governed implementation is a runner/protocol
failure and produces a nonzero process exit. A parser, compiler, emitter, or API
exception produced while faithfully executing a valid request is a successful
capture with a `legacy_failure` outcome and does not by itself make the runner
process fail.

Failure evidence preserves the failing stage, error category/class/name,
message, and, when present, diagnostic code, engine, position, source text,
hint, and deterministic formatted diagnostic. Canonical observations omit
stacks because module URLs and frames are execution details rather than stable
semantic evidence.

## Deterministic identity and serialization

The legacy implementation identity is a SHA-256 Merkle-style fingerprint over
an ordered manifest containing:

-   every tracked `bindings/typescript/src/**/*.ts` implementation input;
-   `bindings/typescript/package.json` and its exact lock file;
-   `bindings/typescript/tsconfig.json`; and
-   the actual Node runtime version executing the compiled implementation.

Each repository file contributes its repository-relative POSIX path, byte
length, and SHA-256 digest. The aggregate uses canonical JSON for the ordered
manifest. It contains no repository commit, timestamp, absolute path, working
tree status, or temporary build location. Thus unrelated repository changes do
not alter identity, while a relevant source, build contract, resolved
dependency, or runtime change does.

Request identity is SHA-256 over the validated canonical request. Canonical JSON
uses UTF-8, lexicographically ordered object keys at every depth, preserved array
order, JSON number/string/boolean/null representations, no insignificant
whitespace, and one trailing LF in command output. Non-finite numbers,
`undefined`, functions, symbols, timestamps, durations, process IDs, absolute
paths, temporary directories, and stack traces are excluded. Potentially
meaningful source, AST, IR, flags, output text, warning order, error messages,
positions, and codes are not normalized.

Observation schema, request protocol, legacy implementation identity, canonical
compiler contract, and any future comparison schema evolve independently. A
breaking request or observation change requires a new protocol/schema version;
a legacy implementation change changes only its implementation fingerprint.

## Evidence lifecycle and later comparison

The focused reference corpus is source-authored migration input, not a semantic
conformance corpus. Canonical observations are intentionally ephemeral: their
value is tied to an explicit implementation fingerprint, and the repository's
generated-artifact registry has no existing authority class for committing
legacy-oracle outputs. Certification regenerates observations repeatedly,
compares canonical bytes, reports fingerprints and counts, and verifies that
fixtures and production sources remain unchanged.

A later comparison system may consume observations and apply its own separately
versioned normalization and discrepancy taxonomy. This runner never labels a
legacy outcome correct, incorrect, equivalent, preserved, intentionally
corrected, or unsupported by the canonical compiler.
