# Canonical compiler contract certification

## Certified system

Contract suite `1.0.0` is certified as one coherent data system:

```text
SourceDocument or normalized semantic input
        |
frontend-specific parsing/building and semantic lowering
        v
Semantic IR
        |
structured diagnostics + target-neutral keyed analysis
        |
immutable target-profile selection + portability decisions
        v
TargetArtifact
```

The certification governs serialized shape and cross-contract invariants. It
does not implement a compiler phase, ratify the draft semantic specification, or
change current runtime/compiler behavior.

## Single ownership of shared concepts

| Concept                             | Owning contract                              | Cross-contract use                                                                                                          |
| ----------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Contract and specification versions | `source.schema.json` shared definitions      | Every family selects them explicitly; profile/compiler/dialect versions remain independent.                                 |
| Source identity and UTF-8 spans     | `source.schema.json`                         | Semantic origin, diagnostics, fixes, artifact maps, and conformance expectations reuse the same half-open coordinate shape. |
| Semantic node identity              | `source.schema.json` shared `NodeId`         | Semantic IR declares nodes; analysis, portability, artifact maps, and conformance facts refer to them.                      |
| Logical capture identity            | `semantic-ir.schema.json` `CaptureId`        | Captures, backreferences, and conformance capture expectations use it; engine numbering is absent.                          |
| Diagnostic identity                 | `diagnostic.schema.json` code/phase/category | Compile results, artifacts, and conformance expectations reuse stable fields without making English prose identity.         |
| Target profile reference            | `portability.schema.json`                    | Requests, plans, artifacts, and cases use the same identity/revision/SHA-256 tuple.                                         |
| Portability status                  | `portability.schema.json`                    | Plans, artifacts, and target expectations use exactly `native`, `equivalent_rewrite`, or `unsupported`.                     |
| Conformance authority               | `conformance-manifest.schema.json`           | Cases cannot self-promote; manifest membership, delegation, and content fingerprints control authority.                     |

## Boundary certification

The following properties are structurally enforced:

-   frontend syntax representations are outside every canonical schema;
-   Semantic IR contains semantic operations, never PCRE2, ECMAScript, Python
    `re`, emitted fragments, engine flags, profile IDs, or host-language
    objects;
-   target profiles and artifacts consume semantic requirements/identities but
    contain no frontend AST or parser representation;
-   derived facts remain in keyed analysis/portability results instead of
    mutating Semantic IR;
-   pattern text and engine options are separate artifact fields;
-   source-less constructed Semantic IR remains valid;
-   partial semantic recovery cannot feed analysis, portability, or emission;
-   unsupported portability and error diagnostics suppress artifacts; and
-   implementation-derived fixtures cannot enter the specification authority
    manifest.

## Determinism and compatibility

Canonical arrays have explicit sort/uniqueness rules for sources, origins,
character-set members, analyses, requirements, diagnostics, profile facts,
options, artifact mappings, target expectations, cases, and manifests. Canonical
JSON uses UTF-8, sorted object keys, no insignificant spaces, Unicode characters
unescaped, and no non-finite numbers. Content fingerprints are SHA-256 of that
encoding.

Contract version `1.0.0` is independent of Semantic Specification
`1.0-draft.1`, compiler versions, dialect versions, engine/runtime versions,
and profile revisions. Unknown fields are rejected. A major contract version
handles incompatible shape/meaning/order changes; minor versions add optional
shape; patch versions clarify or enforce already-stated invalidity.

## Controlled rejection evidence

The committed negative corpus proves rejection of representative invalid states:

-   mixed source/semantic input and missing target selection;
-   duplicate or unresolved node/capture identity and target syntax in Semantic
    IR;
-   invalid/reversed UTF-8 attribution and undeclared sources;
-   contradictory compile outcomes, partial downstream results, and
    nondeterministic diagnostics;
-   timeless Boolean capabilities, malformed engine versions, missing
    constraints, and invalid profile fingerprints;
-   unsupported artifacts, option disorder, and invalid generated mappings; and
-   implementation-authored cases, missing case IDs, invalid target
    expectations, error/execution combinations, false authority delegation, and
    manifest fingerprint drift.

`python3 tooling/contract_validation.py` validates schemas, every authored
positive object, every controlled negative, immutable profile/case references,
and local contract-document links. It runs automatically in both repository
`check` and `certify` aggregates.

## Transitional compatibility state

The shallow TypeScript AST/IR, legacy base/PCRE2 schemas,
implementation-generated `tests/spec` fixtures, duplicated binding semantic
models, and existing emitter capability tables remain present only as migration
and compatibility evidence. This certification does not migrate, delete, or
reinterpret them.

No STRling runtime/compiler semantics intentionally changed.
