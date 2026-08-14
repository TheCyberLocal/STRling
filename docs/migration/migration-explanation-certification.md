# Migration and explanation behavior certification

## Outcome and authority

P15-T04 is the phase-closing certification boundary for regex-compatible
import, structured semantic explanation, canonical conversion to Semantic
STRling and Simply, and bounded no-match evidence. It adds durable
certification data and executable proof. It does not add language semantics,
frontend syntax, target behavior, public APIs, or product features.

The certification identity is
`strling.migration-explanation-certification@1.0.0`. It is migration evidence,
not a normative product contract. Every assertion remains subordinate to the
versioned frontend, conversion, explanation, no-match, compiler, and target
contracts plus their canonical Rust implementation.

The clean starting and rollback boundary is
`75b8c2b0b2ebe6a311d90ef74cc04c1efd556dbe`. At that revision P15-T01 through
P15-T03 are complete. This task may compose their accepted surfaces and expose
gaps; it may not repair a discovered semantic difference in the certification
harness or silently revise an owning contract.

## Locked denominator

Certification consumes these already accepted denominators without changing
their meaning:

| Evidence family        | Locked denominator                                                                                                                                                                                                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend convergence   | 11 cases, 3 host routes, 15 Simply operations, 17 Semantic STRling mappings, 9 regex-import cases, 38 supported legacy features in 10 families, 13 rejected features, and 3 target profiles; fingerprint `sha256:1ce3a851f55ac89bc5cb2825ee0a46bd701dd71f1bf09796edec5a3b5e596cb2` |
| Semantic explanation   | Model `1.0.0`, 1 positive and 3 controlled-negative documents; fingerprint `sha256:6831dc6ae1ddc65cd06016f5e60f4907926e5c4c33d7e6d465e7d3adae3b0d6b`                                                                                                                               |
| Semantic conversion    | Model `1.0.0`, 4 positives and 3 controlled negatives, with 2 exact, 1 partial, and 1 unsupported result across all 12 node kinds and 4 character-set member kinds; fingerprint `sha256:70f12e19b559af4dab77458cf397694c644b69a18c8de66c4da503511b593ce0`                          |
| Bounded no-match       | Model `1.0.0`, 27 reasons, 17 programs, and 24 cases containing matched=1, proven=7, likely=6, unknown=9, and unavailable=1; fingerprint `sha256:62dbff6a46849292eb277a18ecdcdddb3c71dbd0319b90689840515bd1204876`                                                                 |
| Shared target evidence | 20 governed cross-engine cases with checked evidence fingerprint `sha256:9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`                                                                                                                                         |
| Migration differential | 44 historical observations, zero blocking replacement reviews, and three-run determinism under baseline `sha256:83edceb883623274bf2d6fa8cc2022765fd0a75fe21e5cc738c22817910e71da`                                                                                                  |

CP2 freezes a content-addressed certification manifest over those sources. A
source count, identity, fingerprint, required case, or declared coverage class
cannot disappear through an automatic refresh. A changed denominator requires
review in the owning layer and a deliberate manifest update.

## End-to-end proof pipeline

The exact migration path is:

```text
regex-compatible source
    -> canonical Semantic IR
    -> structured semantic explanation
    -> Semantic STRling and/or Simply conversion result
    -> reparse or reconstruct canonical Semantic IR
    -> normalized semantic alpha-equivalence proof
    -> applicable target planning and representative execution evidence
```

Concrete node IDs, capture IDs, and source provenance differ across authored,
imported, and generated representations. The established alpha projection may
exclude only those representation identities. It must preserve node kind and
order, capture/reference relationships, case matching, character domains,
wildcard and line behavior, repetition bounds and modes, assertion direction
and polarity, target requirements, diagnostics, portability decisions, and
artifact behavior.

Emitted-text similarity, matching a small subject sample, or a successful
parse is never sufficient for an `exact` conversion. Exact status requires the
conversion result's existing normalized Semantic IR proof after destination
reconstruction. Partial output must retain every loss, substitution, and
manual-decision marker. Unsupported output must remain absent.

