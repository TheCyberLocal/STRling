# Specification agent guidance

`spec/` owns versioned language, frontend, semantic, target, standard-library,
schema, and delegated conformance contracts. Read [README.md](README.md),
[VERSIONING.md](VERSIONING.md), and the nearest contract README before editing.

Honor each document's authority label. Ratified versioned contracts are
normative only for their declared scope; drafts, legacy grammar, feature
inventories, and implementation-derived fixtures remain transitional evidence.
Schema conformance establishes shape, not semantic correctness.

For a contract change, identify compatibility and versioning impact, update
coupled schemas/examples/manifests deliberately, run the most focused schema or
contract check, then `./strling contracts --check` and the appropriate profile.
Consult `../governance/generated-artifacts.json` before touching generated
stdlib projections or other registered outputs.
