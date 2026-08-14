# STRling

> **STRling is a portable regex-intent compiler: developers express what a
> pattern means once, and STRling produces verified, explainable,
> target-specific regular-expression artifacts while surfacing portability and
> safety constraints before runtime.**

STRling is a compiler platform built around semantic pattern intent. It is not a
set of seventeen independent regex libraries, cosmetic syntax for raw regex, a
PCRE2 wrapper, a TypeScript-centric builder, or an editor-only tool.

This repository is the engineering authority for the STRling language,
specifications, canonical compiler, host integrations, and developer tooling.
It is under active pre-release architectural migration: versioned contracts,
draft specifications, implemented capability, and certified behavior are
identified separately in the linked authority documents.

## Why STRling

-   **Semantic authoring:** Describe matching intent through Semantic STRling or
    idiomatic Simply APIs.
-   **Portability before runtime:** Compare intent with a versioned target
    profile and report native support, safe rewrites, or unsupported behavior.
-   **Safety and explanation:** Produce structured diagnostics and explanations
    before an engine executes a pattern.
-   **Target-aware output:** Lower one semantic program into deterministic
    artifacts for selected regex-engine semantics.
-   **Host-language reach:** Invoke the same compiler capability from multiple
    programming ecosystems without reimplementing meaning.

## Authoring surfaces

**Semantic STRling** is the flagship textual language. Its specification-first
[`strling.semantic@1.0.0`](spec/frontends/semantic/1.0/README.md) source contract
uses readable keyword-and-block syntax and maps deterministically to the
canonical semantic model. One bounded Rust parser and canonical formatter
implement that contract and feed the canonical compiler pipeline.

**Simply** is the first-class family of fluent, idiomatic semantic APIs. Simply
does not define a separate compiler or emit target regex as its semantic
implementation.

The existing regex-shaped `.strl` notation is the **regex frontend**: a
low-level compatibility and import source dialect. It remains useful and
preserved, but it is not the final Semantic STRling DSL.

Start textual authoring with Semantic STRling:

```strling
semantic strling 1.0;
case sensitive;

pattern sequence {
    at input start;
    repeat from 5 to 5 using greedy {
        character from { unicode digit; }
    }
    at input end;
}
```

Use Simply when intent originates in program code. Use regex-compatible source
only when importing or preserving regex-shaped input. The
[`first-contribution tutorial`](docs/tutorial/first_contribution.md) shows the
canonical source request and verification path.

## Conceptual architecture

```text
Semantic STRling ─┐
Simply APIs ──────┼─> canonical semantic representation
Regex frontend ──┘       -> analysis and portability planning
                           -> target lowering
                           -> target-specific emitter
                           -> versioned TargetArtifact
```

Host-language adapters and CLI/LSP/editor tooling expose or consume this same
canonical compiler capability. They do not own independent STRling semantics.

The exact source model, Semantic IR, diagnostic, compiler protocol,
target-profile, and TargetArtifact contracts live under
[`spec/contracts/1.0`](spec/contracts/1.0/README.md); this overview does not
redefine them.

## Host languages are not target engines

A host language answers “From which programming ecosystem can I invoke
STRling?” Examples include Rust, TypeScript, Python, Java, and C#.

A target engine answers “For which regex/runtime semantics should STRling
compile?” Examples include PCRE2, ECMAScript, and Python `re`.

Binding count is therefore not target count. Target support is ultimately
version/profile-sensitive, not a timeless boolean.

## Current transition

The canonical Rust kernel accepts Semantic STRling, Simply, source-less Semantic
IR, and regex-compatible imports through one semantic pipeline. The repository
still contains historical per-binding parsers, compilers, IRs, diagnostics, and
emitters while adapters and packages migrate. TypeScript-derived fixtures and
existing binding outputs remain compatibility evidence, never semantic
authority.

## Developer quick start

Use the root CLI as the canonical setup and verification entry point:

```bash
./strling list
./strling bootstrap <binding>
./strling test <binding>
./strling check all
./strling certify all
```

See [`Toolchains and Quality Commands`](docs/toolchains.md) for governed
versions, capability states, and structured output.

## Authority and documentation

-   [`Product architecture`](governance/product.md)
-   [`Architecture invariants`](governance/architecture.md)
-   [`Engineering authority`](governance/authority.md)
-   [`Specification hub`](spec/README.md)
-   [`Specification versioning`](spec/VERSIONING.md)
-   [`Canonical terminology`](governance/terminology.md)
-   [`Developer documentation`](docs/index.md)

The current versioned schemas keep their declared contract scopes. The
[`STRling Semantic Specification 1.0 draft`](spec/drafts/1.0/README.md) is
unratified and makes no current implementation-conformance claim.

## Contributing, security, and support

- Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before changing semantic behavior,
  generated artifacts, public APIs, targets, or compatibility evidence.
- Report suspected vulnerabilities privately according to
  [`SECURITY.md`](SECURITY.md).
- Use the organization [support and issue-routing guide](https://github.com/strling-lang/.github/blob/main/SUPPORT.md)
  for implementation help and cross-repository questions.
- Community participation is governed by the organization
  [Code of Conduct](https://github.com/strling-lang/.github/blob/main/CODE_OF_CONDUCT.md).

## Ecosystem and license

- [`regex-conformance`](https://github.com/strling-lang/regex-conformance)
  owns controlled regex-system observations and conformance evidence.
- [`research-intelligence`](https://github.com/strling-lang/research-intelligence)
  owns research synthesis and non-normative recommendations.
- [`website`](https://github.com/strling-lang/website) owns the public web
  product and user-facing documentation.

STRling source and documentation are licensed under the
[Apache License 2.0](LICENSE). Copyright 2026 STRling Team.
