# Validation and compiler guarantee boundaries

## Status and controlling contracts

This document is normative for the interaction between standard-library
validation guarantees and STRling compiler intelligence, version `1.0.0`. It
does not add a safety finding, diagnostic code, target capability, portability
decision, or rewrite strategy.

The validation levels and standards-scope vocabulary are defined by
[`VALIDATION_GUARANTEES.md`](VALIDATION_GUARANTEES.md). Existing controlling
contracts remain authoritative in their own domains:

-   [`semantic-safety-analysis.md`](../../docs/migration/semantic-safety-analysis.md)
    for target-neutral positive safety findings and typed uncertainty;
-   [`diagnostic-generation.md`](../../docs/migration/diagnostic-generation.md)
    and [`PROTOCOL.md`](../contracts/1.0/PROTOCOL.md) for diagnostic evidence,
    identity, severity ownership, and compiler-result behavior;
-   versioned target profiles and canonical capability evaluation for factual
    target support; and
-   [`portability-planning.md`](../../docs/portability-planning.md) for native,
    equivalent-rewrite, unsupported, and unresolved planning evidence.

Where this document and helper metadata lack evidence for a property, the
property remains unknown or unsupported. It is never inferred from a helper's
name, standard-library status, guarantee level, citation, examples, or regex.

## Safety boundary

A validation guarantee proves only its enumerated value conditions. It MUST NOT
imply or be used as evidence of:

-   universal ReDoS immunity or absence of denial-of-service risk;
-   bounded, linear, polynomial, exponential, or other runtime complexity;
-   exploitability, attacker control, severity, or operational impact;
-   engine-independent security or behavior;
-   target-specific runtime safety; or
-   safety merely because STRling supplies the helper.

The helper-guarantee contract therefore fixes `safety.claim` to `not_claimed`
and points to the separately authoritative safety-analysis contract. A future
separate safety result may refer to a helper's lowered Semantic IR, but it MUST
retain its own finding identity, proof, uncertainty, target boundary, and
diagnostic mapping. It does not strengthen or weaken the helper's value
guarantee.

A successful validation result does not suppress a safety finding. A safety
finding or warning does not make an otherwise accepted value fail validation.
Safety uncertainty remains uncertainty and MUST NOT become helper acceptance,
rejection, or a claim of safety.

## Diagnostic boundary

The following events are different concepts and MUST NOT share one diagnostic
identity merely because each may contain the word “invalid”:

| Event                     | Meaning and owner                                                                                                                                                                               | Required treatment                                                                                                                                                                                                                                                  |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Invalid helper definition | Governed metadata, validator stages, references, or evidence violate the helper-guarantee contract. Contract/registry certification owns this failure.                                          | Reject the definition before it becomes claim-eligible. This is not an input-validation failure and does not prove anything about a user value.                                                                                                                     |
| Invalid helper argument   | A STRling program invokes a helper with an unsupported name, type, option, version, or argument combination. The authoring/semantic compiler surface owns this failure.                         | Use a helper-argument diagnostic identity distinct from definition, input, safety, and portability identities. Normative compiler-invalidity severity rules apply only when the controlling semantic contract defines the argument rule.                            |
| Input fails a validator   | A completed validator pipeline proves at least one declared value condition false. The helper's validation-result contract owns this outcome.                                                   | Report rejection at the exact guarantee identity and level. This is ordinarily a runtime/helper outcome, not a compiler diagnostic or compiler failure. If a user-facing diagnostic surface is later defined, it must receive a distinct validation-input identity. |
| Portability failure       | The exact target profile and portability plan prove a requirement unsupported, or retain unresolved evidence. Portability planning and any later target-aware diagnostic stage own this result. | Do not relabel it as invalid input or failed semantics. Use target/portability identity and evidence; unresolved evidence remains unresolved.                                                                                                                       |
| Safety warning            | Canonical safety analysis proves one of the documented structures and diagnostic generation maps it to `STRL-SAFETY-0001` through `STRL-SAFETY-0005`.                                           | Preserve safety code, phase, category, evidence, uncertainty, and compiler-policy severity. Do not use these codes for helper failures.                                                                                                                             |
| Compiler semantic error   | Source or Semantic IR violates a ratified semantic rule independently of a helper value being tested. The semantic compiler contract owns this failure.                                         | Use its own semantic diagnostic identity and normative severity. Do not infer it from a runtime value rejection.                                                                                                                                                    |

