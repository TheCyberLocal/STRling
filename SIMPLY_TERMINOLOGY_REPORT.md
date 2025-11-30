# Simply API Terminology Report

This report documents the terminology coherence audit across all 17 language bindings. The goal is **Strict Lexical Parity** with the Gold Standard Vocabulary.

## The "STRling Dictionary" (Gold Standard)

| Concept           | **Gold Standard Keyword** | **Forbidden Synonyms**                |
| :---------------- | :------------------------ | :------------------------------------ |
| **Concatenation** | `merge`                   | `sequence`, `concat`, `chain`, `then` |
| **Zero-or-One**   | `may`                     | `optional`, `opt`, `maybe`            |
| **Character Set** | `anyOf` (or `any_of`)     | `inChars`, `oneOf`, `class`, `set`    |
| **Grouping**      | `capture`                 | `group`, `asCapture`, `named`         |
| **Anchors**       | `start`, `end`            | `begin`, `finish`, `lineStart`        |

## Audit Results

| Binding        | Status | Merge vs Sequence | May vs Optional | AnyOf vs InChars | Remediation                                   |
| :------------- | :----: | :---------------- | :-------------- | :--------------- | :-------------------------------------------- |
| **C**          |   ❌   | `sl_seq`          | `sl_optional`   | `sl_any_of`      | Alias `sl_merge`, `sl_may`                    |
| **C++**        |   ❌   | `sequence`        | `optional`      | `any_of`         | Rename `sequence`->`merge`, `optional`->`may` |
| **C#**         |   ❌   | `Sequence`        | `Optional`      | `AnyOf`          | Rename `Sequence`->`Merge`, `Optional`->`May` |
| **Dart**       |   ⚠️   | `merge`           | `optional`      | `inChars`        | Rename `optional`->`may`, `inChars`->`anyOf`  |
| **F#**         |   ❌   | _(Missing)_       | _(Missing)_     | _(Missing)_      | Implement Simply API                          |
| **Go**         |   ✅   | `Merge`           | `May`           | `AnyOf`          | None                                          |
| **Java**       |   ✅   | `merge`           | `may`           | `anyOf`          | None                                          |
| **Kotlin**     |   ✅   | `merge`           | `may`           | `anyOf`          | None                                          |
| **Lua**        |   ❌   | _(Missing)_       | _(Missing)_     | _(Missing)_      | Implement Simply API                          |
| **Perl**       |   ✅   | `merge`           | `may`           | `any_of`         | None                                          |
| **PHP**        |   ⚠️   | `merge`           | `may`           | `inChars`        | Rename `inChars`->`anyOf`                     |
| **Python**     |   ✅   | `merge`           | `may`           | `any_of`         | None                                          |
| **R**          |   ✅   | `sl_merge`        | `sl_may`        | `sl_any_of`      | None                                          |
| **Ruby**       |   ❌   | _(Missing)_       | _(Missing)_     | _(Missing)_      | Implement Simply API                          |
| **Rust**       |   ✅   | `merge`           | `may`           | `any_of`         | None                                          |
| **Swift**      |   ✅   | `merge`           | `may`           | `anyOf`          | None                                          |
| **TypeScript** |   ✅   | `merge`           | `may`           | `anyOf`          | None                                          |

## Legend

-   ✅ **Pass**: Uses `merge`, `may`, `anyOf` (or idiomatic casing/prefix).
-   ❌ **Fail**: Uses `sequence`, `optional`, `inChars` or API is missing.
-   ⚠️ **Partial**: Mixed usage (e.g., uses `merge` but `optional`).
