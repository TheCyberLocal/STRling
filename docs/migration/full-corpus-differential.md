# Complete Migration Corpus Differential Gate

## Purpose and authority

The complete migration differential is the blocking repository gate over the
focused TypeScript and Python migration corpora. It reproduces every governed
historical observation, records the current canonical-counterpart state for
every case, and fails when corpus coverage, observations, route reviews,
canonical-boundary evidence, comparison evidence, or approved replacement
dispositions change without an explicit baseline review.

The gate remains migration evidence. It cannot define language semantics,
rewrite product sources, or make historical agreement authoritative. The
authority hierarchy in [`governance/authority.md`](../../governance/authority.md)
and the canonical compiler boundary remain controlling.

## Machine contracts and command

The versioned inputs are:

-   [`migration_differential_contract.json`](../../tooling/migration_differential_contract.json),
    which defines artifact and baseline schema `1.0.0`, authority invariants,
    the selected corpora, the canonical implementation boundary, and the exact
    route review for every corpus operation;
-   [`migration_differential_baseline.json`](../../tooling/migration_differential_baseline.json),
    which locks the reviewed corpus, source-observation, canonical-boundary,
    route-coverage, and historical-comparison fingerprints; and
-   [`migration_differential.py`](../../tooling/migration_differential.py),
    which executes the runners, validates the baseline, and emits canonical
    JSON evidence without writing into the repository.

Run the clean-checkout gate from the repository root:

```text
./strling migration-differential --repeat-runs 3
```

The same offline operation is a mandatory member of the `local`,
`pull-request`, `full`, and `release` profiles. Candidate baseline evidence can
be inspected, but not written or accepted automatically, with
`--print-baseline-candidate`. Updating the checked baseline is a governed code
review action.

## Complete corpus coverage

The checked baseline covers all 44 source observations:

| Runner     | Cases | Corpus fingerprint                                                        |
| ---------- | ----: | ------------------------------------------------------------------------- |
| Python     |    20 | `sha256:f3114a423da9928ab12ff7afe5c2ce0eba97c2f57c3599cdc98b2105a5ef914d` |
| TypeScript |    24 | `sha256:744a4d0e029fbb2890e98e25d20402044f5b551a7642255a57c80f5dec48d30a` |

The complete corpus fingerprint is
`sha256:823a6b0806553ed08fe7c367c6510d80235079383632a11a9857c48d951ad2cb`.
The source-observation fingerprint is
`sha256:3cfca8d433dc5436ecdc5e5131e7d2e6f313fbecff46efd3fc486d31d49c92e9`.
Every emitted case record retains runner, case, operation, surface, request,
outcome, raw observation, provenance, route review, and canonical counterpart
identities.

Three complete executions produce identical canonical observation records.
Missing cases, a reduced count, a changed case-set fingerprint, a changed raw
observation, or a changed outcome therefore fails the gate rather than silently
refreshing evidence.

## Canonical counterpart accounting

The current canonical Rust kernel accepts governed structured `SourceProgram`
requests and exposes the pure `strling.regex-compat@1.0.0` parser as
`strling_kernel::regex_frontend::parse(&SourceDocument)`. It intentionally does
not yet expose package-root frontend adapters, Simply conveniences, target
lowering, artifact orchestration, or emission. The parser returns validated
canonical Semantic IR rather than a binding-specific historical AST.

The contract therefore has 11 exact operation reviews that expand across all
44 cases:

-   26 cases are `not_comparable` with reason `operation_not_exposed`;
-   18 cases are `not_comparable` with reason `incompatible_surface`: eight
    legacy compiler cases consume source text while the kernel compiler consumes
    a structured source contract, and ten historical parser observations return
    binding-specific ASTs while the canonical parser returns validated Semantic
    IR;
-   0 cases currently have a comparable canonical replacement observation; and
-   0 production replacement dispositions are approved.

Each not-comparable state has a stable review ID, rationale, authority
reference, and canonical-surface record. Changing the kernel boundary changes
its 30-input implementation fingerprint and blocks until the route reviews and
baseline are deliberately renewed. Marking a route comparable without actual
canonical execution evidence also fails.

## Historical peer discrepancies versus replacement discrepancies

The preceding comparison contract still evaluates the 12 exact shared
TypeScript/Python cases. Six are equivalent and six differ only at
`/outcome/evidence/return_shape`. Those six remain
`unresolved_discrepancy` historical-peer evidence under comparison result
fingerprint
`sha256:06a2e2d095f89ba2fdfb13ffc950e1290b920d558605ab176bd4d08887dfba97`.

The gate does not call those differences equivalent, accept them as product
behavior, or use them to select a winner. They are not replacement
comparisons: both sides are historical, and no current canonical frontend or
adapter establishes correspondence. Their exact observations and comparison
identities are nevertheless baseline-locked so any change is visible.

Replacement discrepancies have a stricter rule. A comparable historical to
canonical result must carry a taxonomy-valid `migration_review`
classification. `unresolved_discrepancy` is always blocking. Preservation,
intentional correction, and unsupported legacy behavior must retain the
authority, scope, rationale, comparison, and classification identity required
by the existing taxonomy. Fixture-only classifications cannot enter the
production baseline.

## Negative and mutation certification

Focused certification proves rejection of:

-   corpus shrinkage or incomplete operation-route coverage;
-   changed source observations or historical peer evidence;
-   stale route reviews or a changed canonical boundary;
-   altered baseline fingerprints;
-   removed or altered approved dispositions; and
-   unresolved replacement reviews.

The controlled approved-disposition mutations use the taxonomy's explicit
`certification_fixture` scope. Production replacement records must use
`migration_review`, so the fixture cannot bypass the canonical-adapter guard.

## Checked identity and product preservation

The checked contract fingerprint is
`sha256:4b8d2d71537fbb04f61ed4afd5ea730a23a8f0074f9b130ee343f0e436cb90dc`.
The route-coverage fingerprint is
`sha256:c6d41f9483e1235ab44e2f2b0e9322a8cb56b69c3ca13aff43de102c313048ae`.
The baseline fingerprint is
`sha256:e52a2b48c01b214cf74a9aee967a55817637b11f5c68666a14a59799227dd845`.

This renewal records the additive pure Rust parser route and no binding,
package, public API, artifact, compiler, emitter, Simply, diagnostic, or target
behavior. Later migration work must replace a not-comparable route only when
authoritative structural correspondence and executable canonical evidence both
exist.
