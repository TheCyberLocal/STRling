# STRling Architecture — Authority and Responsibility Boundaries

> **Scope:** Compiler/specification architecture, authoring surfaces, target
> planning, emitters, adapters, and structural change workflow.

## Controlling model

```text
Semantic STRling / Simply / regex frontend
    -> canonical semantic representation
    -> semantic analysis
    -> portability planning against a versioned target profile
    -> target lowering
    -> target-specific emitter
    -> versioned TargetArtifact
```

Host-language adapters expose this capability without reimplementing semantics.
CLI, LSP, and editor tooling consume the same canonical compiler.

This is conceptual responsibility, not current module layout or a ratified
source/IR schema.

## Authority

The ratified specification and expressly normative versioned contracts define
behavior. Delegated specification-authored conformance cases may define exact
examples within their delegated scope. The reference implementation implements
those sources and cannot silently extend them.

TypeScript is not normative. Current TypeScript output, generated JSON fixtures,
and duplicated binding agreement are compatibility evidence.

There is no ratified Semantic STRling version yet. The current grammar and
semantics documents describe the regex frontend as transitional compatibility
material. `1.0-draft.1` is non-normative.

## Authoring boundaries

-   **Semantic STRling:** future flagship textual semantic frontend.
-   **Simply:** first-class idiomatic semantic APIs lowering through the same
    canonical path.
-   **Regex frontend:** existing regex-shaped compatibility/import source
    dialect, not the final semantic DSL.
-   **Target regex:** emitted output, distinct from every source dialect.

Raw regex is permitted for import and target output. It must not become the
semantic public abstraction or bypass analysis and target planning.

## Compiler boundaries

-   Shared normalization, semantic analysis, portability planning, lowering, and
    emission semantics have one canonical implementation.
-   Target profiles are version-sensitive; capabilities are not timeless
    booleans.
-   Emitters serialize deliberate plans and do not invent semantic fallbacks.
-   Current AST, IR, and TargetArtifact structures are not the final canonical
    contracts by implication.
-   A future Rust core may be the reference implementation but never the
    specification.

## Host and target distinction

Rust, TypeScript, Python, Java, and C# are host ecosystems. PCRE2, ECMAScript,
and Python `re` are target engines. A host binding is not a target backend, and
binding count is not target count.

## Transitional repository state

Per-binding parsers, compilers, validators, diagnostics, and emitters remain
active for compatibility. The TypeScript fixture producer and direct
LSP-to-Python semantic path also remain transitional. Do not remove or bypass
them outside contained migration work with behavior-preservation evidence.

## Change workflow

For semantic or canonical-contract work:

1. identify the controlling draft/specification/contract;
2. declare semantic, schema, diagnostic, target, public API, and architecture
   impact;
3. author independent conformance evidence;
4. implement only after reviewable contracts exist;
5. compare with preserved compatibility evidence; and
6. run the root hardgates.

Do not use “implement in TypeScript first” or generated fixture changes as
semantic authorization.

## Operational version management

`bindings/python/pyproject.toml` is the current operational package-version
source for synchronization. Use `python3 tooling/sync_versions.py --write` for
release metadata. This operational role does not version the semantic
specification; see `spec/VERSIONING.md`.
