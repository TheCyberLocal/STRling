package com.strling.tests.unit;

import com.strling.core.Nodes.Alt;
import com.strling.core.Nodes.Anchor;
import com.strling.core.Nodes.Backref;
import com.strling.core.Nodes.CharClass;
import com.strling.core.Nodes.Dot;
import com.strling.core.Nodes.Group;
import com.strling.core.Nodes.Lit;
import com.strling.core.Nodes.Look;
import com.strling.core.Nodes.Node;
import com.strling.core.Nodes.Quant;
import com.strling.core.Nodes.Seq;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — QuantifiersTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the correct parsing of all quantifier forms ({@code *}, {@code +},
 * {@code ?}, {@code {m,n}}) and modes (Greedy, Lazy, Possessive). It ensures quantifiers
 * correctly bind to their preceding atom, generate the proper {@code Quant} AST node,
 * and that malformed quantifier syntax raises the appropriate {@code ParseError}.
 *
 * <h2>Description</h2>
 * Quantifiers specify the number of times a preceding atom can occur in a
 * pattern. This test suite covers the full syntactic and semantic range of this
 * feature. It verifies that the parser correctly interprets the different
 * quantifier syntaxes and their greedy (default), lazy ({@code ?} suffix), and
 * possessive ({@code +} suffix) variants. A key focus is testing operator
 * precedence—ensuring that a quantifier correctly associates with a single
 * preceding atom (like a literal, group, or class) rather than an entire
 * sequence.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing of all standard quantifiers: {@code *}, {@code +}, {@code ?}.</li>
 * <li>Parsing of all brace-based quantifiers: {@code {n}}, {@code {m,}}, {@code {m,n}}.</li>
 * <li>Parsing of lazy ({@code *?}) and possessive ({@code *+}) mode modifiers.</li>
 * <li>The structure and values of the resulting {@code nodes.Quant} AST node
 * (including {@code min}, {@code max}, and {@code mode} fields).</li>
 * <li>Error handling for malformed brace quantifiers (e.g., {@code a{1,}).</li>
 * <li>The parser's correct identification of the atom to be quantified.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Static analysis for ReDoS risks on nested quantifiers.</li>
 * <li>The emitter's final string output, such as adding non-capturing
 * groups (covered in {@code EmitterEdgesTest.java}).</li>
 * </ul>
 * </ul>
 */
public class QuantifiersTest {

    // Helper to get the AST root from a parse
    private Node parseToAST(String dsl) {
        return Parser.parse(dsl).ast;
    }

    /**
     * Covers all positive cases for valid quantifier syntax and modes.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> quantifierCases() {
            return Stream.of(
                // A.1: Star Quantifier
                Arguments.of("a*", 0, "Inf", "Greedy", "star_greedy"),
                Arguments.of("a*?", 0, "Inf", "Lazy", "star_lazy"),
                Arguments.of("a*+", 0, "Inf", "Possessive", "star_possessive"),
                // A.2: Plus Quantifier
                Arguments.of("a+", 1, "Inf", "Greedy", "plus_greedy"),
                Arguments.of("a+?", 1, "Inf", "Lazy", "plus_lazy"),
                Arguments.of("a++", 1, "Inf", "Possessive", "plus_possessive"),
                // A.3: Optional Quantifier
                Arguments.of("a?", 0, 1, "Greedy", "optional_greedy"),
                Arguments.of("a??", 0, 1, "Lazy", "optional_lazy"),
                Arguments.of("a?+", 0, 1, "Possessive", "optional_possessive"),
                // A.4: Exact Repetition
                Arguments.of("a{3}", 3, 3, "Greedy", "brace_exact_greedy"),
                Arguments.of("a{3}?", 3, 3, "Lazy", "brace_exact_lazy"),
                Arguments.of("a{3}+", 3, 3, "Possessive", "brace_exact_possessive"),
                // A.5: At-Least Repetition
                Arguments.of("a{3,}", 3, "Inf", "Greedy", "brace_at_least_greedy"),
                Arguments.of("a{3,}?", 3, "Inf", "Lazy", "brace_at_least_lazy"),
                Arguments.of("a{3,}+", 3, "Inf", "Possessive", "brace_at_least_possessive"),
                // A.6: Range Repetition
                Arguments.of("a{3,5}", 3, 5, "Greedy", "brace_range_greedy"),
                Arguments.of("a{3,5}?", 3, 5, "Lazy", "brace_range_lazy"),
                Arguments.of("a{3,5}+", 3, 5, "Possessive", "brace_range_possessive")
            );
        }

        @ParameterizedTest(name = "should parse quantifier \"{0}\" correctly (ID: {4})")
        @MethodSource("quantifierCases")
        void shouldParseQuantifierCorrectly(String inputDsl, int expectedMin, Object expectedMax, String expectedMode, String id) {
            /**
             * Tests that all quantifier forms and modes are parsed into a Quant node
             * with the correct min, max, and mode attributes.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(expectedMin, quantNode.min);
            // Convert expectedMax to String if it's "Inf"
            assertEquals(expectedMax instanceof String ? expectedMax : expectedMax.toString(), 
                         quantNode.max instanceof String ? quantNode.max : quantNode.max.toString());
            assertEquals(expectedMode, quantNode.mode);
            assertInstanceOf(Lit.class, quantNode.child);
        }
    }

    /**
     * Covers negative cases for malformed quantifier syntax.
     */
    @Nested
    class CategoryBNegativeCases {

        static Stream<Arguments> malformedBraceCases() {
            return Stream.of(
                Arguments.of("a{1", "Incomplete quantifier", 3, "unclosed_brace_after_num"),
                Arguments.of("a{1,", "Incomplete quantifier", 4, "unclosed_brace_after_comma")
            );
        }

        @ParameterizedTest(name = "should fail for malformed brace quantifier \"{0}\" (ID: {3})")
        @MethodSource("malformedBraceCases")
        void shouldFailForMalformedBraceQuantifier(String invalidDsl, String errorPrefix, int errorPos, String id) {
            /**
             * Tests that malformed brace quantifiers raise a ParseError.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST(invalidDsl));
            assertTrue(e.getMessage().contains(errorPrefix), "Error message mismatch. Was: " + e.getMessage());
            assertEquals(errorPos, e.getPos(), "Error position mismatch.");
        }

        @Test
        void shouldParseAMalformedBraceQuantifierAsALiteral() {
            /**
             * Tests that a brace construct invalid as a quantifier (e.g., '{,5}')
             * is parsed as a literal string.
             */
            Node ast = parseToAST("a{,5}");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Lit.class, seqNode.parts.get(0));
            assertEquals("a", ((Lit) seqNode.parts.get(0)).value);
            assertInstanceOf(Lit.class, seqNode.parts.get(1));
            assertEquals("{,5}", ((Lit) seqNode.parts.get(1)).value);
        }
    }

    /**
     * Covers edge cases for quantifiers.
     */
    @Nested
    class CategoryCEdgeCases {

        static Stream<Arguments> zeroRepetitionCases() {
            return Stream.of(
                Arguments.of("a{0}", 0, 0, "exact_zero"),
                Arguments.of("a{0,5}", 0, 5, "range_from_zero"),
                Arguments.of("a{0,}", 0, "Inf", "at_least_zero")
            );
        }

        @ParameterizedTest(name = "should parse zero-repetition quantifier \"{0}\" (ID: {3})")
        @MethodSource("zeroRepetitionCases")
        void shouldParseZeroRepetitionQuantifier(String inputDsl, int expectedMin, Object expectedMax, String id) {
            /** Tests that quantifiers with zero values are parsed correctly. */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(expectedMin, quantNode.min);
            assertEquals(expectedMax.toString(), quantNode.max.toString());
        }

        @Test
        void shouldApplyAQuantifierToAnEmptyGroup() {
            /** Tests that a quantifier can be applied to an empty group. */
            Node ast = parseToAST("(?:)*");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertInstanceOf(Group.class, quantNode.child);
            Group groupNode = (Group) quantNode.child;
            assertFalse(groupNode.capturing);
            assertInstanceOf(Seq.class, groupNode.body);
            assertTrue(((Seq) groupNode.body).parts.isEmpty());
        }

        @Test
        void shouldNotApplyAQuantifierToAnAnchor() {
            /**
             * Tests that a quantifier correctly applies to the atom before an anchor,
             * not the anchor itself.
             */
            Node ast = parseToAST("a?^");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertInstanceOf(Quant.class, seqNode.parts.get(0));
            assertInstanceOf(Anchor.class, seqNode.parts.get(1));
            Quant quantNode = (Quant) seqNode.parts.get(0);
            assertEquals("a", ((Lit) quantNode.child).value);
            assertEquals("Start", ((Anchor) seqNode.parts.get(1)).at);
        }
    }

    /**
     * Covers the interaction of quantifiers with different atoms and sequences.
     */
    @Nested
    class CategoryDInteractionCases {

        @Test
        void shouldDemonstrateCorrectQuantifierPrecedence() {
            /**
             * A critical test to ensure a quantifier binds only to the immediately
             * preceding atom, not the whole sequence.
             */
            Node ast = parseToAST("ab*");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Lit.class, seqNode.parts.get(0));
            assertEquals("a", ((Lit) seqNode.parts.get(0)).value);
            assertInstanceOf(Quant.class, seqNode.parts.get(1));
            Quant quantNode = (Quant) seqNode.parts.get(1);
            assertInstanceOf(Lit.class, quantNode.child);
            assertEquals("b", ((Lit) quantNode.child).value);
        }


        static Stream<Arguments> quantifyAtomCases() {
            return Stream.of(
                Arguments.of("\\d*", CharClass.class, "quantify_shorthand"),
                Arguments.of(".*", Dot.class, "quantify_dot"),
                Arguments.of("[a-z]*", CharClass.class, "quantify_char_class"),
                Arguments.of("(abc)*", Group.class, "quantify_group"),
                Arguments.of("(?:a|b)+", Group.class, "quantify_alternation_in_group"),
                Arguments.of("(?=a)+", Look.class, "quantify_lookaround")
            );
        }

        @ParameterizedTest(name = "should correctly quantify different atom types for \"{0}\" (ID: {2})")
        @MethodSource("quantifyAtomCases")
        void shouldCorrectlyQuantifyDifferentAtomTypes(String inputDsl, Class<?> expectedChildType, String id) {
            /**
             * Tests that quantifiers correctly wrap various types of AST nodes.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertInstanceOf(expectedChildType, quantNode.child);
        }
    }

    /**
     * Tests for nested quantifiers and redundant quantification patterns.
     */
    @Nested
    class CategoryENestedAndRedundantQuantifiers {

        @Test
        void shouldParseNestedQuantifierStarOnStar() {
            /**
             * Tests that a quantifier can be applied to a group containing a
             * quantified atom: (a*)* is syntactically valid.
             */
            Node ast = parseToAST("(a*)*");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(0, quantNode.min);
            assertEquals("Inf", quantNode.max);
            assertInstanceOf(Group.class, quantNode.child);
            Group groupChild = (Group) quantNode.child;
            assertInstanceOf(Quant.class, groupChild.body);
            Quant innerQuant = (Quant) groupChild.body;
            assertEquals(0, innerQuant.min);
            assertEquals("Inf", innerQuant.max);
        }

        @Test
        void shouldParseNestedQuantifierPlusOnOptional() {
            /**
             * Tests nested quantifiers with different operators: (a+)?
             */
            Node ast = parseToAST("(a+)?");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(0, quantNode.min);
            assertEquals("1", quantNode.max.toString());
            assertInstanceOf(Group.class, quantNode.child);
            Group groupChild = (Group) quantNode.child;
            assertInstanceOf(Quant.class, groupChild.body);
            Quant innerQuant = (Quant) groupChild.body;
            assertEquals(1, innerQuant.min);
            assertEquals("Inf", innerQuant.max);
        }

        @Test
        void shouldParseRedundantQuantifierPlusOnStar() {
            /**
             * Tests redundant quantification: (a*)+
             * This is semantically equivalent to a* but syntactically valid.
             */
            Node ast = parseToAST("(a*)+");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(1, quantNode.min);
            assertEquals("Inf", quantNode.max);
            assertInstanceOf(Group.class, quantNode.child);
            assertInstanceOf(Quant.class, ((Group) quantNode.child).body);
        }

        @Test
        void shouldParseRedundantQuantifierStarOnOptional() {
            /**
             * Tests redundant quantification: (a?)*
             */
            Node ast = parseToAST("(a?)*");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(0, quantNode.min);
            assertEquals("Inf", quantNode.max);
            assertInstanceOf(Group.class, quantNode.child);
            Group groupChild = (Group) quantNode.child;
            assertInstanceOf(Quant.class, groupChild.body);
            Quant innerQuant = (Quant) groupChild.body;
            assertEquals(0, innerQuant.min);
            assertEquals("1", innerQuant.max.toString());
        }

        @Test
        void shouldParseNestedQuantifierWithBrace() {
            /**
             * Tests brace quantifiers on quantified groups: (a{2,3}){1,2}
             */
            Node ast = parseToAST("(a{2,3}){1,2}");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(1, quantNode.min);
            assertEquals("2", quantNode.max.toString());
            assertInstanceOf(Group.class, quantNode.child);
            Group groupChild = (Group) quantNode.child;
            assertInstanceOf(Quant.class, groupChild.body);
            Quant innerQuant = (Quant) groupChild.body;
            assertEquals(2, innerQuant.min);
            assertEquals("3", innerQuant.max.toString());
        }
    }

    /**
     * Tests for quantifiers applied to special atom types like backreferences
     * and anchors.
     */
    @Nested
    class CategoryFQuantifierOnSpecialAtoms {

        @Test
        void shouldParseQuantifierOnBackref() {
            /**
             * Tests that a quantifier can be applied to a backreference: (a)\1*
             */
            Node ast = parseToAST("(a)\\1*");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            Quant quantNode = (Quant) seqNode.parts.get(1);
            assertInstanceOf(Quant.class, quantNode);
            assertInstanceOf(Backref.class, quantNode.child);
            assertEquals(0, quantNode.min);
            assertEquals("Inf", quantNode.max);
        }

        @Test
        void shouldParseQuantifierOnMultipleBackrefs() {
            /**
             * Tests quantifiers on multiple backrefs: (a)(b)\1*\2+
             */
            Node ast = parseToAST("(a)(b)\\1*\\2+");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(4, seqNode.parts.size());

            Quant quant1 = (Quant) seqNode.parts.get(2);
            assertInstanceOf(Quant.class, quant1);
            assertInstanceOf(Backref.class, quant1.child);
            assertEquals(Integer.valueOf(1), ((Backref) quant1.child).byIndex);

            Quant quant2 = (Quant) seqNode.parts.get(3);
            assertInstanceOf(Quant.class, quant2);
            assertInstanceOf(Backref.class, quant2.child);
            assertEquals(Integer.valueOf(2), ((Backref) quant2.child).byIndex);
        }
    }

    /**
     * Tests for patterns with multiple consecutive quantified atoms.
     */
    @Nested
    class CategoryGMultipleQuantifiedSequences {

        @Test
        void shouldParseMultipleConsecutiveQuantifiedLiterals() {
            /**
             * Tests multiple quantified atoms in sequence: a*b+c?
             */
            Node ast = parseToAST("a*b+c?");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertTrue(seqNode.parts.stream().allMatch(p -> p instanceof Quant));

            Quant quant0 = (Quant) seqNode.parts.get(0);
            assertEquals(0, quant0.min);
            assertEquals("Inf", quant0.max);

            Quant quant1 = (Quant) seqNode.parts.get(1);
            assertEquals(1, quant1.min);
            assertEquals("Inf", quant1.max);

            Quant quant2 = (Quant) seqNode.parts.get(2);
            assertEquals(0, quant2.min);
            assertEquals("1", quant2.max.toString());
        }

        @Test
        void shouldParseMultipleQuantifiedGroups() {
            /**
             * Tests multiple quantified groups: (ab)*(cd)+(ef)?
             */
            Node ast = parseToAST("(ab)*(cd)+(ef)?");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertTrue(seqNode.parts.stream().allMatch(p -> p instanceof Quant));
            assertTrue(seqNode.parts.stream().allMatch(p -> ((Quant) p).child instanceof Group));
        }

        @Test
        void shouldParseQuantifiedAtomsWithAlternation() {
            /**
             * Tests quantified atoms in an alternation: a*|b+
             */
            Node ast = parseToAST("a*|b+");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(2, altNode.branches.size());

            Quant branch0 = (Quant) altNode.branches.get(0);
            assertInstanceOf(Quant.class, branch0);
            assertEquals(0, branch0.min);

            Quant branch1 = (Quant) altNode.branches.get(1);
            assertInstanceOf(Quant.class, branch1);
            assertEquals(1, branch1.min);
        }
    }

    /**
     * Additional edge cases for brace quantifiers.
     */
    @Nested
    class CategoryHBraceQuantifierEdgeCases {

        @Test
        void shouldParseBraceQuantifierExactOne() {
            /**
             * Tests exact repetition of one: a{1}
             * Should parse correctly even though it's equivalent to 'a'.
             */
            Node ast = parseToAST("a{1}");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(1, quantNode.min);
            assertEquals("1", quantNode.max.toString());
            assertInstanceOf(Lit.class, quantNode.child);
        }

        @Test
        void shouldParseBraceQuantifierZeroToOne() {
            /**
             * Tests range zero to one: a{0,1}
             * Should be equivalent to a? but valid syntax.
             */
            Node ast = parseToAST("a{0,1}");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(0, quantNode.min);
            assertEquals("1", quantNode.max.toString());
            assertInstanceOf(Lit.class, quantNode.child);
        }

        @Test
        void shouldParseBraceQuantifierOnAlternationInGroup() {
            /**
             * Tests brace quantifier on group with alternation: (a|b){2,3}
             */
            Node ast = parseToAST("(a|b){2,3}");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(2, quantNode.min);
            assertEquals("3", quantNode.max.toString());
            assertInstanceOf(Group.class, quantNode.child);
            assertInstanceOf(Alt.class, ((Group) quantNode.child).body);
        }

        @Test
        void shouldParseBraceQuantifierLargeValues() {
            /**
             * Tests brace quantifiers with large repetition counts: a{100,200}
             */
            Node ast = parseToAST("a{100,200}");
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(100, quantNode.min);
            assertEquals("200", quantNode.max.toString());
            assertInstanceOf(Lit.class, quantNode.child);
        }
    }

    /**
     * Tests for how quantifiers interact with DSL flags.
     */
    @Nested
    class CategoryIQuantifierInteractionWithFlags {

        @Test
        void shouldParseQuantifierWithFreeSpacingMode() {
            /**
             * Tests that free-spacing mode doesn't affect quantifier parsing:
             * %flags x\na * (spaces should be ignored, quantifier still applies
             * to 'a' in the JS test... wait, no, it becomes Lit('a'), Lit('*'))
             */
            Node ast = parseToAST("%flags x\na *");
            // In free-spacing mode, 'a' and '*' are two separate atoms.
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());
            assertInstanceOf(Lit.class, seqNode.parts.get(0));
            assertEquals("a", ((Lit) seqNode.parts.get(0)).value);
            assertInstanceOf(Lit.class, seqNode.parts.get(1));
            assertEquals("*", ((Lit) seqNode.parts.get(1)).value);
        }

        @Test
        void shouldParseQuantifierOnEscapedSpaceInFreeSpacing() {
            /**
             * Tests quantifier on escaped space in free-spacing mode:
             * %flags x\n\ *
             */
            Node ast = parseToAST("%flags x\n\\ *");
            // The '\ ' is an escaped space (Lit(" ")), and * quantifies it.
            assertInstanceOf(Quant.class, ast);
            Quant quantNode = (Quant) ast;
            assertEquals(0, quantNode.min);
            assertEquals("Inf", quantNode.max);
            assertInstanceOf(Lit.class, quantNode.child);
            assertEquals(" ", ((Lit) quantNode.child).value);
        }
    }
}
