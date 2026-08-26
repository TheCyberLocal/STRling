# Release supply-chain certification

Status: P18-T05 complete — READY WITH RECORDED CARRY-FORWARD.

This document records the verification boundary for Fourth Edition release
supply-chain provenance, software bills of materials, checksums, workflow
authorization, dependency risk, and reproducibility. It is migration evidence,
not product, package, registry, license, or publication authority.

## Authority and objective

[`governance/security-policy.json`](../../governance/security-policy.json)
remains the machine authority for repository dependency, advisory, license,
secret, workflow, and waiver policy. [`toolchain.json`](../../toolchain.json)
remains the operation and profile authority. Existing package manifests and
ecosystem-native metadata remain authoritative for package contents and
versions. This task may add release-certification evidence and enforcement, but
it cannot silently change a package version, public API, supported surface,
language behavior, target behavior, or publication policy.

The objective is to make every retained release deliverable traceable through
one reviewable chain:

```text
exact source commit and clean tree
-> authenticated toolchain and governed build command
-> exact built artifact
-> SHA-256 checksum and artifact-specific SPDX SBOM
-> in-toto/SLSA provenance statement
-> dry-run verification and reproducibility result
-> separately authorized registry publication
```

Publication jobs must eventually consume the exact verified artifact rather
than rebuilding an unauthenticated replacement. This task may exercise only
dry-run package construction and local or workflow validation; it does not
authorize a package publication, release creation, registry upload, tag push,
or branch push.

## Starting denominator

The clean starting commit is
`9f5e8c42babefac64e910faaf0897cd68de9f3bd`. The repository already has a
fail-closed security engine, exact waiver records, immutable GitHub Action
references, read-only workflow defaults, a canonical Release profile, and
package/runtime certification for several retained surfaces. Those controls
are inputs and will be extended rather than replaced.

The current dependency policy inventories 27 roots across npm, Cargo, Dart,
Composer, Bundler, Go, SwiftPM, C/C++, NuGet, Maven, Gradle, Python, LuaRocks,
CPAN, and R. A live network-backed risk run on 2026-08-24 produced 55 checks:
13 passed, two failed, and 40 unavailable. The ten VSCE signing packages still
carry unclassified `SEE LICENSE IN LICENSE.txt` metadata. The former npm
advisory waiver now resolves to no live advisory findings and correctly fails
as stale instead of silently remaining accepted. Cargo scanners are absent
from the current shell, and twenty dependency roots still lack complete
authoritative vulnerability and license coverage.

The delivery workflow has 17 compile jobs and 17 corresponding publish jobs:
C, C++, C#, Dart, F#, Go, Java, Kotlin, Lua, Perl, PHP, Python, R, Ruby, Rust,
Swift, and TypeScript. Compile and publish jobs check out the same selected ref
but build independently. They do not transfer an exact artifact, checksum,
SBOM, or provenance record from the certified build to publication. The
workflow retains certification JSON but no package artifact graph. It also
contains 14 long-lived registry/signing secret references, five jobs with
`id-token: write`, no declared protected release environment, and no
`attestations: write` permission or artifact-attestation step.

These observations are gaps, not release-readiness claims. Existing Full and
Release nonpasses remain exact evidence and cannot be converted to green by a
new wrapper, waiver, or report.

## Locked evidence model

CP2 will define one machine-readable authored manifest and one structured
result contract. The authored manifest will enumerate every retained
deliverable, registry or tag destination, package root, build command,
toolchain policy, expected artifact path or pattern, dependency roots,
credential mode, reproducibility mode, and owning profile operation. Missing,
duplicate, extra, or ambiguous artifacts will fail closed.

SPDX 2.3 JSON is the selected SBOM interchange format. It matches the
repository's existing SPDX license vocabulary, supports package and file
evidence, and is accepted by GitHub's supported SBOM-attestation path. Each
SBOM must describe one exact artifact and its reachable direct and transitive
components where the governed ecosystem can resolve them. Unknown components,
licenses, or external trust roots remain explicit findings.

