# Standard-library validation guarantees

## Status and scope

This document is the normative STRling validation-guarantee vocabulary,
version `1.0.0`. It defines what a governed standard-library helper may claim
about accepting a value. It does not ratify the semantics, correctness, or
guarantee level of any existing helper.

The keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**,
and **MAY** are normative requirements in this document.

The core rule is:

```text
lexical shape acceptance
    != normalized structural validity
    != declared semantic validity
    != external-standard conformance
```

Validation is also independent of semantic safety, runtime complexity,
security, target portability, and rewrite equivalence.

## Guarantee identity and claim eligibility

A validation guarantee applies to one stable helper identity, one versioned
guarantee definition, one accepted semantic domain, and one declared validator
pipeline. It proves only the conditions enumerated by that definition.

An input is **accepted at a guarantee level** only when every REQUIRED stage for
that level completes and every declared condition succeeds. An input is
**rejected at a guarantee level** when a completed authoritative stage proves a
declared condition false. If a required stage, condition, target fact, or proof
is unavailable or indeterminate, the result for that level is **unknown** or
**unsupported**, as applicable; it MUST NOT be reported as acceptance,
rejection, or acceptance at a weaker level unless that weaker level is invoked
as a separately identified guarantee.

A metadata declaration is **claim-eligible** only when its required evidence is
complete and valid. Missing evidence makes the claim unavailable. Historical
behavior, implementation agreement, a citation, or a passing example corpus
alone does not make a claim eligible.

Guarantee definitions are versioned independently of helper implementation and
package versions. Strengthening, weakening, or changing an accepted condition,
validator stage, standards scope, exclusion, or omitted check is an explicit
guarantee-contract change. A stronger result MUST NOT silently replace an older
guarantee identity.

## Normative guarantee levels

The complete level vocabulary is `lexical_shape`, `normalized_structure`, and
`semantic`. These values are ordered by the kinds of evidence they may express,
not by marketing quality. A higher level includes only the lower-level
conditions explicitly incorporated into its validation definition.

### `lexical_shape`

#### Meaning

`lexical_shape` proves that the entire supplied textual value satisfies the
declared character, token, delimiter, field-width, and branch pattern. The
definition MUST state its input alphabet/encoding assumptions and exact
anchoring or whole-value policy.

This level does not inherently prove numeric ranges, calendar validity,
cross-field relationships, canonical normalization, external-standard
completeness, resource existence, deliverability, uniqueness, authorization,
or business/domain validity.

#### Required evidence

-   a finite, machine-readable validation definition naming every claimed
    lexical condition;
-   an exact executable validator-stage reference, such as a governed regex or
    deterministic scanner, including whole-value matching behavior;
-   a versioned positive and negative evidence corpus reference; and
-   contract tests proving that the declared stage and evidence references are
    present and deterministic.

Examples demonstrate coverage but do not expand the finite validation
definition.

#### Permissible claims

A helper MAY say that a value “matches the declared lexical shape” or “has the
declared textual representation.” It MAY name individual proved lexical
conditions. It MAY cite an external standard only with an independently
declared standards scope, normally `inspired` or `subset`.

#### Prohibited claims

The level MUST NOT be described as semantic validation, strict validation,
complete conformance, existence verification, normalization, universal safety,
or portability. Words such as “valid email,” “valid IP address,” or “RFC
compliant” are prohibited unless a stronger, separately evidenced contract
actually authorizes them.

#### Unknown, portability, and runtime

A pure regex stage is sufficient only when it proves every declared lexical
condition under the exact execution semantics. Unknown regex semantics or
unsupported target features make that guarantee unavailable on the affected
target; they do not weaken it. A non-regex scanner MAY be used when declared.

### `normalized_structure`

#### Meaning

`normalized_structure` proves that the value can be deterministically parsed or
decomposed into the declared normalized component model and that every listed
structural constraint holds. The contract MUST define “normalized” by naming
the component model, canonicalization rules if any, retained distinctions, and
relationships checked.

Structural constraints MAY include numeric bounds, component counts,
cross-component relationships, required canonical spellings, or other
deterministic conditions that the declared component model can establish. This
level does not imply arbitrary environmental, business, or domain semantics.

#### Required evidence

All `lexical_shape` evidence incorporated by the definition is required, plus:

-   a versioned component/parse model or an exact reference to one;
-   an executable deterministic parse or normalization stage;
-   a machine-readable list of structural checks and their stage ownership;
-   evidence covering parse failure, every claimed structural constraint, and
    normalization idempotence when canonicalization is claimed; and
-   tests proving that no accepted value bypasses a required structural stage.

#### Permissible claims

A helper MAY say that a value “parses as” or “is structurally valid under” its
named component model. It MAY claim the exact ranges, relationships, and
canonical-form rules listed in its definition. It MAY expose the parsed or
normalized result when a separate public API contract authorizes that behavior.

#### Prohibited claims

The level MUST NOT imply unlisted domain semantics, external resource
existence, complete standards conformance, or security. “Normalized” MUST NOT
be used when the contract merely matches textual shape or leaves its canonical
form undefined.

#### Unknown, portability, and runtime

