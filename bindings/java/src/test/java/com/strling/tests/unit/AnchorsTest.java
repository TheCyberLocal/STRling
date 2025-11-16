package com.strling.tests.unit;

import com.strling.core.Nodes.*;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Design — AnchorsTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
 * It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
 * with the proper type and that its parsing is unaffected by flags or surrounding
 * constructs.
 *
 * <h2>Description</h2>
 * Anchors are zero-width assertions that do not consume characters but instead
 * match a specific **position** within the input string, such as the start of a
 * line or a boundary between a word and a space. This suite tests the parser's
 * ability to correctly identify all supported core and extension anchors and
 * produce the corresponding {@code nodes.Anchor} AST object.
 *
 * <h2>Scope</h2>
 * <ul>
 *   <li><strong>In scope:</strong></li>
 *   <ul>
 *     <li>Parsing of core line anchors ({@code ^}, {@code $}) and word boundary anchors
 *         ({@code \b}, {@code \B}).</li>
 *     <li>Parsing of non-core, engine-specific absolute anchors ({@code \A}, {@code \Z}, {@code \z}).</li>
 *     <li>The structure and {@code at} value of the resulting {@code nodes.Anchor} AST node.</li>
 *     <li>How anchors are parsed when placed at the start, middle, or end of a sequence.</li>
 *     <li>Ensuring the parser's output for {@code ^} and {@code $} is consistent regardless
 *         of the multiline ({@code m}) flag's presence.</li>
 *   </ul>
 *   <li><strong>Out of scope:</strong></li>
 *   <ul>
 *     <li>The runtime <em>behavioral change</em> of {@code ^} and {@code $} when the {@code m} flag is
 *         active (this is an emitter/engine concern).</li>
 *     <li>Quantification of anchors.</li>
 *     <li>The behavior of {@code \b} inside a character class, where it represents a
 *         backspace literal (covered in {@code CharClassesTest.java}).</li>
 *   </ul>
 * </ul>
 */
public class AnchorsTest {

    /**
     * Category A: Positive Cases
     * <p>
     * Covers all positive cases for valid anchor syntax. These tests verify
     * that each anchor token is parsed into the correct Anchor node with the
     * expected {@code at} value.
     */

    static Stream<Arguments> positiveAnchorCases() {
        return Stream.of(
            // A.1: Core Line Anchors
            Arguments.of("^", "Start", "line_start"),
            Arguments.of("$", "End", "line_end"),
            // A.2: Core Word Boundary Anchors
            Arguments.of("\\b", "WordBoundary", "word_boundary"),
            Arguments.of("\\B", "NotWordBoundary", "not_word_boundary"),
            // A.3: Absolute Anchors (Extension Features)
            Arguments.of("\\A", "AbsoluteStart", "absolute_start_ext"),
            Arguments.of("\\Z", "EndBeforeFinalNewline", "end_before_newline_ext")
        );
    }

    @ParameterizedTest(name = "should parse anchor ''{0}'' (ID: {2})")
    @MethodSource("positiveAnchorCases")
    void testPositiveAnchorCases(String inputDsl, String expectedAtValue, String id) {
        /**
         * Tests that each individual anchor token is parsed into the correct
         * Anchor AST node.
         */
        Parser.ParseResult result = Parser.parse(inputDsl);
        Node ast = result.ast;
        assertInstanceOf(Anchor.class, ast);
        assertEquals(expectedAtValue, ((Anchor) ast).at);
    }

    /**
     * Category B: Negative Cases
     * <p>
     * This category is intentionally empty. Anchors are single, unambiguous
     * tokens, and there are no anchor-specific parse errors. Invalid escape
     * sequences are handled by the literal/escape parser and are tested in
     * that suite.
     */

    /**
     * Category C: Edge Cases
     * <p>
     * Covers edge cases related to the position and combination of anchors.
     */

