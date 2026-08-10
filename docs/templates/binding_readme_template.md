# STRling — {Language} Binding

> Part of the [STRling Project](https://github.com/strling-lang/strling)

STRling is a portable regex-intent compiler. This host-language binding exposes
the shared compiler capability through idiomatic {Language} APIs; it is not a
separate semantic authority or a regex target by itself.

## Installation

{Installation_Command}

## Usage

{Usage_Snippet}

State which authoring surface the example uses:

-   **Simply** for idiomatic semantic construction;
-   **Semantic STRling** only after its source version is ratified; or
-   **regex frontend** for current regex-compatible import/source notation.

If showing emitted regex, label the target engine/profile and present it as a
TargetArtifact result rather than the source abstraction.

## Architecture

```text
Semantic STRling / Simply / regex frontend
    -> canonical semantic compiler
    -> analysis and portability planning
    -> target lowering and emitter
    -> versioned TargetArtifact
```

This binding should ultimately be a thin adapter that owns {Language} types,
conversion, packaging, interoperability, and host-specific error mapping without
reimplementing STRling semantics.

Existing binding-local parsers, compilers, IRs, diagnostics, and emitters are
transitional compatibility implementations until contained migration work
replaces them.

## Host versus target

{Language} is the host ecosystem. PCRE2, ECMAScript, Python `re`, and other
regex runtimes are target engines. Do not imply that every emitted target is
natively executable by {Language}, and do not use host-binding count as target
count.

## Documentation

-   Binding API reference: `{API_Reference_Path}`
-   [`Project Hub`](https://github.com/strling-lang/strling)
-   [`Product Architecture`](https://github.com/strling-lang/strling/blob/main/governance/product.md)
-   [`Specification Hub`](https://github.com/strling-lang/strling/tree/main/spec)
-   [`Canonical Terminology`](https://github.com/strling-lang/strling/blob/main/governance/terminology.md)
