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
`sha256:c8ebb142d2351651457eb9e5f9db638d93ffbf57fee92228b9a7d572c5ab0bc7`.
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

A candidate batch count is accepted only after two consecutive selector probes
reach the same two-millisecond target. A faster confirmation rejects a cold or
interrupted first probe and continues the existing proportional selection. The
selector probes are neither samples nor warmups: all coordinates still execute
exactly sixteen warmups with the selected batch before collecting the same 64
samples, and the safety target, maximum batch count, and minimum accepted batch
median are unchanged.

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

The initial environment-control correction required each WSL2 calibration and
comparison process to inherit one fixed guest logical CPU affinity. That
Ubuntu 24.04 / WSL2 / Intel Core i9-14900HX investigation selected guest CPU
`20`; both controller and runner verified `[20]`. It proved that guest affinity
is necessary, but not that the guest CPU is a stable physical host resource.
The correction did not change warmups, samples, statistics, budgets, ceilings,
product code, or the Windows host power plan.

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
verifiable host-vCPU binding nor the native host scheduling controls to this
harness. A valid next environment must therefore be an authenticated native
bare-metal host, or a virtual environment with an attested host-pinned
reservation. No further calibration is valid in the current WSL2 guest.
Differential evidence fingerprint:
`sha256:545b3f41e738fbd16da37ad41e619958039174c41ede4081327c465823a4174c`.

That WSL2 result is retained as non-authoritative environment-limitation
evidence. It is not a failed product benchmark, is not superseded by a passing
replay, and cannot be promoted by retrying the guest. The 500-basis-point MAD
limit, 4000-basis-point derived-budget maximum, five repetitions, batching,
sampling, and all product behavior remain unchanged.

## Native host qualification gates

Authoritative performance evidence may be produced on native bare-metal Linux
or native bare-metal Windows x86_64. A hypervisor-pinned environment remains
eligible in policy only when a host-side trust path can authenticate and
enforce its physical CPU reservation. WSL2 and other guest-generated placement
claims remain non-authoritative. Native Windows is not a guest merely because
the same machine can host WSL2.

The offline bare-metal conditioner at
`tests/certification/performance-resource/1.0/environment/bare_metal_linux.py`
must be installed as a root-owned, non-writable executable outside the checkout.
It rejects any hypervisor, any execution affinity or unified-cgroup-v2 effective
cpuset other than logical CPU `20`, a finite CPU quota, a non-`tsc` clocksource,
an online sibling thread on the measured physical core, incomplete
`isolcpus`/`nohz_full`/`rcu_nocbs` isolation, IRQ affinity that includes CPU
`20`, a non-performance governor or energy preference, unavailable or nonzero
thermal-throttle counters, and any unrelated process or kernel thread that can
migrate onto CPU `20`.

The resulting root-owned attestation embeds, rather than merely asserts, the
actual cgroup path/cpuset/quota, host and selected-CPU topology, online CPU set,
processor and microcode identity, isolation and IRQ sets, power controls,
thermal counters, unrelated-task scan, clocksource, and conditioner hash. The
controller independently fingerprints Python, Rust 1.75 `rustc` and Cargo, the
release runner, kernel executable, and native interop library. The Rust runner
independently reads its real cgroup v2 path, `cpuset.cpus.effective`, `cpu.max`,
and current clocksource before either latency or RSS work.

For the dedicated-Linux path, the host must boot with CPU `20` isolated from
scheduling ticks, RCU callbacks, and managed IRQ work; its sibling hardware
thread must be offline; and all
housekeeping services and kernel threads must exclude CPU `20`. After those
host controls are applied, the minimal governed execution sequence is one
persistent systemd scope so attestation, qualification, and calibration retain
the same cgroup identity:

```bash
sudo install -o root -g root -m 0555 \
  tests/certification/performance-resource/1.0/environment/bare_metal_linux.py \
  /usr/local/libexec/strling-performance-bare-metal
sudo systemd-run --scope --pty \
  --unit=strling-performance-certification \
  --property=AllowedCPUs=20 --property=CPUQuota= /bin/bash
taskset --cpu-list --pid 20 $$
/usr/local/libexec/strling-performance-bare-metal attest \
  --selected-logical-cpu 20 \
  --output /run/strling-performance-host-attestation.json
export STRLING_PERFORMANCE_HOST_ATTESTATION=/run/strling-performance-host-attestation.json
python3 -m tooling.performance_resource_certification qualify --json
python3 -m tooling.performance_resource_certification baseline --replace \
  --rationale "P18-T04 dedicated bare-metal five-repetition calibration" --json
```

The native-Windows path runs directly on Windows, never through WSL, Docker, or
a guest. The offline helper at `tooling/performance_windows.py` rejects a
32-bit compatibility process, multiple processor groups in the current
versioned path, firmware that identifies a virtual guest, battery power,
battery saver, a missing power-policy GUID, a CPU-rate-limited Job Object, an
unavailable CPU-set mapping, a processor policy other than minimum/maximum
100 percent with boost disabled, a selected-processor frequency below its
authenticated non-boosted maximum/limit, or any mismatch after applying both
`SetProcessAffinityMask` and `SetProcessDefaultCpuSets`. It also calls
`SetProcessInformation(ProcessPowerThrottling)` with execution-speed control
enabled and state cleared, selecting HighQoS explicitly instead of allowing
Windows heuristics to infer EcoQoS. The selected controller, conditioner, and
every timed runner enforce this policy fail closed. Every timed runner is also
independently constrained to group 0, logical processor `20`, CPU-set `276` on
the current candidate host. Child CLI processes inherit the hard process mask,
and the runner records the actual processor group and logical processor
observed outside every timed interval. Soft CPU-set affinity is not sufficient
for authoritative calibration: after assignment, the controller, conditioner,
and each timed runner query `GetSystemCpuSetInformation` with their own process
handle and require the selected set to report `Allocated` and
`AllocatedToTargetProcess`. The transient parked flag is not treated as stable
identity; actual processor observations retain authority for placement. The
runner authenticates the same Core Reservation before and after every measured
workload. An unreserved
native-Windows host remains supported for development but fails qualification
before calibration.

The Windows fingerprint records the physical processor identity and microcode
revision exposed by the native registry, complete CPU-set topology, selected
core, sibling set, efficiency and scheduling classes, firmware/board/BIOS
identity, OS edition/build/UBR, physical memory, active processor-group counts,
hard affinity and CPU-set identifiers, Job Object CPU-rate state, AC source and
active power-policy GUID/name, exact minimum/maximum/boost settings, selected
processor current/maximum/limit MHz from `CallNtPowerInformation`,
the selected Core Reservation flags and allocation tag, the successfully
enforced process HighQoS execution-speed policy,
QueryPerformanceCounter frequency and resolution, Rust/Cargo/Python identities
and hashes, release profile/target, and the three release artifact hashes.
Windows peak RSS comes from the native process peak-working-set counter rather
than a compatibility utility.

Before qualification and every calibration repetition, one two-second native
processor-counter observation rejects selected-CPU busy time above 500 basis
points, selected DPC/interrupt time above 100 basis points, or whole-host busy
time above 1500 basis points. Each observation is performed once; there is no
retry loop. The threshold identities, placement, quota, timer, and power policy
must remain exact across repetitions, while the raw passing observations are
retained individually. The noise gate is not the source of scheduler
exclusivity. Windows records `exclusive` and `unrelated_workloads_excluded` as
true only when the operating system reports a Core Reservation allocated to
the measured process; `housekeeping_excluded` remains false because this path
does not claim that hardware interrupts or operating-system work are absent.

