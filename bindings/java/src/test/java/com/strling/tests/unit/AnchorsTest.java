package com.strling.tests.unit;

import com.strling.core.Nodes.*;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — AnchorsTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
 * It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
 * with the proper type and that its parsing is unaffected by flags or surrounding
 * constructs.
 *
 * <h2>Description</h2>
 * Anchors are zero-width assertions that do not consume characters but instead
 * match a specific <strong>position</strong> within the input string, such as the start of a
 * line or a boundary between a word and a space. This suite tests the parser's
 * ability to correctly identify all supported core and extension anchors and
 * produce the corresponding {@code nodes.Anchor} AST object.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing of core line anchors ({@code ^}, {@code $}) and word boundary anchors
 * ({@code \b}, {@code \B}).</li>
 * <li>Parsing of non-core, engine-specific absolute anchors ({@code \A}, {@code \Z}).</li>
 * <li>The structure and {@code at} value of the resulting {@code nodes.Anchor} AST node.</li>
 * <li>How anchors are parsed when placed at the start, middle, or end of a sequence.</li>
 * <li>Ensuring the parser's output for {@code ^} and {@code $} is consistent regardless
 * of the multiline ({@code m}) flag's presence.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>The runtime <em>behavioral change</em> of {@code ^} and {@code $} when the {@code m} flag is
 * active (this is an emitter/engine concern).</li>
 * <li>Quantification of anchors.</li>
 * <li>The behavior of {@code \b} inside a character class, where it represents a
 * backspace literal (covered in {@code CharClassesTest.java}).</li>
 * </ul>
 * </ul>
 */
public class AnchorsTest {

    // Helper to get the AST root from a parse
    private Node parseToAST(String dsl) {
        return Parser.parse(dsl).ast;
    }

    /**
     * Covers all positive cases for valid anchor syntax. These tests verify
     * that each anchor token is parsed into the correct Anchor node with the
     * expected `at` value.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> anchorCases() {
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
        @MethodSource("anchorCases")
        void shouldParseAnchor(String inputDsl, String expectedAtValue, String id) {
            /**
             * Tests that each individual anchor token is parsed into the correct
             * Anchor AST node.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Anchor.class, ast);
            assertEquals(expectedAtValue, ((Anchor) ast).at);
        }
    }

    /**
     * This category is intentionally empty. Anchors are single, unambiguous
     * tokens, and there are no anchor-specific parse errors. Invalid escape
     * sequences are handled by the literal/escape parser and are tested in
     * that suite.
     */
    @Nested
    class CategoryBNegativeCases {
        // Intentionally empty
    }

    /**
     * Covers edge cases related to the position and combination of anchors.
     */
    @Nested
    class CategoryCEdgeCases {

        @Test
        void shouldParseAPatternWithOnlyAnchors() {
            /**
             * Tests that a pattern containing multiple anchors is parsed into a
             * correct sequence of Anchor nodes.
             */
            Node ast = parseToAST("^\\A\\b$");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;

            List<Node> parts = seqNode.parts;
            assertEquals(4, parts.size());
            
            // Check all are Anchors
            assertTrue(parts.stream().allMatch(p -> p instanceof Anchor));

            // Check values in order
            assertEquals("Start", ((Anchor) parts.get(0)).at);
            assertEquals("AbsoluteStart", ((Anchor) parts.get(1)).at);
            assertEquals("WordBoundary", ((Anchor) parts.get(2)).at);
            assertEquals("End", ((Anchor) parts.get(3)).at);
        }

        static Stream<Arguments> positionCases() {
            return Stream.of(
                Arguments.of("^a", 0, "Start", "at_start"),
                Arguments.of("a\\bb", 1, "WordBoundary", "in_middle"),
                Arguments.of("ab$", 1, "End", "at_end")
            );
        }