Provenance will use an in-toto Statement binding exact artifact subjects to a
SLSA Provenance v1 predicate. Deterministic local evidence will authenticate
the source SHA, dirty-state disposition, builder implementation, toolchain
fingerprints, invocation, inputs, dependency/SBOM/checksum identities, and
build outputs. GitHub-hosted signed attestations are an additional remote trust
layer; they cannot replace the locally verifiable predicate or make an
unavailable local check pass.

SHA-256 checksums are mandatory for every produced artifact. A checksum file,
SBOM, provenance predicate, or attestation that names a different byte stream
must fail. Generated timestamps, signatures, and workflow-run identities may
vary only in explicitly normalized fields; source, build inputs, component
graph, artifact names, and digests remain exact.

## Reproducibility and profile partition

Byte-for-byte rebuild equivalence is required where the ecosystem can produce
it under governed inputs. Any surface that cannot be byte-identical must name
the unavoidable nondeterministic field, normalize only that field, and prove
the remaining archive and metadata content equivalent. A broad archive rewrite
or ignored-path comparison is not acceptable.

-   Local and Pull Request remain offline. They validate schemas, authored
    denominators, deterministic fixtures, workflow permissions, secret
    boundaries, checksum/provenance mutations, and release-graph architecture.
-   Full may retrieve official advisory/license data and governed tools, build
    bounded dry-run artifacts, generate SBOM/checksum/provenance evidence, and
    compare reproducibility without credentials.
-   Release repeats all Full obligations and validates the exact workflow and
    credential boundary. Registry publication, signing with production keys,
    release creation, and tag/branch pushes remain separate explicitly
    authorized actions.

No pull-request or untrusted-code path may receive a publication credential,
OIDC write permission, repository write permission, or protected release
environment. Publication-capable jobs must use least privilege, an explicit
release environment, an exact certified artifact, and a separate affirmative
non-dry-run authorization.

## Allowed work

The task may add the release-supply-chain schema, authored manifest, fixtures,
producer, verifier, profile routing, dry-run workflow integration, generated
evidence, documentation, and exact tests. It may install governed scanners and
official package-manager prerequisites. It may retire a stale waiver, classify
an exact license from authoritative evidence, or make narrowly scoped
dependency/lock changes required to resolve a current security finding, with
all resulting package graphs regenerated and certified.

## Forbidden work and rollback

The task may not change STRling semantics, compiler behavior, diagnostics,
target lowering, binding APIs, package versions, supported ecosystems,
performance contracts, or publication policy. It may not add undocumented
registry mechanisms, long-lived credentials, broad security suppressions, or
release paths callable from untrusted contexts. It may not publish, create a
release, upload to a registry, push a tag, or push a branch.

If the new producer or workflow integration cannot satisfy exact artifact
identity, fail-closed evidence, or dry-run reproducibility, the rollback unit is
the additive schema/manifest/producer/profile/workflow integration. Existing
security checks and truthful nonpasses remain in place.

## Checkpoint sequence

1.  CP1 locks this denominator, authority boundary, allowed paths, profile
    partition, and non-goals.
2.  CP2 freezes the manifest, result schema, fixtures, controlled negatives,
    SBOM/provenance/checksum rules, and artifact/reproducibility denominator.
3.  CP3 implements the smallest offline producer/verifier and proves local
    deterministic artifact evidence without credentials or publication.
4.  CP4 integrates governed network scanners, clean-checkout rebuilds,
    credential/workflow controls, Full/Release dry-run routing, and exact
    generated evidence.
5.  FINAL records every artifact, trust root, waiver, finding, reproducibility
    disposition, profile result, final SHA, and readiness for P18-T06.

## CP2 frozen contract

Contract version `1.0.0` freezes seventeen sorted release surfaces and their
package names, roots, dependency-root references, compile and publish jobs,
working directories, build commands, toolchain references, artifact patterns,
registry or tag destinations, credential modes, and reproducibility modes. The
manifest fingerprint is
`7f957aa6a5b08d283aa610924d06b7e347874eea7ede2f8604035b2a03b0b5af`.

Five source-tag deliveries—C, Go, PHP, R, and Swift—use exact source-tree
identity and do not invent an archive checksum. The twelve package deliveries
require SHA-256 subjects. Rust and TypeScript require byte-for-byte rebuild
identity. Other package formats permit only their explicit timestamp,
signature, or registry-generated-metadata normalizations; a broad archive or
path exclusion remains invalid.

