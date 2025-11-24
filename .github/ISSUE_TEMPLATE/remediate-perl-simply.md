---
name: Remediate: Perl binding — implement "simply" API
about: Create a `simply`-style Perl module and update README/examples
---

Title: Task: Implement simply builder for Perl binding

Goal: Provide a Perl `STRling::Simply` DSL / helper layer so README and examples avoid direct construction of `STRling::Core::Nodes`.

Target Vectors:

-   bindings/perl/README.md
-   bindings/perl/lib/STRling/

Implementation Plan:

1. Add `lib/STRling/Simply.pm` with helper functions / builder patterns.
2. Convert README examples to use `STRling::Simply::capture` and related functions.
3. Add tests under `bindings/perl/t/` demonstrating parity with reference output.

Acceptance Criteria:

-   README and tests use the `STRling::Simply` API and avoid exposing core AST constructors.
