"""
Test Design — unit/test_ir_compiler.py

## Purpose
This test suite validates the compiler's two primary responsibilities: the
**lowering** of the AST into an Intermediate Representation (IR), and the
subsequent **normalization** of that IR. It ensures that every AST construct is
correctly translated and that the IR is optimized according to a set of defined
rules.

## Description
The compiler (`core/compiler.py`) acts as the "middle-end" of the STRling
pipeline. It receives a structured Abstract Syntax Tree (AST) from the parser
and transforms it into a simpler, canonical Intermediate Representation (IR)
that is ideal for the final emitters. This process involves a direct
translation from AST nodes to IR nodes, followed by a normalization pass that
flattens nested structures and fuses adjacent literals for efficiency. This test
suite verifies the correctness of these tree-to-tree transformations in isolation.

## Scope
-   **In scope:**
    -   The one-to-one mapping (lowering) of every AST node from `nodes.py` to
        its corresponding IR node in `ir.py`.
    -   The specific transformation rules of the IR normalization pass:
        flattening nested `IRSeq` and `IRAlt` nodes, and coalescing adjacent
        `IRLit` nodes.
    -   The structural integrity of the final IR tree after both lowering and
        normalization.
    -   The correct generation of the `metadata.features_used` list for
        patterns containing special features (e.g., atomic groups).

-   **Out of scope:**
    -   The correctness of the input AST (this is the parser's responsibility).
        Tests will construct AST nodes manually.
    -   The final emitted regex string (this is the emitter's responsibility).

    -   The parsing of the source DSL (covered in other unit tests).

"""

import pytest

from STRling.core.compiler import Compiler
from STRling.core import nodes as N
from STRling.core import ir as IR

# --- Test Suite -----------------------------------------------------------------


class TestCategoryALowering:
    """
    Verifies the direct, pre-normalization translation from AST to IR.
    These tests use the private `_lower` method to test this stage in isolation.
    """

    @pytest.mark.parametrize(
        "ast_node, expected_ir_node",
        [
            (N.Lit("a"), IR.IRLit("a")),
            (N.Dot(), IR.IRDot()),
            (N.Anchor("Start"), IR.IRAnchor("Start")),
            (
                N.CharClass(False, [N.ClassRange("a", "z")]),
                IR.IRCharClass(False, [IR.IRClassRange("a", "z")]),
            ),
            (
                N.Seq([N.Lit("a"), N.Dot()]),
                IR.IRSeq([IR.IRLit("a"), IR.IRDot()]),
            ),
            (
                N.Alt([N.Lit("a"), N.Lit("b")]),
                IR.IRAlt([IR.IRLit("a"), IR.IRLit("b")]),
            ),
            (
                N.Quant(N.Lit("a"), 1, "Inf", "Greedy"),
                IR.IRQuant(IR.IRLit("a"), 1, "Inf", "Greedy"),
            ),
            (
                N.Group(True, N.Dot(), name="x"),
                IR.IRGroup(True, IR.IRDot(), name="x"),
            ),
            (N.Backref(byIndex=1), IR.IRBackref(byIndex=1)),
            (
                N.Look("Ahead", False, N.Lit("a")),
                IR.IRLook("Ahead", False, IR.IRLit("a")),
            ),
        ],
        ids=[
            "Lit",
            "Dot",
            "Anchor",
            "CharClass",
            "Seq",
            "Alt",
            "Quant",
            "Group",
            "Backref",
            "Look",
        ],
    )
    def test_ast_nodes_are_lowered_correctly(
        self, ast_node: N.Node, expected_ir_node: IR.IROp
    ):
        """
        Tests that each AST node type is correctly lowered to its corresponding IR node type.
        """
        compiler = Compiler()
        # Accessing protected method for isolated unit testing, ignoring linter warning.
        assert compiler._lower(ast_node) == expected_ir_node  # type: ignore[reportPrivateUsage]


