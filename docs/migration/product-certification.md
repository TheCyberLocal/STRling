# Structured product certification

P18-T01 replaces the historical Omega audit as certification authority with a
versioned product-certification artifact assembled only from machine-readable,
independently authoritative evidence. It does not add product tests, broaden
support claims, or turn unavailable environments into passes.

## Starting state

The clean task anchor is
`f16a04a3c84cabf9fd5debaeb70133ea6fe11163` on `architecture/v4`. The existing
quality framework already provides four canonical profiles and a validated
`strling-profile-certification` 1.0 artifact. Current profile definitions expand
to 33 Local, 70 Pull Request, and 112 Full/Release operation results. The
canonical registry contains 39 operations; 19 have structured result contracts:
15 certification producers, three security producers, and one documentation
producer.

CP3 adds one offline `certification.product-authority` structured operation to
all four profiles after its evidence contract is locked. The current registry
therefore contains 40 operations and 20 structured producers, and profile
expansion becomes 34 Local, 71 Pull Request, and 113 Full/Release results. The
operation validates the authority schema, exact manifest/profile parity,
positive fixture, and mutation catalog; it does not substitute for or recursively
execute product tests.

CP3 implements the deterministic merge in
`tooling/product_certification.py`. One validated Full-profile artifact is
embedded as source evidence, fingerprinted again at the product boundary, and
expanded into exactly 113 ordered result identities. All 20 structured producer
payloads are preserved and fingerprinted. Four authored claims derive only from
those results, and the artifacted aggregate policy determines the exit code.
The same validated artifact is the sole input to the Markdown renderer.

The producer manifest separately records each logical result contract and its
payload-version field/value. This preserves the existing security and
documentation `1.0.0` schemas, the newer `certification-result-v1` payloads,
and the three target-runtime `certification_version: 1.0.0` results without
mislabeling one shape as another.

CP4 extends that closed contract to the canonical `release` profile only when
its ordered operation membership is exactly identical to `full`. The manifest
fingerprint-pins both profile definitions, and each product artifact preserves
the actual source profile identity and fingerprint. CI derives product evidence
for Full and Release artifacts and retains the JSON artifact and Markdown view
beside the source profile evidence. Local and Pull Request remain bounded profile
checks and do not claim complete product certification. Derivation runs even
when the source aggregate is nonpassing so failed, unavailable, incomplete, and
waived evidence remains explicit in the retained product view.

## Authority defect being retired

The former `tooling/audit_omega.py` implementation was a host-ecosystem audit.
It executed setup, build, and test commands through `shell=True`, then inferred
semantic coverage, skips, warnings, and test counts from runner prose. Its three
semantic claims depended on output substrings for duplicate names, ranges, and
the Essential standard-library helpers. It could not distinguish unavailable,
waived, skipped, incomplete, stale, or contradictory evidence and had no
governed producer or corpus identity.

The retired script iterated 18 `toolchain.json` binding entries, including the
shared JVM transport, although the retained language denominator is 17. Its
checked-in report contains 17 rows from an older environment, embeds wall-clock
time, is not reproducibly checked, and is now registered only as transitional
compatibility evidence with no generator or verification command. Release and
CI setup documentation use structured product certification. The retained
`audit` command is a compatibility shim that delegates to the same Full-profile
product authority; it contains no subprocess, regular-expression, test-name,
skip, warning, or test-count inference.

## Locked replacement boundary

Product certification will consume validated structured evidence and an
authored producer/claim manifest. It will never inspect raw stdout or stderr,
test names, filenames, emoji verdicts, or prose summaries to decide success.
The manifest will classify existing profile operations and structured producer
identities into explicit evidence areas such as contracts/specification,
canonical compiler, real target engines, adapters/packages, migration,
architecture/governance, interop/fuzz/sanitizers, documentation, and security.

Aggregate policy is part of the versioned deterministic evidence. Its blocking
precedence is `failed`, `incomplete`, `unavailable`, `waived`, then `passed`.
Explicitly incomplete, skipped, not-yet-configured, and not-yet-enforceable
required results aggregate as `incomplete`; unavailable remains distinct;
not-applicable and passed results are neutral. Failed, incomplete, skipped,
unconfigured, unenforceable, and unavailable evidence produces a nonzero exit.
A waived result is nonblocking only with at least one governed waiver ID.

The versioned machine artifact must record:

-   exact repository SHA and clean/dirty state;
-   product-certification, specification, schema, profile, toolchain, producer,
    target-profile, adapter, corpus, and evidence identity/fingerprint data where
    applicable;
-   executed, skipped, unavailable, waived, passed, failed, incomplete,
    not-applicable, and explicitly unconfigured states without collapsing them;
-   governed waiver IDs for every waived finding;
-   deterministic counts and durations only where their producers declare them;
-   evidence/artifact paths and fingerprints without making generated agreement
    normative;
-   deterministic aggregate precedence and fail-closed completeness; and
-   presentation metadata isolated from the deterministic evidence identity.

Merging must reject duplicate result identities, missing required producers,
unknown producers, conflicting states, stale repository SHAs, stale profile or
producer fingerprints, invalid waiver references, and rehashed aggregate
tampering. A human report is rendered only from a mechanically validated machine
artifact. The legacy Omega command may remain as a compatibility entrypoint only
if it delegates to the structured authority without running its prose scanner.
The historical checked-in report may remain archived, but not as current
certification evidence.

## Evidence and parity obligations

Coverage parity is structural, not a comparison of historical test counts. The
replacement must account for every governed profile result and every required
structured producer, and it must map the three Omega heuristic claims to
canonical contract, runtime, standard-library, and adapter evidence. A missing
producer or unexecuted required claim is non-passing. Existing profile artifacts
remain authoritative for their exact operation executions; existing
certification/security/documentation results remain authoritative for their own
checks. Product certification aggregates and validates those claims but cannot
invent semantic truth.

P18-T02 owns target-engine/version and adapter support matrices. P18-T03 owns
expanded property, fuzz, sanitizer, and mutation evidence. P18-T04 owns
performance and resource budgets. P18-T05 owns final supply-chain provenance,
SBOM, and security controls. T01 provides the stable schema and aggregation path
that those tasks will ratchet without redefining certification semantics.

## Verification boundary

Acceptance requires schema and manifest validation, positive and malformed
fixtures, duplicate/missing/stale/conflicting-result mutation tests, aggregate
precedence tests, repeated deterministic merge, machine/human equivalence,
Omega coverage-parity proof, release-authority retirement, affected governance
and generated-artifact checks, Local/Pull Request/Full profiles, and a clean
committed tree. No package publication, release creation, registry upload,
branch push, semantic behavior change, public API change, support-tier change,
or expansion of an individual product test is authorized.
