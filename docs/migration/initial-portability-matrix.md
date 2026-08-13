# Initial cross-engine portability matrix

[← Back to Architecture](../architecture.md)

P11-T06 closes the initial PCRE2, ECMAScript, and Python `re` backend phase by
turning the already-certified shared observations into a versioned portability
matrix. The matrix is certification evidence. It does not change canonical
language semantics, target profiles, portability plans, rewrites, lowering,
serialization, runtime harnesses, product execution, or public APIs.

## Authority and dependency direction

The dependency direction is closed:

```text
specification-owned conformance manifest and cases
    + immutable exact target profiles
        -> shared-corpus v1 applicability and coverage contract
            -> checked exact-engine observations
                -> machine-authoritative portability matrix
                    -> generated human summary
```

The matrix controller consumes the fixed corpus and checked observation
artifact only after their existing validators prove exact identity and complete
coverage. It does not invoke Rust projection, target runtimes, subprocesses,
bindings, packages, or product routes. The shared-corpus certification remains
the only owner of exact PCRE2, Node/V8, and CPython execution.

Authored semantic and diagnostic expectations remain authoritative. Emitted
pattern text, engine consensus, historical compatibility observations, and the
matrix's own aggregations cannot create or rewrite an expectation. A result
split is evidence of a discrepancy, never a vote on which result is correct.

## Matrix identity and denominator

The initial denominator is the Cartesian product fixed by shared corpus v1:
20 vectors and five exact profiles, yielding 100 ordered entries. Every entry
retains:

-   corpus, manifest, case, vector, and checked-observation fingerprints;
-   exact profile ID, revision, fingerprint, execution adapter, subject
    representation, and applicable runtime identity;
-   feature, semantic-requirement, rewrite-strategy, option, mode, operation,
    application-state, and portability-plan identities;
-   a normalized-observation fingerprint for executed entries; and
-   one explicit matrix disposition and rationale.

The machine artifact also projects entries into feature-by-profile and
requirement-by-profile aggregates. Aggregates report their exact contributing
case/profile identities and counts; they cannot hide an unsupported,
not-applicable, rewrite, or unresolved entry behind an overall percentage.

The machine JSON is authoritative. Its Markdown companion is generated from
that JSON in canonical order and contains the same identities, counts,
divergences, and readiness conclusion. Both outputs have one generated-artifact
owner and are byte-checked.

## Disposition taxonomy

Each vector/profile entry receives exactly one disposition:

-   `native` means the authored plan is native and exact normalized execution
    agrees with the canonical expectation;
-   `planner_certified_equivalent_rewrite` means the authored portability plan
    names a certified equivalent rewrite and exact execution still agrees with
    the canonical expectation;
-   `target_unsupported_or_constraint` means the authored exact profile and
    portability plan prove the application unsupported and no runtime executes;
-   `not_applicable` means the corpus explicitly excludes the profile for a
    stable semantic, representation, or diagnostic reason;
-   `target_profile_or_documentation_discrepancy`, `harness_defect`,
    `canonical_expectation_defect`, and
    `implementation_or_runtime_discrepancy` are reviewed owning-layer
    classifications for a discovered discrepancy; and
-   `unresolved` means the evidence cannot yet justify one of the preceding
    conclusions and is always certification-blocking.

The initial passing artifact is expected to contain 87 native entries, one
planner-certified rewrite, five target unsupported/constraint entries, seven
not-applicable entries, and zero unresolved entries. The six rewrite/support
differences are explicit divergences even though they do not produce an
executed semantic mismatch.

## Semantic comparison and failure policy

For every executed application, the controller independently reconstructs the
canonical normalized expectation and requires the checked normalized
observation to match it. It then groups comparable executed entries by vector
and requires one normalized semantic class across profiles. This verifies
match/nonmatch, UTF-8 spans, logical capture values and spans, mode behavior,
and certified rewrite outcomes without comparing emitted pattern spelling.

Unsupported and not-applicable entries must have no raw or normalized runtime
observation. Native and rewritten entries must have complete observations. A
missing pair, stale profile revision, changed case or corpus fingerprint,
missing runtime fingerprint, duplicate identity, unknown state, unclassified
difference, or more than one executed semantic class fails certification.

The controller does not guess whether an unexpected result comes from the
profile, documentation, harness, authored expectation, implementation, or
runtime. It reports such a result as unresolved and blocks. The owning layer
must be investigated and corrected or supported by reviewed evidence before a
new matrix can pass; no waiver, majority vote, or ignored row can convert it to
portable.

## Full and Release certification

Full and Release run exact PCRE2, ECMAScript, Python `re`, and shared-corpus
certification first. Matrix certification then verifies the checked shared
observation identity, regenerates the machine and human artifacts in memory,
and requires byte equality with both checked outputs. A missing exact runtime
therefore remains `unavailable` at the owning runtime/shared-corpus operation;
the matrix never substitutes an ambient engine or stale evidence.

Bindings, packages, versions, publication, release notes, performance policy,
new targets, and product-facing compiler orchestration remain outside this
task. Future target profiles must extend the same authored corpus and matrix
mechanism rather than creating a separate compatibility authority.

## Certified outcome

The initial matrix is complete at SHA-256
`11f70923cdc200b132d7f68077fd840f3d38cf9aff63949fae24d703b68ea205`
from corpus SHA-256
`e8c069f068b8562518bfcf4f782a0961b53124660e4d40e63e49cbe8c6824fb1`
and checked observation SHA-256
`9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`.
Its 100 entries contain 87 native applications, one planner-certified
equivalent rewrite, five target unsupported or constrained applications,
seven not-applicable applications, six explicit nonblocking divergences, and
zero unresolved entries. All 19 comparable executed cases form one normalized
semantic class; the diagnostic-only case is explicitly not compared.

Exact PCRE2 10.42 and 10.43, Node 22.23.2, CPython 3.11.15, shared-corpus, and
matrix certifications pass. Rust all-target tests, warning-denied Clippy, all
485 tooling tests, canonical and core contracts, stage boundaries, generated
and public contracts, formatting, governance, documentation integrity, patch
integrity, and the reviewed three-run migration differential also pass. The
migration candidate matches baseline SHA-256
`8127c22a016013ff9751540ce39615fa780291da675082f2668bae5d63e4da5c`,
so no baseline renewal is required.

At clean implementation commit
`a38a42fdad264143a553a64b404c24f6fb3c1d53`, Local passes 26/26. Pull Request
records 44/46 passed and Full 1.9.0 records 76/83 passed, with zero failures,
incomplete operations, or waivers. The only unavailable operations are the
inherited repository-managed Ruby Bundler mismatch, missing Swift, and Full's
structured dependency-risk scanner gap. P11-T06 and P11 are therefore `READY
WITH RECORDED CARRY-FORWARD`.
