# Releasing STRling

[← Back to Developer Hub](index.md)

The authoritative Fourth Edition version, support, compatibility, release,
publication, and post-publication rules are maintained in
[`governance/release-policy.json`](../governance/release-policy.json). Read its
generated [`Release Policy`](release-policy.md) projection before changing
package metadata or release automation.

## Current preparation boundary

STRling `4.0.0` is the ratified product release identity. Checked-in package
metadata still projects `3.0.0` during release preparation. P20-T02 owns the
atomic manifest and dry-run pipeline rebuild that changes that projection; do
not edit an individual package version to get ahead of it.

The canonical projection check is:

```bash
python3 tooling/sync_versions.py --check
python3 tooling/release_policy.py --check
```

The Python manifest is no longer product-version authority. Swift and Go use
product-mapped immutable tags; the Lua rockspec and Ruby gemspec use governed
release-time materialization/sentinel rules; the VS Code extension has an
independent Preview version and must state its exact compatible product range.

## Release lifecycle

Release work advances only through the machine-registered states:

```text
source candidate
→ deterministic verified
→ certified
→ publishable
→ published
→ verified
```

Full and no-reuse Release certification are required for a stable candidate.
They execute once in the authorized qualified local environment and are bound
to an immutable SHA-256 evidence root signed by the governed local certifier.
Normal cloud CI runs `./strling certification verify`: it checks the trusted
signature, exact source and profile identities, every evidence hash, producer
aggregates, runtime declarations, samples, and waivers without repeating Full,
Release, real-engine execution, or performance sampling. Certification does not
make a release publishable. P20-T05 may publish only
after explicit owner authorization naming the exact version, source SHA,
artifact identities, destinations, and run. Registry uploads, Marketplace
publication, GitHub Releases, and production release tags are all publication.

The canonical structured product-certification entrypoint is:

```bash
python3 tooling/product_certification.py --run-profile --artifact target/certification/product-certification.json --report target/certification/product-certification.md
```

Its machine artifact aggregates the registered profile results and evidence;
it does not confer `publishable` state or authorize any public action.

The canonical local evidence workflow is:

```bash
./strling profile full --artifact target/certification/profile-full.json
python3 tooling/production_certification.py \
  --profile release --all --no-reuse --plain
./strling certification attest \
  --full-artifact target/certification/profile-full.json \
  --release-artifact artifacts/production-certification/<source>/<run>/profile-release.json \
  --private-key /secure/path/to/authorized-certifier \
  --certifier-id strling-local-release-certifier-2026-01 \
  --output-dir tests/certification/hardened-core/1.0/current
./strling certification verify \
  --bundle tests/certification/hardened-core/1.0/current
```

The private key is never checked in. Adding or rotating a trusted public key is
an owner-reviewed governance change. Required evidence remains in the signed
checked-in bundle; large build trees and disposable execution scratch remain
outside Git. A failed verification is repaired by deliberately producing and
signing fresh same-source evidence, never by cloud fallback or accepting a bare
hash.

P20-T02 may build, inspect, and dry-run packages. P20-T04 may prepare and
certify a candidate. Neither task may use production publication credentials
or create a public coordinate.

## Immutable candidates and releases

Public release candidates use `MAJOR.MINOR.PATCH-rc.N`. Published prerelease
and stable coordinates are immutable and are never overwritten or reused. A
source, dependency, generated-output, artifact-content, or waiver change after
an RC forces a new RC and fresh required certification.

Stable promotion uses the terminal RC source commit. Stable artifacts are
rebuilt from the product policy, compared for approved coordinate-only
differences, and certified again; RC evidence is not treated as publication
authorization.

## Public verification

Publication success leaves a release in `published`, not `verified`. P20-T03's
contract independently fetches every public artifact, verifies exact metadata
and identity, installs into clean consumer environments, runs public API/CLI
smoke checks, confirms binding/core compatibility, resolves provenance and
SBOM associations, and tests the published installation documentation.

If verification fails, stop remaining publication when safe, preserve the
exact partial state, and fix forward under a new immutable version after fresh
certification and authorization. Never silently republish the same coordinate.

The sole currently accepted waiver is `WVR-SEC-VSCE-LICENSE-001`. It remains
explicitly scoped and does not grant publication authority.
