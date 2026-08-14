# Standard-library claim contracts

## Authority

[`VALIDATION_GUARANTEES.md`](../VALIDATION_GUARANTEES.md) defines the normative
validation vocabulary. The versioned schemas in this directory are normative
for governed helper-guarantee metadata and controlled contract fixtures. The
separate audited-decision record applies that vocabulary to current helpers;
example values here remain non-normative.

Contract version `1.0.0` contains:

-   [`helper-guarantee.schema.json`](1.0/helper-guarantee.schema.json), the
    canonical metadata shape;
-   [`controlled-invalid-guarantee.schema.json`](1.0/controlled-invalid-guarantee.schema.json),
    the deterministic negative-fixture shape;
-   [`transition-inventory.schema.json`](1.0/transition-inventory.schema.json),
    the explicit state machine from unclassified historical helpers to
    individually audited decisions;
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
now points every current Essential 5/registry helper to its ratified P14-T01
audit decision. [`stdlib-guarantee-audit.json`](../stdlib-guarantee-audit.json)
assigns `lexical_shape` to all five helpers, and
[`stdlib-guarantee-audit-fixtures.json`](../stdlib-guarantee-audit-fixtures.json)
records eight public behavior variants plus accepted shapes, rejected shapes,
semantic false positives, standard false negatives, and policy non-claims.
The compatibility helpers remain non-semantic; P14-T02 owns their future
canonical registry and generated contract surfaces.

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
-   exact audited coverage for five helpers, eight variants, all 17 bindings,
    every public spelling, and every edge-corpus group;
-   correspondence among transition entries, audit decisions, current
    manifests, binding implementations/tests, and scoped RFC references; and
-   deterministic rejection of every controlled invalid mutation for its
    declared rule.

The canonical validator must not infer semantic validity from prose, regexes,
fixture names, citations, or implementation agreement. P14-T01 records exact
observed lexical behavior as an explicit product decision without promoting it
to normalized or semantic validity.

`python3 tooling/contract_validation.py` is the sole quality-runner entry point.
It invokes the internal standard-library validator, materializes each negative
mutation twice without changing its base fixture, and rejects any case that
fails for a rule other than its declared identity.
