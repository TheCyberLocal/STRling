# Certification profile architecture

## Authority and scope

This document defines STRling's stable repository certification profiles and
their evidence contract. It governs engineering validation and does not define
STRling language, compiler, runtime, target, or package behavior.

`toolchain.json` is the machine-readable authority for the canonical operation
registry and ordered profile definitions. `tooling/quality.py` is the single
executor and result aggregator. The certification artifact schema governs the
durable machine-readable projection of an execution. Human output is a view of
that same structured evidence, never an independent certification authority.

The existing `check` and `certify` commands remain compatibility entry points.
They resolve to governed profiles rather than maintaining separate aggregate
implementations. Full and Release execute only in the authorized local
environment. Cloud automation verifies their signed evidence through the
canonical `./strling certification verify` path; it does not reinterpret or
re-execute those profiles.

## Canonical operation identity

A canonical operation has one stable registry ID, one implementation kind, one
network classification, and one structured-result policy. Component-capable
operations delegate to the existing per-component capability and command in
`toolchain.json`. Repository operations declare their command directly in the
registry. Neither a profile nor a workflow may redefine an operation command or
interpret its stdout as certification evidence.

An executed result is identified by the canonical operation ID and component.
The pair is unique within one profile execution. Ordering is significant and is
resolved only from the requested profile's ordered membership followed by each
member's declared target order. Repository operations produce one repository
result. Component operations produce one result per resolved target.

## Stable profiles

The following identities and purposes are permanent even as their governed
operation sets ratchet forward:

| Profile        | Purpose                                                                                                                                           | Network policy                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `local`        | Fast, deterministic developer feedback from offline-capable baseline operations.                                                                  | Network-backed operations are forbidden.                                                                                          |
| `pull-request` | Merge confidence, including every local guarantee plus applicable tests, generated-state checks, and documentation/example integrity.             | Network-backed operations are forbidden unless a later explicit policy revision can make them deterministic and least-privileged. |
| `full`         | Broad authoritative local certification across the currently governed component, exact-engine, and qualified-environment envelope.               | Governed network operations are permitted and remain unavailable when their authoritative environment is absent.                  |
| `release`      | The independently executed, no-reuse local pre-release envelope and stable input to signed certification attestation.                             | Governed network operations are permitted; release publication is outside this profile.                                           |

The release identity does not assert release readiness. A defined but
unimplemented or unavailable required member makes the result incomplete or
unavailable. Until a release-only capability exists, `release` may share the
same operation envelope as `full` while retaining a distinct identity and
fingerprint.

## Membership and ordering

Profile membership is declared only in the central profile definitions. A
profile entry references a canonical operation and, for component operations,
an ordered default target set. Duplicate operation entries, unknown operations,
duplicate targets, targets outside the component inventory, or a network member
forbidden by the profile are configuration errors.

Profiles do not contain commands or semantic result logic. Membership means the
canonical operation executes with its canonical result contract. Every selected
member is required unless a future contract explicitly introduces and names a
different requirement class. `not_applicable` is an explicit completed result,
not an omitted member.

The declared array order is the execution and artifact order. Filesystem,
mapping, set, locale, completion-time, and workflow-matrix ordering must not
affect it.

## Component scope and mandatory gates

An omitted component uses the profile member's declared target list. An
explicit component selects that target for each compatible component operation.
`all` selects the complete canonical target inventory in deterministic order.

Repository-scoped operations are mandatory global gates. They execute once in
their profile position regardless of component selection. Component selection
cannot remove, replace, or reinterpret them. An unknown component or an
incompatible profile/operation selection is a configuration error rather than
a partial execution.

## Result states and aggregation

Operation results preserve the existing governed states:

-   `passed`: the operation completed without a blocking finding;
-   `failed`: execution or governed evidence found a blocking failure;
-   `waived`: every otherwise-blocking finding is covered by an exact active
    waiver, with waiver identity retained;
