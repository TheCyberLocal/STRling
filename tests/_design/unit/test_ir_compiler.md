# Test Design — `unit/test_ir_compiler.py`

## Purpose

This test suite validates the compiler's two primary responsibilities: the **lowering** of the AST into an Intermediate Representation (IR), and the subsequent **normalization** of that IR. It ensures that every AST construct is correctly translated and that the IR is optimized according to a set of defined rules.

## Description

The compiler (`core/compiler.py`) acts as the "middle-end" of the STRling pipeline. It receives a structured Abstract Syntax Tree (AST) from the parser and transforms it into a simpler, canonical Intermediate Representation (IR) that is ideal for the final emitters. This process involves a direct translation from AST nodes to IR nodes, followed by a normalization pass that flattens nested structures and fuses adjacent literals for efficiency. This test suite verifies the correctness of these tree-to-tree transformations in isolation.

## Scope

-   **In scope:**

    -   The one-to-one mapping (lowering) of every AST node from `nodes.py` to its corresponding IR node in `ir.py`.
    -   The specific transformation rules of the IR normalization pass: flattening nested `IRSeq` and `IRAlt` nodes, and coalescing adjacent `IRLit` nodes.
    -   The structural integrity of the final IR tree after both lowering and normalization.
    -   The correct generation of the `metadata.features_used` list for patterns containing special features (e.g., atomic groups).

-   **Out of scope:**
    -   The correctness of the input AST (this is the parser's responsibility). Tests will construct AST nodes manually.
    -   The final emitted regex string (this is the emitter's responsibility).
    -   The parsing of the source DSL (covered in other unit tests).

## Categories of Tests

### Category A — AST to IR Lowering

These tests verify the direct, pre-normalization translation from an AST node to its IR equivalent by testing the `_lower` method.

-   **Simple Atoms**: Test that `N.Lit`, `N.Dot`, and `N.Anchor` nodes are lowered to their direct `IR.IRLit`, `IR.IRDot`, and `IR.IRAnchor` counterparts.
-   **Character Classes**: Test that an `N.CharClass` with a list of `N.ClassItem`s is correctly lowered to an `IR.IRCharClass` with a corresponding list of `IR.IRClassItem`s.
-   **Structural Nodes**: Test that `N.Seq`, `N.Alt`, `N.Quant`, `N.Group`, `N.Backref`, and `N.Look` nodes are lowered to their `IR` equivalents, and that their children are recursively lowered as well.

### Category B — IR Normalization

These tests validate the specific transformation rules of the `_normalize` method by feeding it un-optimized IR trees.

-   **Literal Fusion**: An `IR.IRSeq` containing adjacent `IR.IRLit` nodes (e.g., `IRSeq(parts=[IRLit('a'), IRLit('b')])`) must be normalized into a single `IR.IRLit('ab')`.
-   **Sequence Flattening**: A nested `IR.IRSeq` (e.g., `IRSeq(parts=[IRLit('a'), IRSeq(...)])`) must be flattened into a single, non-nested `IR.IRSeq`.
-   **Alternation Flattening**: A nested `IR.IRAlt` (e.g., `IRAlt(branches=[IRLit('a'), IRAlt(...)])`) must be flattened into a single `IR.IRAlt` with a combined list of branches.
-   **Idempotency**: Test that running `_normalize` on an already-normalized IR tree results in an identical tree.

### Category C — Full Compilation (Lower + Normalize)

These tests validate the public `compile()` method to ensure both stages work together correctly.

-   **AST with Adjacent Literals**: Test that an AST like `N.Seq(parts=[N.Lit('a'), N.Lit('b')])` compiles to a single `IR.IRLit('ab')`. This verifies that lowering produces two nodes and normalization correctly fuses them.
-   **AST with Nested Sequences**: Test that a deeply nested `N.Seq` AST compiles down to a single, flat `IR.IRSeq` (or a single `IR.IRLit` if it contains only literals).

### Category D — Metadata Generation

These tests validate the `compile_with_metadata` method and its feature analysis.

-   **Atomic Groups**: An AST containing an `N.Group` with `atomic=True` must produce an artifact where `"atomic_group"` is present in the `metadata.features_used` list.
-   **Possessive Quantifiers**: An AST containing an `N.Quant` with `mode="Possessive"` must produce an artifact with `"possessive_quantifier"` in its metadata.
-   **Lookbehinds**: An AST containing an `N.Look` with `dir="Behind"` must produce an artifact with `"lookbehind"` in its metadata.
-   **No Features**: A simple AST with no special features must produce an empty `features_used` list.

## Completion Criteria

-   [ ] There is at least one test case for the lowering of every concrete `Node` type defined in `nodes.py`.
-   [ ] There are specific test cases for each normalization rule: literal fusion, sequence flattening, and alternation flattening.
-   [ ] The tests for the public `compile()` method verify that lowering and normalization work correctly in sequence.
-   [ ] The `compile_with_metadata()` method is tested to ensure it correctly identifies and lists all relevant features.
-   [ ] The structure of the final `IR` tree is asserted for correctness in all positive cases.
