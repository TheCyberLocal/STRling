# Standard-library claim contracts

## Authority

[`VALIDATION_GUARANTEES.md`](../VALIDATION_GUARANTEES.md) defines the normative
validation vocabulary. The versioned schemas in this directory are normative
for governed helper-guarantee metadata and controlled contract fixtures. They
do not assign a guarantee to an existing helper or make example values
normative.

Contract version `1.0.0` contains:

-   [`helper-guarantee.schema.json`](1.0/helper-guarantee.schema.json), the
    canonical metadata shape;
-   [`controlled-invalid-guarantee.schema.json`](1.0/controlled-invalid-guarantee.schema.json),
    the deterministic negative-fixture shape;
-   [`transition-inventory.schema.json`](1.0/transition-inventory.schema.json),
    the explicit non-grandfathering contract for historical helper
    definitions;
-   three positive examples covering `lexical_shape`,
    `normalized_structure`, and `semantic`; and
-   controlled invalid cases for missing levels, unsupported strict claims,
    undefined external-standard scope, contradictory complete/subset scope,
    embedded portability, unsupported safety claims, and malformed evidence
    references.

All positive helpers use `status: example`. They illustrate the contract and
MUST NOT be exposed as standard-library APIs or cited as ratified helper
semantics.

[`validation-guarantee-transition.json`](../validation-guarantee-transition.json)
classifies every current Essential 5/registry helper as
`transitional_unclassified`, `not_ratified`, and entitled to
`no_validation_guarantee` until the later helper-by-helper audit supplies
complete metadata and evidence.

## Cross-field invariants

Schema validation is necessary but not sufficient. Canonical contract
validation additionally enforces:

-   unique condition, stage, check, evidence, exclusion, and omitted-check
    identities;
-   exact condition/category correspondence between the definition and each
    performed check;
-   complete, non-duplicated condition coverage by stages and checks;
-   resolution of every stage, check, evidence, and evidence-binding reference;
-   exactly one evidence binding for every performed check and no binding for
    an omitted check;
-   semantic evidence attached to every semantic check;
-   standard-conformance evidence for `subset`, `profile`, and `complete` scope;
-   repository-relative evidence paths whose file targets exist; and
-   deterministic rejection of every controlled invalid mutation for its
    declared rule.

The canonical validator must not infer helper semantics from prose, regexes,
fixture names, citations, or implementation agreement.

`python3 tooling/contract_validation.py` is the sole quality-runner entry point.
It invokes the internal standard-library validator, materializes each negative
mutation twice without changing its base fixture, and rejects any case that
fails for a rule other than its declared identity.