class TestCategoryBNormalization:
    """
    Verifies the specific transformation rules of the IR normalization pass.
    These tests use the private `_normalize` method in isolation.
    """

    def test_literal_fusion(self):
        """
        An IRSeq with adjacent IRLit nodes must be fused into a single IRLit.

        """
        compiler = Compiler()
        un_normalized = IR.IRSeq(
            [IR.IRLit("a"), IR.IRLit("b"), IR.IRDot(), IR.IRLit("c")]
        )
        normalized = compiler._normalize(un_normalized)  # type: ignore[reportPrivateUsage]
        assert normalized == IR.IRSeq([IR.IRLit("ab"), IR.IRDot(), IR.IRLit("c")])

    def test_sequence_flattening(self):
        """A nested IRSeq must be flattened into a single IRSeq."""
        compiler = Compiler()
        un_normalized = IR.IRSeq(
            [IR.IRLit("a"), IR.IRSeq([IR.IRLit("b"), IR.IRLit("c")])]
        )
        # Note: Flattening and fusion happen in the same pass
        normalized = compiler._normalize(un_normalized)  # type: ignore[reportPrivateUsage]
        assert normalized == IR.IRLit("abc")

    def test_alternation_flattening(self):
        """A nested IRAlt must be flattened into a single IRAlt."""
        compiler = Compiler()
        un_normalized = IR.IRAlt(
            [IR.IRLit("a"), IR.IRAlt([IR.IRLit("b"), IR.IRLit("c")])]
        )
        normalized = compiler._normalize(un_normalized)  # type: ignore[reportPrivateUsage]
        assert normalized == IR.IRAlt([IR.IRLit("a"), IR.IRLit("b"), IR.IRLit("c")])

    def test_normalization_is_idempotent(self):
        """Running normalize on an already-normalized IR should produce no changes."""
        compiler = Compiler()
        normalized_ir = IR.IRSeq([IR.IRLit("ab"), IR.IRDot()])
        result = compiler._normalize(normalized_ir)  # type: ignore[reportPrivateUsage]
        assert result == normalized_ir


class TestCategoryCFullCompilation:
    """
    Verifies the public `compile()` method to ensure both lowering and
    normalization work together correctly.
    """

    def test_compilation_with_adjacent_literals(self):
        """
        An AST with adjacent Lit nodes should compile to a single fused IRLit.

        """
        compiler = Compiler()
        ast = N.Seq([N.Lit("hello"), N.Lit(" "), N.Lit("world")])
        ir = compiler.compile(ast)
        assert ir == IR.IRLit("hello world")

    def test_compilation_with_nested_sequences(self):
        """
        A deeply nested AST Seq should compile to a single, flat, fused IR node.

        """
        compiler = Compiler()
        ast = N.Seq([N.Lit("a"), N.Seq([N.Lit("b"), N.Seq([N.Dot()])])])
        ir = compiler.compile(ast)
        assert ir == IR.IRSeq([IR.IRLit("ab"), IR.IRDot()])


class TestCategoryDMetadataGeneration:
    """
    Verifies the `compile_with_metadata` method and its feature analysis.
    """

    @pytest.mark.parametrize(
        "ast_node, expected_feature",
        [
            (N.Group(False, N.Lit("a"), atomic=True), "atomic_group"),
            (N.Quant(N.Lit("a"), 1, "Inf", "Possessive"), "possessive_quantifier"),
            (N.Look("Behind", False, N.Lit("a")), "lookbehind"),
        ],
        ids=["atomic_group", "possessive_quantifier", "lookbehind"],
    )
    def test_feature_detection(self, ast_node: N.Node, expected_feature: str):
        """
        Tests that ASTs with special features produce an artifact with the
        correct metadata.
        """
        compiler = Compiler()
        artifact = compiler.compile_with_metadata(ast_node)

        # Add a type check to inform Pylance that artifact["metadata"] is a dict
        metadata = artifact["metadata"]
        assert isinstance(metadata, dict)
        assert expected_feature in metadata["features_used"]

    def test_no_features_produces_empty_metadata(self):
        """
        Tests that a simple AST with no special features produces an empty
        features_used list.
        """
        compiler = Compiler()
        ast = N.Seq([N.Lit("a"), N.Dot()])
        artifact = compiler.compile_with_metadata(ast)

        # Add a type check to inform Pylance
        metadata = artifact["metadata"]
        assert isinstance(metadata, dict)
        assert metadata["features_used"] == []


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryEDeeplyNestedAlternations:
    """
    Tests for deeply nested alternation structures and their normalization.
    """

    def test_three_level_nested_alternation(self):
        """
        Tests deeply nested alternation: (a|(b|(c|d)))
        Should be flattened to IRAlt([a, b, c, d]).
        """
        pytest.fail("Not implemented")

    def test_alternation_with_sequences(self):
        """
        Tests alternation containing sequences: (ab|cd|ef)
        """
        pytest.fail("Not implemented")

    def test_mixed_alternation_and_sequence_nesting(self):
        """
        Tests mixed nesting: ((a|b)(c|d))
        Two alternations in a sequence inside a group.
        """
        pytest.fail("Not implemented")


