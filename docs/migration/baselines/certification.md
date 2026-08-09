# Governed Architecture Baseline Certification

## Certified identity

-   Baseline: `governed-architecture-foundation`
-   Certified commit: `77f6a81e6b0a63cc6052fdadb428c719b16c7c61`
-   Governed branch at certification: `architecture/v4`
-   Donor commit: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
-   Main commit: `664d08de53565929c8f62379b006cd29f93b239f`
-   Machine evidence: [`certification.json`](certification.json)

This is engineering and compatibility evidence. It does not supersede a
normative specification, a ratified versioned contract, or the authority order
in `governance/authority.md`.

## Certification result

The complete command contract in `governance/baseline-contract.md` passed from
clean committed state. The focused suite passed all 143 tests. Structured
`check all` reported 49 enforced passes; structured `certify all` reported 63
enforced passes, including 14 builds and all 17 configured binding test
baselines. No result failed or was unavailable.

Thirty-nine incomplete quality capabilities remain explicit policy states:
`not_applicable`, `not_yet_configured`, or `not_yet_enforceable`. They are
not reported as passing hardgates. Check modes left the repository clean and
required no hidden untracked state.

## Frozen public compatibility evidence

Ten deterministic snapshots reproduce exactly:

-   C, Go, Python, R, and TypeScript public APIs;
-   TypeScript package entrypoints;
-   the root CLI; and
-   the base/target-artifact, conformance-fixture, and PCRE2 target schemas.

The C++, C#, Dart, F#, Java, Kotlin, Lua, Perl, PHP, Ruby, Rust, and Swift API
surfaces remain inventoried transitions with ecosystem-specific structural
extractor retirement conditions. Snapshot presence records compatibility
evidence; it does not promote implementation behavior to language semantics.

## Generated artifacts

Three generated families are enforced:

-   public contract snapshots;
-   version-synchronized package metadata; and
-   the Swift projection of the C compatibility fixtures.

Eight families remain explicit transitions: shared semantic fixtures, C
compatibility fixtures, the C test skeleton, the final audit report, package
locks, the Lua release rockspec, the disposable LSP extension payload, and Rust
conformance build source. Their exact rationale and retirement conditions are
recorded in `governance/generated-artifacts.json` and copied by identifier into
the machine evidence.

## Architecture fitness

Eight rules are enforced for governance/product and quality/semantic dependency
direction, generated-input acyclicity, implementation-derived fixture authority,
task and top-level placement, specification-reference authority, and new tooling
semantic islands.

Three structures remain intentionally transitional:

-   duplicated binding compilers;
-   implementation-derived shared fixtures; and
-   direct LSP imports of Python-binding semantics.

The binding-to-canonical-core dependency rule remains future-state because no
canonical compiler core exists. This certification makes no contrary claim.

## Active waivers

The certification records five active or accepted waiver identifiers exactly:

-   `WVR-PERL-PARSER-CASE-001`;
-   `WVR-STATIC-PYTHON-001`;
-   `WVR-STATIC-TYPESCRIPT-PATTERN-001`;
-   `WVR-STATIC-TS-JEST-NODENEXT-001`; and
-   `WVR-STATIC-SHELL-INTEROP-001`.

Their authoritative scopes, expiration where present, and retirement conditions
remain in the referenced governance policies.

## Known defects excluded from the contract

The baseline does not normalize these known inconsistencies:

-   the unresolved callable-TypeScript-`Pattern` typing contract;
-   advertised TypeScript package entrypoint paths that do not match current
    declaration build paths; and
-   the duplicate-cased Perl parser module paths.

They remain separately authorized future product or compatibility decisions.
Current existence is evidence, not a promise to preserve the defect.

## Product behavior

No STRling language/compiler semantics intentionally changed. Grammar, parser,
compiler, emitter, AST/IR meaning, diagnostics, targets, standard-library
semantics, public APIs, package versions, and legacy implementations were not
changed by certification.
