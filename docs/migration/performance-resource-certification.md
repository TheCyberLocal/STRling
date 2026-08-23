# Performance and resource-budget certification

Status: active migration evidence

Authority: this document records engineering measurement and certification
design. It does not define STRling semantics, target behavior, diagnostics,
public APIs, support tiers, or regex-engine performance promises.

## Starting evidence

At the clean task anchor `f4f9cc03cc1277d99a65470ef911e9bfbdee78eb`,
the repository has three performance tests. Each is embedded in one of the
PCRE2, ECMAScript, or Python `re` runtime-certification suites. They use 16
warmups, 128 samples, and a median in an unoptimized Rust test build. Their
ceilings are 10,000 microseconds for analysis and planning, 5,000 for lowering,
and 5,000 for serialization.

A clean starting replay passed with these observed medians:

| Target      | Analysis and planning | Lowering | Serialization |
| ----------- | --------------------: | -------: | ------------: |
| ECMAScript  |              1,133 us |   416 us |         54 us |
| PCRE2       |              1,546 us |   597 us |         58 us |
| Python `re` |              1,233 us |   434 us |         61 us |

These values are reconnaissance, not baselines. The tests do not authenticate
the environment, compiler profile, fixture identity, distribution, variance,
memory, artifact size, or comparison source. Their target-specific duplication
also prevents one complete performance result from being consumed by product
certification.

The repository separately contains 61 searched `MAX_*` declarations across
the core, interop, editor, and verification paths. They bound source, request,
profile and response bytes; semantic material, depth and diagnostics; analysis,
capability, portability, lowering and serialization work; editor results;
no-match explanation; and related result sizes. Existing exact/one-over and
property tests are authoritative behavior evidence. This task will inventory
and authenticate those existing limits and tests; it will not change a limit.

## Closed measurement matrix

The certification denominator has five independent families:

1. Compiler work measures semantic parsing, legacy import, Simply/kernel
   request decoding, normalization, semantic/structural/safety analysis,
   capability and portability evaluation, PCRE2/ECMAScript/Python `re`
   lowering and serialization, and end-to-end compilation.
2. Product entrypoints measure the canonical CLI startup and representative
   commands plus bounded editor diagnostics, formatting, completion, symbols,
   and rewrite interactions.
3. Transport work measures canonical interop request decoding, kernel
   invocation, response encoding, and whole round trips. Supported-host adapter
   overhead is reported separately when its governed toolchain is available;
   it is never substituted for compiler time or support certification.
4. Resource observations measure peak resident memory and governed binary or
   library artifact sizes on supported environments.
5. Pathological cases certify existing hard source, request, node, depth,
   relationship, output, protocol, editor, and explanation ceilings. They
   record functional exact/one-over results separately from elapsed-time and
   memory observations.

Every family uses authored, bounded fixtures in four classes: tiny for startup
and fixed overhead, common for representative development work, large for
scaling, and pathological for declared resource boundaries. Fixture bytes,
semantic intent, expected status, and identity must be authenticated before a
measurement can be accepted.

Target regex-engine matching throughput is not in the denominator. The target
runtime suites continue to prove target acceptance, semantics, safety, and
their own bounded compile-stage smoke budgets; this task makes no universal
claim about PCRE2, JavaScript, or Python regex execution speed.

## Evidence rules to freeze in CP2

The versioned contract must distinguish four artifacts:

-   an authored operation and fixture manifest;
-   an environment-bound measured baseline;
-   a comparison result against exactly one compatible baseline; and
-   a complete certification result consumed by quality profiles.

Environment identity includes operating system and version, architecture, CPU
identity and logical count, available memory, Rust and relevant host toolchain
versions, build profile, target triple, feature set, repository commit,
producer fingerprint, and fixture fingerprint. A comparison is valid only when
the contract declares the identities compatible. Otherwise the result is
truthfully unavailable or informational.

Latency and throughput evidence must retain samples and report at least median,
p95, and median absolute deviation after fixed warmup and sample rules. The
controller must randomize operation order within deterministic rounds, avoid
concurrent benchmark workers, and reject incomplete samples. Peak resident
memory and artifact bytes use their own units and aggregation; they are never
converted into latency scores.

