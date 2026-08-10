# STRling Product Architecture

## Status and authority

This document is a ratified product architecture decision. It defines STRling's
durable identity and conceptual responsibility boundaries. It does not define
language constructs, data-contract fields, module layout, or implementation
language. The precedence rules in [`authority.md`](authority.md) remain
controlling.

## Product definition

> **STRling is a portable regex-intent compiler: developers express what a
> pattern means once, and STRling produces verified, explainable,
> target-specific regular-expression artifacts while surfacing portability and
> safety constraints before runtime.**

STRling is a compiler platform. Its flagship abstraction is semantic pattern
intent, available through multiple authoring surfaces and compiled through one
canonical semantic authority. Its product value comes from semantic authoring,
portability analysis, safety analysis, explanation, and deliberate
target-sensitive lowering.

STRling is not fundamentally:

-   a collection of independently implemented regex libraries;
-   cosmetic syntax over raw regular expressions;
-   a PCRE2 wrapper;
-   a TypeScript-centric builder library; or
-   an editor-only tool.

Bindings, regex syntax, PCRE2 support, fluent APIs, and editor integrations are
important capabilities, but none alone defines the product.

## Permanent conceptual hierarchy

```text
AUTHORING SURFACES
    Semantic STRling DSL
    Simply APIs
    Regex frontend / importer
            |
            v
    Canonical semantic representation
            |
            v
    Semantic analysis
    Portability planning
            |
            v
    Target lowering
            |
            v
    Target-specific emitters
            |
            v
    Versioned target artifacts

HOST-LANGUAGE ADAPTERS
    expose the same compiler capability
    without reimplementing semantics

TOOLING
    CLI / LSP / editor integrations
    consume the same canonical compiler
```

This direction assigns responsibility; it does not select process boundaries,
protocol fields, storage formats, or source-tree layout. Those decisions require
later contract-first architecture work.

## Authoring surfaces

### Semantic STRling

Semantic STRling is the flagship textual authoring surface. It will express
pattern intent against the canonical semantic model. Its syntax and exact
construct set have not yet been designed or ratified.

### Simply

Simply is a first-class semantic authoring surface exposed idiomatically in
supported host languages. Simply expressions lower into the same canonical
semantic representation as other authoring surfaces. A Simply adapter does not
own an independent compiler and does not implement meaning by directly emitting
a target regex.

Existing Simply APIs remain compatibility obligations until a contained,
versioned migration explicitly changes them. This architecture does not redesign
those APIs.

### Regex frontend and importer

The existing regex-shaped `.strl` syntax is the **regex frontend**: a
low-level, regex-compatible source dialect retained for compatibility,
migration, and import workflows. It is useful input evidence and capability,
but it is not the permanent semantic ceiling of STRling and is not sufficient
proof that the future Semantic STRling DSL has already been designed.

“Regex importer” describes the responsibility of accepting regex-shaped input;
“regex frontend” names the current source-facing capability. A future importer
may normalize additional external regex dialects, but that scope is not decided
here.

Raw regex is not forbidden internally. Regex import and target regex output are
necessary. The architectural restriction is that raw target syntax must not
become STRling's semantic public abstraction or bypass deliberate analysis and
target planning.

## Host ecosystems and target engines

A **host language** answers: “From which programming ecosystem can I invoke
STRling?” Rust, TypeScript, Python, Java, and C# are examples.

A **target engine** answers: “For which regex/runtime semantics should STRling
compile?” PCRE2, ECMAScript, and Python `re` are examples.

The number of host-language bindings is never a count of supported regex
targets. A binding or adapter exposes the canonical compiler to a host
ecosystem; a target profile describes version-sensitive target semantics and
capabilities. Engine support must not be modeled as timeless booleans.

## Semantic and implementation authority

The normative specification defines STRling behavior. Simply, textual
frontends, host adapters, target emitters, and the reference implementation
must conform to it.

The future canonical compiler may be implemented in Rust, but Rust would be the
reference implementation rather than the specification. TypeScript behavior
remains compatibility evidence where relevant, not semantic authority.
Host-language adapters must converge on the canonical compiler instead of
remaining independent parser/compiler/emitter implementations.

## Preservation boundary

This decision changes authority and future responsibility, not current runtime
behavior. The certified preservation matrix continues to govern public surfaces,
accepted compatibility evidence, diagnostics, selected tooling outcomes,
standard-library capability, and target-safety inputs. Known non-contractual
defects do not become product requirements, and transitional implementations
remain in place until separately authorized migration work replaces them.
