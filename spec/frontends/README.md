# Frontend contracts

STRling frontends own construction or syntax only. Every accepted frontend
value lowers into the same canonical Semantic IR before analysis, portability
planning, target lowering, or emission. A frontend contract cannot define
canonical semantics, select a target implicitly, execute a runtime, or promote
historical implementation behavior into specification authority.

Current versioned frontend contracts are:

-   [`semantic/1.0/`](semantic/1.0/) for the flagship Semantic STRling textual
    language and deterministic Semantic IR mapping;
-   [`legacy-regex/1.0/`](legacy-regex/1.0/) for the syntax-only
    regex-compatible import dialect; and
-   [`simply/1.0/`](simply/1.0/) for host-neutral semantic builder construction.

Each directory owns its schemas, authored evidence, fingerprint manifest, and
certification rules. Host APIs may remain idiomatic, but their serialized
meaning must conform to the applicable frontend contract and the canonical
compiler contracts under [`../contracts/`](../contracts/).

The Semantic STRling contract is specification-first. Its parser and formatter
remain later implementation work and cannot become specification authority.
