# Frontend convergence and canonical authoring hierarchy

[← Back to migration records](README.md)

This work certifies that STRling's authoring surfaces are different ways to
construct one canonical semantic program. It adds evidence and public guidance;
it does not add language constructs, change semantic meaning, select a new
default target, or grant a frontend independent compiler authority.

## Locked denominator

The convergence corpus contains eleven specification-owned-intent cases. Every
case has authored Semantic STRling source, one host-neutral Simply builder
request, and a source-less Semantic IR route produced by replaying that request.
The same Simply request is reconstructed by native Rust, TypeScript Preview,
and Python Preview. Nine cases also carry an exact regex-compatible import
source.

Completeness is fail-closed against the governing contracts:

-   all 15 operations in `spec/frontends/simply/1.0/protocol.json` occur;
-   all 17 entries in `spec/frontends/semantic/1.0/mapping.json` occur;
-   all 38 accepted or compatibility-only feature IDs in the
    regex-compatible dialect occur across its ten non-extension families; and
-   all 13 rejected legacy features retain the existing
    `unsupported_legacy_behavior` migration disposition. The corpus permits no
    `unresolved_discrepancy` entry.

The denominator is derived from the contracts at validation time. Removing an
operation, mapping, supported legacy feature, legacy family, host route, or
classification makes certification fail rather than silently reducing scope.

## Representation-neutral comparison

Concrete frontend identities and provenance are evidence, not semantic
differences. The comparison projection therefore:

1. traverses the normalized Semantic IR in canonical order and alpha-renames
   material node and logical capture identities while preserving every
   reference relationship;
2. removes source documents, node origins, and source-location fields whose
   only difference is authored versus generated provenance;
3. applies the same alpha-renaming to semantic facts, diagnostics, portability
   plans, source maps, and artifact evidence; and
4. retains all semantic node/member values, case intent, facts, diagnostic
   identity and content, portability decisions, rewrite identities, target
   options, artifact pattern/flags, and compile outcome.

No target spelling, diagnostic, support state, fact, or semantic value may be
discarded to manufacture convergence. Each case is compiled twice to reject
nondeterminism. Target-aware comparisons use exact checked profiles and compare
successful or failed results consistently across every participating frontend.

## Legacy boundary

Regex-compatible syntax participates only where its governed dialect defines a
structural semantic lowering. The nine import cases collectively exercise
assertions, backreferences, classes, composition, directives, escapes, groups,
layout, literals, and quantifiers, including every compatibility-only feature.
Rejected directives and extensions are not reinterpreted as Semantic STRling;
their existing migration disposition and dialect authority are recorded
explicitly. Any future meaningful difference without sufficient authority is
`unresolved_discrepancy` and blocks this certification.

## Public documentation denominator

The canonical hierarchy is:

1. Semantic STRling is the flagship textual authoring language.
2. Simply is the idiomatic programmatic intent API.
3. Regex-compatible source is an import and compatibility dialect.

The migration owns the root README, developer index, first-contribution
tutorial, testing workflow/design examples, specification hub and frontend
index, Semantic frontend reference, architecture overview, and the F#, Java,
Kotlin, and Lua binding README passages that currently call regex-compatible
input the DSL. Dedicated migration history and the normative regex-compatible
dialect remain intact. Documentation validation will check links, executable
examples, hierarchy wording, and the absence of known stale canonical claims.

## Certification boundary

Completion requires native Rust, TypeScript Preview, Python Preview, Semantic
source, source-less Semantic IR, and regex-import routes to agree under the
locked projection; parser/formatter properties and shared exact-target
execution to remain green; documentation and public/architecture contracts to
pass; Local, Pull Request, and Full profiles to complete as available; and the
final repository to be clean and reproducible.