If parsing, normalization, or a structural relationship cannot be determined,
the result is unknown or unsupported for this level. Lexical acceptance alone
MUST NOT be returned as normalized structural acceptance. Regex execution MAY
implement this level only when executable evidence proves every declared parse,
range, normalization, and relationship condition; otherwise a deterministic
validator stage beyond regex execution is REQUIRED.

### `semantic`

#### Meaning

`semantic` proves every semantic condition explicitly enumerated in the
versioned validation definition for the declared semantic domain. It is the
strongest STRling value-validation level and has no implied conditions beyond
that finite list.

A semantic guarantee MUST state whether its rules are STRling-specific or are
associated with a complete external standard, named profile, documented subset,
or inspired representation. The adjective “strict” MAY appear only as the
documentation claim class `strict_semantic` for a claim-eligible `semantic`
definition; it never adds conditions by itself.

#### Required evidence

All lower-level evidence incorporated by the definition is required, plus:

-   a complete machine-readable enumeration of the semantic checks performed;
-   an executable deterministic validator stage for every claimed condition;
-   explicit stage-to-condition and condition-to-evidence correspondence;
-   positive, negative, boundary, and interaction evidence for every condition;
-   an explicit list of checks and cases not performed; and
-   when an external authority is referenced, evidence satisfying the declared
    standards scope and edition/profile/subset rules below.

A regex MAY participate in semantic validation, but a regex-only
implementation is sufficient only when it proves every enumerated semantic
condition. Conditions requiring parsing, arithmetic, lookup, or cross-field
reasoning require another deterministic stage.

#### Permissible claims

A helper MAY say “semantically valid under `<guarantee identity>`” and MAY name
the exact conditions it proves. “Strict” is permissible only under the rule
above. Standards conformance wording is permissible only when the separate
standards-scope contract authorizes it.

#### Prohibited claims

The level MUST NOT be described as proving conditions absent from the
definition or evidence. It MUST NOT imply deliverability, existence,
authorization, security, safety, portability, performance, or universal
correctness unless a separate controlling contract proves that property and
the documentation names that separate claim.

#### Unknown, portability, and runtime

Indeterminate or unavailable evidence for any required semantic condition
prevents semantic acceptance and prevents the `strict_semantic` claim. The
condition MUST remain unknown or unsupported; it MUST NOT be guessed, omitted,
or treated as a lexical failure. Target support for the complete declared
validator pipeline is required before this guarantee is available on that
target.

## Validation and external-standard scope

A validation guarantee and an external-standard claim are orthogonal. Every
referenced RFC, ISO specification, language standard, or other external
authority MUST have exactly one structured scope:

-   `inspired`: only a declared representation or vocabulary is derived from
    the authority; conformance is not claimed;
-   `subset`: a documented proper subset is implemented, with included and
    excluded provisions or cases;
-   `profile`: a named profile is implemented, with its identity, version or
    edition, and deviations recorded; or
-   `complete`: all applicable requirements of the identified edition and
    declared conformance target are implemented and backed by complete
    conformance evidence.

`none` is used when no external authority is part of the claim. `complete`
MUST NOT coexist with subset exclusions or a proper-subset declaration.
`subset` MUST NOT be documented as complete or compliant with the entire
authority. A citation without structured scope authorizes no conformance claim.
Absence of complete proof limits the strongest scope to the strongest
independently evidenced non-complete value.

Validation against a STRling-specific semantic definition is not external
standards conformance. Conversely, complete standards conformance may require
protocol, normalization, or environmental behavior outside a helper's value
validator; the guarantee MUST declare only the conformance target it actually
proves.

## Independence from compiler guarantees

The following dimensions MUST remain separately identified and evidenced:

| Dimension           | Owning authority                                           | Validation consequence                                                                |
| ------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Value acceptance    | This guarantee vocabulary and a governed helper definition | Proves only enumerated value conditions.                                              |
| Semantic safety     | Canonical semantic safety analysis                         | A validation guarantee neither proves nor suppresses a safety finding or uncertainty. |
| Diagnostics         | Canonical diagnostic contracts and owning generation stage | A diagnostic communicates evidence; it does not manufacture a value guarantee.        |
| Target capability   | Versioned target profile and factual capability evaluation | Target support cannot be inferred from successful validation.                         |
| Portability         | Canonical portability planning                             | Validation cannot produce `native`, `equivalent_rewrite`, or `unsupported`.           |
| Rewrite equivalence | Closed rewrite registry and certified proof obligations    | A helper definition cannot authorize an equivalent rewrite.                           |

A helper being supplied by the STRling standard library is not evidence of
ReDoS immunity, bounded runtime complexity, exploitability status,
engine-independent security, universal target support, or rewrite equivalence.

## Documentation vocabulary

Governed documentation MUST identify its claim as one of:

-   `shape_match` for `lexical_shape`;
-   `structural_validity` for `normalized_structure`;
-   `semantic_validity` for `semantic`; or
-   `strict_semantic` for an eligible `semantic` definition satisfying the
    strict rule above.

Presentation text MAY be friendlier, but it MUST preserve the exact boundary
and standards scope. The words “valid,” “strict,” “standard,” “compliant,”
“safe,” “secure,” “supported,” “portable,” “semantic,” “syntax,” and
“normalized” MUST NOT broaden the machine-readable claim.
