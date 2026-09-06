# Adversarial semantic baseline

V4-H01 establishes empirical adversarial evidence for the bounded pre-4.0
semantic-hardening campaign. It does not change the semantic model, profiles,
lowering, requirements extraction, diagnostics, performance governance, or
publication state. The [task record](records/adversarial-semantic-baseline.yaml)
owns scope and verification; the [authority hierarchy](../../governance/authority.md)
continues to govern interpretation.

## Source and independent reconstruction

Starting SHA: `2ff3bfb9126060f250975cfec0d1d74b4f39b03c`. After fetching remotes,
`architecture/v4`, `HEAD`, and `origin/dev` identified that commit; the index
and worktree were clean. Current Fourth Edition architecture was verified through
the README, governing contracts, canonical kernel, serializers, and five profiles.
The historical audit SHA `a8165efa240c209efc5b6f4d8c77d7abbe6d396e` was never
checked out or used as the compiler.

The external source is **STRling Fourth Edition - Definitive Competitive and
First-Principles Audit**, research window 2026-09-04, supplied by the owner as
`strling-v4-competitive-audit.md`, SHA-256
`65a8379675fee74cab3f273e1f7f5349cd1b1879b0b61cd9b880fac822d7f001`.
The original remains untouched. Relevant sections are G-01, G-02, G-03/G-03b,
G-04, G-05/G-05b/G-05c, G-25, G-26, and G-27. Recommendations about safety,
performance, publication, and product expansion are outside this task.

The initial programs and 98 findings were independently reconstructed before
reading the report. Source review then added its ranged quantifier, mixed
negated-set, decomposed-I, anchored scalar, two-capture alternation, and
unbounded capture-reset shapes. The audit disclosed Node 22.22.2 and PCRE2
10.45 substitutions. This reconstruction uses governed Node 22.23.2 and actual
PCRE2 10.43, independently confirming rather than assuming those substitutions
preserve the relevant behavior. No historical expected output enters the corpus.

Each authored Semantic STRling program passes through `strling-kernel compile`
with semantic, analysis, portability, and artifact outputs requested. The
controller validates the existing CompileResult contract, preserves the semantic
tree and source locations, and dispatches the exact artifact to the existing
PCRE2, Node, or Python harness. It applies the governed profile configuration,
never rewrites or wraps emitted patterns, and never uses a peer-majority oracle.

Execution compares the first search result, its UTF-8 span, and capture-slot
participation/value. The capture probes contain the same ordered semantic captures across targets;
slot identity is checked against the preserved semantic programs. ECMAScript UTF-16 and
Python scalar offsets are converted to UTF-8; bytes offsets remain bytes.
Partial UTF-8 matches remain visible as hex, rather than being decoded, dropped,
or rounded into scalar agreement. Raw engine observations remain alongside the
comparison. Target compile rejection is distinct from no match, and unsupported
profiles do not execute.

## Governed engines

Executable/library hashes were checked before execution. These are the current
[runtime manifest](../../governance/exact-runtime-toolchains.json) and
[Node certification](../../tooling/ecmascript_runtime_certification.py) pins,
not the older build hashes printed in historical migration prose.

| Runtime | Exact identity                                                                              | SHA-256                                                            |
| ------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| PCRE2   | 10.42, upstream tag commit `52c08847921a324c804cabf2814549f50bce1265`, governed Linux build | `fdb00bcb3dd68707ed155927738b454a4281bb664e830d60dd205b10d1a2edd1` |
| PCRE2   | 10.43, upstream tag commit `3864abdb713f78831dd12d898ab31bbb0fa630b6`, governed Linux build | `c1426544954ea17aa2d006dca0b0c31d641d8fa3a22eeb5e591e2d51bc721b5c` |
| Node/V8 | Node 22.23.2, V8 12.4.254.21-node.56, Linux x64                                             | `3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327` |
| CPython | 3.11.15, Linux x86-64; separate `str` and `bytes` profiles                                  | `89656b63d58055a8f200f46d52986610f944b5bcff076a7b60521fc6068422cc` |

