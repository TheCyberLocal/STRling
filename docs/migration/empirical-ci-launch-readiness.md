# Empirical CI and launch-readiness hardening

## Scope and starting point

This combined hardening task started from clean `dev` checkpoint
`c255af1550ad988c9ad831e2fb35b73f82f3e87b`, identical to `origin/dev`. It does
not change Semantic STRling meaning, target lowering, the five target profiles,
or the zero-finding adversarial corpus. It makes the already-proven equivalence
work execute on exact real engines in normal Pull Request certification and
repairs bounded launch-facing credibility gaps before final V4-H08
recertification.

## Repository-state audit

| Requirement | Starting classification | Disposition |
| --- | --- | --- |
| Strict adversarial corpus, cross-profile comparison, refusals, and offline zero-finding ratchet | ALREADY_SATISFIED | Reused without weakening coverage or expectations. |
| PCRE2 and CPython exact source/build/artifact identities | ALREADY_SATISFIED | Reused as the runtime authority. |
| Exact Node identity and one complete CI environment handoff | PARTIALLY_SATISFIED | Node is now in the same manifest and validator as PCRE2/CPython. |
| Real-engine execution in Pull Request | IMPLEMENTED_BUT_UNREACHABLE | The strict producer existed but only checked-in evidence was verified; Pull Request now provisions and executes it. |
| Runtime observation source/profile/runtime/artifact/subject binding | ALREADY_SATISFIED | The structured run now exposes those bindings and matrix counts to the profile result. |
| Atomic containment safety handling | ALREADY_SATISFIED | Existing focused safety tests prove atomic and possessive barriers suppress the impossible backtracking path. |
| `tooling/tests` in a deterministic profile | MISSING | Repository tooling tests are now an enforced Pull Request test target. |
| Semantic `.strling` editor registration and static highlighting | PARTIALLY_SATISFIED | `.strling` is primary, `.strl` remains legacy regex compatibility, and an authored TextMate grammar ships in the package. |
| Binding API references | PARTIALLY_SATISFIED | Empty Python/Lua references and false TypeScript/Ruby local-runtime guidance were replaced from current adapters. |
| JSON Schema boundary wording | PARTIALLY_SATISFIED | The contract suite now says explicitly that schemas are necessary, not sufficient, and names the companion validator. |
| Target-profile currency | PARTIALLY_SATISFIED | Exact compatibility scope existed, but release-policy revision labels were stale and no current upstream review was recorded. |
| Lowering/emission diagnostic authority | ALREADY_SATISFIED | Owning Rust error-code enums remain the single active code authorities; one stale Python range in derivative documentation was corrected. |
| Pull Request dependency review | MISSING | A GitHub-native dependency-review job is pinned by full action commit. |

## Exact empirical runtime contract

`governance/exact-runtime-toolchains.json` is the single runtime authority.
Pull Request, Full, and Release inherit one structured strict operation using:

| Profile | Runtime identity | Governed artifact |
| --- | --- | --- |
| `profile:ecmascript/2024` | Node 22.23.2 / V8 12.4.254.21-node.56 | exact upstream Linux x64 executable and archive SHA-256 |
| `profile:pcre2/10.42` | PCRE2 10.42 | source tag/commit, CMake option set, and exact shared-library SHA-256 |
| `profile:pcre2/10.43` | PCRE2 10.43 | source tag/commit, CMake option set, and exact shared-library SHA-256 |
| `profile:python-re/3.11` | CPython 3.11.15 `str` | source archive SHA-256, build recipe, and exact executable SHA-256 |
| `profile:python-re/3.11-bytes` | CPython 3.11.15 `bytes` | the same exact interpreter with the distinct bytes profile |

The CI setup downloads immutable archives or fetches exact PCRE2 tags, verifies
archive checksums and Git commits, builds only the required runtime surfaces,
caches the fixed `/opt` layout by manifest/provisioner identity, then validates
every resulting artifact hash and reported runtime identity. A missing,
corrupt, wrong-version, or wrong-hash runtime is an incomplete/failed profile;
there is no ambient runtime fallback. The developer entrypoint is:

