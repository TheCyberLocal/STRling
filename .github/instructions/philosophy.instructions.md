# STRling Philosophy — Semantic Intent Over Target Syntax

> **Scope:** Product-facing authoring principles, Simply naming, composition,
> and deliberate raw-regex boundaries.

## Prime directive

STRling lets developers express what a pattern means and receive portable,
explainable, target-specific artifacts. User-facing semantic surfaces should be
readable, composable, and discoverable without requiring target-regex expertise.

Semantic intent—not a fluent API shape, host language, or target syntax—is the
flagship abstraction.

## Authoring surfaces

-   **Semantic STRling** will be the flagship textual semantic language.
-   **Simply** is a first-class idiomatic semantic API family.
-   **Regex frontend/importer** accepts the existing regex-shaped compatibility
    dialect and future deliberately supported import dialects.

Raw regex is therefore not globally forbidden. It is necessary as importer
input and target output. It must not become the semantic abstraction of Simply
or Semantic STRling, and target fragments must not bypass analysis and
portability planning.

## Simply design principles

-   Names describe intent rather than target tokens: prefer
    `lookBehind(...)` over `(?<=...)`-shaped APIs.
-   Composition uses semantic pattern values rather than accidental string
    concatenation.
-   Equivalent operations in different hosts lower to the same canonical
    semantic representation.
-   Type systems and IDE discovery should prevent or explain invalid states
    where practical.
-   Builder operations do not directly emit target regex as their semantic
    implementation.
-   Explicit terminal compilation requests select a target profile and route
    through the canonical compiler.

Current Simply public APIs, including raw/unsafe escape hatches and target
convenience methods, are compatibility obligations. This philosophy guides
future contained design; it does not silently remove or redesign them.

## Explanation principles

Lead with semantic meaning, portability, and safety. Target regex may be shown as
a resulting artifact or low-level import form, but it should be clearly labeled
with its target engine/profile.

When a semantic explanation is available, diagnostics should not require users
to decode native engine traces.

## Review questions

Before accepting an authoring API change, ask:

1. Can a developer understand the intent without knowing target syntax?
2. Does the operation lower through the canonical semantic path?
3. Are portability and unsupported outcomes explicit?
4. Is any raw syntax clearly scoped as import/unsafe/target-specific?
5. Does the change preserve existing public obligations or declare a versioned
   migration?
