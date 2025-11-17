package com.strling.tests.unit;

import com.strling.core.Nodes.CharClass;
import com.strling.core.Nodes.ClassEscape;
import com.strling.core.Nodes.ClassItem;
import com.strling.core.Nodes.ClassLiteral;
import com.strling.core.Nodes.ClassRange;
import com.strling.core.Nodes.Node;
import com.strling.core.Nodes.Seq;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — CharClassesTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the correct parsing of character classes, ensuring
 * all forms—including literals, ranges, shorthands, and Unicode properties—are
 * correctly transformed into {@code CharClass} AST nodes. It also verifies that
 * negation, edge cases involving special characters, and invalid syntax are
 * handled according to the DSL's semantics.
 *
 * <h2>Description</h2>
 * Character classes ({@code [...]}) are a fundamental feature of the STRling DSL,
 * allowing a pattern to match any single character from a specified set. This
 * suite tests the parser's ability to correctly handle the various components
 * that can make up these sets: literal characters, character ranges ({@code a-z}),
 * shorthand escapes ({@code \d}, {@code \w}), and Unicode property escapes ({@code \p{L}}). It also
 * ensures that class-level negation ({@code [^...]}) and the special rules for
 * metacharacters ({@code -}, {@code ]}, {@code ^}) within classes are parsed correctly.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing of positive {@code [abc]} and negative {@code [^abc]} character classes.</li>
 * <li>Parsing of character ranges ({@code [a-z]}, {@code [0-9]}) and their validation.</li>
 * <li>Parsing of all supported shorthand ({@code \d}, {@code \s}, {@code \w} and their negated
 * counterparts) and Unicode property ({@code \p{...}}, {@code \P{...}}) escapes
 * within a class.</li>
 * <li>The special syntactic rules for {@code ]}, {@code -}, {@code ^}, and escapes like {@code \b}
 * when they appear inside a class.</li>
 * <li>Error handling for malformed classes (e.g., unterminated {@code [} or invalid
 * ranges {@code [z-a]}).</li>
 * <li>The structure of the resulting {@code nodes.CharClass} AST node and its list
 * of {@code items}.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Quantification of an entire character class (covered in
 * {@code QuantifiersTest.java}).</li>
 * <li>The behavior of character classes within groups or lookarounds.</li>
 * <li>Emitter-specific optimizations or translations (covered in
 * {@code EmitterEdgesTest.java}).</li>
 * </ul>
 * </ul>
 */
public class CharClassesTest {

    // Helper to get the AST root from a parse
    private Node parseToAST(String dsl) {
        return Parser.parse(dsl).ast;
    }

    /**
     * Covers all positive cases for valid character class syntax.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> validCharClassCases() {
            return Stream.of(
                // A.1: Basic Classes
                Arguments.of("[abc]", false, Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c")
                ), "simple_class"),
                Arguments.of("[^abc]", true, Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c")
                ), "negated_simple_class"),
                // A.2: Ranges
                Arguments.of("[a-z]", false, Arrays.asList(
                    new ClassRange("a", "z")
                ), "range_lowercase"),
                Arguments.of("[A-Za-z0-9]", false, Arrays.asList(
                    new ClassRange("A", "Z"), new ClassRange("a", "z"), new ClassRange("0", "9")
                ), "range_alphanum"),
                // A.3: Shorthand Escapes
                Arguments.of("[\\d\\s\\w]", false, Arrays.asList(
                    new ClassEscape("d"), new ClassEscape("s"), new ClassEscape("w")
                ), "shorthand_positive"),
                Arguments.of("[\\D\\S\\W]", false, Arrays.asList(
                    new ClassEscape("D"), new ClassEscape("S"), new ClassEscape("W")
                ), "shorthand_negated"),
                // A.4: Unicode Property Escapes
                Arguments.of("[\\p{L}]", false, Arrays.asList(
                    new ClassEscape("p", "L")
                ), "unicode_property_short"),
                Arguments.of("[\\p{Letter}]", false, Arrays.asList(
                    new ClassEscape("p", "Letter")
                ), "unicode_property_long"),
                Arguments.of("[\\P{Number}]", false, Arrays.asList(
                    new ClassEscape("P", "Number")
                ), "unicode_property_negated"),
                Arguments.of("[\\p{Script=Greek}]", false, Arrays.asList(
                    new ClassEscape("p", "Script=Greek")
                ), "unicode_property_with_value"),
                // A.5: Special Character Handling
                Arguments.of("[]a]", false, Arrays.asList(
                    new ClassLiteral("]"), new ClassLiteral("a")
                ), "special_char_bracket_at_start"),
                Arguments.of("[^]a]", true, Arrays.asList(
                    new ClassLiteral("]"), new ClassLiteral("a")
                ), "special_char_bracket_at_start_negated"),
                Arguments.of("[-az]", false, Arrays.asList(
                    new ClassLiteral("-"), new ClassLiteral("a"), new ClassLiteral("z")
                ), "special_char_hyphen_at_start"),
                Arguments.of("[az-]", false, Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("z"), new ClassLiteral("-")
                ), "special_char_hyphen_at_end"),
                Arguments.of("[a^b]", false, Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("^"), new ClassLiteral("b")
                ), "special_char_caret_in_middle"),
                Arguments.of("[\\b]", false, Arrays.asList(
                    new ClassLiteral("\b") // \b is backspace (\x08) inside class
                ), "special_char_backspace_escape")
            );
        }

        @ParameterizedTest(name = "should parse valid char class ''{0}'' (ID: {3})")
        @MethodSource("validCharClassCases")
        void shouldParseValidCharClass(String inputDsl, boolean expectedNegated, List<ClassItem> expectedItems, String id) {
            /**
             * Tests that various valid character classes are parsed into the correct
             * CharClass AST node with the expected items.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(CharClass.class, ast);
            CharClass ccNode = (CharClass) ast;
            assertEquals(expectedNegated, ccNode.negated);
            // Use .toDict() for structural comparison of lists
            assertEquals(
                expectedItems.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList()),
                ccNode.items.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList())
            );
        }
    }

    /**
     * Covers all negative cases for malformed character class syntax.
     */
    @Nested
    class CategoryBNegativeCases {

        static Stream<Arguments> invalidCharClassCases() {
            return Stream.of(
                // B.1: Unterminated classes
                Arguments.of("[abc", "Unterminated character class", 4, "unterminated_class"),
                Arguments.of("[", "Unterminated character class", 1, "unterminated_empty_class"),
                Arguments.of("[^", "Unterminated character class", 2, "unterminated_negated_empty_class"),
                // B.2: Malformed Unicode properties
                Arguments.of("[\\p{L", "Unterminated \\p{...}", 1, "unterminated_unicode_property"),
                Arguments.of("[\\pL]", "Expected { after \\p/\\P", 1, "missing_braces_on_unicode_property")
            );
        }

        @ParameterizedTest(name = "should fail to parse ''{0}'' (ID: {3})")
        @MethodSource("invalidCharClassCases")
        void shouldFailToParse(String invalidDsl, String errorMessagePrefix, int errorPosition, String id) {
            /**
             * Tests that invalid character class syntax raises a ParseError with the
             * correct message and position.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST(invalidDsl));
            assertTrue(e.getMessage().contains(errorMessagePrefix), "Error message mismatch. Was: " + e.getMessage());
            assertEquals(errorPosition, e.getPos(), "Error position mismatch.");
        }
    }

    /**
     * Covers edge cases for character class parsing.
     */
    @Nested
    class CategoryCEdgeCases {

        static Stream<Arguments> edgeCaseClassCases() {
            return Stream.of(
                Arguments.of("[a\\-c]", Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("-"), new ClassLiteral("c")
                ), "escaped_hyphen_is_literal"),
                Arguments.of("[\\x41-\\x5A]", Arrays.asList(
                    new ClassRange("A", "Z")
                ), "range_with_escaped_endpoints"),
                Arguments.of("[\\n\\t\\d]", Arrays.asList(
                    new ClassLiteral("\n"), new ClassLiteral("\t"), new ClassEscape("d")
                ), "class_with_only_escapes")
            );
        }

        @ParameterizedTest(name = "should correctly parse edge case class ''{0}'' (ID: {2})")
        @MethodSource("edgeCaseClassCases")
        void shouldCorrectlyParseEdgeCaseClass(String inputDsl, List<ClassItem> expectedItems, String id) {
            /**
             * Tests unusual but valid character class constructs.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(CharClass.class, ast);
            assertEquals(
                expectedItems.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList()),
                ((CharClass) ast).items.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList())
            );
        }
    }

    /**
     * Covers how character classes interact with other DSL features, specifically
     * the free-spacing mode flag.
     */
    @Nested
    class CategoryDInteractionCases {

        static Stream<Arguments> freeSpacingCases() {
            return Stream.of(
                Arguments.of("%flags x\n[a b]", Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral(" "), new ClassLiteral("b")
                ), "whitespace_is_literal"),
                Arguments.of("%flags x\n[a#b]", Arrays.asList(
                    new ClassLiteral("a"), new ClassLiteral("#"), new ClassLiteral("b")
                ), "comment_char_is_literal")
            );
        }

        @ParameterizedTest(name = "should handle free-spacing mode (ID: {2})")
        @MethodSource("freeSpacingCases")
        void shouldHandleInFreeSpacingMode(String inputDsl, List<ClassItem> expectedItems, String id) {
            /**
             * Tests that in free-spacing mode, whitespace and '#' are treated as
             * literal characters inside a class, per the specification.
             */
            Node ast = parseToAST(inputDsl);
            assertInstanceOf(CharClass.class, ast);
            assertEquals(
                expectedItems.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList()),
                ((CharClass) ast).items.stream().map(ClassItem::toDict).collect(java.util.stream.Collectors.toList())
            );
        }
    }

    /**
     * Tests for character classes with minimal content.
     */
    @Nested
    class CategoryEMinimalCharClasses {

        @Test
        void shouldParseSingleLiteralInClass() {
            /**
             * Tests character class with single literal: [a]
             */
            Node ast = parseToAST("[a]");
            assertInstanceOf(CharClass.class, ast);
            CharClass ccNode = (CharClass) ast;
            assertFalse(ccNode.negated);
            assertEquals(1, ccNode.items.size());
            assertInstanceOf(ClassLiteral.class, ccNode.items.get(0));
            assertEquals("a", ((ClassLiteral) ccNode.items.get(0)).ch);
        }

        @Test
        void shouldParseSingleLiteralNegatedClass() {
            /**
             * Tests negated class with single literal: [^x]
             */
            Node ast = parseToAST("[^x]");
            assertInstanceOf(CharClass.class, ast);
            CharClass ccNode = (CharClass) ast;
            assertTrue(ccNode.negated);
            assertEquals(1, ccNode.items.size());
            assertInstanceOf(ClassLiteral.class, ccNode.items.get(0));
            assertEquals("x", ((ClassLiteral) ccNode.items.get(0)).ch);
        }

        @Test
        void shouldParseSingleRangeInClass() {
            /**
             * Tests class with only a single range: [a-z]
             * Already exists but validating explicit simple case.
             */
            Node ast = parseToAST("[a-z]");
            assertInstanceOf(CharClass.class, ast);
            CharClass ccNode = (CharClass) ast;
            assertFalse(ccNode.negated);
            assertEquals(1, ccNode.items.size());
            assertInstanceOf(ClassRange.class, ccNode.items.get(0));
            assertEquals("a", ((ClassRange) ccNode.items.get(0)).fromCh);
            assertEquals("z", ((ClassRange) ccNode.items.get(0)).toCh);
        }
    }

    /**
     * Tests for escaped metacharacters inside character classes.
     */
    @Nested
    class CategoryFEscapedMetacharsInClasses {

        @Test
        void shouldParseEscapedDotInClass() {
            /**
             * Tests escaped dot in class: [\.]
             * The dot should be literal, not a wildcard.
             */
            Node ast = parseToAST("[\\.]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(1, ccNode.items.size());
            assertEquals("." , ((ClassLiteral) ccNode.items.get(0)).ch);
        }

        @Test
        void shouldParseEscapedStarInClass() {
            /**
             * Tests escaped star in class: [\*]
             */
            Node ast = parseToAST("[\\*]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(1, ccNode.items.size());
            assertEquals("*" , ((ClassLiteral) ccNode.items.get(0)).ch);
        }

        @Test
        void shouldParseEscapedPlusInClass() {
            /**
             * Tests escaped plus in class: [\+]
             */
            Node ast = parseToAST("[\\+]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(1, ccNode.items.size());
            assertEquals("+" , ((ClassLiteral) ccNode.items.get(0)).ch);
        }

        @Test
        void shouldParseMultipleEscapedMetachars() {
            /**
             * Tests multiple escaped metacharacters: [\.\*\+\?]
             */
            Node ast = parseToAST("[\\.\\*\\+\\?]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(4, ccNode.items.size());
            List<String> chars = ccNode.items.stream()
                .map(item -> ((ClassLiteral) item).ch)
                .collect(java.util.stream.Collectors.toList());
            assertEquals(Arrays.asList(".", "*", "+", "?"), chars);
        }

        @Test
        void shouldParseEscapedBackslashInClass() {
            /**
             * Tests escaped backslash in class: [\\]
             */
            Node ast = parseToAST("[\\\\]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(1, ccNode.items.size());
            assertEquals("\\" , ((ClassLiteral) ccNode.items.get(0)).ch);
        }
    }

    /**
     * Tests for character classes with complex range combinations.
     */
    @Nested
    class CategoryGComplexRangeCombinations {

        @Test
        void shouldParseMultipleNonOverlappingRanges() {
            /**
             * Tests multiple separate ranges: [a-zA-Z0-9]
             * Already covered but validating as typical case.
             */
            Node ast = parseToAST("[a-zA-Z0-9]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(3, ccNode.items.size());
            ClassRange range1 = (ClassRange) ccNode.items.get(0);
            assertEquals("a", range1.fromCh);
            assertEquals("z", range1.toCh);
            ClassRange range2 = (ClassRange) ccNode.items.get(1);
            assertEquals("A", range2.fromCh);
            assertEquals("Z", range2.toCh);
            ClassRange range3 = (ClassRange) ccNode.items.get(2);
            assertEquals("0", range3.fromCh);
            assertEquals("9", range3.toCh);
        }

        @Test
        void shouldParseRangeWithLiteralsMixed() {
            /**
             * Tests ranges mixed with literals: [a-z_0-9-]
             */
            Node ast = parseToAST("[a-z_0-9-]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(4, ccNode.items.size());
            assertInstanceOf(ClassRange.class, ccNode.items.get(0));
            assertEquals("z", ((ClassRange) ccNode.items.get(0)).toCh);
            assertInstanceOf(ClassLiteral.class, ccNode.items.get(1));
            assertEquals("_", ((ClassLiteral) ccNode.items.get(1)).ch);
            assertInstanceOf(ClassRange.class, ccNode.items.get(2));
            assertEquals("9", ((ClassRange) ccNode.items.get(2)).toCh);
            assertInstanceOf(ClassLiteral.class, ccNode.items.get(3));
            assertEquals("-", ((ClassLiteral) ccNode.items.get(3)).ch);
        }

        @Test
        void shouldParseAdjacentRanges() {
            /**
             * Tests adjacent character ranges: [a-z][A-Z]
             * Note: This is two separate classes, not one.
             */
            Node ast = parseToAST("[a-z][A-Z]");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size());

            assertInstanceOf(CharClass.class, seqNode.parts.get(0));
            assertInstanceOf(CharClass.class, seqNode.parts.get(1));
        }
    }

    /**
     * Tests for combinations of Unicode property escapes.
     */
    @Nested
    class CategoryHUnicodePropertyCombinations {

        @Test
        void shouldParseMultipleUnicodeProperties() {
            /**
             * Tests multiple Unicode properties in one class: [\p{L}\p{N}]
             */
            Node ast = parseToAST("[\\p{L}\\p{N}]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(2, ccNode.items.size());
            ClassEscape escape1 = (ClassEscape) ccNode.items.get(0);
            assertEquals("p", escape1.type);
            assertEquals("L", escape1.property);
            ClassEscape escape2 = (ClassEscape) ccNode.items.get(1);
            assertEquals("p", escape2.type);
            assertEquals("N", escape2.property);
        }

        @Test
        void shouldParseUnicodePropertyWithLiterals() {
            /**
             * Tests Unicode property mixed with literals: [\p{L}abc]
             */
            Node ast = parseToAST("[\\p{L}abc]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(4, ccNode.items.size());
            assertInstanceOf(ClassEscape.class, ccNode.items.get(0));
            assertInstanceOf(ClassLiteral.class, ccNode.items.get(1));
            assertEquals("a", ((ClassLiteral) ccNode.items.get(1)).ch);
        }

        @Test
        void shouldParseUnicodePropertyWithRange() {
            /**
             * Tests Unicode property mixed with range: [\p{L}0-9]
             */
            Node ast = parseToAST("[\\p{L}0-9]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(2, ccNode.items.size());
            assertInstanceOf(ClassEscape.class, ccNode.items.get(0));
            assertInstanceOf(ClassRange.class, ccNode.items.get(1));
            assertEquals("9", ((ClassRange) ccNode.items.get(1)).toCh);
        }

        @Test
        void shouldParseNegatedUnicodePropertyInClass() {
            /**
             * Tests negated Unicode property: [\P{L}]
             * Already exists but confirming coverage.
             */
            Node ast = parseToAST("[\\P{L}]");
            CharClass ccNode = (CharClass) ast;
            assertFalse(ccNode.negated); // Class itself is not negated
            assertEquals(1, ccNode.items.size());
            ClassEscape escape = (ClassEscape) ccNode.items.get(0);
            assertEquals("P", escape.type); // The property escape is negated
            assertEquals("L", escape.property);
        }
    }

    /**
     * Tests for negated character classes with various contents.
     */
    @Nested
    class CategoryINegatedClassVariations {

        @Test
        void shouldParseNegatedClassWithRange() {
            /**
             * Tests negated class with range: [^a-z]
             */
            Node ast = parseToAST("[^a-z]");
            CharClass ccNode = (CharClass) ast;
            assertTrue(ccNode.negated);
            assertEquals(1, ccNode.items.size());
            assertInstanceOf(ClassRange.class, ccNode.items.get(0));
        }

        @Test
        void shouldParseNegatedClassWithShorthand() {
            /**
             * Tests negated class with shorthand: [^\d\s]
             */
            Node ast = parseToAST("[^\\d\\s]");
            CharClass ccNode = (CharClass) ast;
            assertTrue(ccNode.negated);
            assertEquals(2, ccNode.items.size());
            assertInstanceOf(ClassEscape.class, ccNode.items.get(0));
            assertEquals("d", ((ClassEscape) ccNode.items.get(0)).type);
        }

        @Test
        void shouldParseNegatedClassWithUnicodeProperty() {
            /**
             * Tests negated class with Unicode property: [^\p{L}]
             */
            Node ast = parseToAST("[^\\p{L}]");
            CharClass ccNode = (CharClass) ast;
            assertTrue(ccNode.negated);
            assertEquals(1, ccNode.items.size());
            assertInstanceOf(ClassEscape.class, ccNode.items.get(0));
            assertEquals("p", ((ClassEscape) ccNode.items.get(0)).type);
        }
    }

    /**
     * Additional error cases for character classes.
     */
    @Nested
    class CategoryJCharClassErrorCases {

        @Test
        void shouldRaiseErrorForTrulyEmptyClass() {
            /**
             * Tests that [] without the special ] handling raises an error.
             * Note: []a] is valid (] is literal), but [] alone should error.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("[]"));
            assertTrue(e.getMessage().contains("Unterminated character class"));
        }

        @Test
        void shouldRejectReversedRange() {
            /**
             * Per IEH audit, reversed character ranges (e.g., [z-a]) are invalid
             * and should be reported as a parse error.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("[z-a]"));
            assertTrue(e.getMessage().contains("Invalid character range"));
        }

        @Test
        void shouldParseIncompleteRangeAtEndAsLiteral() {
            /**
             * Tests incomplete range at class end: [a-]
             * This is valid (hyphen is literal), confirm behavior.
             */
            Node ast = parseToAST("[a-]");
            CharClass ccNode = (CharClass) ast;
            assertEquals(2, ccNode.items.size());
            assertEquals("a", ((ClassLiteral) ccNode.items.get(0)).ch);
            assertEquals("-", ((ClassLiteral) ccNode.items.get(1)).ch);
        }
    }
}
