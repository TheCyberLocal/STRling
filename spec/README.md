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

| Path                                                                               | Current classification                                                                                             | Permanent handling                                                                                                                                                            |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`contracts/`](contracts/)                                                         | Canonical compiler data-contract suite; normative for serialized shape and cross-contract invariants               | Implement every future frontend, kernel, backend, adapter, diagnostic surface, and conformance harness against these versioned contracts.                                     |
| [`frontends/semantic/`](frontends/semantic/)                                       | Normative `strling.semantic` flagship textual frontend syntax and mapping, currently dialect `1.0.0`               | Keep the certified Rust parser/formatter conformant to the ratified grammar, mapping, formatting, diagnostics, and authored fixtures without redefining them.                 |
| [`frontends/legacy-regex/`](frontends/legacy-regex/)                               | Normative `strling.regex-compat` compatibility/import frontend syntax, currently dialect `1.0.0`                   | Parse only its versioned grammar and fixtures, then lower structurally to canonical Semantic IR without target inference or raw passthrough.                                  |
| [`frontends/simply/`](frontends/simply/)                                           | Normative host-neutral Simply construction protocols: immutable `1.0.0` plus backward-compatible `1.1.0`           | Project the closed operation graph and registry-selected standard helpers into canonical Semantic IR and `CompileRequest`; keep host APIs, targets, and runtimes outside it.  |
| [`conversions/semantic/`](conversions/semantic/1.0/README.md)                      | Normative proof-carrying conversion-result contract, currently model `1.0.0`                                       | Convert canonical Semantic IR to Semantic STRling or direct-operation Simply output; require reconstruction proof for exact status and record every partial/unsupported case. |
| [`explanations/semantic/`](explanations/semantic/1.0/README.md)                    | Independently versioned structured semantic explanation contract, currently model `1.0.0`                          | Derive concise and detailed entities only from canonical facts, diagnostics, and completed plans; preserve uncertainty and keep generated text non-normative.                 |
| [`explanations/no-match/`](explanations/no-match/1.0/README.md)                    | Independently versioned bounded no-match evidence contract, currently model `1.0.0`                                | Evaluate canonical semantics against one private subject under hard limits; distinguish matched, proven/likely no-match, unknown, and target-unavailable outcomes.            |
| [`conformance/`](conformance/)                                                     | Specification-owned draft seed corpus; not yet normative language semantics                                        | Activate cases only through a ratified specification delegation and its content-addressed manifest.                                                                           |
| [`targets/profiles/`](targets/profiles/)                                           | Version-aware authored target-profile facts with explicitly enumerated scope                                       | Expand capability coverage deliberately; never infer support for an unlisted capability.                                                                                      |
| [`grammar/dsl.ebnf`](grammar/dsl.ebnf)                                             | Superseded transitional regex-frontend grammar and compatibility evidence                                          | Retain for migration traceability; the versioned frontend contract resolves its contradictions and owns new parser requirements.                                              |
| [`grammar/semantics.md`](grammar/semantics.md)                                     | Superseded transitional behavior/target prose and historical compatibility evidence                                | Retain for evidence only; use the versioned frontend contract for syntax and canonical semantic/target contracts for later stages.                                            |
| [`schema/base.schema.json`](schema/base.schema.json)                               | Legacy versioned TargetArtifact compatibility contract                                                             | Preserve its public compatibility scope; new kernel work uses the canonical contract suite.                                                                                   |
| [`schema/pcre2.v1.schema.json`](schema/pcre2.v1.schema.json)                       | Legacy versioned PCRE2 artifact compatibility contract                                                             | Preserve its public compatibility scope; canonical target profiles and artifacts supersede it for new architecture.                                                           |
| [`schema/conformance-fixture.schema.json`](schema/conformance-fixture.schema.json) | Versioned fixture-shape contract                                                                                   | Governs shape, not the semantic authority of implementation-derived fixture values.                                                                                           |
| [`features.json`](features.json)                                                   | Transitional feature/status inventory                                                                              | Evidence for design and migration; engine capabilities must ultimately be target-profile and version sensitive.                                                               |
| [`stdlib/`](stdlib/)                                                               | Normative guarantee vocabulary, ratified lexical-shape decisions, and the versioned canonical Essential-5 registry | Preserve audited claim boundaries; derive compatibility metadata, supported Preview wrappers, Semantic DSL examples, documentation, and portability views from one registry.  |
| `tests/spec/*.json`                                                                | Implementation-derived shared compatibility evidence outside this directory                                        | Retain for differential migration; replace semantic-oracle use with independently accepted specification-authored cases.                                                      |

## Source-language identities

**Semantic STRling** is the flagship textual authoring language. Its normative
source identity is [`strling.semantic` dialect `1.0.0`](frontends/semantic/1.0/README.md),
designed against the canonical semantic representation. The contract is
independent authority over its certified Rust parser and formatter and does not
by itself ratify the broader Semantic Specification 1.0 draft.

**Simply** is the semantic construction frontend shared by idiomatic host
builders. Its normative construction identity is
[`strling.simply-builder` protocol `1.0.0`](frontends/simply/1.0/README.md).
It produces canonical semantic input and explicit compiler routing; it is not a
host API shape, target regex representation, or runtime execution interface.

The existing regex-shaped source notation, including current `.strl` inputs,
is the **regex frontend** or **regex-compatible source dialect**. It remains a
supported compatibility and import capability, but it does not define the
semantic ceiling of STRling.

Its normative syntax identity is now
[`strling.regex-compat` dialect `1.0.0`](frontends/legacy-regex/1.0/README.md).
Dialect metadata is explicit and out of band; source text does not infer a
target.

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
    frontends/        # versioned syntax and construction frontend contracts
    conversions/      # versioned projections from canonical semantics
    explanations/     # independently versioned structured explanation contracts
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
