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

| Runner     | Cases | Corpus fingerprint                                                          |
| ---------- | ----: | --------------------------------------------------------------------------- |
| Python     |    20 | `sha256:f3114a423da9928ab12ff7afe5c2ce0eba97c2f57c3599cdc98b2105a5ef914d` |
| TypeScript |    24 | `sha256:744a4d0e029fbb2890e98e25d20402044f5b551a7642255a57c80f5dec48d30a` |

The complete corpus fingerprint is
`sha256:04270620441db4715cc40f6c82cea832d1c8d7c85631d96638a427d9f4a968e6`.
The source-observation fingerprint is
`sha256:6019bd838651c22b3c0dfb32cb44fb910a2b8a1620c4bc6d7bc8251428964621`.
Every emitted case record retains runner, case, operation, surface, request,
outcome, raw observation, provenance, route review, and canonical counterpart
identities.

Three complete executions produce identical canonical observation records.
Missing cases, a reduced count, a changed case-set fingerprint, a changed raw
observation, or a changed outcome therefore fails the gate rather than silently
refreshing evidence.

## Canonical counterpart accounting

The current canonical Rust kernel accepts governed structured `SourceProgram`
requests. It intentionally does not yet expose the legacy regex-compatible text
frontend, package-root frontend adapters, Simply conveniences, target lowering,
or emission. Treating legacy source text as if it were already a kernel request
would invent the next frontend and violate the compiler boundary.

The contract therefore has 11 exact operation reviews that expand across all
44 cases:

-   36 cases are `not_comparable` with reason `operation_not_exposed`;
-   8 legacy compiler cases are `not_comparable` with reason
    `incompatible_surface`, because the historical operation consumes source
    text while the kernel consumes a structured source contract;
-   0 cases currently have a comparable canonical replacement observation; and
-   0 production replacement dispositions are approved.

Each not-comparable state has a stable review ID, rationale, authority
reference, and canonical-surface record. Changing the kernel boundary changes
its 29-input implementation fingerprint and blocks until the route reviews and
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
`sha256:c68c9cdb8a77c9f07336d1c82321105cf1941cf0e596b3a05fead15629236cf2`.
The route-coverage fingerprint is
`sha256:18990c0c54f34a8d8b142a81096ac7f9121a2908bb594f9ad9fef30cc1132514`.
The baseline fingerprint is
`sha256:cb763a33bf620c467b1633b7747096da31757f41736368ced0bc859e42464366`.

No language, parser, compiler, emitter, Simply, diagnostic, target, binding,
package, or public API behavior is changed by this gate. Later migration work
must replace a not-comparable route only when the governed canonical surface
exists and the corresponding differential evidence can be executed.
