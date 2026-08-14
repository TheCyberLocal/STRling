# Agent navigation

## Repository ownership

This repository owns STRling language contracts, the canonical compiler and
reference kernel, host bindings, developer tooling, and associated engineering
architecture. It does not own empirical regex-engine evidence
(`regex-conformance`), research synthesis (`research-intelligence`), public web
presentation (`website`), or organization defaults (`.github`).

## Authority and entrypoints

- Read [README.md](README.md), then [governance/authority.md](governance/authority.md)
  when sources disagree.
- Use [governance/architecture.md](governance/architecture.md) for durable
  compiler boundaries and [spec/README.md](spec/README.md) for current language
  and contract authority.
- Use [docs/index.md](docs/index.md) for long-form developer documentation and
  [CONTRIBUTING.md](CONTRIBUTING.md) for contribution policy.
- Before changing a specialized subtree, read its nearest `AGENTS.md`.

Versioned normative contracts and specification-delegated cases outrank
implementations and generated fixtures. The Rust core is the reference kernel;
it cannot independently create language semantics. Historical per-binding
implementations and compatibility fixtures remain transitional where the
canonical documents say so.

## Generated artifacts and validation

Before editing or regenerating an artifact, consult
[governance/generated-artifacts.json](governance/generated-artifacts.json).
Change its authoritative source or generator input, run the registered
generator, and use the registered verification command. Never infer authority
from generated agreement alone.

Use the smallest relevant check first, then escalate:

```text
changed-file or generator check
→ focused component test
→ affected subsystem
→ ./strling profile local
→ ./strling profile pull-request
→ ./strling profile full
→ ./strling profile release
```

`toolchain.json` is the machine authority for profile membership and commands.
`check` and `certify` are convenience aliases, not profile identities. `full`
and `release` are not routine defaults.

## Working safely

Inspect branch, status, staged changes, and recent history before editing.
Preserve concurrent work; stage exact paths only. Semantic, contract,
architecture, generated-output, public-API, security, and release changes need
their controlling authority and proportionate validation. Never reset, clean,
publish, merge, or rewrite history without explicit authorization.

Copilot-specific scopes live in [.github/instructions](.github/instructions),
reusable prompts in [.github/prompts](.github/prompts), and procedural skills
in [.agents/skills](.agents/skills).
