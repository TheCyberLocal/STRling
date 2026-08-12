# STRling Architecture

[← Back to Developer Hub](index.md)

This guide explains the ratified product and compiler architecture in
contributor-facing language. The controlling decisions are
[`governance/product.md`](../governance/product.md) and
[`governance/architecture.md`](../governance/architecture.md).

## Product center

STRling is a portable regex-intent compiler. Its flagship abstraction is
semantic pattern intent, not a particular host binding, regex notation, target
engine, or editor.

Three authoring surface families converge on one semantic compiler path:

-   **Semantic STRling DSL:** the future flagship textual semantic language;
-   **Simply APIs:** idiomatic host-language semantic builders; and
-   **regex frontend/importer:** the existing regex-shaped compatibility source
    dialect.

The current `.strl` grammar belongs to the third family unless later ratified
specification work deliberately extends or reclassifies it.

## Responsibility flow

```text
authoring frontend
    -> canonical semantic representation
    -> semantic analysis
    -> semantic requirement extraction
    -> factual capability evaluation against a versioned target profile
    -> portability planning against a versioned target profile
    -> target lowering
    -> target-specific emitter
    -> versioned TargetArtifact
```

This is a responsibility model, not a module diagram. The checked-in
prepublication source, Semantic IR, compile request/result, diagnostic,
analysis, profile, portability, and artifact contracts live under
`spec/contracts/1.0`. The canonical Rust kernel currently implements the path
through portability planning; target lowering and emission remain deliberately
absent.

**Semantic analysis** owns target-independent validity, diagnostics, safety
findings, and explanation.

**Semantic requirement extraction** describes which target capabilities the
normalized program demands. **Capability evaluation** compares those
requirements with one exact immutable profile and reports only factual native
support, explicit unavailability, constraint violations, or unknown data. Its
[contract](capability-evaluation.md) preserves missing profile information as
unknown and does not choose rewrites.

**Portability planning** consumes that exact evaluation and chooses native
support, a proven semantics-preserving rewrite plan, or an unsupported result.
Its [canonical contract](portability-planning.md) preserves incomplete evidence
as unresolved outside the final portability vocabulary. Engine capabilities
are version/profile-sensitive, and planning neither applies rewrites nor emits
target syntax.

**Lowering** selects deliberate target-specific forms. **Emitters**
deterministically serialize those plans; they do not invent semantic or
portability policy.

## Simply

Simply is first-class semantic authoring. APIs may remain idiomatic in Rust,
TypeScript, Python, Java, C#, and other hosts, but equivalent operations must
lower to the same canonical semantic representation.

Existing public helpers, including direct target convenience methods, remain
compatibility obligations. They are not proof that Simply's permanent
implementation should bypass the canonical compiler, and this architecture does
not redesign them.

## Host adapters and targets

A host adapter exposes compiler capability in a programming ecosystem. A target
profile describes the regex/runtime semantics to compile for. These are
orthogonal:

| Host adapters                                            | Target engines                                               |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| Rust, TypeScript, Python, Java, C#                       | PCRE2, ECMAScript, Python `re`                               |
| Own idiomatic APIs, conversion, packaging, error mapping | Own version-sensitive runtime facts and target serialization |
| Must not reimplement semantics                           | Must not redefine STRling semantic intent                    |

The Rust canonical core is the prepublication reference implementation. It does
not become the specification. TypeScript and Python behavior remain
compatibility evidence, not semantic authority.

## Tooling

The CLI, LSP, editor integrations, documentation tools, and conformance tools
consume the same canonical compiler interface. They may own transport,
presentation, caching, and source projection, but not shadow semantic
implementations.

The root `./strling compile` command is a deterministic JSON transport for
`CompileRequest` and `CompileResult`. It delegates to the Rust kernel and owns
only standard-input/output, argument, target-profile file, and exit-status
handling. The kernel selects source syntax only from the explicit
`SourceDocument.frontend` identity; it currently dispatches
`strling.regex-compat@1.0.0` to the one governed compatibility parser. Neither
the shell nor the Rust transport binary parses regex syntax, selects a default
frontend or target, lowers targets, or emits artifacts.

## Current versus target state

Current per-binding parsers, compilers, validators, ASTs, IRs, diagnostics, and
emitters are transitional. So are TypeScript-derived shared fixtures, shallow
representation models, incomplete target capability tables, and direct
LSP-to-binding semantic dependencies.

These paths remain available until their replacements exist and public behavior
is preserved under the certified migration obligations. Their presence does not
change the permanent dependency direction.

## Specification relationship

The [`engineering authority hierarchy`](../governance/authority.md) places a
ratified versioned specification and expressly normative contracts above the
reference implementation, tests, compatibility evidence, and explanatory
documentation.

There is no ratified Semantic STRling flagship language specification version
yet. [`1.0-draft.1`](../spec/drafts/1.0/README.md) remains a non-normative scope
scaffold. The frozen `strling.regex-compat@1.0.0` grammar is a governed
compatibility/import frontend contract and must not be presented as the
flagship authoring language.