class TestCategoryFComplexSequenceNormalization:
    """
    Tests for complex sequence normalization scenarios.
    """

    def test_deeply_nested_sequences(self):
        """
        Tests deeply nested sequences: Seq([Lit("a"), Seq([Lit("b"), Seq([Lit("c")])])])
        Should normalize to IRLit("abc").
        """
        pytest.fail("Not implemented")

    def test_sequence_with_non_literal_in_middle(self):
        """
        Tests sequence with non-literal: Seq([Lit("a"), Dot(), Lit("b")])
        Should normalize to IRSeq([IRLit("a"), IRDot(), IRLit("b")]).
        """
        pytest.fail("Not implemented")

    def test_empty_sequence_normalization(self):
        """
        Tests normalization of empty sequence: Seq([])
        Should produce IRSeq([]) or equivalent.
        """
        pytest.fail("Not implemented")


class TestCategoryGLiteralFusionEdgeCases:
    """
    Tests for edge cases in literal fusion during normalization.
    """

    def test_fusion_with_escaped_chars(self):
        """
        Tests fusion of literals with escape sequences: Lit("a") + Lit("\\n") + Lit("b")
        Should fuse to single IRLit("a\\nb").
        """
        pytest.fail("Not implemented")

    def test_fusion_with_unicode(self):
        """
        Tests fusion of Unicode literals: Lit("😀") + Lit("a")
        """
        pytest.fail("Not implemented")

    def test_no_fusion_across_non_literals(self):
        """
        Tests that literals don't fuse across non-literal nodes:
        Seq([Lit("a"), Dot(), Lit("b")]) should keep three separate nodes.
        """
        pytest.fail("Not implemented")


class TestCategoryHQuantifierNormalization:
    """
    Tests for quantifier normalization scenarios.
    """

    def test_quantifier_of_single_item_sequence(self):
        """
        Tests quantifier wrapping sequence with single item:
        Quant(Seq([Lit("a")]), ...)
        Should potentially unwrap to Quant(Lit("a"), ...).
        """
        pytest.fail("Not implemented")

    def test_quantifier_of_empty_sequence(self):
        """
        Tests quantifier of empty sequence: Quant(Seq([]), ...)
        Edge case behavior.
        """
        pytest.fail("Not implemented")

    def test_nested_quantifiers_normalization(self):
        """
        Tests normalization of nested quantifiers: Quant(Quant(Lit("a"), ...), ...)
        """
        pytest.fail("Not implemented")


class TestCategoryIFeatureDetectionComprehensive:
    """
    Comprehensive tests for feature detection in metadata.
    """

    def test_feature_detection_for_named_groups(self):
        """
        Tests feature detection for named groups.
        """
        pytest.fail("Not implemented")

    def test_feature_detection_for_backreferences(self):
        """
        Tests feature detection for backreferences (if tracked).
        """
        pytest.fail("Not implemented")

    def test_feature_detection_for_lookahead(self):
        """
        Tests feature detection for lookahead assertions.
        """
        pytest.fail("Not implemented")

    def test_feature_detection_for_unicode_properties(self):
        """
        Tests feature detection for Unicode properties (if tracked).
        """
        pytest.fail("Not implemented")

    def test_multiple_features_in_one_pattern(self):
        """
        Tests pattern with multiple special features:
        atomic group + possessive quantifier + lookbehind.
        """
        pytest.fail("Not implemented")


class TestCategoryJAlternationNormalizationEdgeCases:
    """
    Edge cases for alternation normalization.
    """

    def test_alternation_with_single_branch(self):
        """
        Tests alternation with only one branch: Alt([Lit("a")])
        Should potentially unwrap to just Lit("a").
        """
        pytest.fail("Not implemented")

    def test_alternation_with_empty_branches(self):
        """
        Tests alternation with empty alternatives: Alt([Lit("a"), Seq([])])
        """
        pytest.fail("Not implemented")

    def test_nested_alternations_different_depths(self):
        """
        Tests alternations nested at different depths in different branches.
        """
        pytest.fail("Not implemented")
