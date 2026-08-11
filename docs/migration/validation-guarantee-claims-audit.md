# Validation guarantee claim audit

## Purpose and authority

This audit records the claim vocabulary that existed before STRling ratified a
standard-library validation-guarantee contract. It is migration evidence, not a
semantic guarantee for any helper. The controlling authority model remains
[`spec/README.md`](../../spec/README.md): historical implementation behavior,
binding parity, examples, and compatibility fixtures do not become normative by
agreement or location.

The audit starts at repository commit
`f3803225581099c24308ae0d1478bb839769c290` on `architecture/v4`. No helper
behavior is changed or accepted as correct by this document.

## Claim classes

| Class                       | Meaning in this audit                                                                                                            | Current examples                                                                                                                                                                                                                                   | Disposition                                                                                                             |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Already normatively precise | A ratified contract identifies the property, proof boundary, evidence, unknown handling, and owning stage.                       | Semantic safety finding conditions; structured diagnostic identities and severity ownership; target capability results; portability decisions; the closed rewrite registry and proof obligations; canonical data-shape validation.                 | Preserve. Validation guarantees must reference but never absorb or override these contracts.                            |
| Merely descriptive          | Text describes intended use, examples, or a textual pattern without an authoritative proof contract.                             | Essential 5 summaries such as “matches” an email, URL, IP address, UUID, or datetime; completion/hover documentation; tutorial uses of “validation”; `valid` and `invalid` example buckets.                                                        | Treat as non-normative until governed metadata assigns a guarantee level and evidence.                                  |
| Ambiguous                   | A term could reasonably be read as a stronger semantic, standards, safety, or portability promise than the evidence establishes. | “canonical structure,” “standard format,” “RFC validation,” “conforms to generic URI syntax,” “ISO 8601 / RFC 3339 datetime,” “IP address,” and “valid” fixture labels; unqualified “strict,” “safe,” “secure,” “supported,” or “portable.”        | Replace or qualify where the overclaim is demonstrable; otherwise carry forward for the later helper audit.             |
| Stronger than current proof | The repository has no executable evidence for every condition implied by the claim.                                              | Essential 5 parity described as validation “against the cited RFCs”; URL conformance language; IPv4 acceptance without octet-range proof; datetime wording without calendar/range/offset proof; broad default UUID and email authority references. | The strongest unavailable claim is prohibited. Existing helpers remain transitional rather than silently grandfathered. |
| Implementation-specific     | “Validation” checks an implementation or data-contract invariant and does not validate user data in a helper's semantic domain.  | Canonical Semantic IR validation, normalized-form precondition checks, schema validation, parser validation, fact-store correspondence, CLI artifact validation, and binding-specific `Validator` types.                                           | Retain the established meaning in its local scope. Do not use it as evidence for a standard-library value guarantee.    |
| Historical or non-normative | The source is explicitly compatibility evidence, a design note, tutorial, legacy audit, generated report, or unratified draft.   | `tests/_design/**`, legacy binding tests and docs, historical emitter audits, `tests/spec/**`, current stdlib manifests under their pre-ratification classification, and the Semantic Specification 1.0 draft.                                     | Preserve as evidence only. It cannot authorize semantic or standards claims.                                            |

“Normatively precise” above describes only the existing contract's declared
scope. For example, canonical Semantic IR validation proves contract
well-formedness, not that an email address is deliverable; a safety finding
proves a documented structure, not exploitability.

## Known ambiguity patterns

1. **Shape presented as validity.** A regex constrains field spelling while
   prose or fixture labels call accepted strings “valid.” Numeric ranges,
   calendar rules, cross-field relationships, normalization, existence, and
   domain policy may be unchecked.
2. **Citation presented as conformance.** An RFC or ISO reference appears
   without `complete`, `profile`, `subset`, or `inspired lexical
representation` scope and without a versioned evidence corpus.
3. **Subset presented as the standard.** A documented omission such as quoted
   email forms or compressed IPv6 syntax coexists with broad “email address” or
   “IPv6 address” wording.
