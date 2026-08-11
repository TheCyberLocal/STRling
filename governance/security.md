# Baseline repository security policy

governance/security-policy.json is the normative machine-readable policy for
repository security. Generated reports are evidence only and cannot amend this
policy, the dependency inventory, or a waiver.

## Contract and boundaries

The security baseline covers tracked dependency manifests and lockfiles,
dependency advisory and license evidence where an authoritative scanner can
produce it, tracked content, and GitHub Actions workflows. It does not cover
SBOM generation, artifact provenance or signing, registry credentials, or
release publication. It has no authority over STRling language semantics,
compiler behavior, target lowering, adapters, product APIs, or package versions.

Security operations use the root quality implementation and emit the versioned
contract in governance/schemas/security-result.schema.json. Local and CI
execution call the same operation code. Operation identifiers, check identifiers,
finding codes, input paths, scanner identity, and deterministic local evidence
are stable. Advisory retrieval timestamps and database revisions are explicitly
time-varying evidence and are excluded from structural determinism comparisons.

The result states are:

-   passed: every configured check completed, its evidence was usable, and it
    produced no blocking finding.
-   failed: at least one unwaived blocking finding or malformed governed input
    exists.
-   waived: the only otherwise-blocking findings are covered by exact, accepted,
    unexpired governance waivers.
-   unavailable: a required scanner, package manager, advisory service, or local
    dependency inventory could not be reached or executed.
-   incomplete: configured coverage did not finish or could not produce the
    evidence required to decide pass or fail. Malformed scanner output is
    incomplete, never passed.

failed, unavailable, and incomplete are hardgate failures. A mixed operation
uses the most severe state in that order. waived is successful only for the
exact governed scope and stays visible in structured output.

## Root command and CI integration

`toolchain.json` registers all security operations as canonical repository
hardgates. `./strling check` runs the deterministic, network-free dependency
integrity and tracked-content/workflow operations. `./strling certify` runs
those same implementations and adds the network-backed dependency-risk
operation. Selecting an individual component cannot bypass these hardgates.

Security hardgates emit the security-result contract as nested
`structured_result` evidence in root JSON output. The root adapter verifies that
the operation ID, five-state status, and process exit code agree. A malformed or
contradictory result becomes `INCOMPLETE`; `WAIVED` remains visible and
successful, while `FAILED`, `UNAVAILABLE`, and `INCOMPLETE` fail the aggregate.
The root aggregate status preserves those distinctions.

GitHub Actions invokes the selected canonical profile after installing the
exact `cargo-audit` 0.22.2 pin. Pull-request routing remains offline; only
`full` and `release` can select the network-backed risk operation. CI contains
no separate scanner logic or suppression behavior. Current legacy
`UNAVAILABLE` coverage therefore remains a real certification failure rather
than being hidden in workflow code or artifact upload behavior.

## Dependency inventory

The repository contains npm, Cargo, Dart Pub, Composer, Bundler, Go modules,
SwiftPM, NuGet project files, Maven, Gradle, Python requirements/PEP 517,
LuaRocks, CPAN, and R package metadata, plus C/C++ build-time dependency
declarations. The machine-readable inventory classifies each root as actively
governed, transitional but still built or packaged, or tooling-only. It records
whether a lockfile is required, intentionally not used, or absent as known
transitional debt.

Lock-complete roots are the three npm roots, both Cargo roots, Dart, Composer,
and Bundler. Go and Swift currently declare no external packages and therefore
do not require empty lockfiles. Maven and Gradle pin direct declarations but do
not lock transitives. Python binding and LSP requirements, LuaRocks, CPAN, R,
NuGet project references, and system-managed C/C++ dependencies are visible
transitional coverage gaps. The quality Python requirements are exact but not
hash-locked. This baseline does not claim those roots are lock-complete.

Deterministic integrity checks do not access the network or rewrite dependency
state. They validate inventory completeness, required files, parseability,
manifest/lock agreement where the format exposes it, resolved package integrity
metadata where applicable, and prohibited floating declarations under each
root's declared policy. Native frozen verification may supplement these checks
only when it is read-only and available; its absence cannot be described as a
successful native verification.