Each metric is either hard or informational. Hard metrics have both a measured
relative regression budget and, where product risk requires it, an absolute
ceiling. Informational metrics preserve the same observations, comparisons,
and trend reporting but do not independently fail aggregate certification
unless their governing operation is explicitly reclassified as hard.
Baseline creation or replacement is an explicit command that records its
source commit and rationale; an ordinary certification run cannot rewrite its
comparison authority.

Numeric budgets are deliberately not chosen in CP1. CP2 must derive them from
repeated controlled measurements and documented variance, then use controlled
mutations to prove that just-inside values pass and just-outside values fail.

## CP2 evidence contract

The versioned `1.0.0` contract closes 22 ordered operations: seventeen planned
latency, peak-RSS, and artifact-size measurements and five active groups of
existing hard resource checks. It closes twelve deterministic recipe fixtures
across the four required size classes and nine resource families containing 56
canonical declarations. Nineteen exact test-source fingerprints prevent a
resource claim from retaining its evidence identity after its proving test
changes.

The current pre-calibration manifest fingerprint is
`sha256:10462c638152216c4d641fb56c23877791c714baa2f5e6c1737ea7097eb040c8`.
The fixture-manifest fingerprint is
`sha256:6a8e4aad41dd1b00c8e4bf441ea929a21259737f7ff7aa96b57f465e741c40c4`,
and the resource-inventory fingerprint is
`sha256:e1f5c1a3a1163cab3432b7e63115e09559939f5bc8e4ce41ca3a70a21ee0d5f8`.

The locked sampling policy uses sixteen warmups, 64 measurements, five
baseline repetitions, deterministic operation-order seed `1804`, one worker,
nearest-rank p95, median, and median absolute deviation. A coordinate shorter
than one millisecond selects a batch against a two-millisecond safety target,
bounded to 4,096 operations. The selected integer count is authenticated in
the baseline and reused exactly by Full and Release. Raw batch durations and
normalized per-operation nanoseconds are both retained, and every repetition's
batch-duration median must reach the one-millisecond governed minimum. A hard
relative budget is `max(1000 basis points, ceil(6 * MAD / median * 10000))`; a
baseline whose derived budget exceeds 4000 basis points or whose relative MAD
exceeds 500 basis points cannot become hard comparison authority. Every hard
live metric also requires an explicit absolute ceiling.

All performance operations remain `planned` in CP2. The positive result is
explicitly a synthetic contract fixture with zero commit identity and flags
that deny live-measurement and baseline authority. CP3 must implement the
release-build producer, execute five stable calibration repetitions, record a
real source commit and exact environment, activate measured budgets, and prove
the complete live denominator. This prevents contract design from fabricating
numbers before the measurement path exists.

Fourteen focused tests validate the schema, exact denominators, authenticated
source declarations and tests, robust statistics, exact environment
compatibility, explicit baseline replacement, and controlled just-inside,
exact-boundary, relative-over, and absolute-over comparisons. Mutations that
shrink operations or profiles, prematurely activate metrics, change samples
without statistics, weaken derived budgets, alter environments or update
commands, or promote the synthetic fixture fail closed.

## CP3 release harness and local proof

The verification-only producer is a standalone, `publish = false` Rust release
binary with its own governed lockfile. It consumes public canonical kernel,
interop, and supported Rust-host surfaces but exports no product API. Every
timed result passes through `black_box`; latency is retained as integer
nanoseconds so tiny operations do not acquire artificial microsecond-scale
variance. The 54 live coordinates comprise 50 latency fixture pairs, three
isolated peak-RSS fixture pairs, and one fixture-free aggregate of the release
kernel binary and native interop library.

Live fixture realization corrected one CP2 recipe claim: the Semantic frontend
accepts 127 `without backtracking` wrappers because the root occupies the 128th
depth slot. The previously described 128-wrapper input is the exact one-over
rejection case. The authenticated current manifest and fixture fingerprints are
the values above; no frontend or resource limit changed.

Five calibration repetitions remain explicit in the baseline instead of being
collapsed. Each latency repetition preserves 64 normalized nanosecond samples,
64 raw batch durations, and the exact selected batch count after 16 batched
warmups; each peak-RSS or artifact-size repetition preserves one isolated byte
observation and a batch count of one. Calibration selects a count once per
coordinate and reuses it for the other four repetitions. Full and Release must
reuse that same authenticated count. The baseline distribution is the five
repetition medians. Relative budgets retain the locked six-MAD rule, and each
absolute ceiling is two derived relative budgets above the median. The
controller rejects incomplete coordinates, repetitions, samples, batch
durations or counts, statistics, budgets, fixture-free identity, or partially
activated manifests.

