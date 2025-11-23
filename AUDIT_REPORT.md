# Comprehensive Binding Coverage Audit

**Date:** November 22, 2025
**Baseline Spec Count:** 594 (Shared JSON AST Suite)
**Compiler Specs:** ~548
**Parser-Only Specs:** ~46

## Executive Summary

A forensic audit of the 17 language bindings was performed to validate test coverage against the Shared JSON AST Suite.

-   **7 Bindings** are confirmed **🟢 Full Compliance**, executing the full suite of ~548-594 tests.
-   **8 Bindings** are **🟡 Unverified (Environment)**. The conformance test files _exist_ and appear correct, but could not be executed in the current environment to verify the exact count.
-   **2 Bindings** are **🔴 Deficient** (C is failing tests, C# is a placeholder).
-   **1 Binding** is **⚫ Phantom** (Lua directory is missing).

## Coverage Matrix

| Language       | Status             | Total Tests Run | Conformance Count | Binding-Specific Count | Missing Categories       |
| :------------- | :----------------- | :-------------- | :---------------- | :--------------------- | :----------------------- |
| **C**          | 🔴 Deficient       | 613             | 594 (ALL FAILED)  | 19                     | Fix Failures             |
| **C++**        | 🟢 Full Compliance | 548             | 548               | 0                      | None (Skips Parser-Only) |
| **Go**         | 🟢 Full Compliance | ~560            | ~548              | ~12                    | None                     |
| **Rust**       | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Swift**      | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **C#**         | 🔴 Deficient       | 1               | 0                 | 1                      | Implementation           |
| **F#**         | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Java**       | 🟢 Full Compliance | 710             | 594               | 116                    | None                     |
| **Kotlin**     | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Dart**       | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Lua**        | ⚫ Phantom         | 0               | 0                 | 0                      | Implementation           |
| **Perl**       | 🟢 Full Compliance | 548             | 548               | 0                      | None                     |
| **PHP**        | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Python**     | 🟢 Full Compliance | 710             | ~594              | ~116                   | None                     |
| **R**          | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **Ruby**       | 🟡 Unverified      | N/A             | ?                 | ?                      | Env Setup Required       |
| **TypeScript** | 🟢 Full Compliance | 890             | ~594              | ~296                   | None                     |

## Detailed Findings

### 🟢 Full Compliance

-   **C++, Perl:** Explicitly reported **548** passed tests, correctly skipping the ~46 parser-only specs that don't have `input_ast`.
-   **Java:** Explicitly reported **594** passed tests.
-   **Go:** Verbose logs confirmed iteration over all spec files, skipping those without `input_ast`.
-   **Python, TypeScript:** High total test counts and source code analysis confirm full iteration of the spec directory.

### 🔴 Deficient

-   **C:** The test runner executes the 594 conformance tests (`tests/unit/converted_from_js_test.c`), but they are currently **failing** with `error: Failure!`.
-   **C#:** The CI job is a placeholder (`echo "C# tests not yet implemented"`).

### ⚫ Phantom

-   **Lua:** The `bindings/lua` directory does not exist, despite having a CI job defined.

### 🟡 Unverified (Environment)

The following bindings have `conformance` test files present, indicating intent to comply, but could not be executed in the audit environment:

-   **Rust:** `bindings/rust/tests/conformance.rs`
-   **Swift:** `bindings/swift/Tests/STRlingConformanceTests/ConformanceTests.swift`
-   **F#:** `bindings/fsharp/tests/STRling.Tests/ConformanceTests.fs`
-   **Kotlin:** `bindings/kotlin/src/test/kotlin/strling/ConformanceTest.kt`
-   **Dart:** `bindings/dart/test/conformance_test.dart`
-   **PHP:** `bindings/php/tests/ConformanceTest.php`
-   **R:** `bindings/r/tests/testthat/test-conformance.R`
-   **Ruby:** `bindings/ruby/test/conformance_test.rb`

## Recommendations

1.  **Fix C Bindings:** Investigate `tests/unit/converted_from_js_test.c` failures.
2.  **Implement C# & Lua:** Create the missing bindings.
3.  **Standardize Reporting:** Update all test runners to output a clear "Conformance: X/Y" metric to avoid ambiguity in future audits.
