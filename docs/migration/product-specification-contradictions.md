# Product and Specification Contradiction Inventory

## Purpose and authority

This inventory records the documentation review used to establish STRling's
product and specification architecture. It is migration evidence, not a
normative specification. The ratified decisions live in
[`governance/product.md`](../../governance/product.md),
[`governance/architecture.md`](../../governance/architecture.md), and the
specification entry documents.

The review used the certified baseline, preservation matrix, donor inventory,
Engineering Constitution, root and specification entry points, grammar and
semantics prose, architecture and strategy documents, test design and workflow,
contributor guidance, tutorials, binding documentation, incorporated
development instructions, and frozen migration records.

## Classification contract

| Existing claim or ambiguity                                                                                                                                 | Source class                                                            | Classification                                | Resolution                                                                                                                                                                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STRling is principally prettier/object-oriented syntax compiling to PCRE2 or native regex.                                                                  | Root README and tutorials                                               | Resolved in this task                         | Define STRling as a portable regex-intent compiler platform whose value includes semantic authoring, analysis, explanation, portability, and target-aware lowering.          |
| “One mental model, 17 languages” can be read as 17 regex targets.                                                                                           | Root README, audit/workflow prose, binding docs                         | Resolved in this task                         | Separate host-language bindings from target engines and prohibit using their counts interchangeably.                                                                         |
| The current regex-shaped EBNF is the complete flagship Semantic STRling DSL.                                                                                | Specification entry point, semantics prose, architecture examples       | Resolved in this task                         | Classify it as the transitional regex frontend/source dialect and compatibility evidence; reserve Semantic STRling for the future semantic textual surface.                  |
| The unversioned formal specification and a claimed “STRling v3” normative semantics document describe the same authority state.                             | Frozen baseline, specification README, semantics prose                  | Resolved in this task                         | Establish independent specification versioning, correct the current status, and create an unratified 1.0 draft home without claiming implementation conformance.             |
| TypeScript is the semantic source of truth or logic reference.                                                                                              | Project strategy, contribution workflow, pull-request instructions      | Resolved in this task                         | Treat TypeScript behavior and generated expectations as compatibility evidence subordinate to ratified specification and contracts.                                          |
| TypeScript-generated fixtures create normative semantics or diagnostics.                                                                                    | Contributor, testing, workflow, and pull-request guidance               | Resolved in this task                         | Preserve fixtures as non-normative transitional evidence; future specification-authored cases must derive independently from normative sources.                              |
| Each binding owns core compiler semantics as the desired architecture.                                                                                      | Project strategy, specification implementer guidance, binding templates | Resolved in this task                         | Define existing duplicated parsers, compilers, IRs, analyzers, hints, and emitters as transitional; target thin adapters over one canonical compiler.                        |
| Simply maps directly to today's IR or emits PCRE2/JS as its semantic implementation.                                                                        | Architecture prose and binding APIs                                     | Resolved in this task                         | Make Simply a first-class semantic frontend that lowers through the canonical semantic path; preserve public APIs pending contained migration.                               |
| The parser or a binding is authoritative for editor diagnostics.                                                                                            | Architecture and editor instructions                                    | Resolved in this task                         | Require CLI, LSP, and editor tooling to consume the canonical compiler; retain current binding-coupled tooling as transitional.                                              |
| Target support is a fixed feature boolean or “native” means the host runtime can execute PCRE2.                                                             | Semantics, feature tables, binding docs                                 | Resolved in this task at responsibility level | Require version/profile-sensitive target capability planning; defer exact target-profile contracts and backend support.                                                      |
| Current AST, IR, TargetArtifact schemas, or public APIs are already the final canonical semantic contracts.                                                 | Specification schemas, architecture examples, implementation docs       | Future product-design question                | Preserve their contract/evidence roles while the next task designs canonical source, Semantic IR, diagnostic, request/result, target-profile, and target-artifact contracts. |
| Callable TypeScript Pattern typing, TypeScript package-path mismatch, duplicate-cased Perl parser modules, and inconsistent safety guards are requirements. | Waivers, public-surface gaps, audits                                    | Implementation defect                         | Keep them explicitly non-contractual; correction requires contained implementation work, not product ratification.                                                           |
| Essential standard-library meaning and exact source authority are already ratified.                                                                         | Standard-library registry and binding helpers                           | Future product-design question                | Preserve the capability and evidence; ratify its semantics in later specification work.                                                                                      |

## Documents corrected directly

The task corrects documents whose authority or contributor reach could otherwise
compete with the ratified model:

-   root product and developer entry points;
-   specification entry, versioning, and current semantics status;
-   engineering authority, product, architecture, and terminology documents;
-   primary architecture and project-strategy documents;
-   contributor, testing, pull-request, and incorporated instruction files; and
-   documentation and migration indexes.

## Transitional documentation retained for later work

Lower-authority binding READMEs, binding API references, tutorials, old audit
reports, generated reports, and historical migration records are not rewritten
wholesale. Remaining contradictory phrases are acceptable only when clearly
historical/transitional or listed as follow-up debt here. In particular:

-   binding-local examples may still expose direct PCRE2 helpers and
    independently implemented compiler paths;
-   older tutorials may describe the regex frontend simply as “the DSL”;
-   historical audit and migration records retain the terminology that described
    the repository at the time; and
-   generated reports remain frozen evidence and are not edited as authored
    truth.

Before lower-authority material is promoted or reused for new design, it must be
reconciled with the ratified vocabulary and authority model.