Every surface requires an SPDX 2.3 JSON document and an in-toto Statement v1
whose predicate is SLSA Provenance v1. The structured evidence binds the
artifact subject to its checksum, SBOM, provenance subject, exact source commit,
governed build-command fingerprint, toolchain identities and policy
fingerprint, credential mode, and reproducibility result. A passed surface
cannot retain an unresolved SBOM component or finding.

Dart, Python, Ruby, Rust, and TypeScript are locked to secretless OIDC. Other
credential names remain exact inputs under the protected `release` environment
and may not enter an untrusted context. This is an intended target contract,
not a claim that the current workflow already meets it.

The synthetic contract fixture fingerprints to
`6f73c90a5a6bdc0da23a42ebd75175fe1efc8313b2e8b9e3b4c54f6c11eb408a`.
It explicitly denies live-artifact and publication authority. Twenty-five
focused tests prove the positive contract and reject denominator drift, stale
identity, checksum or provenance mismatch, toolchain drift, unbounded
normalization, credential expansion, OIDC issuer changes, false passes,
inconsistent summaries/status, and synthetic-to-live promotion.

## CP3 offline producer and local proof

[`tooling/release_supply_chain.py`](../../tooling/release_supply_chain.py) now
implements a create-only offline collector and verifier over two separately
prepared artifact trees. It does not build, download, sign, attest remotely, or
publish. Before live collection it authenticates an exact clean Git commit,
rejects submodules and dirty inputs, fingerprints every required executable and
the governed toolchain policy, and qualifies the common release workflow's
read-only default, protected environment, immutable actions, attestation
permissions, and exact upload/download handoff.

The collector resolves the frozen patterns for all seventeen surfaces, rejects
missing, escaping, symlinked, empty, extra, or ambiguous subjects, and emits one
checksum list, SPDX 2.3 JSON document, and in-toto Statement v1 / SLSA
Provenance v1 statement per surface. Each statement binds the concrete artifact
members, exact source commit, build-command fingerprint, manifest fingerprint,
toolchain identities, and dependency-root inputs. No credential value is read;
only the frozen credential mode and name boundary enters evidence.

Reproducibility compares a separately prepared second tree. Rust and TypeScript
remain byte-for-byte. Source-tag surfaces retain exact tree identity. ZIP and
tar normalization ignores only declared entry timestamps and known signature
entries; registry-generated metadata receives no implicit path or content
exclusion. Any other difference is a blocking mismatch.

The verifier rehashes artifact bytes and trees, reconstructs aggregate subjects,
and cross-checks checksum, SPDX package, and provenance subjects. Output is
create-only, preventing a prior evidence directory from being silently
overwritten. A controlled all-pass bundle covers 17/17 surfaces and fingerprints
to `4d1b6eb01c665b3f6c8d591c8103429078151eba81a4567ebf67f70a2b2c4a20`.
Thirty-three focused tests prove deterministic repeat output, bounded
normalization, byte mutation detection, companion-document tamper detection,
dirty-source rejection, missing-handoff rejection, and no false pass. This
fixture has synthetic contract authority only and cannot authorize a live build
or publication.

## CP4 dependency evidence and decision boundary

The noncontroversial dependency hardening is complete. The Python binding now
has a pip-tools 7.6.1 hash lock, Kotlin uses Gradle dependency locking and
strict SHA-256 verification metadata, and R uses an exact `renv.lock` graph for
R 4.3.3. The former npm advisory waiver is retired because its exact scope no
longer resolves to a finding. The existing VSCE license waiver remains exact
and visible.

OSV-Scanner 2.4.0 is authenticated by version and platform SHA-256 before it
can evaluate supported lock and manifest formats. Dart and Python license
evidence is derived from official registry metadata and exact package archives,
bound back to the governed locks, and registered as generated evidence. Its 49
records reproduce at fingerprint
`sha256:1a69546db84612835d1627a5bc572328e1d4f611bd21d53927635fcde1738e50`.
Composer and R retain native lockfile license evidence. Forty focused security
tests and all thirty local dependency-integrity checks pass.

