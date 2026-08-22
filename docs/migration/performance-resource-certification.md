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

| Target | Analysis and planning | Lowering | Serialization |
| --- | ---: | ---: | ---: |
| ECMAScript | 1,133 us | 416 us | 54 us |
| PCRE2 | 1,546 us | 597 us | 58 us |
| Python `re` | 1,233 us | 434 us | 61 us |

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

- an authored operation and fixture manifest;
- an environment-bound measured baseline;
- a comparison result against exactly one compatible baseline; and
- a complete certification result consumed by quality profiles.

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
ceiling. Informational metrics preserve trends but cannot silently block or
pass readiness. Baseline creation or replacement is an explicit command that
records its source commit and rationale; an ordinary certification run cannot
rewrite its comparison authority.

Numeric budgets are deliberately not chosen in CP1. CP2 must derive them from
repeated controlled measurements and documented variance, then use controlled
mutations to prove that just-inside values pass and just-outside values fail.

## Profile ownership

- Local validates the authored contract and fixture identities without timing
  a developer workstation.
- Pull Request executes deterministic resource-limit checks and bounded
  controlled comparisons that do not depend on noisy wall-clock equivalence.
- Full and Release execute optimized latency, throughput, peak-memory, artifact
  size, interop, and available supported-host observations on a compatible,
  fingerprinted environment.
- Scheduled Linux reaches the same Full producer through the canonical profile
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
