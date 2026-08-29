# Standard-library surface convergence

## Scope

This task derives supported public standard-library views from registry
version `1.0.0` and the sole canonical Rust implementation. It owns the
backward-compatible Simply `1.1.0` helper operation, Python and TypeScript
Preview wrappers, binding-support metadata, Semantic DSL examples, public
reference documentation, portability views, structured frontend evidence, and
the associated public-contract snapshots.

Historical Essential constructors remain compatibility-only surfaces. They
are not relabeled as canonical adapters, and their independent implementations
are not inputs to generated semantics.

## Closed denominator

-   Five registered helpers and eight lexical-shape variants.
-   Seventeen host-binding spelling maps.
-   Two canonical Preview adapters and fifteen compatibility-only bindings.
-   Five governed target profiles and forty variant/profile cells.
-   580 executable runtime applications and five explicitly not-applicable
    Python-bytes applications from checked P14-T03 evidence.
-   Zero semantic validators.

## Verification design

The Simply `1.1.0` contract inherits all fifteen immutable `1.0.0` operations
and adds only `stdlib_helper`. Generated wrappers record a helper identity and
parameter map. Rust convergence tests compare every helper selection with the
direct canonical builder and generated Semantic DSL form after removing only
representation identities and provenance.

The `stdlib-surface-projections` generator must reproduce all fourteen outputs
byte-for-byte. Public snapshot, generated-artifact, governance, architecture,
frontend, adapter, target-portability, structured semantic-authority, and
campaign profile gates complete certification before phase closure.
