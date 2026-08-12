# Diagnostic and compiler protocol contract

## Transport-independent operation

[`compile-request.schema.json`](compile-request.schema.json) and
[`compile-result.schema.json`](compile-result.schema.json) define data, not an
RPC or process boundary. An implementation may expose them in-process, through
FFI, or over a transport, but transport correlation IDs, exceptions, streams,
and host objects are outside canonical compiler semantics.

Given the same compiler version, request object, and immutable target profile
selected by identity/version/SHA-256, the result is deterministic. Requests do
not contain filesystem paths and never select an implicit latest specification
or profile.

## Compile request

The request declares one specification version and exactly one input form:

-   `source` embeds a `SourceDocument`. Its frontend owns syntax parsing and
    lowering into Semantic IR.
-   `semantic` embeds normalized Semantic IR. It supports Simply and other
    frontend-derived callers without exposing their implementation structures to
    the compiler core.

The input and request specification versions must match. Source frontend IDs
are open identifiers because a structurally valid request may name a frontend
that a compiler release does not implement. That condition returns diagnostic
`STRL-PROTOCOL-0002`; it is not a schema exception.

The canonical kernel currently implements exactly the explicit
`strling.regex-compat` frontend at dialect version `1.0.0`. It performs no
frontend guessing from media type, display name, content, or caller. Supported
inline documents lower through the governed compatibility frontend and then
enter the same normalization, analysis, diagnostics, portability, and resource
limit stages as semantic input. Frontend diagnostics cross the compile boundary
with their stable identity and UTF-8 provenance unchanged.

A reference-form `SourceDocument` remains valid transport data, but the
in-process kernel never reads a URI or host filesystem. Callers must verify and
resolve referenced bytes before compilation. An unresolved reference returns
`STRL-PROTOCOL-0006` as a failed `CompileResult`.

`requested_outputs` is unique and ordered as `semantic`, `analysis`,
`portability`, `target_artifact`. Portability or artifact requests require a
target-profile reference containing immutable profile identity, revision, and
content fingerprint.

Compiler options are deliberately narrow:

-   `partial_semantics` either forbids partial trees or permits them only as
    diagnostic recovery data;
-   `diagnostic_policy.minimum_severity` may filter advisory diagnostics but
    never required error diagnostics; and
-   optional resource limits bound work deterministically without altering the
    meaning of accepted Semantic IR.

## Canonical JSON CLI transport

The repository root exposes the same boundary as
`./strling compile [--target-profile PATH]`. It reads exactly one
`CompileRequest` JSON document from standard input and writes exactly one
compact, newline-terminated `CompileResult` JSON document to standard output.
The optional path supplies the exact immutable `TargetProfile` named by the
request; it does not select a profile implicitly. The shell and Rust binary are
transport adapters only and contain no frontend parser, target policy, lowering,
or emission implementation.

Exit status is stable: `0` for a successful result, `2` for a valid failed
result, `64` for usage or contract decoding failure, `69` when the root wrapper
cannot locate Cargo, `70` for a typed kernel boundary failure, and `74` for
transport I/O failure. Help exits `0` without reading standard input. Standard
output is reserved for help or result JSON; transport and typed boundary
failures are written to standard error.

## Structured diagnostics

[`diagnostic.schema.json`](diagnostic.schema.json) is the one diagnostic shape
for compiler APIs, CLI, LSP, editors, bindings, and conformance assertions.

`code`, `phase`, and `category` form stable machine identity. English `message`,
related-location messages, fix titles, and advice remain presentation text
unless a separate normative source deliberately constrains them.

`severity_basis` makes severity ownership explicit:

-   syntax errors, semantic invalidity, malformed protocol, and unsupported
    requested emission use `normative` error severity;
-   a versioned profile may prescribe `target_profile` severity for a target
    fact; and
-   advisory safety/style information uses `compiler_policy` unless the
    specification promotes a specific class.

Primary location is optional. Every supplied location and text edit uses the
canonical UTF-8 byte span. Related locations preserve authored explanatory
order. Fix edits sort by source/start/end and may not overlap.

Result diagnostics sort by located diagnostics first, then source ID, start,
end, phase order, severity (`error`, `warning`, `info`, `hint`), code, and the
unique deterministic `occurrence` ordinal. Location-free diagnostics follow
located diagnostics. Exact prose is never used as a sort or identity key.

## Analysis and portability separation

[`analysis.schema.json`](analysis.schema.json) attaches derived facts to stable
node IDs. The initial contract includes nullability, Unicode-scalar length
bounds, and feature requirements. It intentionally does not mutate Semantic IR
with analysis fields. Future overlap and safety result families follow the same
keyed-results boundary.

[`portability.schema.json`](portability.schema.json) records a selected profile,
overall status, and per-requirement decisions. Status is exactly `native`,
`equivalent_rewrite`, or `unsupported`; overall status is the least-supported
decision. Profile capability facts and emitted artifacts are separate
contracts.

## Compile result and failure model

The result always identifies compiler and specification versions, has
`succeeded` or `failed` outcome, and contains a deterministic diagnostic array.
Sections are independent:

-   `semantic_result` contains complete normalized semantics or explicitly
    partial recovery semantics;
-   `analysis` contains target-neutral derived facts;
-   `portability` contains profile comparison and planning decisions; and
-   `artifact` contains target-specific emitted material.

A successful exchange contains every requested output. A failed result contains
at least one error diagnostic and may omit unavailable sections. Callers never
parse an exception or console stream to determine failure.

Partial semantics require `allow_for_diagnostics`, carry status `partial`, and
occur only on failure. They are inspection/recovery data and cannot feed
analysis, portability planning, target lowering, or emission. Any error
suppresses `artifact`. An unsupported portability decision also suppresses it.

Protocol request/result pairs demonstrate complete source success, malformed
regex source, unsupported frontend directive, unresolved referenced content,
exact-profile source portability, a diagnostic-only unsupported frontend,
partial recovery, and canonical multiple-diagnostic ordering. Controlled
invalid examples reject malformed input unions, missing profile selection,
reversed spans, contradictory outcomes, analysis attached to partial semantics,
and nondeterministic diagnostic ordering.
