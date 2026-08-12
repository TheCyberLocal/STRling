# Regex frontend orchestration and canonical JSON CLI

P08-T04 exposes the frozen `strling.regex-compat@1.0.0` compatibility/import
frontend through the canonical `CompileRequest` boundary and the repository
root JSON CLI. This is an additive compatibility surface, not a flagship
language launch, binding migration, target emitter, package publication, or
release action.

## Canonical boundary

`strling_kernel::compile` now handles `CompileInput::Source` by inspecting the
explicit `SourceDocument.frontend.id`. Only `strling.regex-compat` dispatches to
the existing pure Rust frontend; every other identifier returns
`STRL-PROTOCOL-0002`. The frontend itself enforces dialect `1.0.0`, so conflicting
metadata remains the frozen `STRL-FRONTEND-0003` diagnostic. No media type,
filename, content, target, or runtime probe participates in selection.

Successful parsing produces canonical Semantic IR and then reuses the same
resource preflight, normalization, target-neutral analysis/diagnostics,
exact-profile portability planning, requested-output projection, diagnostic
filtering, result validation, and exchange validation as semantic input.
Embedded source identity, frontend/dialect metadata, exact content, provenance,
and node origins survive into the semantic result. Frontend syntax diagnostics
cross the boundary unchanged.

The kernel remains in-memory and host-independent. A valid reference-form
source that the caller has not resolved returns `STRL-PROTOCOL-0006`; the kernel
does not open its URI or filesystem. Invalid source contracts remain typed
request failures, and an invalid frontend-produced program remains a typed
canonical-stage invariant failure. Target artifact requests still return
`STRL-PROTOCOL-0005`; this task adds no lowering or emission.

## CLI transport

`./strling compile [--target-profile PATH]` delegates directly to the explicit
Rust `strling-kernel` binary target from `core/cli`. It reads one request from
standard input, optionally reads the exact target profile named in that
request, and emits one compact newline-terminated result to standard output.
It contains no source parser, semantic stage, target policy, or emitter.

The stable exits are `0` for success, `2` for a valid failed result, `64` for
usage/contract decoding, `69` when the root wrapper cannot locate Cargo, `70`
for a typed kernel failure, and `74` for I/O. Help exits `0` without reading
input. Missing target evidence and mismatched profiles do not trigger default
selection.

## Contract and migration evidence

Five public request/result pairs cover source success, malformed syntax,
unsupported directives, unresolved reference content, and exact-profile
portability. Rust integration tests execute each pair and compare the emitted
result exactly, including deterministic serialization.

The specification-authored orchestration corpus contains 22 unique source
cases and maps them exhaustively onto all 34 source-bearing cases in the
governed Python and TypeScript historical corpora. The blocking migration
differential now executes those cases through `CompileRequest` before either
historical runner. Historical AST, compiler metadata, and emitted target shapes
remain machine-classified `not_comparable` where their surface differs or the
canonical target stage is absent; none is silently treated as equivalent.

Architecture tests require the kernel dispatch, forbid parser logic in the
shell and Rust CLI transports, assert one production owner for frontend
dispatch, and retain the frontend prohibition on target lowering and emission.

## Verification status

The canonical core, 12 focused orchestration tests, warnings-denied Clippy,
rustfmt, 11 schema mappings, 73 contract fixtures, public-contract
reproduction, generated artifacts, governance, architecture, documentation,
pinned formatting, security integrity/content, hygiene, and patch integrity all
pass.

The native three-run differential certifies 44 observations with zero
mismatches and zero blocking unresolved replacements:

-   Baseline: `sha256:a914c350fd1facee7a0460cf586c2a576e113fb165be3597d733cd13ae7d0595`.
-   Result: `sha256:a8f8288adfda0c74c72fbbdcee5a5e803b8af59cff3d560502002d8dcfeae706`.
-   Canonical boundary: `sha256:c6afd58a149f7fb0241847be2ad33bffefaf0c41397fc31efc0dab262e42d3e8`.
-   Full corpus: `sha256:e6307c75de2a7af8a0e6958bca7a6a318fca6ba8ca232f9b17a4c46316306386`.
-   Route coverage: `sha256:96f519848f9a4ef3d3fe926c17ffcee81b98ba1fce33f216511ca7749044699e`.

Clean-tree profiles at commit
`d928e5ca330b10e23d6440ee23c575a2275d95ac` pass every P08-T04-scoped
operation. Local records 25 passed and one inherited repository-lint failure,
fingerprint `13382079b1a1665cab77f4fc497e4468e0f44ca9d01171c87182cd170915a4a9`.
Pull Request records 43 passed, that same failure, and the existing Bundler and
Swift host gaps, fingerprint
`aaa72c2475bdc01ad41a5af81d0613b89b95833dabe4940c7a8680347277d6fd`.
Full records 70 passed, the same failure, unavailable dependency-risk scanning,
and the existing Ruby and Swift host gaps, fingerprint
`33ee765835d6a5c2689b788f7673fba6e693182182df421957a323cd9000a745`.
No carry-forward finding is waived or reported as passing.