## Corpus classes

The certification manifest must account for all of these classes:

-   exact regex-import round trips through both canonical destinations;
-   source-less, Semantic STRling, and Simply convergence where regex import is
    not representable;
-   structured explanation identity, stable evidence classes, source links,
    uncertainty, and optional target projection;
-   partial and unsupported conversion results, including capture-name loss
    and invalid backreference topology;
-   no-match matched, proven, likely, unknown, and unavailable dispositions;
-   captures and backreferences, assertions and anchors, alternation,
    repetition, Unicode and text assumptions, options, and target constraints;
-   malformed contract inputs and stale cross-document correspondence; and
-   pathological nesting, repetition, zero-width behavior, ambiguity, and
    every declared no-match resource guard.

The manifest references existing normative contracts and checked evidence; it
does not copy their values into a second semantic source. New certification
fixtures live under `tests/certification/migration-explanation/1.0/` and are
explicitly implementation/campaign evidence.

## Mutation contract

At least one controlled mutation must be detected for each category below:

1. capture identity or capture/backreference relationship;
2. alternation branch order;
3. repetition minimum, maximum, or mode;
4. case matching, character domain, wildcard, or compiler option;
5. source span or source-authority correspondence;
6. explanation confidence, evidence class, reason, or limit disposition;
7. conversion loss, substitution, manual-decision, status, or output presence;
8. contract version, profile identity, semantic digest, or other authority
   evidence.

Mutation success means the relevant schema, correspondence check, canonical
alpha proof, target comparison, or certification-manifest validator rejects
the altered evidence. The harness cannot normalize away the mutated field,
replace it with an expected value, or classify the divergence after seeing an
implementation result.

## Resource and determinism boundary

Certification reuses existing hard production limits rather than creating a
larger test-only execution model. In particular, bounded no-match retains its
16 KiB subject-byte, 4,096-scalar, 100,000-step, depth-128, 4,096-branch,
32-finding, and 250 ms ceilings. Semantic conversion retains whole-operation
failure, reconstruction proof, and bounded-depth behavior. Frontends retain
their own validated input and nesting limits.

Pathological cases execute twice or more with identical logical results and no
panic. A reached guard must be represented as the contract already requires;
it cannot be waived, truncated into a proof, or hidden by a test timeout.
Elapsed time remains a fail-safe and is not a byte-stability field.

## Architecture boundary

The contained implementation consists of:

-   one versioned certification manifest and schema under `tests/`;
-   one Python validator with mutation-focused unit tests;
-   one Rust integration test that composes existing public canonical APIs;
-   one offline repository hardgate registered in all canonical profiles; and
-   migration documentation and closure evidence.

Production modules under `core/src`, all bindings and packages, versioned
semantic/frontend/conversion/explanation/target contracts, governed runtime
observations, and historical reference runners are read-only inputs. The task
cannot add a compensating parser, converter, matcher, target emitter, semantic
projection, or product-facing adapter.

The new hardgate must be deterministic, offline, and fail closed for missing or
stale evidence. Local, Pull Request, Full, and Release profiles invoke the same
gate. Profile or host-tool unavailability is reported exactly; it is never
converted to a semantic pass.

## Verification and closure

CP2 freezes the schema, manifest, counts, fingerprints, mutation inventory,
and positive/negative/pathological evidence. CP3 implements the manifest
validator and end-to-end Rust proof and runs focused property/mutation tests.
CP4 registers the gate, runs adjacent Rust/TypeScript/Python and cross-engine
checks, the migration differential, architecture/public/generated/docs and
security checks, and Local/Pull Request/Full profiles.

Closure records corpus counts, exact/partial/unsupported and explanation
dispositions, equivalence and execution results, resource bounds, mutations
detected, unresolved items, environment carry-forward, final SHA, and P15 phase
readiness. UI flows, CLI/LSP features, binding adapters, new semantic
constructs, expanded target support, and changes to explanation prose remain
outside this phase-closing certification task.
