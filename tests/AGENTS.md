# Test agent guidance

Read [README.md](README.md) and the controlling specification or contract
before changing expectations. Tests verify delegated conformance,
implementation behavior, compatibility, regressions, or target runtime facts;
they do not all have the same authority.

`tests/spec/*.json` is generated transitional compatibility evidence. Runtime
observations and portability projections under `conformance/evidence/` are
registered generated artifacts. Never hand-edit either family; consult
`../governance/generated-artifacts.json` and change the authoritative source or
generator input.

Start with the smallest test that proves the change. Run the affected binding,
core, schema, target, or tooling suite next. Escalate to `profile local` and
higher profiles only when the change's scope requires it. A generated expected
value cannot validate the producer that generated it.
