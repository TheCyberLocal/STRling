# Emission diagnostic delivery

V4-H05 closes the final diagnostic-integrity gap in the bounded pre-Fourth-
Edition semantic-hardening campaign. The implementation changes no canonical
language meaning and no target lowering. It makes the existing `CompileResult`
failure contract authoritative when a target lowerer or serializer already has
structured diagnostic evidence.

## Reproduced boundary

At starting checkpoint `73cb34e443e605f18033887867958b2048c1b65d`, exact
count 65,536 for either governed PCRE2 profile reaches post-lowering capability
evaluation and produces `STRL-PCRE2_LOWERING-0014`. The diagnostic is an error
with `target_profile` severity basis, `target_lowering` phase,
`target_capability` category, exact profile/revision prose, affected Semantic IR
node advice, and source span `[46, 99)` in
`src:adversarial.pcre2-serialization-limit`.

The first loss occurs in `core/src/kernel.rs::project_target_artifact`: each
typed target failure was converted to `KernelCompileError::StageFailure` using
only its display string. The CLI consequently exited 70, wrote no stdout, and
printed only a generic stage failure. No `CompileResult` existed and
`TargetArtifact.emission_diagnostics` was unreachable. Both PCRE2 revisions
account for the two final audit findings.

## Authoritative failure contract

Source parsing, analysis, portability planning, lowering, and serialization may
all discover valid compilation failures. The disposition depends on the
producer result, not merely on which stage found it:

| Producer state                                                                        | Canonical public state                                                                   |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| One or more valid structured error diagnostics                                        | `CompileResult.outcome = failed`, diagnostics retained, artifact absent, CLI exit 2      |
| Successful target artifact with non-fatal emission diagnostics                        | successful `TargetArtifact`; every artifact diagnostic also occurs in result diagnostics |
| Typed target failure with no diagnostic payload                                       | internal `KernelCompileError::StageFailure`, CLI exit 70                                 |
| Malformed diagnostic, contradictory fatal diagnostic plus artifact, or invalid result | fail-closed contract/internal error; never publish the artifact                          |
| Serializer panic or process/tooling failure                                           | genuine internal/tooling failure outside the normal compile-failure envelope             |

The kernel now projects all current PCRE2, ECMAScript, and Python `re` lowering
and serialization failures through one rule. A non-empty diagnostic vector is
preserved as an artifact-projection failure, merged with the target-neutral and
portability diagnostics, canonically sorted, and validated by `CompileResult`.
An empty vector remains a stage failure so a broken producer cannot fabricate a
normal diagnostic result.

The failed result retains requested complete semantics, analysis, and
portability evidence when those stages succeeded. Error diagnostics always
suppress `artifact`; an incomplete artifact is never used as a diagnostic
carrier. JSON CLI output is the parseable failed result on stdout with exit 2.
Human output says compilation failed and renders each canonical code and
message. Interop returns the same failed result as a completed adapter response;
bindings do not synthesize diagnostics.

## Adversarial hardgate

Exact-engine execution remains the registered producer of empirical evidence
and remains distinct from normative specification authority. Now that the
finding inventory is empty, the existing enforced
`adversarial-semantic-observations` generated family is the deterministic
regression gate:

-   `python3 -m tooling.adversarial_semantic_audit --write` executes the 41
    programs twice on the pinned engines and may write only a zero-finding run;
-   `python3 -m tooling.adversarial_semantic_audit --strict` executes current
    source and fails for any finding;
-   `python3 -m tooling.adversarial_semantic_audit --check` verifies the
    checked-in evidence schema, raw identities, current audit-input digests,
    deterministic reconstruction, and zero findings without invoking engines.

The generated-artifact verifier runs that enforced offline check through the
existing `generate_check` operation in both Local and Pull Request. A later
change to any registered kernel, profile, corpus, audit, or harness input makes
the evidence stale; any preserved semantic, target-compile, requirement, or
diagnostic finding also fails the gate. This reuses the canonical generated-
artifact architecture instead of duplicating real-engine certification.

## Certification boundary

V4-H05 requires focused target, protocol, CLI, interop, audit, architecture,
governance, generated-artifact, documentation, Local, and Pull Request checks.
The registered Full and Release profiles own exact-runtime and sampled release-
candidate certification. This checkpoint is not a release candidate and does
not change semantic meaning, target behavior, performance baselines, ceilings,
samples, or isolation policy. Fresh Full/Release evidence therefore remains a
P20 release-candidate obligation after publication-pipeline work changes the
candidate; V4-H05 does not consume or invent sampled certification.

## Campaign accounting

The immutable historical baseline remains 148 findings: 25 requirement-
soundness findings resolved by V4-H03, 121 semantic/target-acceptance findings
resolved by V4-H04, and the two delivery findings resolved here. No finding is
waived or removed from history. The current evidence must contain zero known,
unexpected, unreproduced, or unaccounted findings before publication work can
resume.

At clean implementation checkpoint
`8058770bcf8ae59d781b1ceff9880f09355e5388`, the exact-engine strict audit is
green, Local 1.14.0 passes 36/36 with fingerprint
`dc4f5f68cc638df8571e41d2ccaf516a86109c6b3ccc1717c75752d7af52e295`, and
Pull Request 1.19.0 passes 76/76 with fingerprint
`7090ed78e0e210662255f16f1c7dac4954b3f72e982428839db02ef9f77f35fa`.
All three report zero unresolved or unaccounted results. The bounded campaign
is FINAL and P20-T02 is reactivated without starting publication work.
