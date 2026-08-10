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

The current seed manifest is `draft` because STRling Semantic Specification
1.0 is not ratified. Moving it to normative status requires ratification and a
real delegation; changing an implementation or copying implementation output is
insufficient. The manifest pins every case by stable case ID, repository path,
and canonical JSON SHA-256.

Files under `tests/spec/` remain implementation-derived compatibility evidence.
They are not included in this authority manifest. A seed case may cite one in
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
