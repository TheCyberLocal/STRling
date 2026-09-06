# Target-profile semantic facts

Status: implementation design record for the bounded pre-4.0 semantic-hardening
campaign. This record does not define STRling language semantics and does not
claim that target lowering is equivalent.

## Current-model audit

Before this change, the target-profile contract described a capability by
`available`, `constrained`, or `unavailable`. Constraints used `equals`,
`at_most`, `at_least`, `one_of`, or `requires_option` over string, numeric, or
Boolean scalars; `one_of` supplied the enumerated form, and `requires_option`
had to name a declared compile/runtime option. Profile evidence carried sorted
HTTPS URLs and locators, but individual capabilities did not link semantic
claims to evidence. The enumerated capability scope already made every unlisted
capability `unknown` rather than unavailable.

The Rust loader, Python contract validator, capability evaluator, portability
planner, explanations, and diagnostics nevertheless treated affirmative
availability (and satisfied constraints) as complete semantic evidence.
Wildcards produced no capability requirement. The canonical profile SHA covered
the complete serialized profile, but there were no set, algorithm, or target-
limit facts to serialize.

This is insufficient for the V4-H01 word, line, wildcard, case-folding,
backreference, repeated-capture, matching-unit, and compiled-pattern findings.
The observed PCRE2 repetition cutoff is artifact-shape-specific and is not a
universal syntactic quantifier limit.

## Chosen contract

The existing profile system is extended in place with three required, sorted
collections: `semantic_sets`, `semantic_algorithms`, and `target_limits`. Every
fact has a unique identifier, a closed machine-readable definition, and one or
more sorted references to the profile's authoritative evidence records.

Capabilities gain sorted, role-bearing `semantic_fact_refs`. A reference states
whether its target is a set, algorithm, or limit and why the capability consumes
it. Contract validation owns the required capability-to-role relationships;
engine names never supply defaults. Dangling references invalidate the profile,
and absent required facts make evaluation fail closed.

Semantic sets use closed canonical definitions for character sets and line-
terminator sequences. Character-set definitions identify a byte or Unicode-
scalar universe and contain canonical scalar, range, and Unicode general-
category members. Category-derived sets require an explicit Unicode data
identity: either a fixed `MAJOR.MINOR.PATCH` version or a closed governed policy
identity where the upstream standard does not pin a numeric version.
Line-terminator definitions independently enumerate LF, VT, FF, CR, CRLF, NEL,
LS, and PS as applicable and declare whether multi-scalar sequences are treated
as independent code points or atomic-longest sequences. This preserves the
observed ECMAScript/PCRE2 CRLF boundary distinction. `wildcard_exclusions` is a
separate character set and is never inferred from `line_terminators`.

Semantic algorithms use closed definitions for unset backreferences
(`empty|fail`), repeated-capture state (`reset|retain`), case folding
(`ascii|simple_unicode|full_unicode|engine_specific` plus governed variants or
special equivalence classes), and matching unit (`byte|unicode_code_point`).
Unicode-sensitive folding requires the same explicit Unicode data identity.
ECMA-262 2024 follows a normative Unicode policy rather than pinning a numeric
Unicode release, so its profile records that policy/edition identity instead of
inventing a version number.

Target limits reuse typed operator/value/unit bounds while naming their scope
and prediction quality. PCRE2's compiled-pattern limit is recorded separately
from its syntactic quantifier bound and marked artifact/configuration dependent;
the V4-H01 4,369/4,370 bisection is retained only as empirical evidence.

Canonical arrays are rejected when unordered rather than normalized during
hashing. This preserves the existing cross-language canonical-JSON contract:
equivalent JSON object-key order hashes identically, while semantic fact changes
necessarily change the profile fingerprint.

## Capability relationships

The governed relationships are:

| Capability | Required semantic facts when usable |
| --- | --- |
| `boundaries.word` | set `word_characters` |
| `character_classes.unicode` | set `word_characters` when `word` is supported |
| `matching.case_insensitive` | algorithm `case_folding` |
| `anchors.line_start` | set `line_terminators` |
| `anchors.line_end` | set `line_terminators` |
| `anchors.end_before_final_line_terminator` | set `line_terminators` |
| `references.backreference` | algorithms `backreference_unset` and `capture_reset_on_iteration` |
| `character_semantics.unicode_scalar` | algorithm `matching_unit` (`unicode_code_point` for the current text engines) |
| `character_classes.wildcard` | set `wildcard_exclusions` and algorithm `matching_unit` |
| `repetition.bounded` | applicable syntactic or compiled-pattern target limits |

Unavailable capabilities may retain facts that describe native target behavior,
but unavailability itself does not become support. Later requirement
reconciliation and lowering work decides native equivalence, an equivalent
rewrite, constrained support, or unavailability.

## Version and migration decision

This pre-release change is treated as a correction to the target-profile member
of the shared `1.0.0` canonical contract suite. A whole-suite version bump would
unnecessarily migrate ten unrelated contracts. All five governed profile
revisions are bumped, and profiles lacking the new required collections or
capability references are rejected. Third-party and future profiles must migrate
explicitly; no compatibility defaults or engine-name inference are provided.

## Non-goals

This work does not change emitted regex, reconcile post-lowering requirements,
weaken the adversarial corpus, accept known divergences, or begin V4-H03/V4-H04.
The strict V4-H01 audit is expected to remain non-green.