English prose is not diagnostic identity. Presentation layers MAY explain
related events together, but the structured records, codes, phases, categories,
severity bases, and evidence owners MUST remain separable. A helper definition
fixture, a rejected runtime input, and a compiler `Diagnostic` are not
interchangeable artifacts.

No diagnostic is proof beyond its cited evidence. In particular, “valid,”
“safe,” “portable,” and “unsupported” in presentation text MUST preserve the
machine-readable domain that authorized the word.

## Portability boundary

Validation success does not imply target support. The guarantee is available on
a target only when every required validator stage and semantic condition is
representable and executable under separately certified target facts and
planning evidence.

`target_support.claim: not_claimed` states that helper metadata makes no target
claim. `profile_limited` records explicit limitations and exact authored profile
references; it does not create a final portability decision and MUST NOT be
documented as universal or automatically portable. The exact target profile,
capability evaluation, and portability plan remain authoritative.

An unsupported validator stage makes the declared guarantee unavailable for
that target. It MUST NOT silently degrade `semantic` to `normalized_structure`
or `lexical_shape`. A caller may deliberately invoke a separately identified
weaker guarantee only when that guarantee has its own complete metadata and
evidence.

## Rewrite boundary

A validation helper MUST NOT claim equivalent target behavior merely because a
rewrite candidate or plan exists. The helper-guarantee contract therefore fixes
`rewrite_equivalence.claim` to `not_claimed` and points to the canonical
portability-planning contract.

Only the closed rewrite registry and its certified proof obligations may
produce `equivalent_rewrite`. A rewrite preserves a validation guarantee only
when all of the following are true:

1.  the canonical planner certifies the registered strategy for the exact
    Semantic IR, facts, requirements, and target profile;
2.  the certified equivalence covers every affected condition and stage used by
    the helper's guarantee, rather than only a superficially similar regex;
3.  every replacement requirement is supported for the same exact profile;
4.  no safety-warning suppression, source heuristic, emitted spelling,
    benchmark, or helper metadata substitutes for proof; and
5.  later rewrite application and lowering preserve the certified plan without
    inventing semantic behavior.

The currently certified atomic-literal elision strategy retains exactly its
existing proof boundary. This contract neither registers it for a helper nor
adds variable-lookbehind, possessive, atomic, capture, flag, anchor, Unicode,
escaping, or syntax-alias rewrites.

A regex-stage rewrite cannot by itself certify a complete multi-stage semantic
validator. Parser, normalization, arithmetic, cross-field, and other semantic
stages remain required unless the existing equivalence infrastructure proves
their complete observable behavior is preserved.

## Unknown and unsupported states

Unknown is neither valid nor invalid, safe nor unsafe, supported nor
unsupported. Each owner preserves its own uncertainty:

-   incomplete helper evidence makes the metadata claim ineligible;
-   an indeterminate required validator stage makes the result unknown at that
    guarantee level;
-   `SafetyUncertainty` remains separate from positive safety findings and
    validation outcomes;
-   target-profile `Unknown` remains unresolved capability evidence and cannot
    become `unsupported`; and
-   an indeterminate rewrite proof prevents `equivalent_rewrite`.

Unsupported means an identified required operation or representation is
unavailable under its owning contract. It does not mean the input is
semantically invalid. Unknown or unsupported in one dimension MUST NOT be
coerced into a conclusion in another dimension.

## No product behavior change

These boundaries classify claims and evidence only. They do not change pattern
matching, helper execution, parser behavior, compiler stages, Semantic IR,
safety detection, diagnostics, capability evaluation, portability planning,
rewrites, target lowering or emission, bindings, public package APIs, package
versions, or publication.
