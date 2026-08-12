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
Rust `strling-kernel` binary target. It reads one request from standard input,
optionally reads the exact target profile named in that request, and emits one
compact newline-terminated result to standard output. It contains no source
parser, semantic stage, target policy, or emitter.

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

Implementation-focused orchestration, architecture, contract, public-surface,
and differential gates are recorded in the governed task record. Final
certification fingerprints and aggregate carry-forward are appended only after
the implementation commit and clean-tree certification are complete.
