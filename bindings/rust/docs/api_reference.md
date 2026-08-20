# Rust facade reference

## Compilation

-   `compile(&CompileRequest, Option<&TargetProfile>)` executes the sole
    canonical compiler facade.
-   `check` is an ergonomic alias over the exact request. It does not infer a
    target or change requested outputs.
-   `compile_with_evidence` returns the canonical result plus explanation
    evidence from the same stage execution.

Canonical boundary failures use `KernelCompileError`. A semantically invalid
program normally remains a completed `CompileResult` whose outcome is
`failed`; it is not converted into a host boundary error.

## Contract modules

-   `contract` exposes compile request/result and analysis contracts.
-   `diagnostics` exposes structured canonical diagnostics.
-   `semantic` exposes canonical Semantic IR values.
-   `source` exposes identity, provenance, and UTF-8 byte-coordinate values.
-   `target` exposes exact profiles, portability evidence, and artifacts.
-   `simply` exposes the canonical Simply 1.0/1.1 builder and replay surface.
-   `stdlib` exposes registered canonical standard-helper builders.

Common request, result, target, diagnostic, and Simply types are also
re-exported at the crate root. The historical binding-owned `core` and
`emitters` modules are intentionally removed; callers should not depend on
compiler-stage representations.

## Target behavior

A target-aware request succeeds only with the exact supplied `TargetProfile`
whose identity, version, and fingerprint match the request. No filesystem,
installed regex engine, platform, or ambient package default selects a target.

## Standard-library guarantees

`stdlib::email`, `url`, `uuid`, `ip`, and `date_time` use the one canonical
registry implementation. Their current guarantee is `lexical_shape`; values
may intentionally be semantically invalid. The Rust facade does not strengthen
that promise or substitute regex-shape validation for canonical semantics.
