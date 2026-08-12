# Versioned PCRE2 feature correctness

P10-T03 closes the gap between the complete canonical PCRE2 operation
vocabulary and the exact authored PCRE2 10.42 and 10.43 profiles. It does not
add new Semantic IR, syntax, target operations, public compiler orchestration,
bindings, or packages. Its authority is limited to exact profile declarations,
capability facts needed to evaluate those declarations, deterministic artifact
verification, and bounded direct engine evidence.

## Exact profile authority

The two governed profiles are independent immutable claims. A feature is
available only when exact version documentation and the canonical requirement
model prove it. Unlisted support, host behavior, current-version documentation,
and silent fallback are not evidence.

Both profiles enumerate the complete current PCRE2 requirement vocabulary:
input and line anchors, lookahead, fixed lookbehind, Unicode classes and
properties, Unicode scalar matching, word boundaries, captures and references,
atomic groups, greedy/lazy/possessive repetition, and case-insensitive matching.
Required engine options remain separate artifact data. UTF, UCP, multiline
anchor behavior, and the selected `pcre2_match` API are explicit; PCRE2 10.43
also carries the governed maximum variable-lookbehind length.

The profile evidence uses exact upstream release-tag documents. Moving
`current` documentation cannot silently change either profile.

## Lookbehind classification

PCRE2 10.42 accepts a lookbehind whose top-level alternatives each have a
fixed length, even when those branch lengths differ. That is not a
variable-length branch. Capability extraction therefore distinguishes:

- one fixed length;
- fixed top-level alternatives with a finite minimum and maximum;
- a genuinely variable but finitely bounded branch;
- an unbounded branch; and
- an indeterminate bound.

The first two require `assertions.lookbehind.fixed_length`. PCRE2 10.42 rejects
the other forms. PCRE2 10.43 admits genuinely variable branches only when the
maximum is at most the profile limit and the selected matcher is
`pcre2_match`; no DFA or inferred API substitution is allowed.

## Capture and Unicode constraints

Named-capture requirements retain the actual semantic name. Capability facts
report its ASCII-identifier shape and ASCII code-unit length. Both profiles
require PCRE2's documented syntax and maximum of 32 code units. The serializer
also enforces that limit as a final target-syntax invariant, while Unicode
property identifiers retain their separate bound.

Unicode claims are versioned rather than generalized. UTF and UCP are required
profile options. PCRE2 10.42 Unicode shorthand support is limited to the exact
classes whose canonical semantics are proved; its older `\w`/`\b` category set
is not promoted to full STRling Unicode word semantics. PCRE2 10.43 records the
documented expansion of UCP word characters and word boundaries. Exact direct
tests retain the observed version delta instead of treating it as an ambient
library detail.

## Feature evidence matrix

A shared, deterministic feature corpus covers positive and negative lookahead,
fixed and fixed-alternative lookbehind, bounded variable lookbehind at and
above its boundary, numbered and named captures/references, all position forms,
atomic groups, lazy and possessive repetition, scoped insensitive matching,
Unicode properties/classes/boundaries, and nested interactions. Each case
declares the expected profile disposition, deterministic pattern/options, and
direct match observations when runtime execution is relevant.

Rust integration consumes the corpus through foundational analysis,
structural analysis, capability evaluation, portability planning, lowering,
and serialization. It proves that authored profiles, not test-only synthetic
capability lists, decide every artifact. Unsupported and constraint-boundary
cases must fail before artifact emission with stable governed requirement
evidence.

A separate test-only PCRE2 ABI probe consumes only the serialized artifact and
explicit options, verifies the loaded engine's exact version, compiles through
the selected 8-bit API, and executes `pcre2_match`. It records the engine
version, library digest, corpus digest, compile result, and match result in
canonical JSON. The probe does not become a product runtime and does not infer
options from pattern text.

## Exclusions and handoff

This task uses bounded direct execution to verify exact feature behavior. It
does not claim exhaustive pathological-input resistance, sanitizer coverage,
JIT behavior, match/depth/heap limits, UTF-16 or UTF-32 parity, or performance
budgets. P10-T04 owns those runtime and adversarial obligations. Public facade
orchestration, bindings, editor integration, package versions, publication,
and release actions remain outside this task.