        @ParameterizedTest(name = "should parse anchors in different positions (ID: {3})")
        @MethodSource("positionCases")
        void shouldParseAnchorsInDifferentPositions(String inputDsl, int expectedPosition, String expectedAtValue, String id) {
            /**
             * Tests that anchors are correctly parsed as part of a sequence at
             * various positions.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            Node anchorNode = seqNode.parts.get(expectedPosition);
            assertInstanceOf(Anchor.class, anchorNode);
            assertEquals(expectedAtValue, ((Anchor) anchorNode).at);
        }
    }

    /**
     * Covers how anchors interact with other DSL features, such as flags
     * and grouping constructs.
     */
    @Nested
    class CategoryDInteractionCases {

        @Test
        void shouldNotChangeTheParsedASTWhenMultilineFlagIsPresent() {
            /**
             * A critical test to ensure the parser's output for `^` and `$` is
             * identical regardless of the multiline flag. The flag's semantic
             * effect is a runtime concern for the regex engine.
             */
            Node astNoM = parseToAST("^a$");
            Node astWithM = parseToAST("%flags m\n^a$");

            // Compare the .toDict() representations for structural equality
            assertEquals(astNoM.toDict(), astWithM.toDict());
            
            // Specific checks
            assertInstanceOf(Seq.class, astNoM);
            Seq seqNode = (Seq) astNoM;
            assertInstanceOf(Anchor.class, seqNode.parts.get(0));
            assertInstanceOf(Anchor.class, seqNode.parts.get(2));
            assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
            assertEquals("End", ((Anchor) seqNode.parts.get(2)).at);
        }

        static Stream<Arguments> containerCases() {
            return Stream.of(
                Arguments.of("(^a)", Group.class, "Start", "in_capturing_group"),
                Arguments.of("(?:a\\b)", Group.class, "WordBoundary", "in_noncapturing_group"),
                Arguments.of("(?=a$)", Look.class, "End", "in_lookahead"),
                Arguments.of("(?<=^a)", Look.class, "Start", "in_lookbehind")
            );
        }

        @ParameterizedTest(name = "should parse anchors inside groups and lookarounds (ID: {3})")
        @MethodSource("containerCases")
        void shouldParseAnchorsInsideGroupsAndLookarounds(String inputDsl, Class<?> containerType, String expectedAtValue, String id) {
            /**
             * Tests that anchors are correctly parsed when nested inside other
             * syntactic constructs.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(containerType, ast, "AST root should be of type " + containerType.getSimpleName());

            // Get the body of the Group or Look
            Node body;
            if (ast instanceof Group) {
                body = ((Group) ast).body;
            } else if (ast instanceof Look) {
                body = ((Look) ast).body;
            } else {
                fail("AST node was not a Group or Look");
                return; // Unreachable
            }

            // Find the anchor
            Anchor anchorNode = null;
            if (body instanceof Seq) {
                for (Node part : ((Seq) body).parts) {
                    if (part instanceof Anchor) {
                        anchorNode = (Anchor) part;
                        break;
                    }
                }
            } else if (body instanceof Anchor) {
                anchorNode = (Anchor) body;
            }

            assertNotNull(anchorNode, "No anchor found in container's body");
            assertEquals(expectedAtValue, anchorNode.at);
        }
    }

    /**
     * Tests for anchors in complex sequences with quantified atoms.
     */
    @Nested
    class CategoryEAnchorsInComplexSequences {

        @Test
        void shouldParseAnchorBetweenQuantifiedAtoms() {
            /**
             * Tests anchor between quantified atoms: a*^b+
             * The ^ anchor appears between two quantified literals.
             */
            Node ast = parseToAST("a*^b+");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Quant.class, seqNode.parts.get(0));
            assertInstanceOf(Anchor.class, seqNode.parts.get(1));
            assertEquals("Start", ((Anchor) seqNode.parts.get(1)).at);
            assertInstanceOf(Quant.class, seqNode.parts.get(2));
        }

        @Test
        void shouldParseAnchorAfterQuantifiedGroup() {
            /**
             * Tests anchor after quantified group: (ab)*$
             */
            Node ast = parseToAST("(ab)*$");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Quant.class, seqNode.parts.get(0));
            assertInstanceOf(Anchor.class, seqNode.parts.get(1));
            assertEquals("End", ((Anchor) seqNode.parts.get(1)).at);
        }

        @Test
        void shouldParseMultipleAnchorsOfSameType() {
            /**
             * Tests multiple same anchors: ^^
             * Edge case: semantically redundant but syntactically valid.
             */
            Node ast = parseToAST("^^");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Anchor.class, seqNode.parts.get(0));
            assertEquals("Start", ((Anchor) seqNode.parts.get(0)).at);
            assertInstanceOf(Anchor.class, seqNode.parts.get(1));
            assertEquals("Start", ((Anchor) seqNode.parts.get(1)).at);
        }

        @Test
        void shouldParseMultipleEndAnchors() {
            /**
             * Tests multiple end anchors: $$
             */
            Node ast = parseToAST("$$");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Anchor.class, seqNode.parts.get(0));
            assertEquals("End", ((Anchor) seqNode.parts.get(0)).at);
            assertInstanceOf(Anchor.class, seqNode.parts.get(1));
            assertEquals("End", ((Anchor) seqNode.parts.get(1)).at);
        }
    }

