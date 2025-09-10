# STRling Testing Strategy

This document outlines the testing philosophy, development workflow, and directory structure for the STRling monorepo. Our approach is designed to ensure that every feature is purposeful, robust, and fully documented from its inception.

---

## Testing Philosophy

STRling uses a spec-driven, test-driven feature development workflow: **specifications → tests → features**.

This methodology guarantees that every feature is:

-   **Purposeful**: A feature only exists because it was first defined in a formal specification.
-   **Test-Backed**: A feature is not considered "done" until it passes a comprehensive, pre-defined suite of tests.
-   **Fully Documented**: The specification and test design documents serve as living documentation created at the very beginning of the development lifecycle.

---

## Development & Testing Workflow

Every new feature or bug fix follows this structured, procedural workflow to ensure quality and consistency.

1.  **Specification (`spec/`)**
    The process begins by defining the feature's syntax in the EBNF grammar (`spec/grammar/dsl.ebnf`) and its behavior in the semantics document (`spec/grammar/semantics.md`).

2.  **Test Design (`tests/_design/`)**
    Before any implementation code is written, a formal **Test Charter** (a markdown file) is created in the top-level `tests/_design/` directory. This document outlines the feature's scope, enumerates test cases, and defines the "definition of done" for the test suite.

3.  **Test Implementation**
    The Test Charter is then translated into an executable test file within the relevant binding's test directory (e.g., `bindings/python/tests/` or `bindings/javascript/__tests__/`). Initially, these tests are expected to fail.

4.  **Feature Implementation (`core/`, `bindings/`, etc.)**
    With a clear specification and a failing test suite, the production code is then written. The goal is to write the simplest, cleanest code required to make the tests pass.

5.  **Verification & Refinement**
    Once the tests pass, quality gates such as **code coverage** and **mutation testing** are run to ensure the tests are thorough and effective. The feature code is then refactored for clarity and performance before being merged.

---

## Testing Directory Structure

STRling uses a hybrid testing structure to separate global, binding-agnostic tests from local, binding-specific tests.

### Global Test Directory (`tests/`)

This top-level directory is for tests and documents that apply to the **entire project**, not just a single language binding.

-   **`tests/_design/`**: Contains the markdown **Test Charters**. These are the human-readable design documents that guide the implementation of all test files.
-   **`tests/conformance/`**: Contains the conformance suite. Its purpose is to run a single STRling pattern against **multiple backend engines** (PCRE2, ECMAScript, etc.) and assert that the matching behavior is identical across all of them.

### Binding-Specific Test Directories

Each language binding contains its own `tests/` directory for tests that validate its specific implementation.

-   **Python (`bindings/python/tests/`)**:
    ```
    bindings/python/
    └── tests/
        ├── unit/
        └── e2e/
    ```
-   **JavaScript (`bindings/javascript/__tests__/`)**:
    ```
    bindings/javascript/
    └── __tests__/  <-- Jest convention
        ├── unit/
        └── e2e/
    ```