The authorized non-distribution dispositions are exact and fail closed on
reachability expansion. Eleven package/root/version records cover JUnit 5.10.1
only on Maven or Gradle test classpaths, trove4j 1.0.20200330 only on the
enumerated Kotlin compiler/build configurations, and diffobj 0.3.8 only through
the locked R `testthat -> waldo -> diffobj` development path. Focused negatives
prove a Maven runtime scope, an extra Gradle runtime classpath, or moving
`testthat` from `Suggests` to `Imports` produces a blocking scope violation.

LuaRocks and CPAN now have primary-source evidence rather than unavailable
scanner rows. The Lua runtime lock resolves only `lua-cjson@2.1.0.10-1`; its
official rockspec SHA-256, immutable source commit
`96e6e0ce67ed070a52223c1e9518c9018b1ce376`, source archive, license file, and
commit-based OSV response all agree. Perl's Carton 1.0 snapshot resolves four
exact distributions under the official `perl:5.44.0` image digest and pins the
core-module closure. The evaluator authenticates CPANSA repository commit
`711ae63a6e3b523a2a49e9cca38d9aee8ffccd08`, content commit
`d72bc8e564db8a4cb96d6450d6f8fff032c25ffd`, and database SHA-256
`d8cdf2dd3d16c62e2c18bc38001daa8b14f6ba8414c2b8b23592492157812dfd`
before applying independently tested exact-version ranges. Missing database
records are distinguished from retrieval failure.

CPANSA's high label for `CPANSA-File-Temp-2011-4116` is reconciled to the exact
GitHub reviewed advisory for the same CVE, whose CVSS 3.1 score is 3.3 and
severity is medium. The source, advisory, CVE, score, and vector are all pinned
and reauthenticated; drift is incomplete, and this is not a waiver. The selected
Perl graph therefore has two visible nonblocking medium findings: that File-Temp
record and `CPANSA-perl-2026-15534`. The earlier CPAN::Audit range-inconsistent
result and unrelated Storable row are preserved as tool-discrepancy history, not
promoted as selected-graph evidence.

The regenerated license evidence now contains 54 exact records at fingerprint
`sha256:248f426df0e64c38252695eed556b1ae765e1324d72fc012441b3809084559ed`.
Fifty focused security tests pass. Live risk now reports 54 passed, zero failed,
zero unavailable, and the one existing VSCE waiver. The shipped Perl consumer
dependency surface resolves `FFI-CheckLib@0.31`, `FFI-Platypus@2.11`, and
`File-Which@1.27`. Exact root/package/version dispositions select
`Artistic-1.0-Perl` from the authoritative upstream dual-license evidence and
require the governing license material in every distributed payload. Any
version, root, metadata, material, package-set, release-surface, or reachability
drift fails closed. This is not a general Artistic/GPL allowlist or a legal
waiver.

## CP4 Rust distribution and package integration

The permanent Rust release surface is one publishable `strling` crate rooted at
the repository `Cargo.toml`. Its curated P17 crate root is
`core/src/lib_public.rs`, which compiles the canonical `core/src` implementation
directly while keeping compiler and kernel stages private. There is no
publishable `strling-kernel`, copied semantic source, repository-relative
consumer dependency, or second provenance subject. The retained `3.0.0`
manifest value is operational packaging input and does not ratify the Fourth
Edition version or support policy reserved for P20.

Cargo 1.75 packages exactly 70 intentional files. Two isolated builds are
byte-identical at
`8f6aa9366aecf90adc6123dd8586442bfb7fe0cbdc713ec75e41996d90a04ab3`;
fresh Windows and Linux consumers install the artifact without repository paths
and execute canonical compile and Simply smoke behavior. Public-contract checks
show only the declared dependency/module-origin correction and no accidental
compiler-stage exposure.

The remaining package corrections are contained: Python sdists include the
governed native rebuild source and produce a wheel from that sdist; Perl carries
an exact `MANIFEST` and license; Dart carries `LICENSE` and `CHANGELOG.md` and
passes its official publish dry run without warnings; TypeScript performs an
exact locked Cargo prefetch, includes `LICENSE`, reports zero npm vulnerabilities,
and packs 28 intentional files. A fixed JVM archive timestamp also makes two
clean Maven builds byte-identical and is bound by strict Gradle verification
metadata.