Every application binds its exact profile revision and canonical fingerprint,
runtime key, source program identity, artifact fingerprint, source SHA, hashed
compiler/controller inputs (source text normalized to LF), subject ID/value/hash, portability and diagnostics,
and raw and normalized result. The envelope supplies UTC execution time and a
content-derived run identity. Two independent complete executions must agree
before evidence can be written. No machine-specific paths are stored.

## Corpus coverage

The separate [empirical corpus](../../tests/conformance/adversarial/1.0/corpus.json)
contains 41 programs, 95 named subjects (90 distinct values), 402 case/subject
applications, and 205 explicit case/profile applications. It supplements the
previous shared corpus without assigning normative authority to engine behavior.
Every program is considered for all five governed profiles; refusals remain
observable rather than silently disappearing from the denominator.

-   LF, VT, FF, CR, CRLF, NEL, LS, and PS occur as bare values, between a prefix
    and line-start probe, before a line-end suffix, and at final input. Separate
    probes test the interior of CRLF.
-   Unicode word and boundary probes include Mn, Pc, Lo, Nl, Nd, No, ASCII word,
    ASCII non-word, U+0301, U+203F, U+2040, and U+00E9.
-   Thirteen insensitive literal programs probe both directions of dotted/dotless
    I, long S, Kelvin sign, and all three sigma forms, with ASCII controls.
-   Optional, alternation, negative-lookahead, and repeated-alternation captures
    cover nonparticipation, unset references, and reset versus retained capture
    state. A capture-only repetition distinguishes capture disagreement even
    where overall match spans agree.
-   Bytes applications include one-, two-, three-, and four-byte UTF-8 scalars,
    both wildcard policies, positive ASCII sets, negated sets, and non-ASCII
    literal/set refusal controls.
-   `wildcard-excluding-lines` and `unicode-word-class` are explicit durable
    semantic case IDs.

Schema, metadata/value consistency, semantic-tree checks, and mutation tests
prevent removed line forms, fake Unicode tags, one-direction-only folding,
unexecuted coverage subjects, missing capture algorithms, ASCII-only bytes
coverage, dropped profiles, and corrupt artifact/observation identities. These
tests verify evidence quality; they do not assert that the product already
implements equivalence.

## Finding inventory and ownership

The [machine evidence](../../tests/conformance/adversarial/1.0/evidence.json)
enumerates every individual finding by stable ID. `semantic/<case>/<subject>`
identifies one cross-profile behavioral disagreement; requirement findings are
separate for each emitted capability/profile; compile and diagnostic findings
are separate for each affected profile. Counts are not collapsed to reproduce a
historical headline number. Every finding is classified and every application
retains its observed support/diagnostic status.

