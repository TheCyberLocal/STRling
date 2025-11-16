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

    @Test
    void testMultipleFeaturesDetected() {
        /**
         * Tests that multiple features are correctly detected in a complex pattern.
         */
        Compiler compiler = new Compiler();
        // Pattern with atomic group containing a lookbehind
        Node ast = new Group(false, 
            new Look("Behind", false, new Lit("a")),
            null, true);
        
        Map<String, Object> artifact = compiler.compileWithMetadata(ast);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) artifact.get("metadata");
        @SuppressWarnings("unchecked")
        List<String> featuresUsed = (List<String>) metadata.get("features_used");
        
        assertTrue(featuresUsed.contains("atomic_group"),
            "Should detect atomic_group");
        assertTrue(featuresUsed.contains("lookbehind"),
            "Should detect lookbehind");
        assertEquals(2, featuresUsed.size(),
            "Should detect exactly 2 features");
    }
}
