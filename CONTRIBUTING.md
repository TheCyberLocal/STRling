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

TypeScript is not semantic authority. Its current compiler, HintEngine, tests,
and generated `tests/spec/*.json` outputs are transitional compatibility
evidence.

## Current fixture and hint workflow

Existing error fixtures require exact `expected_hint` values, and current
bindings preserve those values. When a contained compatibility change must use
the TypeScript producer:

1. identify the controlling diagnostic contract or explicit compatibility
   decision;
2. declare semantic, diagnostic, schema, public, target, and generated changes;
3. update the transitional producer;
4. run `npm run build:specs` in `bindings/typescript`;
5. review every output against the controlling decision; and
6. verify every affected binding plus canonical hardgates.

Generation does not approve behavior, and the TypeScript HintEngine is not the
normative source of diagnostic meaning.

## Host bindings and targets

A binding exposes STRling from a programming ecosystem. A target profile
describes regex/runtime semantics such as PCRE2, ECMAScript, or Python `re`.
Never use a host-binding count as a target count.

Existing per-binding compilers remain transitional. New architecture work must
converge on the canonical compiler rather than create another semantic island.

## Resources

-   [`Developer Hub`](docs/index.md)
-   [`Contribution Guidelines`](docs/guidelines.md)
-   [`Specification Hub`](spec/README.md)
-   [`Specification Versioning`](spec/VERSIONING.md)
-   [`Canonical Terminology`](governance/terminology.md)
-   [`Test Suite Guide`](tests/README.md)
-   [`Security Policy`](SECURITY.md)
-   [`Organization Support`](https://github.com/strling-lang/.github/blob/main/SUPPORT.md)
-   [`Code of Conduct`](https://github.com/strling-lang/.github/blob/main/CODE_OF_CONDUCT.md)