    /**
     * Tests for anchors used in alternation patterns.
     */
    @Nested
    class CategoryFAnchorsInAlternation {

        @Test
        void shouldParseAnchorInAlternationBranch() {
            /**
             * Tests anchor in one branch of alternation: ^a|b$
             * Parses as (^a)|(b$).
             */
            Node ast = parseToAST("^a|b$");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(2, altNode.branches.size());
            // First branch: ^a
            Seq branch0 = (Seq) altNode.branches.get(0);
            assertInstanceOf(Seq.class, branch0);
            assertEquals(2, branch0.parts.size());
            assertInstanceOf(Anchor.class, branch0.parts.get(0));
            assertEquals("Start", ((Anchor) branch0.parts.get(0)).at);
            assertInstanceOf(Lit.class, branch0.parts.get(1));
            // Second branch: b$
            Seq branch1 = (Seq) altNode.branches.get(1);
            assertInstanceOf(Seq.class, branch1);
            assertEquals(2, branch1.parts.size());
            assertInstanceOf(Lit.class, branch1.parts.get(0));
            assertInstanceOf(Anchor.class, branch1.parts.get(1));
            assertEquals("End", ((Anchor) branch1.parts.get(1)).at);
        }

        @Test
        void shouldParseAnchorsInGroupAlternation() {
            /**
             * Tests anchors in grouped alternation: (^|$)
             */
            Node ast = parseToAST("(^|$)");
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
        void shouldParseWordBoundaryInAlternation() {
            /**
             * Tests word boundary in alternation: \ba|\bb
             */
            Node ast = parseToAST("\\ba|\\bb");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(2, altNode.branches.size());
            // First branch: \ba
            Seq branch0 = (Seq) altNode.branches.get(0);
            assertInstanceOf(Seq.class, branch0);
            assertEquals(2, branch0.parts.size());
            assertInstanceOf(Anchor.class, branch0.parts.get(0));
            assertEquals("WordBoundary", ((Anchor) branch0.parts.get(0)).at);
            // Second branch: \bb
            Seq branch1 = (Seq) altNode.branches.get(1);
            assertInstanceOf(Seq.class, branch1);
            assertEquals(2, branch1.parts.size());
            assertInstanceOf(Anchor.class, branch1.parts.get(0));
            assertEquals("WordBoundary", ((Anchor) branch1.parts.get(0)).at);
        }
    }

    /**
     * Tests for anchors inside atomic groups.
     */
    @Nested
    class CategoryGAnchorsInAtomicGroups {

