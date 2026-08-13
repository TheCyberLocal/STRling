# Specification-authored conformance cases

This directory is the specification-owned source for future conformance
expectations. Cases use
[`conformance-case.schema.json`](../contracts/1.0/conformance-case.schema.json);
authority is assigned only through the content-addressed
[`manifest.json`](manifest.json).

## Authority and ownership

A case cannot declare itself normative. Its schema requires independent
`specification_authored` intent and deliberately has no normative-status field.
The specification-owned manifest determines authority:

-   `draft` cases record reviewed specification intent but are not active
    normative requirements;
-   `delegated_normative` requires an explicit ratified specification source,
    section, and approval record.

The current shared manifest is `draft` because STRling Semantic Specification
1.0 is not ratified. Moving it to normative status requires ratification and a
real delegation; changing an implementation or copying implementation output is
insufficient. The manifest pins every case by stable case ID, repository path,
and canonical JSON SHA-256.

Files under `tests/spec/` remain implementation-derived compatibility evidence.
They are not included in this authority manifest. A case may cite one in
`compatibility_evidence`, but that reference is review context and never
controls the case's expected result.

## Normative and descriptive fields

Once a manifest is validly delegated, these fields are normative for each layer
the case actually declares:

-   `input`, `specification_version`, and all present `expectations`;
-   exact Semantic IR or selected semantic facts;
-   diagnostic code/phase/category/severity/count and location when present;
-   abstract match operation, positive/negative subjects, and logical capture
    expectations; and
-   immutable profile references and target portability statuses.

`title`, `tags`, compatibility-evidence references, and English diagnostic
prose outside these expectation shapes are descriptive. A case need not exercise
every layer. In particular, a parser-error case has no target or execution
expectation, and a target-support case need not prescribe emitted regex text.

## Determinism and invalid combinations

Case IDs are unique and stable. Arrays with identity-bearing members sort by
their stable IDs or immutable profile tuple. Match IDs and capture IDs are
unique in their scopes. UTF-8 subject and source spans must end on code-point
boundaries.

An expected error cannot coexist with match or target execution expectations.
Exact expected semantics and all inputs use the case specification version.
Target expectations resolve to an authored profile identity/revision/fingerprint.
Manifest membership must match case ID, path, specification version, authorship,
and canonical content fingerprint exactly.

## Shared cross-engine execution corpus

[`shared-corpus-v1.json`](shared-corpus-v1.json) is the versioned execution and
coverage index over these unchanged case contracts. It fixes a denominator of
PCRE2 10.42, PCRE2 10.43, ECMAScript 2024, Python `re` 3.11 text, and Python
`re` 3.11 bytes. Every case has an explicit `execute`, `unsupported`, or
`not_applicable` disposition for every profile; omission is not an
applicability signal.

The corpus records feature, capability-requirement, rewrite-strategy, mode, and
rationale metadata, but matching and support expectations remain in the
specification-authored case documents. Target artifacts and runtime
observations are forbidden as expectation sources. Completeness guards pin the
case count, application-state counts, case-set fingerprint, vector-set
fingerprint, portable feature tags, and every registered equivalence strategy.

The repository-only Rust projection applies the canonical analysis,
capability, planning, lowering, and serialization stages. The isolated Python
controller then executes only `execute` entries on exact governed engines,
normalizes UTF-16/code-point offsets to UTF-8 bytes and target capture slots to
logical capture IDs, and preserves raw plus normalized observations under
`tests/conformance/evidence/`. Those observations are certification evidence,
never semantic authority. P11-T06 owns classification of any future divergence.
