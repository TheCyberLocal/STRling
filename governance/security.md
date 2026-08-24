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
`full` and `release` can select the network-backed risk operation. OSV-Scanner
2.4.0 is accepted only through the configured executable path after its
platform SHA-256 and reported version match policy. CI contains no separate
scanner logic or suppression behavior. Any remaining `UNAVAILABLE` coverage
therefore remains a real certification failure rather than being hidden in
workflow code or artifact upload behavior.

## Dependency inventory

The repository contains npm, Cargo, Dart Pub, Composer, Bundler, Go modules,
SwiftPM, NuGet project files, Maven, Gradle, Python requirements/PEP 517,
LuaRocks, CPAN, and R package metadata, plus C/C++ build-time dependency
declarations. The machine-readable inventory classifies each root as actively
governed, transitional but still built or packaged, or tooling-only. It records
whether a lockfile is required, intentionally not used, or absent as known
transitional debt.

Lock-complete roots include the three npm roots, Cargo roots, Dart, Composer,
Bundler, the Python binding hash lock, the Kotlin Gradle lock plus strict
dependency-verification metadata, the Lua runtime `luarocks.lock`, the Perl
Carton snapshot, and the R `renv.lock` graph. Go and Swift
currently declare no external packages and therefore do not require empty
lockfiles. Maven, the language-server Python requirements, NuGet project
references, and system-managed C/C++ dependencies remain visible
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
source, and retrieval state. High, critical, and unknown-severity findings
block; lower severities remain visible as nonblocking evidence. Scanner failure,
unavailable advisory data, malformed output, and partial root coverage are never
passed. Dependencies are not upgraded or regenerated by an audit.

The network operation runs `npm audit` against all three governed npm lockfiles,
uses `cargo-audit` 0.22.2 against the Cargo locks, and uses authenticated
OSV-Scanner 2.4.0 for its supported Dart, Composer, Bundler, NuGet, Maven,
Gradle, Python, and R inputs. A missing executable, mismatched scanner version,
platform digest mismatch, malformed result, or unsupported input is never a
pass. Go and Swift roots pass only because their integrity operations prove
they have no external dependencies. LuaRocks binds its exact locked rock to the
official rockspec, immutable source commit, source archive and license hashes,
then queries OSV by that commit. CPAN binds Carton 1.0 snapshot distributions to
their primary archives and evaluates the exact selected distribution and pinned
Perl 5.44 core-module graph against a commit- and SHA-256-pinned CPANSA database.
An absent CPANSA distribution record means the pinned database contains no
advisory record for that exact distribution; malformed ranges or records remain
incomplete. Advisory ranges are bound to exact resolved versions; advisory
payload fields are evidence and are not normative policy.

The CPANSA File-Temp record classifies CVE-2011-4116 as high, while the reviewed
GitHub Advisory Database record classifies the same CVE as medium with CVSS 3.1
score 3.3. Policy records an exact advisory/CVE/source/vector correction and the
network operation reauthenticates every field before use. This is evidence
reconciliation, not a waiver or threshold change; any identity or vector drift
fails closed.

License classification is metadata policy, not legal advice. SPDX identifiers in
the permitted set pass; identifiers in the prohibited set fail; missing,
ambiguous, or unclassified metadata remains unknown and blocks until classified
or governed by an exact waiver. Package metadata is evidence, not normative
policy. An exact scoped permit names the ecosystem, package, version, license
expression, dependency roots, and required root usage. It is not a global
license classification: the same dependency reachable from any other root or
usage is a blocking scope violation.
npm license evidence comes from lockfile v3 package entries. Cargo license
evidence comes from the selected manifest root's reachable graph in
`cargo metadata --locked --offline`; unrelated workspace members that merely
share the lockfile are excluded. A missing selected root, malformed resolve
graph, or unpopulated Cargo cache is not a pass. Composite and legacy expressions
are classified only by exact policy entries. A top-level SPDX `OR` passes only
when at least one complete branch is already permitted; this expression rule
does not add either branch to the allowlist. Composer and R use exact native
lock metadata. Dart, Python, LuaRocks, and CPAN use the registered
`governance/dependency-license-evidence.json` projection, whose official
registry archive hashes, license-file hashes, lock bindings, and document
fingerprint are revalidated before use. The exact
`LIC-CARGO-LIBFUZZER-SYS-0.4.13` disposition permits
`libfuzzer-sys@0.4.13` with `(MIT OR Apache-2.0) AND NCSA` only through the
tooling-only `interop-fuzz-cargo` root. Reachability through `interop-cargo` or
any other runtime root fails. The sole metadata correction is scoped to npm
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

One security waiver remains active and expires on 2026-09-10:

-   `WVR-SEC-VSCE-LICENSE-001` covers only ten enumerated VSCE signing
    package/version bindings whose metadata remains `SEE LICENSE IN LICENSE.txt`.

The record retains exact scope, owner, review context, rationale, expiry, and
replacement work. It does not classify the unknown license as permitted. The
former `WVR-SEC-NPM-TOOLING-001` waiver was retired on 2026-08-24 after every
enumerated npm advisory binding resolved and authoritative npm audit returned no
matching finding; retaining it would have failed closed as stale scope.

## Certification environment acquisition

Certification may acquire the exact governed scanners and official package
manager prerequisites without making them repository dependencies. Their
version, executable identity, and required hashes remain evidence inputs.
Gradle is repository-managed through its wrapper. Scanner presence alone never
proves coverage: the selected input must be supported, resolved, and represented
in structured output. LuaRocks and CPAN use their governed primary-source paths
rather than treating package-manager executable presence or a scanner's missing
database row as proof of safety.
