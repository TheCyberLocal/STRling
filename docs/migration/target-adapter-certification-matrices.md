# Target and adapter certification matrices

[← Back to Architecture](../architecture.md)

This migration record defines the evidence boundary for STRling 4.0 target and
adapter certification. It does not create language semantics, target-profile
facts, adapter behavior, package policy, or consumer-facing support promises.

The target denominator is the five immutable profiles under
`spec/targets/profiles`: PCRE2 10.42, PCRE2 10.43, ECMAScript 2024, and Python
`re` 3.11 text and bytes. Their semantic execution evidence remains owned by
the existing exact-engine, shared-corpus, standard-library, and portability
certifiers.

The adapter denominator is the seventeen language rows in binding-support
certification evidence. Twelve rows currently carry `supported_candidate`
dispositions and five carry `preview_candidate`; no row is Legacy. These are
certification tiers, not permanent public support policy. P20-T01 retains that
policy authority.

P18-T02 derives one deterministic machine evidence family and one
documentation-ready projection from a minimized, checked Full-profile source
bundle. Every cell names an exact engine/profile/version or
adapter/package/runtime/platform coordinate, its tier-appropriate obligation,
an explicit status, evidence links and fingerprints, and the last certified
commit. Missing or stale cells fail closed when profiles, corpus versions,
adapters, package coordinates, or certification tiers change.

The matrices will not execute or modify product semantics. They will preserve
`passed`, `failed`, `unavailable`, `not_applicable`, `waived`, and
`unsupported` distinctions and will never label an unexecuted cell supported.
F# and Python package findings remain exact evidence dispositions. Python
source-distribution repair belongs to P20-T02, dependency-risk remediation to
P18-T05, permanent support tiers to P20-T01, and global regex-engine research
to the external `regex-conformance` repository.

The current governed matrix is checked at commit
`4a195240a9889996d6c665d42eccf365876cb4da`. All 35 target cells pass. Of 80
adapter cells, 78 pass and two Python cells fail: package installation and the
quality profile. Both failures preserve the Full-profile deferral that Python's
build and pytest requirements lack a governed version constraint or lockfile;
P20-T02 owns that repair. The matrix does not reinterpret the separate
repository dependency-risk failure owned by P18-T05.
