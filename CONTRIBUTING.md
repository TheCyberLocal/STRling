# Contributing to STRling

Welcome to the STRling project! We are building the **Universal Regular Expression Compiler**, a polyglot engine that ensures regex behavior is readable, maintainable, and identical across 17+ programming languages.

This guide details the strict architectural standards required to maintain parity across such a diverse ecosystem.

## 🏗️ Architecture Overview

STRling is not a simple wrapper library. It is a **Compiler** that follows a strict pipeline:

1.  **Parse (`DSL -> AST`)**: The human-readable STRling syntax is parsed into an Abstract Syntax Tree.
2.  **Compile (`AST -> IR`)**: The AST is transformed into a target-agnostic **Intermediate Representation (IR)**. Optimizations (like literal merging) happen here.
3.  **Emit (`IR -> Regex`)**: The IR is emitted as a native regex string for the target engine (PCRE2, Python `re`, JS `RegExp`, etc.).

### The "Single Source of Truth" (SSOT)

To prevent logic drift, we enforce a **Golden Master** workflow:

-   **Logic SSOT:** The **TypeScript Binding** (`bindings/typescript`) is the reference implementation. It generates the **Shared Spec Suite** (`tests/spec/*.json`).
-   **Verification:** All other 16 bindings (Python, Rust, C, etc.) are consumers. They **must** execute the Shared Spec Suite to be considered passing.
-   **Versioning SSOT:** The **Python Binding** (`bindings/python/pyproject.toml`) holds the master version number.

---

## 📂 Directory Structure

-   `bindings/`: Source code for all language implementations.
    -   `typescript/`: **The Golden Master.** Contains the source parser and spec generator.
    -   `python/`: **The Release Master.** Contains the versioning source of truth.
    -   `[lang]/`: "Thin" bindings for other languages (Rust, Go, Java, etc.).
-   `spec/`: Documentation for the grammar and semantics.
-   `tests/spec/`: **The Conformance Suite.** Hundreds of JSON files defining Inputs (AST) and Expected Outputs (IR).
-   `tooling/`: Maintenance scripts (audits, version syncing, release helpers).

---

## 💻 Development Workflow

### 1. Modifying Core Logic (The Grammar)

If you want to add a new feature (e.g., a new Quantifier syntax), you must implement it in **TypeScript** first.

1.  Modify `bindings/typescript/src/STRling/core/`.
2.  Add a test case in `bindings/typescript/__tests__/conformance.test.ts` (or legacy unit tests).
3.  Run the generator to update the Shared Specs:
    ```bash
    cd bindings/typescript
    npm run build:specs
    ```
4.  Verify the new JSON files appear in `tests/spec/`.

### 2. Updating a Binding

If you are working on a specific language binding (e.g., Rust), your goal is **Compliance**.

1.  **Do not** write manual unit tests for core logic (e.g., `assert(compile("literal") == "literal")`).
2.  **Do** implement a Conformance Runner that loads `../../tests/spec/*.json`.
3.  **Hydrate:** Parse the JSON `input_ast` into your language's native AST structures.
4.  **Compile:** Transform your AST to IR.
5.  **Assert:** Check that your generated IR matches `expected_ir` from the JSON.

### 3. Running Tests

We support a massive matrix of languages. Here is the cheat sheet for running tests in each binding:

| Language       | Command                                                                                   |
| :------------- | :---------------------------------------------------------------------------------------- |
| **C**          | `cd bindings/c && make tests`                                                             |
| **C++**        | `cd bindings/cpp && cmake -S . -B build && cmake --build build && ctest --test-dir build` |
| **C#**         | `cd bindings/csharp && dotnet test`                                                       |
| **Dart**       | `cd bindings/dart && dart test`                                                           |
| **Go**         | `cd bindings/go && go test ./...`                                                         |
| **Java**       | `cd bindings/java && mvn test`                                                            |
| **JavaScript** | (See TypeScript)                                                                          |
| **Kotlin**     | `cd bindings/kotlin && ./gradlew test`                                                    |
| **Lua**        | `cd bindings/lua && busted`                                                               |
| **PHP**        | `cd bindings/php && vendor/bin/phpunit`                                                   |
| **Python**     | `cd bindings/python && pytest`                                                            |
| **Perl**       | `cd bindings/perl && prove -l t`                                                          |
| **R**          | `cd bindings/r && Rscript -e "testthat::test_dir('tests/testthat')"`                      |
| **Ruby**       | `cd bindings/ruby && bundle exec rake test`                                               |
| **Rust**       | `cd bindings/rust && cargo test`                                                          |
| **Swift**      | `cd bindings/swift && swift test`                                                         |
| **TypeScript** | `cd bindings/typescript && npm test`                                                      |

---

## 📦 Release Process

**⚠️ WARNING:** Never manually edit version numbers in `package.json`, `Cargo.toml`, etc. The CI pipeline handles this.

To cut a new release:

1.  **Update Source:** Edit `bindings/python/pyproject.toml` to set the new version (e.g., `3.0.0`).
2.  **Propagate:** Run the synchronization tool to update all 17 bindings:
    ```bash
    python3 tooling/sync_versions.py --write
    ```
3.  **Commit:** Commit the changes with a message like `chore: bump version to 3.0.0`.
4.  **Tag & Push:**
    ```bash
    git tag v3.0.0
    git push --tags
    ```

The GitHub Actions pipeline will automatically:

1.  Verify all tests pass.
2.  Check idempotency (skip if version exists on registry).
3.  Publish to NPM, PyPI, Crates.io, NuGet, RubyGems, Pub.dev, etc.

---

## 📏 Coding Standards

-   **Instructional Error Handling:** Errors should not just say "Invalid Syntax". They should say _"Invalid Quantifier: Range {5,2} is invalid because min (5) cannot be greater than max (2)."_
-   **Zero Dependencies:** The core compiler logic in any binding should rely on the standard library whenever possible.
-   **Immutability:** AST and IR nodes should be immutable data structures.

Thank you for helping us build the universal regex standard!
