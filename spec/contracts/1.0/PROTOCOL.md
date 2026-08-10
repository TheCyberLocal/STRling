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

Protocol result examples demonstrate complete success, a diagnostic-only
unsupported frontend, partial recovery, and canonical multiple-diagnostic
ordering. Controlled invalid examples reject malformed input unions, missing
profile selection, reversed spans, contradictory outcomes, analysis attached
to partial semantics, and nondeterministic diagnostic ordering.