| Audit family                    | Current reconstruction                                  | Concrete observation                                                                                                                                                                                                                                                                                          | Remediation owner                          |
| ------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Wildcard line terminators       | REPRODUCED — SEMANTIC_DIVERGENCE                        | `.` excludes all governed PCRE2 newline forms, only LF in Python, and LF/CR/LS/PS in ECMAScript. VT/FF/NEL and CR expose different outcomes while native.                                                                                                                                                     | V4-H02 sets; V4-H04 corrections            |
| Line start                      | REPRODUCED — SEMANTIC_DIVERGENCE                        | On `x<terminator>a`, PCRE2 finds `a` for every form, ECMAScript for LF/CR/CRLF/LS/PS, Python only LF/CRLF.                                                                                                                                                                                                    | V4-H02 sets; V4-H04 corrections            |
| Line end                        | REPRODUCED — SEMANTIC_DIVERGENCE                        | On `a<terminator>x`, PCRE2 accepts every form, ECMAScript LF/CR/CRLF/LS/PS, Python only LF.                                                                                                                                                                                                                   | V4-H02 sets; V4-H04 corrections            |
| Before final terminator         | REPRODUCED — SEMANTIC_DIVERGENCE                        | `a<terminator>` gives the same three terminator-set partitions as line end. Python and PCRE2 accept the LF interior of final CRLF where ECMAScript refuses. This corrected projection follows the machine evidence.                                                                                           | V4-H02 sets/algorithms; V4-H04 corrections |
| Unicode word characters         | REPRODUCED_WITH_DIFFERENT_DETAILS — SEMANTIC_DIVERGENCE | G-03 confirms actual governed PCRE2 10.43 and ECMAScript accept Mn/Pc; Python refuses U+0301/U+203F/U+2040. PCRE2 10.42 and Python bytes refuse compilation as unsupported.                                                                                                                                   | V4-H02 sets; V4-H04 corrections            |
| Word boundaries                 | REPRODUCED — SEMANTIC_DIVERGENCE                        | ECMAScript native `\b` is inconsistent with its expanded Unicode word class; `é`, Mn, Pc, Lo, Nl, Nd, and No expose differing boundary decisions. Python also differs from PCRE2 10.43 on Mn/Pc.                                                                                                              | V4-H02 sets/algorithms; V4-H04 corrections |
| Case folding                    | REPRODUCED_WITH_DIFFERENT_DETAILS — SEMANTIC_DIVERGENCE | Python text folds ASCII I/i with dotted/dotless I while ECMAScript and both PCRE2 profiles do not. Long S/Kelvin agree among text profiles; bytes fails those cross-scalar folds. Sigma forms agree among executable text profiles.                                                                           | V4-H02 algorithms; V4-H04 corrections      |
| Unset backreference             | REPRODUCED — SEMANTIC_DIVERGENCE                        | Optional capture plus reference matches empty input in ECMAScript only. Alternation and negative-lookahead variants also expose nonparticipating-reference differences.                                                                                                                                       | V4-H02 algorithms; V4-H04 corrections      |
| Capture reset in repetition     | REPRODUCED — SEMANTIC_DIVERGENCE                        | Repeated `(capture a or b)` followed by the reference accepts `ab` in ECMAScript and `aba` in PCRE2/Python. Without the reference, all match `ab` but ECMAScript unsets capture 1 while the other engines retain `a`.                                                                                         | V4-H02 algorithms; V4-H04 corrections      |
| PCRE2 quantifier acceptance     | REPRODUCED — TARGET_COMPILE_FAILURE                     | Both `repeat from 1 to 65535` and exact count 65535 over `text "a";` emit native patterns (`(?:a){1,65535}` and `(?:a){65535}`), classified native, but both governed PCRE2 libraries reject compilation.                                                                                                     | V4-H04 concrete target acceptance          |
| Python bytes/scalar semantics   | REPRODUCED — SEMANTIC_DIVERGENCE                        | Both wildcard policies and negated sets consume just the first byte of `é`, `中`, and an astral scalar, despite canonical analysis declaring one Unicode scalar. The profile already declares scalar support unavailable; the needed requirement is absent.                                                   | V4-H02 model; V4-H04 corrections           |
| Emitter-introduced requirements | RESOLVED — REQUIREMENT_SOUNDNESS                        | Mixed builtin negated sets introduce lookahead in all target families; scalar-only negated sets also do so in Python; ECMAScript line start introduces lookbehind, final-line position both lookahead/lookbehind. Structured post-lowering extraction now declares and evaluates every introduced capability. | V4-H03 complete                            |
| Emission diagnostic delivery    | REPRODUCED — DIAGNOSTIC_DELIVERY_DEFECT                 | Count 65536 passes the source-side check, then post-lowering constraint evaluation refuses it. CLI exits 70, stdout is empty, and only a generic stage message reaches stderr. The direct probe retains code, message, and source span, all lost from the public failed-result channel.                       | V4-H05 diagnostic integrity                |

V4-H06 owns promotion of corrected real-engine equivalence into mandatory CI
after these findings close. All `SEMANTIC_DIVERGENCE` IDs map to V4-H02 and
V4-H04, the 25 historical `REQUIREMENT_UNSOUNDNESS` IDs were resolved by
V4-H03, all `TARGET_COMPILE_FAILURE` IDs map to V4-H04, and all
`DIAGNOSTIC_DELIVERY_DEFECT` IDs map to V4-H05. This mapping covers every
machine finding, including adjacent probes.

