# Regex parser provenance and canonical diagnostics

P08-T03 completes the evidence path inside the frozen `strling.regex-compat@1.0.0` parser. It does not add a binding, CLI command, package API, editor route, import adapter, or frontend-selection surface; those remain P08-T04 work.

## Implemented boundary

- Every accepted syntax node lowers with a `SourceOrigin` containing sorted, unique, non-overlapping half-open UTF-8 byte spans tied to the input `SourceDocument`.
- Container nodes cover their complete source construct, including delimiters and quantifiers. Decoded escapes retain the source range of the escape rather than the range of the decoded scalar.
- Adjacent literals separated by extended-mode whitespace or comments merge semantically while retaining discontiguous source spans. This prevents ignored layout from being claimed as literal provenance.
- The optional `%flags` directive retains its own `SourceSpan`; the embedded source document preserves frontend identity, exact inline content, and imported or derived provenance.
- Normalization preserves the embedded source document and canonicalizes node origins without discarding precise spans.
- All 45 frozen parser error identities project to canonical `Diagnostic` values with stable `STRL-FRONTEND-*` codes, frozen messages, error severity, normative basis, `frontend-parse` phase, deterministic category, primary source span, and document provenance.
- Duplicate flag and named-capture declarations include deterministic related locations for the first declaration. EOF failures use a valid zero-width span at the final UTF-8 boundary.

## Validation rules

`SourceSpan` continues to reject reversed, out-of-range, and non-UTF-8-boundary endpoints. `SourceOrigin` additionally rejects overlapping spans from the same source. Semantic validation rejects origins that reference a source not embedded in the program and validates every inline span against the exact embedded text.

The parser keeps three non-syntax failure boundaries explicit:

- An invalid `SourceDocument` returns its canonical `ValidationErrors`.
- A referenced source must be resolved to inline content by orchestration before parsing.
- Invalid lowered Semantic IR returns canonical semantic validation errors as an internal invariant failure.

This separation avoids inventing frontend diagnostic codes for source-contract, orchestration, or internal invariant failures.

## Specification-authored evidence

`spec/frontends/legacy-regex/1.0/provenance/cases.json` freezes multibyte, escaped-scalar, nested, multiline, extended-layout, empty-input, EOF, and related-location behavior. The Rust contract suite consumes the file directly and verifies the same spans after normalization.

## Verification

The implementation checkpoint passed the focused gates:

- `cargo test --manifest-path core/Cargo.toml --test regex_frontend --locked`: 10 passed.
- `cargo test --manifest-path core/Cargo.toml --test source_semantic_contracts --locked`: 11 passed.
- `python3 -m unittest tooling.tests.test_regex_frontend_architecture tooling.tests.test_core_contracts`: 20 passed.
- `cargo fmt --manifest-path core/Cargo.toml --all -- --check`: passed.
- `git diff --check`: passed.

Migration differential, governed baseline renewal, full Rust validation, repository governance/documentation/formatting, and local/pull-request profile evidence are recorded at the certification checkpoint.
