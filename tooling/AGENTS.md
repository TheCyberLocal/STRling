# Tooling agent guidance

`tooling/` implements repository orchestration, validation, generators,
certification, migration comparison, and developer tools. Tooling must report
the authority it checks; it must not create semantic authority.

`../toolchain.json` is the machine authority for tools, components, operation
commands, and the `local`, `pull-request`, `full`, and `release` profiles.
Governance registries—especially
`../governance/generated-artifacts.json`—are machine authority for their
declared relationships. Update code, registry/schema, tests, and documentation
together when a tooling contract changes.

Run the narrow tooling unit test first, then the affected registered check.
Escalate through the root profile ladder. Preserve deterministic, offline
behavior for `local` and `pull-request`; do not silently add network access or
make an expensive certification routine.