A reviewed environment-control correction requires every governed Linux
calibration and comparison process to inherit one fixed logical CPU affinity.
The current Ubuntu 24.04 / WSL2 / Intel Core i9-14900HX environment selects
logical CPU `20`. The controller applies that selection before building or
measuring, and each release runner independently rejects a process whose
effective affinity is not exactly `[20]`. The authenticated environment records
the single-CPU policy, selected logical CPU, effective affinity, and effective
cpuset; Full and Release require an exact baseline match. This correction does
not change warmups, samples, statistics, budgets, ceilings, product code, or the
host power plan.

The first fresh governed five-repetition calibration from clean commit
`078154cb991cef9b1a2183b8e94ad93e03946cc7` failed closed with
`unstable-baseline` before any manifest, baseline, or evidence file was written.
An exact non-promoting diagnostic replay on the same logical CPU then found all
54 coordinates inside the unchanged contracts, but left
`latency:pcre2-lower-serialize / fixture:semantic-large` at 488 basis points,
only 12 basis points below the 500-basis-point limit. The original
`latency:python-re-lower-serialize / fixture:simply-large` coordinate measured
205 basis points in that replay. Because a governed run failed and a retry
cannot erase that evidence, CP3 remains in progress with no active baseline;
Full, CP4, and FINAL are not advanced.

The differential investigation established that the two paths were not
environmentally equivalent. The governed writer performed fresh release builds
and environment probes immediately before timing; the replay reused those
artifacts after the failed hour-long calibration. Their five-round measurement
loops, order seeds, runner processes, timing source, warmups, samples, batching,
and guest affinity were otherwise equivalent. The original writer emitted only
an aggregate derived-budget error before its atomic write, so its exact failing
coordinate is not recoverable and must not be inferred from the replay.

More importantly, WSL2 guest affinity does not attest host-CPU placement. The
runner's process affinity was `[20]`, but the actual container cgroup cpuset was
`0-31`, CPU quota was unlimited, and the existing `effective_cpuset` field
merely repeated the process affinity. Windows counter probes observed guest
CPU-20 work across the same host scheduling pool as material background load;
host CPU 20 was not its physical execution identity. WSL2 exposes neither a
verifiable host-vCPU binding nor thermal telemetry to this harness. A valid
next environment therefore requires a bare-metal isolated hardware thread or a
hypervisor-attested host-pinned vCPU, plus authenticated actual cgroup cpuset,
host binding/reservation, quota, clocksource, artifact hashes, and identical
pre-measurement conditioning. No further calibration is valid on the current
WSL2 environment. Differential evidence fingerprint:
`sha256:545b3f41e738fbd16da37ad41e619958039174c41ede4081327c465823a4174c`.

Windows local proof passes all 48 non-process latency coordinates, both CLI
startup coordinates, the memory workload entrypoint, nineteen focused contract
and architecture tests, all five authenticated resource groups, and the
controlled one-unit relative regression. Full truthfully remains unavailable
until an active baseline is produced on the exact Linux x86_64 environment; no
Windows timing is promoted or compared.

## Profile ownership

-   Local validates the authored contract and fixture identities without timing
    a developer workstation.
-   Pull Request executes deterministic resource-limit checks and bounded
    controlled comparisons that do not depend on noisy wall-clock equivalence.
-   Full and Release execute optimized latency, throughput, peak-memory, artifact
    size, interop, and available supported-host observations on a compatible,
    fingerprinted environment.
-   Scheduled Linux reaches the same Full producer through the canonical profile
    router; workflow YAML does not own a second implementation.

A hard regression beyond its governed budget or an absolute resource ceiling
fails certification. Waivers, if ever needed, must use the repository's
existing explicit governance rather than editing evidence or widening a
baseline in place.

## Forbidden expansion

The task cannot change product semantics, compiler implementation, diagnostics,
target profiles or outputs, public APIs, packages, dependencies, support tiers,
or existing hard resource values. It cannot publish, upload, release, push, or
turn measurements from unlike machines into a common performance claim. Any
need for one of those changes is a new governed decision, not a benchmark fix.
