# Tooling index

This directory contains repository maintenance, generation, architecture, and
certification tools. The root `strling`/`strling.ps1` entrypoints and
`toolchain.json` are the authoritative command/profile registry.

## Current certification and governance

-   `product_certification.py` validates and aggregates structured profile
    evidence, then derives its human report from the validated machine artifact.
-   `semantic_authority.py` proves that canonical profiles consume structured
    authority and that retired implementation oracles cannot re-enter current
    generation or certification.
-   `architecture_fitness.py`, `governance.py`, and `generated_artifacts.py`
    enforce architecture, contained-change, and generated-output ownership.
-   `public_contracts.py` checks governed package, API, CLI, and schema snapshots.
-   `legacy_removal_inventory.py` validates the P19 removal inventory, including
    the immutable 1,094-path fixture denominator and its retained/removed split.
-   `performance_resource_certification.py`, `deep_quality_certification.py`,
    and the security producers provide structured specialist evidence consumed by
    Full and Release product certification.
-   `structured_operation_execution.py` provides the versioned atomic transport
    used when a repository producer must bind its structured result to the exact
    invocation, process outcome, and recoverable sample-consumption boundary.

Use the root profile commands for aggregate verification:

```bash
./strling profile local
./strling profile pull-request
./strling profile full
./strling profile release
```

## Historical evidence

`legacy_reference/` contains exactly two frozen implementation-era corpora and
an explanatory README. It is data-only, non-normative migration archaeology.
There is no historical runner, comparator, generator, audit command, or profile
operation, and architecture fitness forbids current product, specification,
generation, workflow, or certification consumers.

The 596 checked-in `tests/spec/*.json` files are likewise retained historical
fixtures. Their TypeScript-derived donor patterns and generator/tool files were
removed in P19-T03; current semantics come from specification-authored
contracts, the canonical compiler, structured certification, and real-engine
evidence.

## Developer utilities

-   `lsp-server/` owns editor integration assembly and development utilities.
-   `sync_versions.py`, `lua_rockspec.py`, and `check_version_exists.py` support
    deterministic release preparation without publishing.

Before editing a generated output, consult
`governance/generated-artifacts.json`, change the registered authority/input,
run its canonical producer, and run the registered check command.
