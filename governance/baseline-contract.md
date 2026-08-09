# Certified Migration Baseline Contract

## Purpose and authority

The certified migration baseline freezes reviewable engineering evidence before
STRling's product architecture changes. It records accepted current behavior,
public compatibility surfaces, hardgate results, transition debt, and donor
provenance. It is not a language specification, semantic oracle, public release,
or substitute for a versioned contract.

The authority order in [`authority.md`](authority.md) remains controlling. A
baseline conflict with a normative specification or ratified versioned contract
must be resolved in favor of the higher-authority artifact. Historical behavior
can require an explicit compatibility decision without becoming semantic truth.

## Frozen identity and records

A baseline has two distinct identities:

-   `certified_commit` is the committed repository state against which the full
    certification command set passed.
-   `donor_commit` is the immutable commit object representing the preserved
    donor line. Branch names are discovery aids only; recorded full SHAs are
    authoritative.

The baseline manifest conforms to
`schemas/migration-baseline.schema.json`. It fingerprints only artifacts that
materially define compatibility, governance, or certification. Each fingerprint
states whether its bytes come from the certified Git tree or from a later frozen
record. This separation avoids pretending that self-referential metadata was
present in the commit it identifies.

The frozen-baseline registry conforms to
`schemas/frozen-baseline-registry.schema.json`. It anchors the manifest digest;
the manifest in turn anchors certification, inventory, and preservation records.
Git history supplies immutable provenance, while validation detects accidental
working-tree or later-commit alteration of the frozen evidence.

## Certification evidence

Machine-readable certification evidence conforms to
`schemas/certification-evidence.schema.json` and has a concise human companion.
It records commands and normalized result summaries rather than full logs. The
evidence must identify:

-   the certified commit and clean committed-state precondition;
-   active hardgates and their result;
-   enforced and transitional public surfaces and generated artifacts;
-   enforced, transitional, and future architecture rules;
-   active waivers and retirement conditions;
-   declared transitions and their source policies; and
-   known defects or contradictions excluded from compatibility obligations.

An incomplete capability is not a passing hardgate. It is acceptable only when
the existing quality policy explicitly classifies it as `not_applicable`,
`not_yet_configured`, or `not_yet_enforceable` and the aggregate has no
`failed` or `unavailable` result.

## Donor inventory classification

The donor inventory conforms to `schemas/donor-inventory.schema.json`. Each
capability has exactly one target disposition:

-   **preserve** — retain the asset substantially as-is because its form and
    architectural role remain suitable.
-   **port** — transfer valuable implementation or behavior into the target
    architecture with bounded adaptation.
-   **rewrite** — retain the capability or evidence obligation, but replace an
    implementation that conflicts with the target architecture.
-   **retire** — deliberately remove behavior or tooling superseded by the
    target architecture after its replacement is certified.
-   **evidence** — retain for historical, regression, conformance, or
    differential comparison, not as future implementation.
-   **discard** — exclude accidental, obsolete, generated, package, or otherwise
    irrelevant material from preservation obligations.

Disposition is independent of branch representation. A capability separately
records whether it is equivalent in the governed branch, modified there,
partially superseded, fully superseded, or absent. This prevents an already
incorporated asset from being scheduled for a false future port.

## Compatibility preservation categories

The preservation matrix conforms to
`schemas/compatibility-preservation.schema.json` and assigns every entry to one
of four obligations:

-   **must-preserve** — a governed public contract, accepted semantic case, or
    selected user-facing capability that requires an explicit versioned decision
    before incompatible change.
-   **evidence-only** — material retained for regression or differential review
    without implementation or semantic-authority status.
-   **intentionally-replace** — architecture or tooling whose current form must
    be superseded after replacement evidence exists.
-   **known-defect-non-contractual** — a documented inconsistency or suspected
    defect that must not be normalized into a permanent requirement.

These categories describe migration obligations, not semantic precedence.

## Required certification commands

The complete committed-state certification contract is:

```sh
./strling format --check all
./strling hygiene
./strling lint all
./strling typecheck all
./strling generate --check
./strling generate --check --json
./strling contracts --check
./strling contracts --check --json
./strling governance
./strling governance --json
BUNDLER_VERSION=2.4.20 ./strling check all
BUNDLER_VERSION=2.4.20 ./strling check all --json
BUNDLER_VERSION=2.4.20 ./strling certify all
BUNDLER_VERSION=2.4.20 ./strling certify all --json
python3 -m unittest discover -s tooling/tests -p 'test_*.py'
git diff --check
git status --short
```

The Bundler selector chooses the repository-locked Bundler already installed in
the certification environment; it does not relax the version probe. Successful
certification requires parseable structured output, no failed or unavailable
operation, no repository mutation by check modes, and an empty final status.