Additional observations are retained: ECMAScript line start accepts the interior
of CRLF; Python final-line handling accepts its LF interior; ECMAScript input-end
and line-end serialization also introduce lookahead. These were `NEW_FINDING`
relative to the explicitly requested V4-H01 mechanisms, with the historical
machine classifications SEMANTIC_DIVERGENCE or REQUIREMENT_UNSOUNDNESS. V4-H03
now accounts for those introduced lookaheads. The Python text Unicode-word declaration is also classified PROFILE_DATA_ERROR
(G-03): its supported class constraint includes word, despite the Mn/Pc
disagreement that the PCRE2 10.42 profile explicitly excludes. For bytes, the
profile already declares the missing scalar capability unavailable.

V4-H02 adds governed profile facts without resolving any finding. The complete
inventory maps as follows:

| Governed fact                                            | Finding count | Covered evidence family                                        |
| -------------------------------------------------------- | ------------: | -------------------------------------------------------------- |
| set `word_characters`                                    |            19 | Unicode word class and word-boundary probes                    |
| set `line_terminators` plus sequence policy              |            22 | line start, line end, final-line, and CRLF-interior probes     |
| set `wildcard_exclusions` plus algorithm `matching_unit` |            35 | both wildcard policies across separator and multibyte subjects |
| algorithm `case_folding`                                 |            16 | dotted/dotless I, long S, Kelvin, and sigma probes             |
| algorithm `backreference_unset`                          |             4 | nonparticipating-reference probes                              |
| algorithm `capture_reset_on_iteration`                   |             9 | bounded and unbounded repeated-capture probes                  |
| algorithm `matching_unit`                                |            12 | Python bytes negated built-in/set multibyte probes             |
| limits `quantifier_value` and `compiled_pattern_size`    |             4 | PCRE2 target-compilation failures                              |

These facts cover 121 semantic/target-limit findings. At V4-H02, the remaining
25 requirement-unsoundness findings were assigned to V4-H03 and the two
diagnostic-delivery findings to V4-H05: `121 + 25 + 2 = 148`. The profile model
did not itself resolve, waive, or reclassify any observation.

### V4-H03 disposition

V4-H03 reran the unchanged 41-program, 95-subject corpus at committed source
`143e6f68774bb6b1343f04a0ef94e8e36e00a949`. Structured post-lowering
extraction now finds assertion, anchor, wildcard, repetition, capture,
backreference, Unicode-class, and case-folding requirements directly in each
target operation tree. Final artifact requirements are the deterministic union
of semantic and introduced requirements, with distinct `semantic` and
`lowering` identity namespaces. Every emitted assertion marker in the focused
inventory is declared; `missing_requirements` is empty for all 190 emitted
artifacts.

The strict reconciliation is therefore:

| Disposition                                     | Count |
| ----------------------------------------------- | ----: |
| V4-H01 findings                                 |   148 |
| Resolved by V4-H03 requirement reconciliation   |    25 |
| Remaining semantic/target acceptance for V4-H04 |   121 |
| Remaining diagnostic delivery for V4-H05        |     2 |
| New findings                                    |     0 |
| Unexpected or unaccounted findings              |     0 |

The current strict audit exits 1 with 123 known findings, zero unexpected
findings, and 25 unreproduced baseline findings. Those 25 are the deliberately
resolved requirement-unsoundness IDs, not weakened assertions or missing
evidence. The remaining 123 comprise 117 semantic divergences, four target
compile/resource failures, and two diagnostic-delivery defects.

### V4-H04 disposition

V4-H04 consumes the governed semantic facts and corrects all 121 remaining
semantic/target-acceptance findings. Native target operations are retained only
when their set, algorithm, matching unit, and limit facts are compatible.
Otherwise lowering emits a canonical explicit target form or capability
evaluation refuses the exact reachable mismatch. The correction adds no waiver
and no equivalence-registry rewrite.

The regenerated strict evidence now reports two known findings, zero unexpected
findings, and 121 unreproduced V4-H03 findings. Those 121 non-reproductions are
the resolved V4-H04 set: 117 former `SEMANTIC_DIVERGENCE` IDs and four former
`TARGET_COMPILE_FAILURE` IDs. At finding-ID granularity all 121 include at least
one precise constraint/refusal; surviving target cells use equivalent native or
direct canonical lowerings. Only the two
`diagnostic/pcre2-serialization-limit/*` delivery defects remain for V4-H05.