This reservation requirement was added from measured evidence, not assumed.
The first exact-environment canonical Full replay retained CPU 20, CPU-set 276,
HighQoS, fixed 2.2 GHz reporting, and every artifact hash, but its process CPU
time was only 94.9 percent of wall time during a sustained coordinate. The
single failing coordinate was 153 nanoseconds above its unchanged relative
ceiling. [Windows documents ordinary CPU Sets as soft affinity](https://learn.microsoft.com/en-us/windows/win32/procthread/cpu-sets)
and exposes Core Reservation through `Allocated` and
[`AllocatedToTargetProcess`](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemcpusetinformation);
the historical
soft-affinity calibration is therefore preserved as non-authoritative evidence
and cannot be promoted or retried.

The native-Windows policy is a dedicated, reversible clone; the user's Balanced
scheme is not modified. Disabling boost and fixing the processor state is an
environment control, not a warmup or benchmark change. The stable scheme must
remain active through qualification, calibration, controlled regression, and
Full certification. Before these commands, the Windows host administrator must
assign the CPU Set corresponding to governed logical processor `20` as a Core
Reservation available to the complete certification workload; setting affinity
in this script does not create that reservation. `qualify` rejects the host if
the operating system cannot attest the allocation to the actual process:

```powershell
$certScheme = "37dbead1-8ee2-4ebd-b7f4-0f21a5f4c180"
powercfg /duplicatescheme SCHEME_BALANCED $certScheme
powercfg /changename $certScheme "STRling Performance Certification" `
  "P18 native Windows invariant-frequency certification"
powercfg /setacvalueindex $certScheme SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg /setdcvalueindex $certScheme SUB_PROCESSOR PROCTHROTTLEMIN 100
powercfg /setacvalueindex $certScheme SUB_PROCESSOR PROCTHROTTLEMAX 100
powercfg /setdcvalueindex $certScheme SUB_PROCESSOR PROCTHROTTLEMAX 100
powercfg /setacvalueindex $certScheme SUB_PROCESSOR PERFBOOSTMODE 0
powercfg /setdcvalueindex $certScheme SUB_PROCESSOR PERFBOOSTMODE 0
powercfg /setactive $certScheme
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
python -m tooling.performance_resource_certification qualify --json
python -m tooling.performance_resource_certification baseline --replace `
  --rationale "P18-T04 native Windows five-repetition calibration" --json
```

After all evidence has been produced and authenticated, restore the prior
scheme and remove only the disposable certification clone:

```powershell
powercfg /setactive SCHEME_BALANCED
powercfg /delete 37dbead1-8ee2-4ebd-b7f4-0f21a5f4c180
```

`qualify` requires a clean checkout, builds and hashes the release artifacts,
authenticates the live environment, and runs the conditioner without collecting
performance samples. Baseline creation is permitted only after that command
passes. It runs the conditioner immediately before each of the five repetitions
and rejects any conditioning-identity drift before promotion. Full repeats the
same exact environment and conditioning-identity checks before comparison and
rejects the run unless the rebuilt runner, kernel, and interop fingerprints
exactly equal the calibrated artifact set. Rust 1.75 resource-limit tests use a
dedicated target directory so build-script state from another Rust toolchain
cannot contaminate certification.
There is no retry loop or partial preconditioning path: a qualification failure
blocks timing, and an unstable coordinate remains a product/harness or
Windows-environment investigation under the unchanged limits.

Native Windows focused proof covers the exact CPU-set/core/class mapping,
affinity and CPU-set enforcement, actual execution-processor observation,
unlimited Job Object CPU state, AC and fixed-frequency power-policy identity,
native processor MHz state, QPC identity, native peak working set, firmware
guest rejection, and exact-boundary/one-over quiescence cases. Full remains
unavailable until one clean five-repetition calibration produces an active
baseline on the exact qualified native host.

## Profile ownership

-   Local validates the authored contract and fixture identities without timing
    a developer workstation.
-   Pull Request executes deterministic resource-limit checks and bounded
    controlled comparisons that do not depend on noisy wall-clock equivalence.
-   Full and Release execute optimized latency, throughput, peak-memory, artifact
    size, interop, and available supported-host observations on a compatible,
    fingerprinted environment.
-   Scheduled native hosts reach the same Full producer through the canonical
    profile router; workflow YAML does not own a second implementation.

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
