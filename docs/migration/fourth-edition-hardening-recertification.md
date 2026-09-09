# Fourth Edition hardened-core recertification

## Candidate and authority

V4-H08 started from clean `dev` checkpoint
`61338f1581e8ecf436fc59acbfae28a603a90382`, identical to fetched
`origin/dev`. The machine profile authority is `toolchain.json`; release-state
and waiver authority is `governance/release-policy.json`; execution and result
semantics are governed by `governance/certification-profiles.md`.

The registered lifecycle requires the following sequence for this final
hardened-core boundary:

1. exact clean-source Local and Pull Request deterministic preflight;
2. one canonical Full 1.29.0 execution through the supported WSL aggregate
   controller, with its governed sampled operation delegated to the
   baseline-authenticated native Windows host;
3. after terminal green Full, a separate clean-worktree Release 1.29.0
   execution through the governed no-reuse production launcher for the same
   source SHA, with no result or performance-sample reuse;
4. creation of one trusted, signed local evidence bundle for both results;
5. cheap cloud verification of signature, source, contract, evidence, waiver,
   runtime, invocation, and aggregate integrity;
6. final adversarial, waiver, identity, generated-state, and clean-tree review.

Full and Release currently share the same 125-result operation envelope but
retain distinct profile identities and independently produced evidence. Each
includes exact target runtimes, interop/runtime matrices, deep-quality checks,
networked dependency risk, supply-chain dry runs, and the native governed
performance/resource producer. The active performance baseline authenticates
this native Windows machine, so a hosted Linux runner cannot substitute for
the sampled operation. Certification never authorizes publication.

## Steering amendment and architecture audit

The H08 steering amendment makes the qualified local environment authoritative
for expensive certification. The previous workflows provisioned exact engines
and recomputed Pull Request, Full, Release, runtime, and sampled evidence in
GitHub. Existing profile artifacts already bound source, profile definitions,
operation results, runtime declarations, sample consumption, and deterministic
evidence fingerprints. Existing release-supply-chain tooling already used
SHA-256 and in-toto/SLSA statements for package artifacts. Neither mechanism,
however, authorized a local certifier, signed a complete certification root, or
prevented a contributor from hashing fabricated evidence.

The bounded extension adds one trust policy and one attestation contract rather
than a parallel result system. Full and Release remain the sole expensive result
authorities. `./strling certification attest` validates those existing profile
artifacts, collects durable evidence, binds the exact source commit/tree,
profile/operation registries, kernel and interop trees, all target profiles,
exact runtimes, producer invocations, waivers, authenticated samples, and the
real-engine result, then signs the deterministic SHA-256 root with the governed
Ed25519 SSHSIG identity. The private key remains outside Git.

Normal cloud CI uses the verifier and trust policy from the trusted base
revision and treats the candidate checkout only as data. It rejects stale
source, wrong profile or invocation, missing/changed files, aggregate
contradiction, unapproved waiver, malformed signature, or untrusted certifier.
It performs no Full/Release execution, performance sampling, real-engine corpus,
or multi-language certification matrix. Delivery consumes the same verifier;
successful verification establishes `CLOUD_VERIFIED`, never `PUBLISHABLE`.

The evidence bundle is added in a post-certification closure commit. The trust
policy permits only the bundle, this record, the migration ledger, and active
task-state update in that closure. The verifier proves the certified commit is
an ancestor and rejects every other changed path, preventing a record commit
from silently changing the hardened source. P20 must bind packages back to the
recorded certified source through the existing supply-chain provenance path.

The registered Pull Request profile retains its exact-engine operation for the
canonical local preflight. Only its automatic cloud recomputation is replaced;
the profile contract and semantic hardgate are not weakened.

## Deterministic preflight correction

The first exact-SHA Pull Request preflight, hosted run `34213813721`, passed 77
of 78 operations and stopped before sampled certification. The sole failure was
not semantic: the enforced `dependency-license-evidence` generated-family
`--check` rebuilt evidence over the network inside the nominally offline Pull
Request profile, and a pub.dev request reset.

The correction makes check mode validate the checked-in 54-entry projection
without network access. It verifies document identity, canonical ordering,
fingerprint, required fields, duplicate absence, complete Dart/Lua/CPAN/Python
lock identities, and archive hashes bound by the locks. Network-authenticated
official archive retrieval and license classification remain the unchanged
registered `--write` producer. The exact producer reproduced fingerprint
`sha256:248f426df0e64c38252695eed556b1ae765e1324d72fc012441b3809084559ed`
without changing the governed output.

The first Full attempt at correction checkpoint `9f85a00c` reached the governed
native performance producer but the Windows host did not satisfy the unchanged
quiet-host conditioning policy. Its atomic result records zero started
coordinates and zero authenticated samples. The remaining already-doomed
aggregate work was stopped; this was an environmental pre-sample attempt, not a
measured failing attempt and not certification evidence.

The next clean candidate Full run completed 122 operations before two newly
published dependency/security prerequisites failed and the native performance
producer rejected a Windows build-identity change before sampling. The result
recorded zero started coordinates and zero authenticated samples. The
dependency repair updates only the affected transitive locks, classifies the
exact JUnit BOM through the existing test-classpath policy, and regenerates the
Perl Makefile with the governed WSL Perl rather than consuming a
Windows-generated ignored build file. The remaining Windows identity mismatch
is governed by the existing immutable environment-rollover boundary; it cannot
be papered over or treated as a performance pass.

## Certification result

Final deterministic, Full, Release, exact-engine, performance, waiver, and
repository identities are recorded after the canonical runs complete. The
source baseline named here will be the exact semantic-core authority for
P20-T02; publication preparation may change packaging machinery but may not
silently change this certified core.

No package is published, no release tag or GitHub Release is created, `main`
is unchanged, and P20-T02 does not begin in this task.