The independent PCRE2 boundary probe now verifies the conservative governed
compiler envelope: count 4,096 emits and compiles, while count 4,097 is refused
after structured lowering requirements are evaluated. This does not replace the
profile's honest unknown, artifact/configuration-dependent compiled-size fact
with an invented engine cutoff.

Non-reproductions and controls are explicit. As G-26 also reports, a non-ASCII literal or positive
non-ASCII set in Python bytes is refused structurally before emission; it does
not reproduce an emission failure (a deliberate non-failing control, NOT_REPRODUCED,
EXPECTED_PROFILE_DIFFERENCE). The PCRE2 quantifier probe independently supplies
the diagnostic-delivery reproduction. As G-04 reports, long S, Kelvin sign, and final sigma are
not divergences between executable text profiles in these probes
(NOT_REPRODUCED for a text-only divergence, EXPECTED_PROFILE_DIFFERENCE for
unsupported bytes source). They remain in the corpus as controls. No semantic,
target-acceptance, or diagnostic-delivery family is claimed fixed or superseded
by V4-H03; only the 25 requirement-unsoundness findings are resolved. No
governed engine is environment-blocked.

## Requirements and diagnostics evidence

Each artifact row contains `requirements_probe`: semantic requirements,
emitted assertion markers, authoritative artifact requirements, missing
capability IDs, and exact profile support for any missing entry. The lexical
marker inventory remains a bounded audit cross-check, not the production
extractor and not a general regex parser. Production extraction operates on the
closed target operation trees before serialization. No probe contains
assertion-shaped literal text. The runtime still executes the actual emitted
artifact.

The serialization-limit rows additionally contain a successful source-side
`pre_emission` CompileResult and direct lowering evidence produced by the
[repository-only probe](../../core/examples/adversarial_emission_probe.rs).
For both PCRE2 profiles, post-lowering evaluation emits
`STRL-PCRE2_LOWERING-0014`: bounded repetition requires
`repetition.bounded`, but exact count 65536 violates the governed profile
constraint. The diagnostic identifies the semantic node, exact profile and
revision, disposition, reason for refusal, and source span `[46, 99)`. The CLI
still returns no structured failed result and no `TargetArtifact`; stderr only
reports that target lowering failed with one diagnostic. The repository-only
probe retains the structured diagnostic so V4-H03 can verify its correctness
without consuming V4-H05's delivery repair.

## Focused operation and evidence policy

Configure the four existing exact-runtime environment variables from the local
governed installations: `STRLING_PCRE2_1042_LIBRARY`,
`STRLING_PCRE2_1043_LIBRARY`, `STRLING_NODE_22_BINARY`, and
`STRLING_CPYTHON_311_BINARY`. The controller validates hashes, so substitute
versions cannot produce authoritative audit observations.

```sh
python3 -m tooling.adversarial_semantic_audit --strict
python3 -m tooling.adversarial_semantic_audit --check
python3 -m unittest tooling.tests.test_adversarial_semantic_audit
```

`--strict` executes the corpus twice and reports actual disagreements as
failures. `--write` is the registered evidence producer and also reports the
known-red result; it writes only after complete deterministic execution.
`--check` is the offline schema/identity/raw-observation integrity verifier,
not an equivalence assertion. No strict command was added to Local or Pull
Request. The normal tooling tests protect corpus quality and evidence integrity.
No assertion is waived or weakened to make a known semantic defect green.

The V4-H01 baseline was 148 findings: 117 behavioral disagreement coordinates,
25 missing-requirement/profile coordinates, four target compile failures, and
two emission-delivery failures. After V4-H03, the strict summary must report
123 known, zero unexpected, and 25 unreproduced baseline findings; the complete
25-ID difference must be the historical requirement-unsoundness set.
Unexpected agreement requires investigation of source, options, corpus,
artifact execution, and normalization; observation integrity alone never
certifies equivalence.

The bounded bisection independently reproduces G-05c's range boundary on both
actual governed versions: `(?:a){1,4369}` compiles and `(?:a){1,4370}` fails
(error 120). Each probe stores its Semantic source, native status, artifact,
profile identity, fingerprint, and raw engine result. The audit's 10.45
substitution was unnecessary: 10.42 and 10.43 have the same boundary for this
program. The independently chosen exact-count form also fails at 65535; its
initial exploratory accepted/rejected boundary was 8191/8192. That different
boundary is caused by a different quantifier shape, not a contradictory engine
observation. This task did not investigate general compiled-size limits.

