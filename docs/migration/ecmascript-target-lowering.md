# Structured ECMAScript target lowering

P11-T01 begins the second canonical backend at the same boundary used by PCRE2:
normalized Semantic IR plus an exact governed target profile and a completed
portability plan. It produces deterministic ECMAScript-specific structure. It
does not serialize JavaScript regular-expression text, construct a `RegExp`,
execute Node, construct a `TargetArtifact`, migrate a binding, or publish a
package.

## Normative target authority

The target profile is authored from the
[ECMAScript 2024 RegExp grammar and matching semantics](https://tc39.es/ecma262/2024/multipage/text-processing.html).
The Pattern, Assertion, Quantifier, AtomEscape, GroupSpecifier,
CharacterClassEscape, RegExp initialization, Canonicalize, and WordCharacters
clauses govern the facts consumed here. Historical JavaScript bindings and the
PCRE2 lowering/serializer are compatibility evidence only; neither is target
authority.

The completed profile enumerates all eighteen canonical capability identities.
It records native lookahead and backward lookbehind grammar, including
variable and unbounded bodies; named/numbered captures and backreferences;
Unicode scalar/property behavior under the required `u` mode; lazy repetition;
and target-specific anchor, line, wildcard, class, and boundary representations.
Atomic groups and possessive repetition remain unavailable and may lower only
when the existing planner supplies an exact certified rewrite.

## Independent structured representation

The lowering plan owns a closed ECMAScript vocabulary for empty, sequence,
alternation, literal, wildcard, character set, repetition, position, capture,
backreference, and lookaround operations. Each node retains sorted Semantic IR
node identities, source spans, and applied-rewrite identity. Captures receive
deterministic one-based slots while preserving logical capture identity and
optional semantic names.

Global semantic case intent and exact profile options remain separate from the
operation tree. Position and class variants retain the semantic distinction
needed by later ECMAScript serialization: absolute input boundaries, line
boundaries, final-line-terminator behavior, Unicode word boundaries, ASCII and
Unicode built-in classes, dot line-terminator policy, and both lookaround
directions. P11-T02 will choose syntax and `RegExp` flags. P11-T01 does not
embed punctuation, escaping, source text, a JavaScript literal, or host API
construction.

## Certified-input and failure boundary

Lowering validates the normalized program, node/depth limits, target profile,
contract/specification compatibility, canonical program fingerprint, exact
profile revision/fingerprint, portability-plan self-validation, final status,
requirement order, capture references, and rewrite evidence before returning a
plan. Only native decisions and the already-certified atomic-literal elision
are admitted. Unsupported, unresolved, stale, malformed, conflicting, or
cross-target evidence fails closed with stable `target_lowering` diagnostics
and no partial output.

Architecture fitness rejects imports from the PCRE2 lowering/serializer,
capability or planning recomputation, regex serialization, generated spans,
`TargetArtifact`, Node or `RegExp` execution, filesystem/environment/network/
clock/process/thread/randomness inputs, bindings, frontends, editors, and
historical emitters. Target-neutral modules cannot depend back on this stage,
and the public kernel cannot bypass the ordered compiler pipeline to call it.

## Verification boundary

Tests cover every Semantic IR variant, ASCII/Unicode class domains, wildcard
line policy, all position and lookaround variants, capture slots and names,
case intent, options, all repetition modes, certified atomic-literal elision,
unsupported and unresolved plans, profile/version/fingerprint drift,
malformed rewrites, capture errors, resource ceilings, deterministic output,
and generated nested/interacting programs. No test fabricates target support by
replacing the governed profile.

P11-T02 owns ECMAScript syntax/escaping, `RegExp` flags, `TargetArtifact`
construction, and exact Node/V8 execution certification. Cross-engine behavior
and Python lowering remain later ordered tasks.