4. **Parity presented as proof.** Cross-binding equality proves consistent
   output, not that the shared output implements an external standard.
5. **Compiler validation conflated with value validation.** Parser, schema,
   normalized-form, and invariant checks are cited as if they establish a
   helper's accepted semantic domain.
6. **Independent dimensions collapsed.** “Safe,” “supported,” “portable,” or
   the existence of a rewrite is attached to successful value validation.
7. **Unknown silently weakened.** Missing semantic or target evidence is
   treated as lexical acceptance, invalidity, safety, or target support instead
   of being retained as unknown or unsupported for the relevant claim.
8. **Marketing adjectives without conditions.** “Strict,” “secure,”
   “standards-compliant,” and similar terms lack a finite validation definition
   and executable evidence for every implied condition.

## Existing certified boundaries

Validation-guarantee metadata will describe only acceptance of values within a
declared semantic domain. It is independent of these existing authorities:

-   [`semantic-safety-analysis.md`](semantic-safety-analysis.md) owns positive
    structural safety findings and typed uncertainty. It does not prove
    universal ReDoS immunity, runtime complexity, exploitability, or
    engine-independent security.
-   [`diagnostic-generation.md`](diagnostic-generation.md) maps certified
    evidence to stable diagnostics. Diagnostic prose and severity are not
    validation evidence, and current safety codes cannot be reused for helper
    definition, argument, input, or portability failures.
-   [`capability-evaluation.md`](../capability-evaluation.md) owns factual
    target-profile support. A value guarantee cannot infer a capability result.
-   [`portability-planning.md`](../portability-planning.md) owns native,
    equivalent-rewrite, unsupported, and unresolved planning evidence for an
    exact target profile. A helper guarantee cannot claim universal target
    behavior.
-   The closed rewrite registry in the portability contract is the only current
    authority that may certify an equivalent semantic rewrite. Matching helper
    metadata cannot supply or replace its proof.

## Scope lock

The remaining contract work is limited to:

-   a small normative taxonomy separating lexical shape, normalized structural
    validity, and explicitly enumerated semantic validation;
-   a versioned machine-readable helper-guarantee schema with structured
    standards scope, performed and omitted checks, portability limitations,
    evidence, and documentation claim class;
-   positive and controlled-invalid fixtures plus deterministic contract tests;
-   an explicit transitional inventory for existing Essential 5 and stdlib
    entries that have not received an individual correctness audit;
-   canonical contract-validation and certification-profile integration; and
-   reconciliation of normative documentation and the demonstrably strongest
    claims in the two stdlib manifests.

The contract may permit a deterministic validator stage beyond regex execution
when a claimed semantic condition requires it. It does not require or invent
such a stage for any existing helper.

## Relationship to later standard-library work

This task defines what future governed entries must say and prove. It does not
decide whether each existing helper's regex accepts the right language. The
later helper-by-helper audit must assign metadata, verify or correct semantic
conditions, build or complete the canonical registry as needed, expose
generated bindings/frontends, and certify cross-target behavior.

Existing helpers may continue only as explicitly transitional compatibility
entries. Transitional status is absence of a ratified validation claim, not a
waiver permitting an implicit strong claim.

## Explicit non-goals

-   No helper regex, AST, fixture outcome, exported function, binding, parser,
    compiler stage, Semantic IR, safety rule, capability result, portability
    plan, rewrite, target output, package version, or publication behavior is
    changed.
-   No external standard is declared completely implemented.
-   No DNS, network, deliverability, uniqueness, authorization, business-rule,
    or other environmental validation is added.
-   No runtime-complexity, ReDoS-immunity, exploitability, security, or
    universal portability claim is introduced.
-   No helper-by-helper Essential 5 correctness audit or full stdlib registry
    implementation is performed.