-   `unavailable`: a required tool, environment, scanner, advisory source, or
    other authoritative capability could not execute;
-   `incomplete`: evidence is malformed, contradictory, or insufficient for the
    operation contract;
-   `not_applicable`: the operation deliberately has no meaningful action for the
    selected component;
-   `not_yet_configured` and `not_yet_enforceable`: the declared capability does
    not yet provide certifying evidence.

Aggregate precedence is:

```text
failed > incomplete > unavailable > waived > passed
```

`not_yet_configured` and `not_yet_enforceable` contribute `incomplete` to a
profile aggregate. `not_applicable` is neutral but remains visible in evidence.
An aggregate is `passed` only when every applicable required member passed.
`waived` is successful for process-exit purposes but remains distinct from
`passed`. `failed`, `incomplete`, and required `unavailable` are nonzero and
can never be converted to success by a profile, component selection, summary,
artifact upload, or workflow setting.

## Certification artifact ownership

The executor constructs the certification artifact directly from the exact
ordered `OperationResult` sequence used to compute aggregate status and process
exit. The artifact records repository commit and dirty state, profile identity
and definition fingerprint, component scope, operation identities and results,
tool/environment evidence, findings, waiver references, unavailable/incomplete
reasons, counts, and aggregate status.

Deterministic evidence is isolated from execution-instance metadata such as a
timestamp or machine description. A deterministic fingerprint covers only the
canonical deterministic evidence projection. Timestamps and local paths must
not change profile identity or evidence fingerprints.

Artifact generation does not scan stdout. An operation with a nested structured
contract, including security, documentation, or exact-engine certification,
must validate that contract, operation identity, status, and exit code before
its evidence is accepted. Artifact schema validation is mechanical.

## Definition identity and result identity

Profile-definition identity is deterministically available before a profile
executes. The canonical `profile_source_identity` producer derives it from the
profile and operation registries, governed schemas, producer contracts, and the
current source identity. Its checked-in definitions bundle and per-invocation
evidence have the explicit role `identity-only`; they contain no pass status,
benchmark sample, target result, adapter result, or readiness claim.

Certification-result identity exists only after execution. Full and Release
artifacts bind the exact definition identity they executed, but a pre-execution
authority gate may not depend on a previous successful Full or Release result.
The governed certification dependency graph is acyclic:

```text
profile and producer definitions
  -> identity-only renewal
  -> pre-execution authority validation
  -> Full result
  -> Release result
  -> signed local attestation
  -> cloud integrity verification
```

Result-only projections, including target/adapter execution matrices, may be
validated and published after the producing profile completes. They cannot be
used as prerequisites for that same profile. A stale, partial, prior-source,
wrong-profile, contradictory, or result-substituted identity artifact fails
closed.

## Exact-engine certification

Full and Release include canonical `pcre2_runtime_certification` and
`ecmascript_runtime_certification` repository operations. The PCRE2 gate
consumes only explicitly supplied exact PCRE2 10.42 and 10.43 8-bit libraries.
The ECMAScript gate consumes only the explicitly supplied Node v22.23.2 Linux
x64 executable derived from the verified official distribution, validates its
exact executable SHA-256 plus Node v22.23.2 and process-reported V8
12.4.254.21-node.56 identities, and executes only the fixed bounded harness.
Both preserve
`certification-result-v1` evidence in the profile artifact. Missing or
mismatched engines produce `unavailable`; component selection, profile
rendering, and CI cannot scope either operation away or reinterpret it as
passing.

The operation is offline and deterministic with respect to semantic evidence.
Their structured results fingerprint exact binaries, profiles, corpora,
harnesses, platforms, configurations, bounded generated cases, runtime
observations, and repeated semantic digests. Raw timing observations remain
visible but are excluded from deterministic evidence digests. Local and Pull
Request omit both operations so their bounded developer and merge-confidence
purposes remain unchanged.

