# PCRE2 runtime certification

P10-T04 certifies the already-governed PCRE2 10.42 and 10.43 artifacts
against exact real engines, adversarial serializer inputs, resource limits,
and bounded compiler-stage performance budgets. It does not add language
semantics, target capabilities, public runtime orchestration, bindings,
packages, or release behavior.

## Certification boundary

The canonical lowering and serialization stages remain the only source of
patterns and options under test. The runtime harness is test-only: it accepts
an exact library path, verifies the selected engine version, compiles the
artifact through the 8-bit API, executes `pcre2_match`, and records structured
evidence. It must not infer options from pattern text or ambient process state.

The governed matrix covers positive and negative matches, overall and capture
spans, numbered and named capture values, compile failures, UTF/UCP and
newline behavior, anchors, lookarounds and lookbehind, atomic and possessive
constructs, and the planner rewrite already proved equivalent by the canonical
registry. Unsupported or malformed artifacts remain explicit failures before
engine execution.

Exact PCRE2 10.42 and 10.43 libraries are supplied explicitly. A missing or
wrong-version library is `unavailable`; it is never skipped or represented as
passing. Full and Release profiles preserve that state through the shared
structured-result contract.

## Pathological and resource evidence

The test corpus includes deeply nested groups and classes, escape-heavy and
empty constructs, large bounded quantifiers, legal and illegal capture names,
malformed lowered artifacts, and conflicting or shuffled options. Deterministic
generated cases exercise repeatability and rejection boundaries. Every case is
bounded by declared subject, pattern, match, depth, and heap limits so a
pathological target-engine case cannot turn certification into an unbounded
operation.

Native sanitizer evidence is collected from isolated exact-tag builds when the
host provides the required compiler runtime. The record distinguishes
executed, unavailable, and out-of-scope sanitizer configurations and retains
the exact build configuration. Passing certification claims only that the
governed bounded corpus produced no crash, undefined-behavior report, panic, or
nondeterministic semantic result; it is not a universal regex-safety claim.

## Performance budgets

Performance certification measures STRling analysis/planning,
lowering, and serialization separately after warm-up. The test uses a fixed
corpus, fixed iteration counts, monotonic timing, and generous per-stage and
total ceilings derived from a recorded baseline. It reports samples and robust
summary statistics, while the deterministic evidence fingerprint covers the
corpus, method, thresholds, pass/fail decisions, and semantic results rather
than raw wall-clock values.

PCRE2 compile and match timing is reported separately as target-engine
observation. No threshold is promoted into a language guarantee, no comparison
is made across unrelated machines, and no claim is made about arbitrary regex
runtime complexity.

## Reproducibility and exclusions

Each certification result fingerprints the harness, corpus, exact profile,
library, engine version, platform, configuration, semantic observations,
resource-limit outcomes, generated-case seed/count, and budget decisions.
Repeated execution with the same governed inputs must produce the same
deterministic result digest.

JIT behavior, UTF-16/UTF-32 parity, public compilation orchestration, editor or
LSP integration, bindings, package/version changes, publication, tagging,
release notes, and artifact upload remain outside P10-T04.
