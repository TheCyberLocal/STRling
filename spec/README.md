# STRling Specification Hub

## Current authority state

This directory is the entry point for STRling specification material. A file is
normative only when a ratified specification or contract expressly designates
it normative for a version and scope. Location under `spec/` does not grant
authority by itself.

The specification identity is **STRling Semantic Specification**. There is
currently **no ratified semantic specification version**. The certified
migration baseline records the prior formal specification state as
`unversioned-transitional`; that frozen record remains valid historical
evidence and is not retroactively relabeled.

The initial semantic specification work has the draft identity
**STRling Semantic Specification 1.0-draft**. Its
[`draft home`](drafts/1.0/README.md) is unratified and non-normative. No current
compiler or binding is represented as conforming to it.

See [`VERSIONING.md`](VERSIONING.md) for the permanent version and ratification
policy and [`governance/authority.md`](../governance/authority.md) for
repository-wide precedence.

## Authority model

STRling behavior may be defined by, in descending order:

1. a ratified, versioned specification;
2. versioned formal schemas or contracts expressly designated normative for
   their declared scope;
3. accepted specification-authored conformance cases only where the controlling
   specification delegates exact examples to them; and
4. ratified architecture decisions governing semantic interpretation within
   their scope.

The reference implementation implements these sources. It does not silently
extend them. Behavior found only in an implementation remains implementation
behavior until it is formally accepted through the authority and versioning
process.

Historical binding behavior, implementation tests, generated fixtures, and
legacy outputs remain compatibility evidence. Agreement among implementations
does not make them normative. Tutorials and examples explain controlling
sources; they do not create behavior and must be corrected when they conflict.

## Current material

| Path                                                                               | Current classification                                                                                  | Permanent handling                                                                                                                             |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [`contracts/`](contracts/)                                                         | Canonical compiler data-contract suite; normative for serialized shape and cross-contract invariants    | Implement every future frontend, kernel, backend, adapter, diagnostic surface, and conformance harness against these versioned contracts.      |
| [`conformance/`](conformance/)                                                     | Specification-owned draft seed corpus; not yet normative language semantics                             | Activate cases only through a ratified specification delegation and its content-addressed manifest.                                            |
| [`targets/profiles/`](targets/profiles/)                                           | Version-aware authored target-profile facts with explicitly enumerated scope                            | Expand capability coverage deliberately; never infer support for an unlisted capability.                                                       |
| [`grammar/dsl.ebnf`](grammar/dsl.ebnf)                                             | Transitional regex-frontend grammar and compatibility evidence                                          | Preserve accepted behavior until an explicit versioned decision revises it; do not treat it as the final Semantic STRling DSL.                 |
| [`grammar/semantics.md`](grammar/semantics.md)                                     | Transitional description of regex-frontend behavior and historical target expectations                  | Use for compatibility and specification input; its previous “STRling v3 normative” label is not a ratified semantic specification version.     |
| [`schema/base.schema.json`](schema/base.schema.json)                               | Legacy versioned TargetArtifact compatibility contract                                                  | Preserve its public compatibility scope; new kernel work uses the canonical contract suite.                                                    |
| [`schema/pcre2.v1.schema.json`](schema/pcre2.v1.schema.json)                       | Legacy versioned PCRE2 artifact compatibility contract                                                  | Preserve its public compatibility scope; canonical target profiles and artifacts supersede it for new architecture.                            |
| [`schema/conformance-fixture.schema.json`](schema/conformance-fixture.schema.json) | Versioned fixture-shape contract                                                                        | Governs shape, not the semantic authority of implementation-derived fixture values.                                                            |
| [`features.json`](features.json)                                                   | Transitional feature/status inventory                                                                   | Evidence for design and migration; engine capabilities must ultimately be target-profile and version sensitive.                                |
| [`stdlib/`](stdlib/)                                                               | Normative validation-guarantee vocabulary and claim schemas plus transitional helper compatibility data | Apply the contract to future governed claims; existing Essential 5 and registry helpers remain explicitly unratified pending individual audit. |
| `tests/spec/*.json`                                                                | Implementation-derived shared compatibility evidence outside this directory                             | Retain for differential migration; replace semantic-oracle use with independently accepted specification-authored cases.                       |

## Source-language identities

**Semantic STRling** is the future flagship textual authoring language designed
against the canonical semantic representation.

The existing regex-shaped source notation, including current `.strl` inputs,
is the **regex frontend** or **regex-compatible source dialect**. It remains a
supported compatibility and import capability, but it does not define the
semantic ceiling of STRling.

Target regex is emitted output for a selected target engine/profile. It is
neither Semantic STRling nor the regex frontend, even when surface spellings
overlap.

## Stable directory strategy

The repository evolves toward this structure without mass relocation:

```text
spec/
    README.md
    VERSIONING.md
    drafts/<major>.<minor>/
    versions/<major>.<minor>/
    grammar/          # current regex-frontend material; future dialect grammars
    semantics/        # future versioned semantic material
    schema/           # versioned formal contracts
    conformance/      # specification-authored cases
    targets/          # target-profile specifications
    stdlib/           # standard-library specification material
```

Directories are created when they have reviewed content. Existing grammar,
schemas, fixtures, and tests are not moved merely to match the target layout.

## Change rules

A semantic proposal starts in a draft and follows
[`VERSIONING.md`](VERSIONING.md). Ratification must identify every normative
file and delegated conformance set. New behavior must not be authored by
changing an implementation and then accepting its generated output as the
specification.

Compatibility evidence remains review input. A future specification may retain,
clarify, deprecate, or deliberately reject historical behavior, but an
incompatible decision requires the appropriate specification version change and
explicit migration treatment.
