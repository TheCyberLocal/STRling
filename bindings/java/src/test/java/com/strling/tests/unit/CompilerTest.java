package com.strling.tests.unit;

import com.strling.core.Compiler;
import com.strling.core.Nodes.*;
import com.strling.core.IR.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.*;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Design — CompilerTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the compiler's two primary responsibilities: the
 * <strong>lowering</strong> of the AST into an Intermediate Representation (IR), and the
 * subsequent <strong>normalization</strong> of that IR. It ensures that every AST construct is
 * correctly translated and that the IR is optimized according to a set of defined
 * rules.
 *
 * <h2>Description</h2>
 * The compiler ({@code core/Compiler.java}) acts as the "middle-end" of the STRling
 * pipeline. It receives a structured Abstract Syntax Tree (AST) from the parser
 * and transforms it into a simpler, canonical Intermediate Representation (IR)
 * that is ideal for the final emitters. This process involves a direct
 * translation from AST nodes to IR nodes, followed by a normalization pass that
 * flattens nested structures and fuses adjacent literals for efficiency. This test
 * suite verifies the correctness of these tree-to-tree transformations in isolation.
 *
 * <h2>Scope</h2>
 * <ul>
 *   <li><strong>In scope:</strong></li>
 *   <ul>
 *     <li>The one-to-one mapping (lowering) of every AST node to its corresponding IR node.</li>
 *     <li>The specific transformation rules of the IR normalization pass:
 *         flattening nested {@code IRSeq} and {@code IRAlt} nodes, and coalescing adjacent
 *         {@code IRLit} nodes.</li>
 *     <li>The structural integrity of the final IR tree after both lowering and
 *         normalization.</li>
 *     <li>The correct generation of the {@code metadata.features_used} list for
 *         patterns containing special features (e.g., atomic groups).</li>
 *   </ul>
 *   <li><strong>Out of scope:</strong></li>
 *   <ul>
 *     <li>The correctness of the input AST (this is the parser's responsibility).
 *         Tests will construct AST nodes manually.</li>
 *     <li>The final emitted regex string (this is the emitter's responsibility).</li>
 *     <li>The parsing of the source DSL (covered in other unit tests).</li>
 *   </ul>
 * </ul>
 */
public class CompilerTest {

    /**
     * Category A: AST to IR Lowering
     * <p>
     * Verifies the direct, pre-normalization translation from AST to IR.
     */

    static Stream<Arguments> loweringTestCases() {
        return Stream.of(
            Arguments.of("Lit", new Lit("a"), new IRLit("a")),
            Arguments.of("Dot", new Dot(), new IRDot()),
            Arguments.of("Anchor", new Anchor("Start"), new IRAnchor("Start")),
            Arguments.of("CharClass",
                new CharClass(false, Arrays.asList(new ClassRange("a", "z"))),
                new IRCharClass(false, Arrays.asList(new IRClassRange("a", "z")))),
            Arguments.of("Seq",
                new Seq(Arrays.asList(new Lit("a"), new Dot())),
                new IRSeq(Arrays.asList(new IRLit("a"), new IRDot()))),
            Arguments.of("Alt",
                new Alt(Arrays.asList(new Lit("a"), new Lit("b"))),
                new IRAlt(Arrays.asList(new IRLit("a"), new IRLit("b")))),
            Arguments.of("Quant",
                new Quant(new Lit("a"), 1, "Inf", "Greedy"),
                new IRQuant(new IRLit("a"), 1, "Inf", "Greedy")),
            Arguments.of("Group",
                new Group(true, new Dot(), "x"),
                new IRGroup(true, new IRDot(), "x")),
            Arguments.of("Backref",
                new Backref(1, null),
                new IRBackref(1, null)),
            Arguments.of("Look",
                new Look("Ahead", false, new Lit("a")),
                new IRLook("Ahead", false, new IRLit("a")))
        );
    }

    @ParameterizedTest(name = "should lower AST node for {0} correctly")
    @MethodSource("loweringTestCases")
    void testLowering(String id, Node astNode, IROp expectedIrNode) {
        /**
         * Tests that each AST node type is correctly lowered to its corresponding IR node type.
         */
        Compiler compiler = new Compiler();
        IROp result = compiler.lower(astNode);
        assertEquals(expectedIrNode.toDict(), result.toDict(),
            "Lowered IR should match expected for " + id);
    }

    /**
     * Category B: IR Normalization
     * <p>
     * Verifies the specific transformation rules of the IR normalization pass.
     */

    @Test
    void testFuseAdjacentLiterals() {
        /**
         * An IRSeq with adjacent IRLit nodes must be fused into a single IRLit.
         */
        Compiler compiler = new Compiler();
        IROp unNormalized = new IRSeq(Arrays.asList(
            new IRLit("a"),
            new IRLit("b"),
            new IRDot(),
            new IRLit("c")
        ));
        
        IROp normalized = compiler.normalize(unNormalized);
        IROp expected = new IRSeq(Arrays.asList(
            new IRLit("ab"),
            new IRDot(),
            new IRLit("c")
        ));
        
        assertEquals(expected.toDict(), normalized.toDict());
    }

    @Test
    void testFlattenNestedSequences() {
        /**
         * A nested IRSeq must be flattened into a single IRSeq.
         * Note: Flattening and fusion happen in the same pass.
         */
        Compiler compiler = new Compiler();
        IROp unNormalized = new IRSeq(Arrays.asList(
            new IRLit("a"),
            new IRSeq(Arrays.asList(new IRLit("b"), new IRLit("c")))
        ));
        
        IROp normalized = compiler.normalize(unNormalized);
        IROp expected = new IRLit("abc");
        
        assertEquals(expected.toDict(), normalized.toDict());
    }

    @Test
    void testFlattenNestedAlternations() {
        /**
         * A nested IRAlt must be flattened into a single IRAlt.
         */
        Compiler compiler = new Compiler();
        IROp unNormalized = new IRAlt(Arrays.asList(
            new IRLit("a"),
            new IRAlt(Arrays.asList(new IRLit("b"), new IRLit("c")))
        ));
        
        IROp normalized = compiler.normalize(unNormalized);
        IROp expected = new IRAlt(Arrays.asList(
            new IRLit("a"),
            new IRLit("b"),
            new IRLit("c")
        ));
        
        assertEquals(expected.toDict(), normalized.toDict());
    }

    @Test
    void testNormalizationIsIdempotent() {
        /**
         * Running normalize on an already-normalized IR should produce no changes.
         */
        Compiler compiler = new Compiler();
        IROp normalizedIr = new IRSeq(Arrays.asList(new IRLit("ab"), new IRDot()));
        
        IROp result = compiler.normalize(normalizedIr);
        
        assertEquals(normalizedIr.toDict(), result.toDict());
    }

    /**
     * Category C: Full Compilation (Lower + Normalize)
     * <p>
     * Verifies the public {@code compile()} method to ensure both lowering and
     * normalization work together correctly.
     */

    @Test
    void testCompileAdjacentLiteralsToSingleFusedIRLit() {
        /**
         * An AST with adjacent Lit nodes should compile to a single fused IRLit.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(
            new Lit("hello"),
            new Lit(" "),
            new Lit("world")
        ));
        
        IROp ir = compiler.compile(ast);
        IROp expected = new IRLit("hello world");
        
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testCompileNestedASTSequenceToFlatFusedIR() {
        /**
         * A deeply nested AST Seq should compile to a single, flat, fused IR node.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(
            new Lit("a"),
            new Seq(Arrays.asList(new Lit("b"), new Seq(Arrays.asList(new Dot()))))
        ));
        
        IROp ir = compiler.compile(ast);
        IROp expected = new IRSeq(Arrays.asList(new IRLit("ab"), new IRDot()));
        
        assertEquals(expected.toDict(), ir.toDict());
    }

    /**
     * Category D: Metadata Generation
     * <p>
     * Verifies the {@code compileWithMetadata} method and its feature analysis.
     */

    static Stream<Arguments> featureDetectionTestCases() {
        return Stream.of(
            Arguments.of("atomic_group",
                new Group(false, new Lit("a"), null, true),
                "atomic_group"),
            Arguments.of("possessive_quantifier",
                new Quant(new Lit("a"), 1, "Inf", "Possessive"),
                "possessive_quantifier"),
            Arguments.of("lookbehind",
                new Look("Behind", false, new Lit("a")),
                "lookbehind"),
            Arguments.of("lookahead",
                new Look("Ahead", false, new Lit("a")),
                "lookahead"),
            Arguments.of("named_group",
                new Group(true, new Lit("a"), "mygroup"),
                "named_group"),
            Arguments.of("backreference",
                new Backref(1, null),
                "backreference")
        );
    }

    @ParameterizedTest(name = "should detect feature for {0}")
    @MethodSource("featureDetectionTestCases")
    void testFeatureDetection(String id, Node astNode, String expectedFeature) {
        /**
         * Tests that ASTs with special features produce an artifact with the
         * correct metadata.
         */
        Compiler compiler = new Compiler();
        Map<String, Object> artifact = compiler.compileWithMetadata(astNode);
        
        assertNotNull(artifact.get("metadata"), "Metadata should be present");
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) artifact.get("metadata");
        @SuppressWarnings("unchecked")
        List<String> featuresUsed = (List<String>) metadata.get("features_used");
        
        assertTrue(featuresUsed.contains(expectedFeature),
            "Features list should contain " + expectedFeature);
    }

    @Test
    void testEmptyMetadataForSimplePattern() {
        /**
         * Tests that a simple AST with no special features produces an empty
         * features_used list.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(new Lit("a"), new Dot()));
        Map<String, Object> artifact = compiler.compileWithMetadata(ast);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) artifact.get("metadata");
        @SuppressWarnings("unchecked")
        List<String> featuresUsed = (List<String>) metadata.get("features_used");
        
        assertTrue(featuresUsed.isEmpty(),
            "Features list should be empty for simple patterns");
    }

    /**
     * Category E: Deeply Nested Alternations
     * <p>
     * Tests for deeply nested alternation structures and their normalization.
     */

    @Test
    void testFlattenThreeLevelNestedAlternation() {
        /**
         * Tests deeply nested alternation: (a|(b|(c|d)))
         * Should be flattened to IRAlt([a, b, c, d]).
         */
        Compiler compiler = new Compiler();
        // Build: Alt([Lit("a"), Alt([Lit("b"), Alt([Lit("c"), Lit("d")])])])
        Node ast = new Alt(Arrays.asList(
            new Lit("a"),
            new Alt(Arrays.asList(
                new Lit("b"),
                new Alt(Arrays.asList(new Lit("c"), new Lit("d")))
            ))
        ));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRAlt(Arrays.asList(
            new IRLit("a"),
            new IRLit("b"),
            new IRLit("c"),
            new IRLit("d")
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testFuseSequencesWithinAlternation() {
        /**
         * Tests alternation containing sequences: (ab|cd|ef)
         * Each sequence should be fused into a single literal.
         */
        Compiler compiler = new Compiler();
        Node ast = new Alt(Arrays.asList(
            new Seq(Arrays.asList(new Lit("a"), new Lit("b"))),
            new Seq(Arrays.asList(new Lit("c"), new Lit("d"))),
            new Seq(Arrays.asList(new Lit("e"), new Lit("f")))
        ));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRAlt(Arrays.asList(
            new IRLit("ab"),
            new IRLit("cd"),
            new IRLit("ef")
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testMixedAlternationAndSequenceNesting() {
        /**
         * Tests mixed nesting: ((a|b)(c|d))
         * Two alternations in a sequence inside a non-capturing group.
         */
        Compiler compiler = new Compiler();
        Node ast = new Group(
            false, // non-capturing
            new Seq(Arrays.asList(
                new Alt(Arrays.asList(new Lit("a"), new Lit("b"))),
                new Alt(Arrays.asList(new Lit("c"), new Lit("d")))
            )),
            null
        );
        IROp ir = compiler.compile(ast);
        // Should preserve structure: Group with Seq containing two Alts
        IROp expected = new IRGroup(
            false,
            new IRSeq(Arrays.asList(
                new IRAlt(Arrays.asList(new IRLit("a"), new IRLit("b"))),
                new IRAlt(Arrays.asList(new IRLit("c"), new IRLit("d")))
            )),
            null
        );
        assertEquals(expected.toDict(), ir.toDict());
    }

    /**
     * Category F: Complex Sequence Normalization
     * <p>
     * Tests for complex sequence normalization scenarios.
     */

    @Test
    void testFlattenDeeplyNestedSequences() {
        /**
         * Tests deeply nested sequences: Seq([Lit("a"), Seq([Lit("b"), Seq([Lit("c")])])])
         * All literals should be fused into one.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(
            new Lit("a"),
            new Seq(Arrays.asList(new Lit("b"), new Seq(Arrays.asList(new Lit("c")))))
        ));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRLit("abc");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testSequenceWithNonLiteralInMiddle() {
        /**
         * Tests sequence with non-literal: Seq([Lit("a"), Dot(), Lit("b")])
         * Should preserve structure with no fusion across Dot.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(new Lit("a"), new Dot(), new Lit("b")));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRSeq(Arrays.asList(
            new IRLit("a"),
            new IRDot(),
            new IRLit("b")
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testNormalizeEmptySequence() {
        /**
         * Tests normalization of empty sequence: Seq([])
         * Should produce IRSeq([]).
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList());
        IROp ir = compiler.compile(ast);
        IROp expected = new IRSeq(Arrays.asList());
        assertEquals(expected.toDict(), ir.toDict());
    }

    /**
     * Category G: Literal Fusion Edge Cases
     * <p>
     * Tests for edge cases in literal fusion during normalization.
     */

    @Test
    void testFuseLiteralsWithEscapedChars() {
        /**
         * Tests fusion of literals with escape sequences: Lit("a") + Lit("\n") + Lit("b")
         * Should fuse to single IRLit("a\nb").
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(
            new Lit("a"),
            new Lit("\n"),
            new Lit("b")
        ));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRLit("a\nb");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testFuseUnicodeLiterals() {
        /**
         * Tests fusion of Unicode literals: Lit("😀") + Lit("a")
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(new Lit("😀"), new Lit("a")));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRLit("😀a");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testNotFuseAcrossNonLiterals() {
        /**
         * Tests that literals don't fuse across non-literal nodes:
         * Seq([Lit("a"), Dot(), Lit("b")]) should keep three separate nodes.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(new Lit("a"), new Dot(), new Lit("b")));
        IROp ir = compiler.compile(ast);
        // Should NOT fuse across the Dot
        IROp expected = new IRSeq(Arrays.asList(
            new IRLit("a"),
            new IRDot(),
            new IRLit("b")
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }

    /**
     * Category H: Quantifier Normalization
     * <p>
     * Tests for quantifier normalization scenarios.
     */

    @Test
    void testUnwrapQuantifierOfSingleItemSequence() {
        /**
         * Tests quantifier wrapping sequence with single item:
         * Quant(Seq([Lit("a")]), ...)
         * Single-item sequence should be unwrapped.
         */
        Compiler compiler = new Compiler();
        Node ast = new Quant(
            new Seq(Arrays.asList(new Lit("a"))),
            1,
            "Inf",
            "Greedy"
        );
        IROp ir = compiler.compile(ast);
        IROp expected = new IRQuant(new IRLit("a"), 1, "Inf", "Greedy");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testPreserveQuantifierOfEmptySequence() {
        /**
         * Tests quantifier of empty sequence: Quant(Seq([]), ...)
         * Quantifier of empty sequence should preserve structure.
         */
        Compiler compiler = new Compiler();
        Node ast = new Quant(new Seq(Arrays.asList()), 0, "Inf", "Greedy");
        IROp ir = compiler.compile(ast);
        IROp expected = new IRQuant(new IRSeq(Arrays.asList()), 0, "Inf", "Greedy");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testPreserveNestedQuantifiers() {
        /**
         * Tests normalization of nested quantifiers: Quant(Quant(Lit("a"), ...), ...)
         * Should preserve the nested structure.
         */
        Compiler compiler = new Compiler();
        Node ast = new Quant(
            new Quant(new Lit("a"), 1, 3, "Greedy"),
            0,
            1,
            "Greedy"
        );
        IROp ir = compiler.compile(ast);
        IROp expected = new IRQuant(
            new IRQuant(new IRLit("a"), 1, 3, "Greedy"),
            0,
            1,
            "Greedy"
        );
        assertEquals(expected.toDict(), ir.toDict());
    }

    /**
     * Category I: Feature Detection Comprehensive
     * <p>
     * Comprehensive tests for feature detection in metadata.
     */

    @Test
    void testDetectUnicodeProperties() {
        /**
         * Tests feature detection for Unicode properties.
         */
        Compiler compiler = new Compiler();
        Node ast = new CharClass(false, Arrays.asList(
            new ClassEscape("p", "L")
        ));
        Map<String, Object> artifact = compiler.compileWithMetadata(ast);

        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) artifact.get("metadata");
        @SuppressWarnings("unchecked")
        List<String> featuresUsed = (List<String>) metadata.get("features_used");

        assertTrue(featuresUsed.contains("unicode_property"));
    }

    @Test
    void testDetectMultipleFeaturesInOnePattern() {
        /**
         * Tests pattern with multiple special features:
         * atomic group + possessive quantifier + lookbehind.
         */
        Compiler compiler = new Compiler();
        Node ast = new Seq(Arrays.asList(
            new Group(false, new Lit("a"), null, true), // atomic
            new Quant(new Lit("b"), 1, "Inf", "Possessive"),
            new Look("Behind", false, new Lit("c"))
        ));
        Map<String, Object> artifact = compiler.compileWithMetadata(ast);

        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) artifact.get("metadata");
        @SuppressWarnings("unchecked")
        List<String> featuresUsed = (List<String>) metadata.get("features_used");

        assertTrue(featuresUsed.contains("atomic_group"));
        assertTrue(featuresUsed.contains("possessive_quantifier"));
        assertTrue(featuresUsed.contains("lookbehind"));
    }

    /**
     * Category J: Alternation Normalization Edge Cases
     * <p>
     * Edge cases for alternation normalization.
     */

    @Test
    void testUnwrapAlternationWithSingleBranch() {
        /**
         * Tests alternation with only one branch: Alt([Lit("a")])
         * Single-branch alternation should be unwrapped to just Lit("a").
         */
        Compiler compiler = new Compiler();
        Node ast = new Alt(Arrays.asList(new Lit("a")));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRLit("a");
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testPreserveAlternationWithEmptyBranches() {
        /**
         * Tests alternation with empty alternatives: Alt([Lit("a"), Seq([])])
         * Should preserve both branches, with empty sequence normalized.
         */
        Compiler compiler = new Compiler();
        Node ast = new Alt(Arrays.asList(new Lit("a"), new Seq(Arrays.asList())));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRAlt(Arrays.asList(
            new IRLit("a"),
            new IRSeq(Arrays.asList())
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }

    @Test
    void testFlattenAlternationsNestedAtDifferentDepths() {
        /**
         * Tests alternations nested at different depths in different branches.
         * Alt([Lit("a"), Alt([Lit("b"), Lit("c")]), Lit("d")])
         * Nested alternation should be flattened.
         */
        Compiler compiler = new Compiler();
        Node ast = new Alt(Arrays.asList(
            new Lit("a"),
            new Alt(Arrays.asList(new Lit("b"), new Lit("c"))),
            new Lit("d")
        ));
        IROp ir = compiler.compile(ast);
        IROp expected = new IRAlt(Arrays.asList(
            new IRLit("a"),
            new IRLit("b"),
            new IRLit("c"),
            new IRLit("d")
        ));
        assertEquals(expected.toDict(), ir.toDict());
    }
}
