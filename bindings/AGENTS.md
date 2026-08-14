# Binding agent guidance

`bindings/` exposes STRling to host-language ecosystems. Bindings are adapters
and compatibility projections; they do not own language semantics or target
capabilities. Use the canonical contracts and core behavior, then read the
binding's README and manifest before editing.

Keep the binding's public API, implementation, tests, package metadata,
examples, and documentation coherent. Shared `tests/spec/*.json` data is
transitional compatibility evidence produced through its registered workflow,
not permission to change semantics. Version files, public-contract snapshots,
lockfiles, and fixture projections may be generated; consult
`../governance/generated-artifacts.json` before editing them.

Begin with the binding's focused test through `./strling test <binding>`. Add
format, lint, typecheck, contract, cross-binding, or profile checks when the
changed surface requires them. Do not run every binding merely for a localized
adapter change unless a shared contract or fixture changed.