## Secrets and workflows

Tracked-content scanning rejects private-key material, high-confidence access or
API tokens, embedded repository credentials, and obvious credential assignments.
Tests construct nonfunctional markers at runtime; functional credential-shaped
values must never be tracked as fixtures. False positives require an exact
governed waiver. Broad path suppression is not policy.

Every workflow must declare explicit read-only default permissions. Jobs may
elevate only named capabilities that their release purpose requires. Validation
jobs may not receive secrets or write permissions. Privileged publication jobs
remain in the delivery workflow. Action dependencies must use immutable full
commit SHAs, and checkout credentials must not persist except in the narrowly
identified tag-push jobs that require repository authentication. Mechanically
detectable secret interpolation into shell command text is prohibited; secrets
belong in step environment variables.

## Dependency risk

Advisory auditing is network-dependent and certification-only. Scanner command
shape and parsing are deterministic, while advisory data is not. Results identify
the ecosystem, package, resolved version, advisory identifier, supplied severity,
source, and retrieval state. High and critical findings block; lower or unknown
severity remains visible according to scanner evidence. Scanner failure,
unavailable advisory data, malformed output, and partial root coverage are never
passed. Dependencies are not upgraded or regenerated by an audit.

The network operation runs `npm audit` against all three governed npm lockfiles
and uses `cargo-audit` 0.22.2 against both Cargo locks. The Cargo scanner is an
exact repository tool pin; a missing executable is `UNAVAILABLE` and a mismatched
version is `FAIL`. Go and Swift roots pass only because their integrity operations
prove they have no external dependencies. Every other configured ecosystem emits
explicit `UNAVAILABLE` vulnerability and license checks until an authoritative
repository scanner is governed for it. Those checks remain aggregate blockers.
Advisory ranges are bound to exact locked versions; advisory payload fields are
time-varying evidence and are not normative policy.

License classification is metadata policy, not legal advice. SPDX identifiers in
the permitted set pass; identifiers in the prohibited set fail; missing,
ambiguous, or unclassified metadata remains unknown and blocks until classified
or governed by an exact waiver. Package metadata is evidence, not normative
policy.
npm license evidence comes from lockfile v3 package entries. Cargo license
evidence comes from `cargo metadata --locked --offline`, so an unpopulated Cargo
cache is `UNAVAILABLE`, not pass. Composite and legacy expressions are classified
only by exact policy entries. The sole metadata correction is scoped to npm
`exit@0.1.2`: its published legacy `licenses` field identifies MIT while the lock
entry omits `license`. `SEE LICENSE IN LICENSE.txt` remains unknown; the engine
does not infer a permissive classification from file contents.

## Waivers

Security exceptions use governance/schemas/waiver.schema.json and
governance/waivers/. A security waiver must be accepted, name the exact rule or
finding code, enumerate exact paths and dependency/advisory scope as applicable,
identify an owner and review context, justify the risk, specify creation and
expiry dates, and state planned remediation. Expired, unknown, malformed,
over-broad, or mismatched waivers fail. A match is a Cartesian set of exact
finding fields; every declared combination must exist, every matched check input
must equal the declared path scope, and overlapping matches fail.

Two security waivers are active as of 2026-08-11 and both expire on 2026-09-10:

-   `WVR-SEC-NPM-TOOLING-001` covers only the 53 enumerated high/critical npm
    advisory bindings reached through development or packaging chains.
-   `WVR-SEC-VSCE-LICENSE-001` covers only ten enumerated VSCE signing
    package/version bindings whose metadata remains `SEE LICENSE IN LICENSE.txt`.

The records retain exact scope, owner, review context, rationale, expiry, and
replacement work. They do not classify the unknown license as permitted.

## Initial environment limitations

The local environment has npm, Cargo, Go, Maven, Composer, Dart, .NET, Bundler,
SwiftPM, LuaRocks, R, and CPAN tooling, but no cargo-audit executable. Gradle is
available through the repository wrapper rather than a global executable.
Advisory-network availability was not treated as evidence during inventory.
These facts are coverage inputs, not passing audit results.
