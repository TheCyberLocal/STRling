# Test Design — `<type>/test_<module>.py`

## Purpose

Explain in 1–3 sentences **why this test suite exists**.
Example: Validate correct handling of flags and free-spacing in the DSL, ensuring both parsing and emission conform to expected semantics.

## Description

Provide a **high-level overview** of what’s being tested.

-   Summarize the feature/module.
-   Describe its role in the DSL/compiler.
-   Clarify what kinds of behaviors or invariants are expected.

## Scope

Define **what is in scope** and **what is out of scope** for this test file.

-   _In scope:_ DSL syntax for flags, artifact structure, emitter behavior.
-   _Out of scope:_ Backend integration, language-specific bindings (covered elsewhere).

## Categories of Tests

Organize the tests into **structured categories**. Each should contain an explanation of what it covers (not actual test code).

-   **Category A — Positive Cases**
    Describe standard inputs and the expected correct outputs.

-   **Category B — Negative Cases**
    Describe invalid syntax, malformed DSL, or unsupported constructs that should raise errors.

-   **Category C — Edge Cases**
    Describe boundary conditions, minimal/maximal inputs, or ambiguous grammar constructs.

-   **Category D — Cross-Semantics / Interaction**
    Describe how this module interacts with other features (e.g., flags with quantifiers).

-   **Category E — Extension Features**
    Describe any additional features or behaviors that are specific to certain contexts or use cases.

## Completion Criteria

Checklist for knowing when this test suite is _exhaustively written but not redundant_.

-   All grammar rules related to this module have at least one test.
-   Both valid and invalid paths are covered.
-   Emission and schema validation are exercised.
-   No overlapping tests unless justified (parametrized instead).