All registered generated artifacts now reproduce after the same-source
implementation-reference correction. The 54-entry license evidence fingerprint
remains
`sha256:248f426df0e64c38252695eed556b1ae765e1324d72fc012441b3809084559ed`.
All 27 public-contract surfaces, six adapter evidence suites, documentation
integrity, 135 focused security/supply-chain/public-contract tests, and five
Python packaging tests pass. At that point CP4 promotion remained fail-closed
until final profile, security, governance, and clean-tree evidence could be
reconciled against an exact checkpoint SHA.

## CP4 and FINAL closure

CP4 closes at clean checkpoint
`59aa27a233d056e6c2bac0bb29ba49ca7c0928fe`. The final reconciled evidence is:

-   Dependency integrity: 30 passed, zero nonpasses.
-   Secret and workflow security: four passed, zero nonpasses.
-   Live dependency and license risk: 54 passed, zero failed, zero unavailable,
    and existing waiver `WVR-SEC-VSCE-LICENSE-001` unchanged.
-   Fifty-four exactly reproducible license records at
    `sha256:248f426df0e64c38252695eed556b1ae765e1324d72fc012441b3809084559ed`.
-   One hundred focused final security, supply-chain, architecture, and
    performance-architecture tests passed.
-   Every registered generated artifact, all 27 public-contract surfaces,
    governance, Ruff, patch integrity, and documentation integrity across 206
    Markdown files passed.
-   The 17-artifact supply-chain manifest fingerprint remained
    `962277776e90764882783f29a382c10d0eeddc0635660128f7d016b001785f5a`;
    Local, Pull Request, Full, and Release contract profiles all passed with
    `publication_authorized=false`.

Every retained artifact class is governed by SHA-256 checksums, an SPDX 2.3 JSON
SBOM, and an in-toto Statement v1 with SLSA Provenance v1 binding exact source,
toolchain policy and executable evidence, build inputs, build command, artifact
identity, and dependency evidence. Rust and TypeScript remain byte-for-byte;
source-tag deliveries remain exact-source; other archives permit only their
enumerated normalized-equivalence fields. No production credential or registry
was used.

The clean Linux `55f996d4` checkpoint passed canonical Local 37/37. Its immediate
predecessor `c5c3b394` passed Pull Request 77/77 and reached Full with 115 passed,
zero failed, six honest environment unavailables, and the existing waiver after
all task-owned producers passed. Later changes only corrected the internal
performance artifact resolver and made synthetic supply-chain fixtures byte
stable across Windows and Linux; 29 focused performance tests and the 100-test
final set prove those corrections.

One exact native-Windows Local attempt at `59aa27a2` was interrupted without an
evidence artifact after the legacy Unix launcher delegated into this host's
already wedged WSL service. That attempt is not called green. Exact aggregate
Full/Release production evidence is recorded as a P18-T06 environment
carry-forward, together with revalidation of the current performance artifact
identity in its qualified host. This does not reopen P18-T04, authorize WSL as
performance evidence, suppress an inherited nonpass, or relax a gate.

The checkpoint chain is CP1
`8aa35fe681405dabb61fc79c2d258f90cc7fe8e7`, CP2
`af02bb85bdfe4ebcad824c738c13f4e0e67550c0`, CP3
`fdd23e016d7c846c5876ebecbd85ebfbe3db877b`, and CP4
`59aa27a233d056e6c2bac0bb29ba49ca7c0928fe`. The documentation-only FINAL
checkpoint is `9d665e8ad1ee914fcf57cb3b4de63a00cb84e75f`.

P18-T05 therefore exits **READY WITH RECORDED CARRY-FORWARD**. P18-T06 may start
from the clean final repository and run the full production-certification dry
run. Publication, release creation, registry upload, tag or branch push, and
production publication credentials remain unauthorized.

## External standards and platform trust

-   [SPDX 2.3 specification](https://spdx.github.io/spdx-spec/v2.3/)
-   [SLSA provenance model](https://slsa.dev/spec/v1.0/provenance)
-   [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
-   [`actions/attest` supported inputs and permissions](https://github.com/actions/attest)