```text
python3 -m tooling.exact_runtime_provision --provision --execute-adversarial
```

Provisioning is network-enabled setup. The strict operation itself is declared
offline and runs every emitted artifact twice. Its structured evidence binds
the source SHA and source-file digests, corpus and case identity, exact profile
fingerprint, runtime identity and artifact hash, `TargetArtifact` fingerprint,
subject identity, compile/refusal state, normalized runtime result, comparison
result, and run identity. These observations validate the normative semantics
and target-profile declarations; they do not define either.

## Equivalence denominator

The unchanged corpus contains 41 semantic programs and 95 distinct subjects.
Across the five profiles it produces 205 compile decisions, 1,531 real-runtime
executions, 48 governed refusals, and 1,129 cross-profile comparison edges.
Every emitted applicable result must agree; a known unsupported condition must
be stopped by a governed refusal before execution. The hardgate accepts zero
semantic or diagnostic findings, zero unexpected target rejections, zero
runtime identity mismatches, and zero unaccounted observations.

The ephemeral Pull Request evidence lives under
`artifacts/adversarial-semantic-runtime/` and is retained with the profile
artifact. Historical checked-in evidence remains separately governed by the
generated-artifact producer and its current-source zero-finding check.

## Target-profile currency decision

The 2026-09-07 upstream review found ECMAScript 2026, PCRE2 10.48, and CPython
3.14.7 current upstream. STRling's supported profile identifiers are exact
compatibility contracts, not moving aliases, so silently retargeting them would
invalidate their V4-H02 semantic facts and H04 differential evidence. No new
profile is added without a complete fact set, runtime identity, differential
matrix, and explicit support decision.

The reviewed decision is therefore to retain the five exact profiles for 4.0:
ECMAScript 2024 is a versioned compatibility target; PCRE2 10.42/10.43
deliberately bracket the material UCP semantic boundary; Python 3.11 remains in
upstream security-fix support through October 2027, with 3.11.16 recorded as the
current patch at review time. The exact 3.11.15 certification binary is an
empirical semantic anchor, not an interpreter-distribution recommendation.
PCRE2 compatibility likewise is not a deployment-security recommendation:
consumers must follow upstream lifecycle and backport guidance.
`governance/target-profile-currency.json` records the current upstream versions,
primary evidence, rationale, and a 366-day review ratchet. Pull Request tests
require every governed profile/revision to appear there and every release-policy
label to match its profile file.

## Launch-facing cleanup

- Repository tooling tests now run in Pull Request, Full, and Release through
  the canonical `test` operation rather than an extra workflow command.
- The VS Code package recognizes `.strling` as Semantic STRling, keeps `.strl`
  on the governed legacy-regex frontend, and provides static highlighting
  before LSP initialization. Grammar payload inclusion and routing are tested.
- Python, Lua, TypeScript, and Ruby API references now document their actual
  thin native/WASM adapters and canonical result model. They no longer promise
  retired ASTs, local emitters, implicit regex strings, or runtime execution.
- The public contract documentation identifies JSON Schema as necessary but
  not sufficient and directs users to `./strling contracts --check`.
- The active Python lowering diagnostic range is documented through `0016`;
  H05 emission codes remain owned by their closed target-stage enums.
- Pull Request dependency changes are reviewed by the pinned GitHub dependency
  review action. Broader post-4.0 security roadmap work remains out of scope.

## Verification and handoff

Focused runtime identity, provisioning, adversarial-result, launch-readiness,
editor-package, safety, and tooling tests precede generated-artifact,
contracts, documentation, architecture, governance, formatting/static-analysis,
Local, and Pull Request verification. Final exact counts and profile
fingerprints are retained in the controlled task record.

Full and Release are intentionally not run here. The repository release
contract reserves final hardened-core recertification for V4-H08; this task
changes deterministic Pull Request coverage and launch surfaces without
changing performance sampling, baselines, thresholds, or publication state.
P20-T02 remains paused, and V4-H08 is the next task.
