# Contributing to STRling

[← Back to Developer Hub](docs/index.md)

The organization-wide
[`contribution principles`](https://github.com/strling-lang/.github/blob/main/CONTRIBUTING.md)
apply alongside this repository-specific guide.

STRling is governed by the
[`Engineering Constitution`](governance/ENGINEERING_CONSTITUTION.md),
[`authority hierarchy`](governance/authority.md), and
[`product architecture`](governance/product.md). Read the applicable
specification and architecture material before changing semantic behavior.

## Quick start

```bash
./strling bootstrap <binding>
./strling test <binding>
./strling check all
./strling certify all
```

Use `./strling environment <component>` to validate declared tool versions and
`--json` for automation. See
[`Toolchains and Quality Commands`](docs/toolchains.md).

## Semantic and architecture changes

Semantic work starts with a ratified specification or reviewed draft/contract,
then independent conformance evidence, implementation, and certification.

There is no ratified Semantic STRling version yet. The current regex-shaped
grammar is the compatibility/import frontend. Do not modify it, Simply, the
canonical data model, targets, or adapters by inferring behavior from one
binding.

TypeScript and other host bindings are not semantic authority. All registered
bindings route through the canonical core. Retained implementation-derived
fixtures are non-normative, data-only history and cannot feed product,
generation, profile, or certification authority.

## Host bindings and targets

A binding exposes STRling from a programming ecosystem. A target profile
describes regex/runtime semantics such as PCRE2, ECMAScript, or Python `re`.
Never use a host-binding count as a target count.

New bindings must register a semantic-free adapter route through an approved
canonical transport and must not create another semantic island.

## Version and release changes

Read the generated [`release policy`](docs/release-policy.md) before changing a
product version, package coordinate, support claim, compatibility promise,
release channel, or publication workflow. The machine authority is
`governance/release-policy.json`; package manifests are projections, not
independent product-version sources. Passing certification never authorizes
publication.

## Resources

-   [`Developer Hub`](docs/index.md)
-   [`Contribution Guidelines`](docs/guidelines.md)
-   [`Specification Hub`](spec/README.md)
-   [`Specification Versioning`](spec/VERSIONING.md)
-   [`Product Version, Support, and Release Policy`](docs/release-policy.md)
-   [`Canonical Terminology`](governance/terminology.md)
-   [`Test Suite Guide`](tests/README.md)
-   [`Security Policy`](SECURITY.md)
-   [`Organization Support`](https://github.com/strling-lang/.github/blob/main/SUPPORT.md)
-   [`Code of Conduct`](https://github.com/strling-lang/.github/blob/main/CODE_OF_CONDUCT.md)
