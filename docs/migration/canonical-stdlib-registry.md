# Canonical standard-library registry

## Scope and boundary

P14-T02 converts the ratified Essential-5 audit into one versioned source of
standard-library metadata. It does not change any public helper name,
parameter default, emitted regex, match result, target runtime, or diagnostic.
It also does not implement stronger validators or generate every binding and
documentation surface. Canonical Rust helper semantics remain P14-T03 work;
broad frontend and adapter generation remains P14-T04 work.

The starting baseline is clean commit
`c3d67ac20690a63935699eaa913475fa2126a7c0`, the P14-T01 closure.

## Authority design

The authored source is
[`spec/stdlib/registry/1.0/registry.json`](../../spec/stdlib/registry/1.0/registry.json).
Its versioned schema is closed and rejects unknown fields. A three-node
derivation graph distinguishes the normative registry from two generated,
non-normative compatibility projections:

```text
canonical.registry
├── projection.essential-5  -> spec/stdlib/essential_5.json
└── projection.lsp-registry -> spec/stdlib/registry.json
```

The generator never consumes either output. The generated-artifact registry
enforces deterministic write and non-mutating check commands and classifies
both outputs as `non-normative-projection`.

Helper identity is deliberately independent of host-language spelling. Five
stable IDs own semantic and guarantee metadata, while seventeen binding maps
own language-specific names and implementation/test evidence. This preserves
idiomatic names such as C `sl_ip_v4`, Go `IP`, and Python `date_time` without
creating competing helper identities.

## Migrated contract

The initial `1.0.0` registry contains five helpers and eight behavior variants:

| Helper ID          | Variants                         | Guarantee       | Support tier    |
| ------------------ | -------------------------------- | --------------- | --------------- |
| `stdlib.date_time` | default                          | `lexical_shape` | `compatibility` |
| `stdlib.email`     | default                          | `lexical_shape` | `compatibility` |
| `stdlib.ip`        | IPv4, full IPv6, default/either  | `lexical_shape` | `compatibility` |
| `stdlib.url`       | default                          | `lexical_shape` | `compatibility` |
| `stdlib.uuid`      | generic/default and version four | `lexical_shape` | `compatibility` |

Each entry carries exact parameter and fallback-selector semantics, output
type, regex construction variants, audit guarantees, standards scope,
non-guarantees, lifecycle fields, migration disposition, target profiles,
target constraint IDs, Unicode/text assumptions, diagnostics policy,
documentation metadata, and repository evidence. The forty P14-T01 edge cases
are divided into accepted examples, rejected counterexamples, and explicit
target-dependent examples without changing their classifications or expected
outcomes.

The registry records the current lexical construction identity, including the
historical Email AST where one already exists, but marks canonical-core
implementation as pending. This supplies the identity and validation hooks
T03 needs without pretending that regex compatibility data is already the
future Rust implementation.

## Validation and determinism

`tooling/stdlib_registry.py` is an internal contract library used by the sole
canonical contract operation. It combines JSON Schema with cross-object rules
for helper and name uniqueness, complete binding coverage, repository and JSON
Pointer resolution, target-catalog membership, example/variant correspondence,
acyclic and unambiguous derivations, audit reconciliation, and fingerprint and
serialization stability.

Nine controlled invalid fixtures cover duplicate IDs, duplicate names, invalid
guarantee levels, unresolved evidence, missing examples, missing evidence,
unsupported target constraints, cyclic derivation, and ambiguous derivation
output. Each mutation is materialized twice and must fail for its declared rule.

The current fingerprint is
`sha256:07065e1cb66d3277e4f482df0d9cf91c94be0417e05f1b157f15658ae504a382`.
It covers all registry data except the self-describing fingerprint member.

## Compatibility

The Essential and editor JSON documents preserve helper names, emitted regex
values, shared fixture values, naming metadata, reference wording, snippets,
and completion keywords. Their descriptions now state generated,
non-normative status, and historical `ast_ref` fields point into the canonical
registry rather than treating a generated output as authority. JSON member
ordering is deterministic but carries no behavior.

No helper behavior is strengthened or weakened. Stronger IPv4, date/time,
email, URL, or UUID validation remains a separately named additive future
surface, exactly as required by the P14-T01 compatibility disposition.