The final corpus produces 1,836 subject observations per run, 13 structured
unsupported applications, four target compile errors, and two kernel emission
transport failures. All 205 applications are accounted for.

Raw observations are stored in per-case files under
`tests/conformance/adversarial/1.0/observations/`. The evidence index binds every
file by its case identity and canonical SHA-256; the complete reconstructed
observation envelope has its own fingerprint. Missing, altered, duplicate, and
unreferenced files fail integrity checks. This preserves the complete raw
evidence while keeping each file within the repository size limit.

## Verification and ending checkpoint

Ending verified implementation/evidence SHA:
`59b08b49ba9410c7a25ea497a893fb94aae5e823` on `architecture/v4`.
The final documentation-only closure commit records this immutable checkpoint;
it does not change the compiler, controller, corpus, or engine observations.
The preserved observation run compiled source
`0e2a8fa403e9c9befd5fd5ef0b762935a7c8b13e`; the ending checkpoint adds only its
generated evidence. Its UTC timestamp is `2026-09-05T17:04:00.593479+00:00`,
run identity is `cd766de502247bc20ffb4072139b011ea670248befc114c2a492d83d251cf47d`,
and evidence fingerprint is
`62e9f93bb5b4d8d3518668ce7e6996cd88544cb3b2af18de94dfd471b6e125f2`.

The focused corpus, harness, evidence-integrity, shared-conformance, and three
engine-adapter suites pass 60 tests, including 26 adversarial tests. The strict
command was then rerun at the clean ending checkpoint: exit 1, 148 known
findings, zero unexpected findings, and zero unreproduced baseline findings.
The failing status is intentional evidence of unresolved defects, not a waiver.

Local 1.14.0 passes 36/36 operations at the clean ending checkpoint, with zero
failed, waived, unavailable, or incomplete results. Its evidence fingerprint is
`5e479af592f59b95782a7469802f39483d37207a98c4e28588d6f2cb861c9f73`.
Pull Request 1.19.0 passes 76/76 operations at the same clean checkpoint, also
with zero failed, waived, unavailable, or incomplete results. Its fingerprint is
`5d59abb90be82899525358a2bd1de2de27939835af4af369c8f80c1ac502345b`.

The first Local attempt exposed one evidence-storage defect (a 3.7 MB file
exceeding the 1 MiB repository limit) and missing restored .NET/Dart dependencies
in the fresh verification checkout. Evidence was split into hash-bound files;
case-folded filename collisions on Windows were corrected with identity-hash
suffixes and a portability test. The existing dependencies were restored, public
contracts rechecked successfully, and the corrected source committed before
Local was rerun. No hygiene threshold, contract assertion, or product behavior
was relaxed. Full and Release were not required or run, and no governed
performance samples were consumed.

The first Pull Request attempt passed 65/76 operations, with nine failures and
two unavailable operations caused by incomplete fresh-checkout setup: the native
bridge library, C/C++ build directories, .NET test-project restores, and locked
PHP development dependencies. These prerequisites were prepared without tracked
changes. The exact failed C/C++ tests, warnings-denied .NET builds, and all three
affected adapter runtime certifications then passed before the full PR rerun.
The offline adversarial evidence verifier also passes directly on Windows.

The successful profiles cover canonical/public contracts, all registered
generated-artifact checks, architecture and governance invariants,
documentation integrity, formatting, lint, type checks, adapter certification,
and the required compiler and binding tests. Local copies of their structured
reports are available under `target/adversarial-audit/59b08b49/` as `local.json`,
`pull-request.json`, and `strict.txt`; these ignored convenience copies accompany
the durable fingerprints above. The tracked empirical corpus, indexed raw
observations, finding inventory, and task record are the repository-owned record.

All requested audit families are classified and reproducible against the current
governed engines. No substantive engine or evidence issue remains unresolved.
The semantic defects remain open with the ownership mapping above. P20
publication work remains paused; no V4-H02 implementation has begun.

READY — GO FOR V4-H02
