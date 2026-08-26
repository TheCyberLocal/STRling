# Initial cross-engine portability matrix

> Generated from the machine-authoritative matrix JSON. Do not edit by hand.

- Matrix SHA-256: `80347d681953cedab69fa34d72293db1d58f8cb83f98eabd43932ed6a57a9bbd`
- Corpus SHA-256: `e8c069f068b8562518bfcf4f782a0961b53124660e4d40e63e49cbe8c6824fb1`
- Observation SHA-256: `d7a857db479b33c6e572469e11112ce41ec35758caa163def889f7160c6800cf`
- Readiness: `ready`

## Disposition totals

| Disposition | Count |
| --- | ---: |
| `native` | 87 |
| `planner_certified_equivalent_rewrite` | 1 |
| `target_unsupported_or_constraint` | 5 |
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
| `profile:ecmascript/2024` | `1.1.0` | `node-v8 22.23.2` | `unsupported_for_profile` | `17/1/1/1/0` |
| `profile:pcre2/10.42` | `1.1.0` | `pcre2 10.42` | `unsupported_for_profile` | `17/0/2/1/0` |
| `profile:pcre2/10.43` | `1.1.0` | `pcre2 10.43` | `portable_native_for_applicable_vectors` | `19/0/0/1/0` |
| `profile:python-re/3.11` | `1.2.0` | `cpython-re 3.11.15` | `unsupported_for_profile` | `18/0/1/1/0` |
| `profile:python-re/3.11-bytes` | `1.0.0` | `cpython-re 3.11.15` | `unsupported_for_profile` | `16/0/1/3/0` |

## Classified divergences

| Case | Profile | Classification | Blocking |
| --- | --- | --- | --- |
| `case:matching/atomic-literal-rewrite` | `profile:ecmascript/2024` | `planner_certified_equivalent_rewrite` | no |
| `case:matching/input-anchors-word-boundaries` | `profile:pcre2/10.42` | `target_unsupported_or_constraint` | no |
| `case:matching/possessive-repeat-interaction` | `profile:ecmascript/2024` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:pcre2/10.42` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:python-re/3.11` | `target_unsupported_or_constraint` | no |
| `case:targets/variable-lookbehind` | `profile:python-re/3.11-bytes` | `target_unsupported_or_constraint` | no |

## Feature matrix

| Key | profile:ecmascript/2024 | profile:pcre2/10.42 | profile:pcre2/10.43 | profile:python-re/3.11 | profile:python-re/3.11-bytes |
| --- | --- | --- | --- | --- | --- |
| `alternation` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.input` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.line` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookahead` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.fixed` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.variable` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `backreference` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `boundary.word` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `capture.logical` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) |
| `character_class.ascii` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `character_class.negated` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `character_class.unicode` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `diagnostic.malformed` | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) | not_applicable (0/0/0/1/0) |
| `literal` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/1/0) |
| `repeat.greedy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repeat.lazy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repeat.possessive` | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `rewrite.atomic_literal_elision` | portable_with_certified_rewrite (0/1/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `sequence` | unsupported_for_profile (9/0/1/0/0) | unsupported_for_profile (8/0/2/0/0) | portable_native_for_applicable_vectors (10/0/0/0/0) | unsupported_for_profile (9/0/1/0/0) | unsupported_for_profile (9/0/1/0/0) |
| `unicode.case_insensitive` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `wildcard.include_line_terminators` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |

## Requirement matrix

| Key | profile:ecmascript/2024 | profile:pcre2/10.42 | profile:pcre2/10.43 | profile:python-re/3.11 | profile:python-re/3.11-bytes |
| --- | --- | --- | --- | --- | --- |
| `anchors.input_end` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.input_start` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.line_end` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `anchors.line_start` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookahead` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.fixed_length` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `assertions.lookbehind.variable_length` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | unsupported_for_profile (0/0/1/0/0) |
| `boundaries.word` | portable_native_for_applicable_vectors (1/0/0/0/0) | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `character_classes.unicode` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `character_semantics.unicode_scalar` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `groups.atomic` | portable_with_certified_rewrite (0/1/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `groups.named_capture` | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) | portable_native_for_applicable_vectors (2/0/0/0/0) |
| `matching.case_insensitive` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | not_applicable (0/0/0/1/0) |
| `references.backreference` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repetition.lazy` | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
| `repetition.possessive` | unsupported_for_profile (0/0/1/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) | portable_native_for_applicable_vectors (1/0/0/0/0) |
