# Operation Omnibus (Redux) — Global Test Audit

**Date:** November 30, 2025
**Executor:** GitHub Copilot (Gemini 3 Pro)
**Objective:** Validate ecosystem integrity using the `./strling` CLI test runner.

## Executive Summary

This audit executed the standardized test suite across all 17 language bindings.

-   **Total Bindings:** 17
-   **Passing:** 8
-   **Failing:** 9

## Detailed Results

### 1. The Reference Tier (Critical)

| Binding        | Status      | Notes                                     |
| :------------- | :---------- | :---------------------------------------- |
| **TypeScript** | ✅ **PASS** | Gold Master. 17 suites, 890 tests passed. |
| **Python**     | ✅ **PASS** | Version Master. 714 tests passed.         |

### 2. The Systems Tier

| Binding   | Status      | Failure Analysis                                                                                                   |
| :-------- | :---------- | :----------------------------------------------------------------------------------------------------------------- |
| **C**     | ❌ **FAIL** | `test_generated_ast_compile` failed. Missing file: `../tooling/js_to_json_ast/out/js_test_pattern_1.json`.         |
| **C++**   | ❌ **FAIL** | 15 tests failed (73% pass rate). Failures in `ErrorsGrouping`, `ErrorsBackref`, `ErrorsEscape`, `ErrorsCharClass`. |
| **Rust**  | ❌ **FAIL** | Compilation error in `examples/demo.rs`: `use of undeclared crate or module strling`.                              |
| **Swift** | ❌ **FAIL** | Runtime Crash (Signal 4) in `LiteralsAndEscapesTests.testCategoryD_InteractionCases`.                              |
| **Go**    | ✅ **PASS** | All tests passed (cached).                                                                                         |

### 3. The JVM & .NET Tier

| Binding    | Status      | Failure Analysis                                                                                               |
| :--------- | :---------- | :------------------------------------------------------------------------------------------------------------- |
| **Java**   | ❌ **FAIL** | Build Failure: `Fatal error compiling: error: invalid target release: 17`. Environment likely using older JDK. |
| **Kotlin** | ❌ **FAIL** | Build Failure: `Gradle requires JVM 17 or later to run. Your build is currently configured to use JVM 11.`     |
| **C#**     | ✅ **PASS** | All tests passed.                                                                                              |
| **F#**     | ✅ **PASS** | All tests passed.                                                                                              |

### 4. The Scripting & Web Tier

| Binding  | Status      | Failure Analysis                                                                        |
| :------- | :---------- | :-------------------------------------------------------------------------------------- |
| **Ruby** | ✅ **PASS** | All tests passed.                                                                       |
| **PHP**  | ✅ **PASS** | All tests passed.                                                                       |
| **Perl** | ❌ **FAIL** | `t/us_phone.t` failed. Generated regex mismatch (e.g., `[\d]{3}` vs `\d{3}`).           |
| **Lua**  | ❌ **FAIL** | Runtime Error: `module 'cjson' not found`.                                              |
| **Dart** | ✅ **PASS** | All tests passed.                                                                       |
| **R**    | ❌ **FAIL** | 3 Failures. `could not find function "sl_merge"`, `could not find function "sl_start"`. |

## Recommendations

1.  **Environment Upgrade:** Update CI/Local environment to support Java 17+ for Java and Kotlin bindings.
2.  **Dependency Fix:** Install `lua-cjson` for Lua binding.
3.  **Code Fixes:**
    -   **Rust:** Fix `examples/demo.rs` imports.
    -   **C:** Ensure test fixtures are generated/present.
    -   **C++:** Investigate error handling logic discrepancies.
    -   **Swift:** Debug crash in `LiteralsAndEscapesTests`.
    -   **Perl:** Align expected regex output with generator.
    -   **R:** Fix function exports/imports.