    @Test
    void testParsePatternWithOnlyAnchors() {
        /**
         * Tests that a pattern containing multiple anchors is parsed into a
         * correct sequence of Anchor nodes.
         */
        Parser.ParseResult result = Parser.parse("^\\A\\b$");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;

        assertEquals(4, seqNode.parts.size());
        // Verify all parts are anchors
        assertTrue(seqNode.parts.stream().allMatch(part -> part instanceof Anchor));
        
        String[] atValues = seqNode.parts.stream()
            .map(part -> ((Anchor) part).at)
            .toArray(String[]::new);
        assertArrayEquals(new String[]{"Start", "AbsoluteStart", "WordBoundary", "End"}, atValues);
    }

    static Stream<Arguments> anchorsInDifferentPositions() {
        return Stream.of(
            Arguments.of("^a", 0, "Start", "at_start"),
            Arguments.of("a\\bb", 1, "WordBoundary", "in_middle"),
            Arguments.of("ab$", 1, "End", "at_end")
        );
    }

    @ParameterizedTest(name = "should parse anchors in different positions (ID: {3})")
    @MethodSource("anchorsInDifferentPositions")
    void testAnchorsInDifferentPositions(String inputDsl, int expectedPosition, String expectedAtValue, String id) {
        /**
         * Tests that anchors are correctly parsed as part of a sequence at
         * various positions.
         */
        Parser.ParseResult result = Parser.parse(inputDsl);
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        Node anchorNode = seqNode.parts.get(expectedPosition);
        assertInstanceOf(Anchor.class, anchorNode);
        assertEquals(expectedAtValue, ((Anchor) anchorNode).at);
    }

    /**
     * Category D: Interaction Cases
     * <p>
     * Covers how anchors interact with other DSL features, such as flags
     * and grouping constructs.
     */

    @Test
    void testMultilineFlagDoesNotChangeAST() {
        /**
         * A critical test to ensure the parser's output for ^ and $ is
         * identical regardless of the multiline flag. The flag's semantic
         * effect is a runtime concern for the regex engine.
         */
        Parser.ParseResult resultNoM = Parser.parse("^a$");
        Parser.ParseResult resultWithM = Parser.parse("%flags m\n^a$");

        Node astNoM = resultNoM.ast;
        Node astWithM = resultWithM.ast;

        assertEquals(astNoM.toDict(), astWithM.toDict());

        // Add specific checks to be explicit
        assertInstanceOf(Seq.class, astNoM);
        Seq seqNode = (Seq) astNoM;
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertInstanceOf(Anchor.class, seqNode.parts.get(2));
        assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
        assertEquals("End", ((Anchor) seqNode.parts.get(2)).at);
    }

    static Stream<Arguments> anchorsInsideGroupsAndLookarounds() {
        return Stream.of(
            Arguments.of("(^a)", Group.class, "Start", "in_capturing_group"),
            Arguments.of("(?:a\\b)", Group.class, "WordBoundary", "in_noncapturing_group"),
            Arguments.of("(?=a$)", Look.class, "End", "in_lookahead"),
            Arguments.of("(?<=^a)", Look.class, "Start", "in_lookbehind")
        );
    }

    @ParameterizedTest(name = "should parse anchors inside groups and lookarounds (ID: {3})")
    @MethodSource("anchorsInsideGroupsAndLookarounds")
    void testAnchorsInsideGroupsAndLookarounds(String inputDsl, Class<?> containerType, String expectedAtValue, String id) {
        /**
         * Tests that anchors are correctly parsed when nested inside other
         * syntactic constructs.
         */
        Parser.ParseResult result = Parser.parse(inputDsl);
        Node ast = result.ast;
        assertInstanceOf(containerType, ast);

        // The anchor may be part of a sequence inside the container, find it
        Node containerNode = ast;
        Node anchorNode = null;
        
        Node body;
        if (containerNode instanceof Group) {
            body = ((Group) containerNode).body;
        } else if (containerNode instanceof Look) {
            body = ((Look) containerNode).body;
        } else {
            throw new AssertionError("Unexpected container type");
        }

        if (body instanceof Seq) {
            // Find the anchor in the sequence
            for (Node part : ((Seq) body).parts) {
                if (part instanceof Anchor) {
                    anchorNode = part;
                    break;
                }
            }
        } else if (body instanceof Anchor) {
            // Direct anchor
            anchorNode = body;
        }

        assertNotNull(anchorNode, "No anchor found in sequence: " + body);
        assertInstanceOf(Anchor.class, anchorNode);
        assertEquals(expectedAtValue, ((Anchor) anchorNode).at);
    }