        @Test
        void shouldParseStartAnchorInAtomicGroup() {
            /**
             * Tests start anchor in atomic group: (?>^a)
             */
            Node ast = parseToAST("(?>^a)");
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
        void shouldParseEndAnchorInAtomicGroup() {
            /**
             * Tests end anchor in atomic group: (?>a$)
             */
            Node ast = parseToAST("(?>a$)");
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
        void shouldParseWordBoundaryInAtomicGroup() {
            /**
             * Tests word boundary in atomic group: (?>\ba)
             */
            Node ast = parseToAST("(?>\\ba)");
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
    }

    /**
     * Tests for word boundary anchors in various contexts.
     */
    @Nested
    class CategoryHWordBoundaryEdgeCases {

        @Test
        void shouldParseWordBoundaryWithNonWordCharacter() {
            /**
             * Tests word boundary with non-word character: \b.\b
             * The dot matches any character, boundaries on both sides.
             */
            Node ast = parseToAST("\\b.\\b");
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
        void shouldParseWordBoundaryWithDigit() {
            /**
             * Tests word boundary with digit: \b\d\b
             */
            Node ast = parseToAST("\\b\\d\\b");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Anchor.class, seqNode.parts.get(0));
            assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(0)).at);
            assertInstanceOf(CharClass.class, seqNode.parts.get(1)); // \d is a CharClass
            assertInstanceOf(Anchor.class, seqNode.parts.get(2));
            assertEquals("WordBoundary", ((Anchor) seqNode.parts.get(2)).at);
        }

        @Test
        void shouldParseNotWordBoundaryUsage() {
            /**
             * Tests not-word-boundary: \Ba\B
             */
            Node ast = parseToAST("\\Ba\\B");
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
    }

    /**
     * Tests for patterns combining different anchor types.
     */
    @Nested
    class CategoryIMultipleAnchorTypes {

        @Test
        void shouldParseStartAndEndAnchors() {
            /**
             * Tests both start and end anchors: ^abc$
             * Already covered but confirming as typical case.
             */
            Node ast = parseToAST("^abc$");
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
        void shouldTreatLowercaseZAsUnknownEscape() {
            /** The trailing `\z` is an unknown escape sequence and must raise */
            STRlingParseError e1 = assertThrows(STRlingParseError.class, () -> parseToAST("\\A^abc$\\z"));
            assertTrue(e1.getMessage().contains("Unknown escape sequence \\z"));

            STRlingParseError e2 = assertThrows(STRlingParseError.class, () -> parseToAST("\\z"));
            assertTrue(e2.getMessage().contains("Unknown escape sequence \\z"));
        }

        @Test
        void shouldTreatLowercaseZAsUnknownEscapeSingle() {
            /**
             * Renamed from 'should treat lowercase \z as unknown escape' for clarity
             * and to match the JS file's distinct test.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("\\z"));
            assertTrue(e.getMessage().contains("Unknown escape sequence \\z"));
        }

        @Test
        void shouldParseWordBoundariesAndLineAnchors() {
            /**
             * Tests word boundaries with line anchors: ^\ba\b$
             */
            Node ast = parseToAST("^\\ba\\b$");
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
    }

    /**
     * Tests confirming that anchors themselves cannot be quantified.
     */
    @Nested
    class CategoryJAnchorsWithQuantifiers {

        @Test
        void shouldRaiseErrorForAnchorQuantifiedDirectly() {
            /**
             * Tests that ^* raises an error (cannot quantify anchor).
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("^*"));
            assertTrue(e.getMessage().contains("Cannot quantify anchor"));
        }

        @Test
        void shouldRaiseErrorForEndAnchorFollowedByQuantifier() {
            /**
             * Tests $+ raises an error (cannot quantify anchor).
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("$+"));
            assertTrue(e.getMessage().contains("Cannot quantify anchor"));
        }
    }
}