The adversarial semantic audit uses a complementary two-part registration. Its
exact-engine `--write` and `--strict` executions produce or directly verify
current empirical observations. The enforced generated-family `--check` binds
those observations to every registered source input and requires zero semantic,
target-compile, requirement, or diagnostic-delivery findings. Because
`generate_check` belongs to both Local and Pull Request, stale evidence or a
restored finding fails those deterministic profiles. Pull Request retains the
exact real-engine operation for canonical local execution, and Full and Release
include it in the signed evidence root. Normal cloud verification does not run
the Pull Request profile, provision those engines, or repeat the corpus.
Empirical observations remain certification evidence and never become normative
semantic authority.

## Authoritative local attestation and cloud verification

`governance/local-certification-trust.json` is the trust policy. It names the
authorized Ed25519 certifier public key, SSHSIG namespace, required Full and
Release profiles, sole permitted waiver, durable bundle location, and the exact
paths permitted in a post-certification evidence-only closure commit. Private
keys and publication credentials are never repository content.

`./strling certification attest` accepts terminally successful, clean-source
Full and Release artifacts for the same commit. It validates their governed
schemas, aggregates, producer statuses, profile versions and fingerprints,
sample counts, real-engine observations, runtime identities, invocation IDs,
and waiver inventory. It copies selected evidence into one immutable bundle,
hashes every file with SHA-256, computes a deterministic root over all governed
claims and file hashes, and signs that payload with SSHSIG Ed25519. The command
immediately verifies its own output.

`./strling certification verify` independently validates the trust policy and
attestation schemas, authorized signer and signature, evidence root and every
file hash, exact certified commit and Git tree, profile and operation registry
fingerprints, kernel and interop trees, target profiles, runtime identities,
producer aggregates, authenticated sample counts, real-engine counts, waivers,
and invocation bindings. Evidence for an older source, another profile, another
invocation, a changed or missing file, an untrusted signer, or a nonpassing
producer fails closed with the exact mismatch. There is no latest-passing lookup
and no fallback to expensive cloud certification.

The workflow state vocabulary remains deliberately distinct:

```text
LOCALLY_CERTIFIED
  -> CLOUD_VERIFIED
  -> PUBLISHABLE
  -> PUBLISHED
  -> PUBLICLY_VERIFIED
```

Only the first two states belong to this certification architecture. Cloud
verification proves that trusted evidence for the exact source is authentic and
unchanged; it grants no publication authority. P20 owns package derivation,
publication authorization, registry actions, and public verification.

For untrusted pull requests, `pull_request_target` executes only the verifier and
trust policy from the trusted base revision. The candidate checkout is treated
as data. Full, Release, performance sampling, real-engine execution, and the
multi-language certification matrix are not recomputed in cloud CI. A later
evidence-only closure commit is accepted only when every changed path matches
the trust policy; any semantic, compiler, profile, tooling, or workflow change
requires fresh local certification.

## Human-summary ownership

The human-readable summary is rendered from the completed certification
artifact/result model. It reports profile, repository state, aggregate result,
passed and failed operations, waived findings, unavailable or incomplete
operations, and the relevant next action. There is no second result-counting or
status-derivation path.

## Profile evolution

Future work adds a canonical operation to the registry, tests its result
contract, and appends its ID to the appropriate ordered profiles. It does not
change the executor, aggregate precedence, artifact contract, component bypass
rules, or stable profile meanings.

Profile definitions carry a version and deterministic fingerprint. Membership,
ordering, target scope, requirement, or network-policy changes advance the
definition version and fingerprint. Implementation refactoring that preserves
those fields does not. Later phases may ratchet a profile only toward its stated
purpose: local remains bounded and offline-capable; pull-request retains local
guarantees; full remains broad; release remains the highest pre-release
envelope. Removing a gate requires an explicit governed policy change and may
not be hidden in CI.
