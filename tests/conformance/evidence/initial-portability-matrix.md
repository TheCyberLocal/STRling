# Initial cross-engine portability matrix

> Generated from the machine-authoritative matrix JSON. Do not edit by hand.

- Matrix SHA-256: `04d99cad6892e36010cea231f6e2742ff99473a2f7399ab30933772138429056`
- Corpus SHA-256: `43d290338574876994fd491bddc4c36ccb99d28b57ecac305d409ca3f4e4f9b3`
- Observation SHA-256: `9e33845262ca431c2108887dc299de6bdc7331e92d82a14e316d5de494e1780f`
- Readiness: `ready`

## Disposition totals

| Disposition | Count |
| --- | ---: |
| `native` | 83 |
| `planner_certified_equivalent_rewrite` | 1 |
| `target_unsupported_or_constraint` | 9 |
| `not_applicable` | 7 |
| `target_profile_or_documentation_discrepancy` | 0 |
| `harness_defect` | 0 |
| `canonical_expectation_defect` | 0 |
| `implementation_or_runtime_discrepancy` | 0 |
| `unresolved` | 0 |

The compact aggregate cells below are ordered as `native/rewrite/unsupported/not-applicable/unresolved`.

## Exact profiles

| Profile | Revision | Runtime | Claim | Counts |
| --- | --- | --- | --- | --- |
| `profile:ecmascript/2024` | `1.3.0` | `node-v8 22.23.2` | `unsupported_for_profile` | `17/1/1/1/0` |
| `profile:pcre2/10.42` | `1.3.0` | `pcre2 10.42` | `unsupported_for_profile` | `18/0/1/1/0` |
| `profile:pcre2/10.43` | `1.3.0` | `pcre2 10.43` | `portable_native_for_applicable_vectors` | `19/0/0/1/0` |
| `profile:python-re/3.11` | `1.4.0` | `cpython-re 3.11.15` | `unsupported_for_profile` | `17/0/2/1/0` |
| `profile:python-re/3.11-bytes` | `1.2.0` | `cpython-re 3.11.15` | `unsupported_for_profile` | `12/0/5/3/0` |

## Classified divergences

| Case | Profile | Classification | Blocking |
| --- | --- | --- | --- |
| `case:matching/atomic-literal-rewrite` | `profile:ecmascript/2024` | `planner_certified_equivalent_rewrite` | no |
| `case:matching/input-anchors-word-boundaries` | `profile:python-re/3.11` | `target_unsupported_or_constraint` | no |
| `case:matching/input-anchors-word-boundaries` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |
| `case:matching/line-anchors` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |
| `case:matching/negated-character-class` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |
| `case:matching/possessive-repeat-interaction` | `profile:ecmascript/2024` | `target_unsupported_or_constraint` | no |
| `case:matching/wildcard-including-lines` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:pcre2/10.42` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:python-re/3.11` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |

## Feature matrix

| Key | profile:ecmascript/2024 | profile:pcre2/10.42 | profile:pcre2/10.43 | profile:python-re/3.11 | profile:python-re/3.11-bytes |
| --- | --- | --- | --- | --- | --- |
| `alternation` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.input` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `anchors.line` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `assertions.lookahead` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.fixed` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.variable` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `backreference` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `boundary.word` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `capture.logical` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) |
| `character_class.ascii` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `character_class.negated` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `character_class.unicode` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `diagnostic.malformed` | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) |
| `literal` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/1/0) |
| `repeat.greedy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repeat.lazy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repeat.possessive` | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `rewrite.atomic_literal_elision` | portable_with_certified_rewrite (0/1/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `sequence` | unsupported_for_profile (9/0/1/0/0) | unsupported_for_profile (9/0/1/0/0) | portable_native_for_applicable_vectors (10/0/0/0/0) | unsupported_for_profile (8/0/2/0/0) | unsupported_for_profile (6/0/4/0/0) |
| `unicode.case_insensitive` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `wildcard.include_line_terminators` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) |

## Requirement matrix

| Key | profile:ecmascript/2024 | profile:pcre2/10.42 | profile:pcre2/10.43 | profile:python-re/3.11 | profile:python-re/3.11-bytes |
| --- | --- | --- | --- | --- | --- |
| `anchors.input_end` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `anchors.input_start` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `anchors.line_end` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `anchors.line_start` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `assertions.lookahead` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.fixed_length` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.variable_length` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `boundaries.word` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `character_classes.unicode` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `character_semantics.unicode_scalar` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `groups.atomic` | portable_with_certified_rewrite (0/1/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `groups.named_capture` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) |
| `matching.case_insensitive` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `references.backreference` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repetition.lazy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repetition.possessive` | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