    /**
     * Category E: Anchors in Complex Sequences
     * <p>
     * Tests for anchors in complex sequences with quantified atoms.
     */

    @Test
    void testAnchorBetweenQuantifiedAtoms() {
        /**
         * Tests anchor between quantified atoms: a*^b+
         * The ^ anchor appears between two quantified literals.
         */
        Parser.ParseResult result = Parser.parse("a*^b+");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Quant.class, seqNode.parts.get(0));
        assertInstanceOf(Anchor.class, seqNode.parts.get(1));
        assertEquals("Start", ((Anchor) seqNode.parts.get(1)).at);
        assertInstanceOf(Quant.class, seqNode.parts.get(2));
    }

    @Test
    void testAnchorAfterQuantifiedGroup() {
        /**
         * Tests anchor after quantified group: (ab)*$
         */
        Parser.ParseResult result = Parser.parse("(ab)*$");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(2, seqNode.parts.size());
        assertInstanceOf(Quant.class, seqNode.parts.get(0));
        assertInstanceOf(Anchor.class, seqNode.parts.get(1));
        assertEquals("End", ((Anchor) seqNode.parts.get(1)).at);
    }

    @Test
    void testMultipleAnchorsOfSameType() {
        /**
         * Tests multiple same anchors: ^^
         * Edge case: semantically redundant but syntactically valid.
         */
        Parser.ParseResult result = Parser.parse("^^");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(2, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Anchor.class, seqNode.parts.get(1));
        assertEquals("Start", ((Anchor) seqNode.parts.get(1)).at);
    }

    @Test
    void testMultipleEndAnchors() {
        /**
         * Tests multiple end anchors: $$
         */
        Parser.ParseResult result = Parser.parse("$$");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(2, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("End", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Anchor.class, seqNode.parts.get(1));
        assertEquals("End", ((Anchor) seqNode.parts.get(1)).at);
    }

    /**
     * Category F: Anchors in Alternation
     * <p>
     * Tests for anchors used in alternation patterns.
     */

    @Test
    void testAnchorInAlternationBranch() {
        /**
         * Tests anchor in one branch of alternation: ^a|b$
         * Parses as (^a)|(b$).
         */
        Parser.ParseResult result = Parser.parse("^a|b$");
        Node ast = result.ast;
        assertInstanceOf(Alt.class, ast);
        Alt altNode = (Alt) ast;
        assertEquals(2, altNode.branches.size());
        
        // First branch: ^a
        Node branch0 = altNode.branches.get(0);
        assertInstanceOf(Seq.class, branch0);
        Seq seqBranch0 = (Seq) branch0;
        assertEquals(2, seqBranch0.parts.size());
        assertInstanceOf(Anchor.class, seqBranch0.parts.get(0));
        assertEquals("Start", ((Anchor) seqBranch0.parts.get(0)).at);
        assertInstanceOf(Lit.class, seqBranch0.parts.get(1));
        
        // Second branch: b$
        Node branch1 = altNode.branches.get(1);
        assertInstanceOf(Seq.class, branch1);
        Seq seqBranch1 = (Seq) branch1;
        assertEquals(2, seqBranch1.parts.size());
        assertInstanceOf(Lit.class, seqBranch1.parts.get(0));
        assertInstanceOf(Anchor.class, seqBranch1.parts.get(1));
        assertEquals("End", ((Anchor) seqBranch1.parts.get(1)).at);
    }

    @Test
    void testAnchorsInGroupAlternation() {
        /**
         * Tests anchors in grouped alternation: (^|$)
         */
        Parser.ParseResult result = Parser.parse("(^|$)");
        Node ast = result.ast;
        assertInstanceOf(Group.class, ast);
        Group groupNode = (Group) ast;
        assertTrue(groupNode.capturing);
        assertInstanceOf(Alt.class, groupNode.body);
        Alt altBody = (Alt) groupNode.body;
        assertEquals(2, altBody.branches.size());
        assertInstanceOf(Anchor.class, altBody.branches.get(0));
        assertEquals("Start", ((Anchor) altBody.branches.get(0)).at);
        assertInstanceOf(Anchor.class, altBody.branches.get(1));
        assertEquals("End", ((Anchor) altBody.branches.get(1)).at);
    }

    @Test
    void testWordBoundaryInAlternation() {
        /**
         * Tests word boundary in alternation: \ba|\bb
         */
        Parser.ParseResult result = Parser.parse("\\ba|\\bb");
        Node ast = result.ast;
        assertInstanceOf(Alt.class, ast);
        Alt altNode = (Alt) ast;
        assertEquals(2, altNode.branches.size());
        
        // First branch: \ba
        Node branch0 = altNode.branches.get(0);
        assertInstanceOf(Seq.class, branch0);
        Seq seqBranch0 = (Seq) branch0;
        assertEquals(2, seqBranch0.parts.size());
        assertInstanceOf(Anchor.class, seqBranch0.parts.get(0));
        assertEquals("WordBoundary", ((Anchor) seqBranch0.parts.get(0)).at);
        
        // Second branch: \bb
        Node branch1 = altNode.branches.get(1);
        assertInstanceOf(Seq.class, branch1);
        Seq seqBranch1 = (Seq) branch1;
        assertEquals(2, seqBranch1.parts.size());
        assertInstanceOf(Anchor.class, seqBranch1.parts.get(0));
        assertEquals("WordBoundary", ((Anchor) seqBranch1.parts.get(0)).at);
    }

    /**
     * Category G: Anchors in Atomic Groups
     * <p>
     * Tests for anchors inside atomic groups.
     */

    @Test
    void testStartAnchorInAtomicGroup() {
        /**
         * Tests start anchor in atomic group: (?>^a)
         */
        Parser.ParseResult result = Parser.parse("(?>^a)");
        Node ast = result.ast;
        assertInstanceOf(Group.class, ast);
        Group groupNode = (Group) ast;
        assertTrue(groupNode.atomic);
        assertInstanceOf(Seq.class, groupNode.body);
        Seq seqBody = (Seq) groupNode.body;
        assertEquals(2, seqBody.parts.size());
        assertInstanceOf(Anchor.class, seqBody.parts.get(0));
        assertEquals("Start", ((Anchor) seqBody.parts.get(0)).at);
        assertInstanceOf(Lit.class, seqBody.parts.get(1));
    }

    @Test
    void testEndAnchorInAtomicGroup() {
        /**
         * Tests end anchor in atomic group: (?>a$)
         */
        Parser.ParseResult result = Parser.parse("(?>a$)");
        Node ast = result.ast;
        assertInstanceOf(Group.class, ast);
        Group groupNode = (Group) ast;
        assertTrue(groupNode.atomic);
        assertInstanceOf(Seq.class, groupNode.body);
        Seq seqBody = (Seq) groupNode.body;
        assertEquals(2, seqBody.parts.size());
        assertInstanceOf(Lit.class, seqBody.parts.get(0));
        assertInstanceOf(Anchor.class, seqBody.parts.get(1));
        assertEquals("End", ((Anchor) seqBody.parts.get(1)).at);
    }

    @Test
    void testWordBoundaryInAtomicGroup() {
        /**
         * Tests word boundary in atomic group: (?>\ba)
         */
        Parser.ParseResult result = Parser.parse("(?>\\ba)");
        Node ast = result.ast;
        assertInstanceOf(Group.class, ast);
        Group groupNode = (Group) ast;
        assertTrue(groupNode.atomic);
        assertInstanceOf(Seq.class, groupNode.body);
        Seq seqBody = (Seq) groupNode.body;
        assertEquals(2, seqBody.parts.size());
        assertInstanceOf(Anchor.class, seqBody.parts.get(0));
        assertEquals("WordBoundary", ((Anchor) seqBody.parts.get(0)).at);
        assertInstanceOf(Lit.class, seqBody.parts.get(1));
    }

    /**
     * Category H: Word Boundary Edge Cases
     * <p>
     * Tests for word boundary anchors in various contexts.
     */

    @Test
    void testWordBoundaryWithNonWordCharacter() {
        /**
         * Tests word boundary with non-word character: \b.\b
         * The dot matches any character, boundaries on both sides.
         */
        Parser.ParseResult result = Parser.parse("\\b.\\b");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Dot.class, seqNode.parts.get(1));
        assertInstanceOf(Anchor.class, seqNode.parts.get(2));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(2)).at);
    }

    @Test
    void testWordBoundaryWithDigit() {
        /**
         * Tests word boundary with digit: \b\d\b
         */
        Parser.ParseResult result = Parser.parse("\\b\\d\\b");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(CharClass.class, seqNode.parts.get(1));
        assertInstanceOf(Anchor.class, seqNode.parts.get(2));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(2)).at);
    }

    @Test
    void testNotWordBoundaryUsage() {
        /**
         * Tests not-word-boundary: \Ba\B
         */
        Parser.ParseResult result = Parser.parse("\\Ba\\B");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("NotWordBoundary", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Lit.class, seqNode.parts.get(1));
        assertEquals("a", ((Lit) seqNode.parts.get(1)).value);
        assertInstanceOf(Anchor.class, seqNode.parts.get(2));
        assertEquals("NotWordBoundary", ((Anchor) seqNode.parts.get(2)).at);
    }

    /**
     * Category I: Multiple Anchor Types
     * <p>
     * Tests for patterns combining different anchor types.
     */

    @Test
    void testStartAndEndAnchors() {
        /**
         * Tests both start and end anchors: ^abc$
         * Already covered but confirming as typical case.
         */
        Parser.ParseResult result = Parser.parse("^abc$");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Lit.class, seqNode.parts.get(1));
        assertEquals("abc", ((Lit) seqNode.parts.get(1)).value);
        assertInstanceOf(Anchor.class, seqNode.parts.get(2));
        assertEquals("End", ((Anchor) seqNode.parts.get(2)).at);
    }

    @Test
    void testAbsoluteAndLineAnchors() {
        /**
         * The trailing \z is an unknown escape sequence and must raise
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("\\A^abc$\\z");
        });
        assertTrue(error.getMessage().contains("Unknown escape sequence \\z"));
    }

    @Test
    void testLowercaseZAsUnknownEscape() {
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("\\z");
        });
        assertTrue(error.getMessage().contains("Unknown escape sequence \\z"));
    }

    @Test
    void testWordBoundariesAndLineAnchors() {
        /**
         * Tests word boundaries with line anchors: ^\ba\b$
         */
        Parser.ParseResult result = Parser.parse("^\\ba\\b$");
        Node ast = result.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(5, seqNode.parts.size());
        assertInstanceOf(Anchor.class, seqNode.parts.get(0));
        assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
        assertInstanceOf(Anchor.class, seqNode.parts.get(1));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(1)).at);
        assertInstanceOf(Lit.class, seqNode.parts.get(2));
        assertEquals("a", ((Lit) seqNode.parts.get(2)).value);
        assertInstanceOf(Anchor.class, seqNode.parts.get(3));
        assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(3)).at);
        assertInstanceOf(Anchor.class, seqNode.parts.get(4));
        assertEquals("End", ((Anchor) seqNode.parts.get(4)).at);
    }

    /**
     * Category J: Anchors with Quantifiers
     * <p>
     * Tests confirming that anchors themselves cannot be quantified.
     */

    @Test
    void testAnchorQuantifiedDirectlyRaisesError() {
        /**
         * Tests that ^* raises an error (cannot quantify anchor).
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("^*");
        });
        assertTrue(error.getMessage().contains("Cannot quantify anchor"));
    }

    @Test
    void testEndAnchorFollowedByQuantifier() {
        /**
         * Tests $+ raises an error (cannot quantify anchor).
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("$+");
        });
        assertTrue(error.getMessage().contains("Cannot quantify anchor"));
    }
}
