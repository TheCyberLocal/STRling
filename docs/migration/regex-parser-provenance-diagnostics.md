# Regex parser provenance and canonical diagnostics

P08-T03 completes the evidence path inside the frozen `strling.regex-compat@1.0.0` parser. It does not add a binding, CLI command, package API, editor route, import adapter, or frontend-selection surface; those remain P08-T04 work.

## Implemented boundary

-   Every accepted syntax node lowers with a `SourceOrigin` containing sorted, unique, non-overlapping half-open UTF-8 byte spans tied to the input `SourceDocument`.
-   Container nodes cover their complete source construct, including delimiters and quantifiers. Decoded escapes retain the source range of the escape rather than the range of the decoded scalar.
-   Adjacent literals separated by extended-mode whitespace or comments merge semantically while retaining discontiguous source spans. This prevents ignored layout from being claimed as literal provenance.
-   The optional `%flags` directive retains its own `SourceSpan`; the embedded source document preserves frontend identity, exact inline content, and imported or derived provenance.
-   Normalization preserves the embedded source document, retains discontiguous precise spans, and unions only overlapping spans from the same source so normalized output satisfies the origin invariant.
-   All 45 frozen parser error identities project to canonical `Diagnostic` values with stable `STRL-FRONTEND-*` codes, frozen messages, error severity, normative basis, `frontend-parse` phase, deterministic category, primary source span, and document provenance.
-   Duplicate flag and named-capture declarations include deterministic related locations for the first declaration. EOF failures use a valid zero-width span at the final UTF-8 boundary.

## Validation rules

`SourceSpan` continues to reject reversed, out-of-range, and non-UTF-8-boundary endpoints. `SourceOrigin` additionally rejects overlapping spans from the same source. Semantic validation rejects origins that reference a source not embedded in the program and validates every inline span against the exact embedded text.

The parser keeps three non-syntax failure boundaries explicit:

-   An invalid `SourceDocument` returns its canonical `ValidationErrors`.
-   A referenced source must be resolved to inline content by orchestration before parsing.
-   Invalid lowered Semantic IR returns canonical semantic validation errors as an internal invariant failure.

This separation avoids inventing frontend diagnostic codes for source-contract, orchestration, or internal invariant failures.

## Specification-authored evidence

`spec/frontends/legacy-regex/1.0/provenance/cases.json` freezes multibyte, escaped-scalar, nested, multiline, extended-layout, empty-input, EOF, and related-location behavior. The Rust contract suite consumes the file directly and verifies the same spans after normalization.

## Verification

The implementation checkpoint passed the focused gates:

-   `cargo test --manifest-path core/Cargo.toml --test regex_frontend --locked`: 10 passed.
-   `cargo test --manifest-path core/Cargo.toml --test normalization --locked`: 11 passed.
-   `cargo test --manifest-path core/Cargo.toml --test source_semantic_contracts --locked`: 11 passed.
-   `python3 -m unittest tooling.tests.test_regex_frontend_architecture tooling.tests.test_core_contracts`: 20 passed.
-   `cargo fmt --manifest-path core/Cargo.toml --all -- --check`: passed.
-   `git diff --check`: passed.

Certification then passed all 237 canonical-core tests under rustc/cargo 1.75.0, warnings-denied Clippy, core contract validation, public-contract reproduction, generated-artifact verification, governance, documentation integrity, pinned Prettier 3.3.3/Ruff 0.15.21 formatting, and whitespace validation.

The three-run migration differential covers 44 observations with zero mismatches and zero blocking unresolved replacements. Its final evidence is:

-   Baseline: `sha256:f21d86ac5c2028adb7dfdeb2004300a5d86e478101d8cea08ccbdc26578add7f`.
-   Result: `sha256:6180b35ab9ff211a07e907d7907527b6c4d11195457d9fd1e8d3eccb32f5fcd0`.
-   Canonical boundary: `sha256:b34af79220c8a5f17721d38d32e20bd88fe2ce8daef880ed9f8999b0a399ebbc`.
-   Full corpus: `sha256:823a6b0806553ed08fe7c367c6510d80235079383632a11a9857c48d951ad2cb`.
-   Route coverage: `sha256:c6d41f9483e1235ab44e2f2b0e9322a8cb56b69c3ca13aff43de102c313048ae`.
-   Historical peer result, unchanged: `sha256:06a2e2d095f89ba2fdfb13ffc950e1290b920d558605ab176bd4d08887dfba97`.

The structured local profile records 25 passed operations and one pre-existing repository-lint failure with evidence fingerprint `0e0f6019c733b51576919319a9235ca00b0dc765a9bd0c984030a196a0d4a0bf`. The pull-request profile records 43 passed, the same lint failure, and two unavailable operations for the existing Bundler 2.7.2 versus 2.4.20 mismatch and missing Swift executable; its evidence fingerprint is `a3eef39ce900a1c4d145a8c3d42cb17cae5fb2c2c0255c70b41d5fb9d72b7f0a`. A direct all-target legacy Rust binding run also retains six existing E2E failures in lookaround and validation cases; `bindings/rust/**` is unchanged from the task base. No carry-forward finding is waived or reported as passing.
