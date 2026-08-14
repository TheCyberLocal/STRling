# Canonical standard-library registry

## Authority

[`1.0/registry.json`](1.0/registry.json) is the normative metadata source for
the current STRling standard-library helpers. Its authority covers helper
identity, logical signatures, audited guarantee levels, exact lexical
definitions, target assumptions, examples, lifecycle and migration data,
host-language spellings, documentation metadata, evidence, and derivation
identity. [`1.0/stdlib-registry.schema.json`](1.0/stdlib-registry.schema.json)
is normative for the registry's serialized shape.

The registry does not claim that a canonical Rust implementation exists yet.
Every current entry records
`compatibility-definition-pending-canonical-core`; P14-T03 owns implementing
the corresponding Semantic IR builders or semantic validators in the Rust
core. The registry also does not generate every public binding or
documentation surface; P14-T04 owns that broader convergence work.

## Current denominator

Registry version `1.0.0` contains five stable compatibility helpers, eight
behavior variants, seventeen host-binding maps, and forty audited edge cases.
All five retain the P14-T01 `lexical_shape` guarantee. The registry fingerprint
is computed with SHA-256 over UTF-8, sorted-key compact JSON after removing the
entire `fingerprint` member. Checked-in registry serialization is sorted,
four-space JSON with one trailing newline.

Helper IDs such as `stdlib.date_time` are independent of surface spelling.
Canonical, display, registry, and Simply names live with each helper; C,
Python, Go, and other host-language names live only under `host_bindings`.
This prevents an idiomatic adapter spelling from becoming semantic identity.

Each helper entry records:

-   lifecycle status and support tier;
-   accepted parameter types, defaults, selector semantics, and output type;
-   exact registry pattern variants and their construction identity;
-   guarantee level, accepted and rejected shapes, normalization behavior,
    explicit non-guarantees, and scoped standards references;
-   supported target-profile references, constraint IDs, Unicode assumptions,
    and text-model assumptions;
-   accepted, rejected, and target-dependent examples from the ratified edge
    corpus;
-   diagnostic/error policy, aliases, compatibility classification, future
    migration surface, documentation metadata, and repository evidence.

## Generated compatibility projections

[`../essential_5.json`](../essential_5.json) and
[`../registry.json`](../registry.json) are generated, non-normative projections.
They preserve the current Essential binding fixture shape and flat editor/LSP
metadata shape while existing consumers migrate. Their generated-artifact
identity is `stdlib-compatibility-projections`; neither output may be used as
an input to its own generator or cited as competing semantic authority.

Run:

```bash
python3 tooling/stdlib_registry.py --write
python3 tooling/stdlib_registry.py --check
```

Write mode validates the canonical source and rewrites both projections. Check
mode validates schema, references, audit completeness, the derivation graph,
fingerprint, deterministic serialization, all nine controlled invalid cases,
and exact projection bytes without changing the tree. The root canonical
contract operation invokes the same internal suite.

## Fail-closed invariants

In addition to JSON Schema, validation rejects duplicate helper IDs or names,
ambiguous public names within a binding, incomplete binding coverage,
unsupported target profiles or constraints, unresolved repository or JSON
Pointer references, missing accepted/rejected examples, missing evidence,
duplicate example or variant identities, cyclic derivations, multiple
derivations for one output, stale fingerprints, and any mismatch with the
ratified helper, variant, binding, standards, migration, target, or edge-case
audit denominator.

[`1.0/registry.json`](1.0/registry.json) is the positive contract instance.
The controlled fixtures under [`1.0/fixtures/invalid/`](1.0/fixtures/invalid/)
prove rejection of every required negative class and declare the exact rule
that must fail.
