---
applyTo: "tests/**,bindings/**/tests/**,bindings/**/__tests__/**,tooling/tests/**,tooling/**/tests/**"
---

# Test guidance

Read the nearest `AGENTS.md`, [tests/README.md](../../tests/README.md), and the
controlling contract before changing expectations. Distinguish delegated
conformance, implementation tests, compatibility fixtures, and runtime
evidence; generated agreement does not create semantic authority.

Run the smallest test that proves the change, then the affected component or
subsystem. Escalate through `profile local`, `pull-request`, `full`, and
`release` only as risk and scope require. Consult
[governance/generated-artifacts.json](../../governance/generated-artifacts.json)
before changing registered fixtures or evidence.
