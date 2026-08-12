# Structured Python `re` target lowering

P11-T03 adds the third independent canonical target-lowering stage. It consumes
normalized Semantic IR, one exact governed CPython `re` profile, and the
completed portability plan. It produces deterministic Python-specific
structure only. Serialization, Python source spelling, `re.compile`, runtime
execution, bindings, packages, and publication remain outside this task.

## Target authority and selected profile

The target facts come from the official Python 3.11 `re` documentation, not
the historical Python binding. The selected profile is CPython `re` 3.11 with
a required `str` pattern kind. Python 3.11 supports lookahead, common-width
fixed lookbehind, named and numbered captures and references, atomic groups,
lazy and possessive quantifiers, absolute and line anchors, word boundaries,
Unicode-aware built-in classes for `str`, and case-insensitive matching.
Variable-length lookbehind and Unicode property escape syntax remain
unavailable. Bytes applicability is retained explicitly and fails closed for
Unicode-only semantic requirements.

The profile will enumerate the same complete canonical capability vocabulary
used by the other target backends. Its option remains data owned by the target
profile; lowering must never infer pattern kind or flags from a host process.

## Independent representation

The plan will own a closed Python `re` operation vocabulary for empty,
sequence, alternation, literal, wildcard, character set, greedy/lazy/
possessive repetition, positions, captures, backreferences, lookarounds, and
atomic groups. It will retain deterministic capture slots, logical capture
identities, exact profile options, pattern kind, global case intent,
portability resolutions, applied rewrite evidence, semantic identities, and
source spans without choosing regex punctuation.

Python pattern structure stays separate from host `re` flags and API options.
Line, dot, case, verbose, ASCII/Unicode, locale, string, and bytes distinctions
must remain explicit typed inputs for later serialization. This task does not
create inline modifiers, Python string literals, byte literals, or compiled
pattern objects.

## Certified-input and failure boundary

Lowering will validate canonical Semantic IR, bounded node/depth resources,
the exact Python `re` engine and CPython runtime identities, contract and
specification compatibility, program/profile fingerprints, completed planner
correspondence, capture resolution, options, pattern-kind applicability, and
rewrite evidence. Unsupported, unresolved, stale, malformed, cross-target,
over-limit, or Unicode-in-bytes evidence returns stable target-lowering
diagnostics and no partial plan.

Architecture fitness will prohibit PCRE2/ECMAScript lowering reuse,
capability/planner recomputation, serializer/runtime/product dependencies,
ambient state, historical Python semantic authority, target-neutral reverse
dependencies, and direct kernel bypass.

## Verification boundary

Focused tests will cover every current Semantic IR variant, string and bytes
applicability, all position/lookaround variants, common-width lookbehind,
captures/references, Unicode/ASCII classes, case intent, options, atomic and
all repetition modes, deterministic nested programs, immutable inputs,
profile/version/fingerprint drift, malformed plans and rewrites, unsupported
and unknown states, and resource ceilings. Complete core, contract,
architecture, governance, migration, Local, and Pull Request checks are
required before completion.

P11-T04 owns Python syntax, escaping, artifact construction, and exact CPython
execution certification.
