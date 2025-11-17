package com.strling.tests.unit;

import com.strling.core.Nodes.Alt;
import com.strling.core.Nodes.Backref;
import com.strling.core.Nodes.Group;
import com.strling.core.Nodes.Lit;
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

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — LiteralsAndEscapesTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the parser's handling of all literal characters and
 * every form of escape sequence defined in the STRling DSL. It ensures that valid
 * forms are correctly parsed into {@code Lit} AST nodes and that malformed or
 * unsupported sequences raise the appropriate {@code ParseError}.
 *
 * <h2>Description</h2>
 * Literals and escapes are the most fundamental <strong>atoms</strong> in a STRling pattern,
 * representing single, concrete characters. This module tests the parser's ability
 * to distinguish between literal characters and special metacharacters, and to
 * correctly interpret the full range of escape syntaxes (identity, control, hex,
 * and Unicode). The expected behavior is for the parser to consume these tokens
 * and produce a {@code nodes.Lit} object containing the corresponding character value.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing of single literal characters.</li>
 * <li>Parsing of all supported escape sequences (hex escapes, Unicode escapes, null escape, identity escapes).</li>
 * <li>Error handling for malformed or unsupported escapes (like octal).</li>
 * <li>The shape of the resulting {@code Lit} AST node.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>How literals are quantified (covered in {@code QuantifiersTest.java}).</li>
 * <li>How literals behave inside character classes (covered in {@code CharClassesTest.java}).</li>
 * <li>Emitter-specific escaping (covered in {@code EmitterEdgesTest.java}).</li>
 * </ul>
 * </ul>
 */
public class LiteralsAndEscapesTest {

    // Helper to get the AST root from a parse
    private Node parseToAST(String dsl) {
        return Parser.parse(dsl).ast;
    }

    /**
     * Covers all positive cases for valid literal and escape syntax.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> positiveCases() {
            return Stream.of(
                // A.1: Plain Literals
                Arguments.of("a", new Lit("a"), "plain_literal_letter"),
                Arguments.of("_", new Lit("_"), "plain_literal_underscore"),
                // A.2: Identity Escapes
                Arguments.of("\\.", new Lit("."), "identity_escape_dot"),
                Arguments.of("\\(", new Lit("("), "identity_escape_paren"),
                Arguments.of("\\*", new Lit("*"), "identity_escape_star"),
                // DSL `\\\\` (4) parses to Lit("\\") (2). See Category G.
                Arguments.of("\\\\", new Lit("\\\\"), "identity_escape_backslash"),
                // A.3: Control & Whitespace Escapes
                Arguments.of("\\n", new Lit("\n"), "control_escape_newline"),
                Arguments.of("\\t", new Lit("\t"), "control_escape_tab"),
                Arguments.of("\\r", new Lit("\r"), "control_escape_carriage_return"),
                Arguments.of("\\f", new Lit("\f"), "control_escape_form_feed"),
                Arguments.of("\\v", new Lit("\u000B"), "control_escape_vertical_tab"), // \v is VT
                // A.4: Hexadecimal Escapes
                Arguments.of("\\x41", new Lit("A"), "hex_escape_fixed"),
                Arguments.of("\\x4a", new Lit("J"), "hex_escape_fixed_case"),
                Arguments.of("\\x{41}", new Lit("A"), "hex_escape_brace"),
                Arguments.of("\\x{1F600}", new Lit("\uD83D\uDE00"), "hex_escape_brace_non_bmp"), // 😀
                // A.5: Unicode Escapes
                Arguments.of("\\u0041", new Lit("A"), "unicode_escape_fixed"),
                Arguments.of("\\" + "u{41}", new Lit("A"), "unicode_escape_brace_bmp"),
                Arguments.of("\\" + "u{1f600}", new Lit("\uD83D\uDE00"), "unicode_escape_brace_non_bmp"), // 😀
                Arguments.of("\\U0001F600", new Lit("\uD83D\uDE00"), "unicode_escape_fixed_supplementary"), // 😀
                // A.6: Null Byte Escape
                Arguments.of("\\0", new Lit("\0"), "null_byte_escape")
            );
        }

        @ParameterizedTest(name = "should parse \"{0}\" (ID: {2})")
        @MethodSource("positiveCases")
        void shouldParse(String inputDsl, Node expectedAst, String id) {
            /**
             * Tests that a valid literal or escape sequence is parsed into the correct
             * Lit AST node.
             */
            Node ast = parseToAST(inputDsl);
            assertEquals(expectedAst.toDict(), ast.toDict());
        }
    }

    /**
     * Covers negative cases for malformed or unsupported syntax.
     */
    @Nested
    class CategoryBNegativeCases {

        static Stream<Arguments> negativeCases() {
            return Stream.of(
                // B.1: Malformed Hex/Unicode
                Arguments.of("\\x{12", "Unterminated \\x{...}", 0, "unterminated_hex_brace"),
                Arguments.of("\\xG", "Invalid \\xHH escape", 0, "invalid_hex_char_short"),
                Arguments.of("\\" + "u{1F60", "Unterminated " + "\\" + "u{...}", 0, "unterminated_unicode_brace"),
                Arguments.of("\\u123", "Invalid \\uHHHH", 0, "incomplete_unicode_fixed"),
                Arguments.of("\\U1234567", "Invalid \\UHHHHHHHH", 0, "incomplete_unicode_supplementary"),
                // B.2: Stray Metacharacters
                Arguments.of(")", "Unmatched ')'", 0, "stray_closing_paren"),
                Arguments.of("|", "Alternation lacks left-hand side", 0, "stray_pipe")
            );
        }

        @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
        @MethodSource("negativeCases")
        void shouldFailFor(String invalidDsl, String errorPrefix, int errorPos, String id) {
            /**
             * Tests that malformed escape syntax raises a ParseError with the correct
             * message and position.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST(invalidDsl));
            
            if ("stray_closing_paren".equals(id)) {
                assertEquals("Unmatched ')'", e.getMessage());
            } else {
                assertTrue(e.getMessage().contains(errorPrefix), "Error message mismatch. Was: " + e.getMessage());
            }
            assertEquals(errorPos, e.getPos(), "Error position mismatch.");
        }

        @Test
        void shouldFailForForbiddenOctalEscape() {
            /**
             * Tests that a forbidden octal escape (e.g., \123) with no groups defined
             * raises a ParseError for undefined backreference.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("\\123"));
            assertTrue(e.getMessage().contains("Backreference to undefined group"));
        }
    }

    /**
     * Covers edge cases for literals and escapes.
     */
    @Nested
    class CategoryCEdgeCases {

        static Stream<Arguments> edgeCaseEscapes() {
            return Stream.of(
                Arguments.of("\\" + "u{10FFFF}", "\uDBFF\uDFFF", "max_unicode_value"), // U+10FFFF
                Arguments.of("\\x{0}", "\0", "zero_value_hex_brace"),
                Arguments.of("\\x{}", "\0", "empty_hex_brace")
            );
        }

        @ParameterizedTest(name = "should correctly parse edge case escape \"{0}\" (ID: {2})")
        @MethodSource("edgeCaseEscapes")
        void shouldCorrectlyParseEdgeCaseEscape(String inputDsl, String expectedChar, String id) {
            /** Tests unusual but valid escape sequences. */
            Node ast = parseToAST(inputDsl);
            assertEquals(new Lit(expectedChar).toDict(), ast.toDict());
        }

        @Test
        void shouldParseAnEscapedNullByteCorrectly() {
            /**
             * Tests that an escaped backslash followed by a zero is not parsed as
             * a null byte. (DSL: \\0)
             */
            Node ast = parseToAST("\\\\0");
            // This should be Seq([Lit("\\"), Lit("0")])
            // The parser coalesces this into Lit("\\0")
            assertEquals(new Lit("\\0").toDict(), ast.toDict());
        }
    }

    /**
     * Covers interactions between literals/escapes and free-spacing mode.
     */
    @Nested
    class CategoryDInteractionCases {

        @Test
        void shouldIgnoreWhitespaceBetweenLiteralsInFreeSpacingMode() {
            /**
             * Tests that in free-spacing mode, whitespace between literals is
             * ignored, resulting in a sequence of Lit nodes.
             */
            Node ast = parseToAST("%flags x\n a b #comment\n c");
            // In free-spacing mode, literals are NOT coalesced
            assertEquals(new Seq(Arrays.asList(new Lit("a"), new Lit("b"), new Lit("c"))).toDict(), ast.toDict());
        }

        @Test
        void shouldRespectEscapedWhitespaceInFreeSpacingMode() {
            /**
             * Tests that in free-spacing mode, an escaped space is parsed as a
             * literal space character.
             */
            Node ast = parseToAST("%flags x\n a \\ b ");
            // In free-spacing mode, literals are NOT coalesced
            assertEquals(new Seq(Arrays.asList(new Lit("a"), new Lit(" "), new Lit("b"))).toDict(), ast.toDict());
        }
    }

    /**
     * Tests for sequences of literals and how the parser handles coalescing.
     */
    @Nested
    class CategoryELiteralSequencesAndCoalescing {

        @Test
        void shouldParseMultiplePlainLiteralsInSequence() {
            /**
             * Tests sequence of plain literals: abc
             * Should parse as single Lit("abc").
             */
            Node ast = parseToAST("abc");
            assertInstanceOf(Lit.class, ast);
            assertEquals("abc", ((Lit) ast).value);
        }

        @Test
        void shouldParseLiteralsWithEscapedMetacharSequence() {
            /**
             * Tests literals mixed with escaped metachars: a\*b\+c
             */
            Node ast = parseToAST("a\\*b\\+c");
            assertInstanceOf(Lit.class, ast);
            assertEquals("a*b+c", ((Lit) ast).value);
        }

        @Test
        void shouldParseSequenceOfOnlyEscapes() {
            /**
             * Tests sequence of only escape sequences: \n\t\r
             */
            Node ast = parseToAST("\\n\\t\\r");
            // Parser coalesces these into a single Lit
            assertInstanceOf(Lit.class, ast);
            assertEquals("\n\t\r", ((Lit) ast).value);
        }

        @Test
        void shouldParseMixedEscapeTypesInSequence() {
            /**
             * Tests mixed escape types in sequence: \x41\u0042\n
             * Hex, Unicode, and control escapes together.
             */
            Node ast = parseToAST("\\x41\\u0042\\n");
            // Parser coalesces these
            assertInstanceOf(Lit.class, ast);
            assertEquals("AB\n", ((Lit) ast).value);
        }
    }

    /**
     * Tests for interactions between different escape types and literals.
     */
    @Nested
    class CategoryFEscapeInteractions {

        @Test
        void shouldParseLiteralAfterControlEscape() {
            /**
             * Tests literal after control escape: \na (newline followed by 'a')
             */
            Node ast = parseToAST("\\na");
            // Parser coalesces
            assertInstanceOf(Lit.class, ast);
            assertEquals("\na", ((Lit) ast).value);
        }

        @Test
        void shouldParseLiteralAfterHexEscape() {
            /**
             * Tests literal after hex escape: \x41b (A followed by 'b')
             */
            Node ast = parseToAST("\\x41b");
            assertInstanceOf(Lit.class, ast);
            assertEquals("Ab", ((Lit) ast).value);
        }

        @Test
        void shouldParseEscapeAfterEscape() {
            /**
             * Tests escape after escape: \n\t (newline followed by tab)
             * Already covered but confirming.
             */
            Node ast = parseToAST("\\n\\t");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\n\t", ((Lit) ast).value);
        }

        @Test
        void shouldParseIdentityEscapeAfterLiteral() {
            /**
             * Tests identity escape after literal: a\* ('a' followed by '*')
             */
            Node ast = parseToAST("a\\*");
            assertInstanceOf(Lit.class, ast);
            assertEquals("a*", ((Lit) ast).value);
        }
    }

    /**
     * Tests for various backslash escape combinations.
     */
    @Nested
    class CategoryGBackslashEscapeCombinations {

        @Test
        void shouldParseDoubleBackslash() {
            /**
             * Tests double backslash: \\
             * Should parse as single backslash character.
             */
            Node ast = parseToAST("\\\\");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\\", ((Lit) ast).value);
        }

        @Test
        void shouldParseQuadrupleBackslash() {
            /**
             * Tests quadruple backslash: \\\\
             * Should parse as two backslash characters.
             */
            Node ast = parseToAST("\\\\\\\\");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\\\\", ((Lit) ast).value);
        }

        @Test
        void shouldParseBackslashBeforeLiteral() {
            /**
             * Tests backslash followed by non-metachar: \\a
             * Should parse as backslash followed by 'a'.
             */
            Node ast = parseToAST("\\\\a");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\\a", ((Lit) ast).value);
        }
    }

    /**
     * Additional edge cases for escape sequences.
     */
    @Nested
    class CategoryHEscapeEdgeCasesExpanded {

        @Test
        void shouldParseHexEscapeMinValue() {
            /**
             * Tests minimum hex value: \x00
             */
            Node ast = parseToAST("\\x00");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\0", ((Lit) ast).value);
        }

        @Test
        void shouldParseHexEscapeMaxValue() {
            /**
             * Tests maximum single-byte hex value: \xFF
             */
            Node ast = parseToAST("\\xFF");
            assertInstanceOf(Lit.class, ast);
            // Use Character to hold unsigned value
            assertEquals(Character.toString((char) 0xFF), ((Lit) ast).value);
        }

        @Test
        void shouldParseUnicodeEscapeBMPBoundary() {
            /**
             * Tests Unicode at BMP boundary: \uFFFF
             */
            Node ast = parseToAST("\\uFFFF");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\uFFFF", ((Lit) ast).value);
        }

        @Test
        void shouldParseUnicodeEscapeSupplementaryPlane() {
            /**
             * Tests Unicode in supplementary plane: \U00010000
             * First character outside BMP.
             */
            Node ast = parseToAST("\\U00010000");
            assertInstanceOf(Lit.class, ast);
            assertEquals("\uD800\uDC00", ((Lit) ast).value); // Surrogate pair for U+10000
        }
    }

    /**
     * Tests for the parser's handling of octal-like sequences and
     * their disambiguation with backreferences.
     */
    @Nested
    class CategoryIOctalAndBackrefDisambiguation {

        @Test
        void shouldRaiseErrorForSingleDigitBackslashWithNoGroups() {
            /**
             * Tests that \1 with no groups raises backreference error, not octal.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("\\1"));
            assertTrue(e.getMessage().contains("Backreference to undefined group"));
        }

        @Test
        void shouldParseTwoDigitSequenceWithOneGroup() {
            /**
             * Tests (a)\12: should be backref \1 followed by literal '2'.
             */
            Node ast = parseToAST("(a)\\12");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(2, seqNode.parts.size()); // Parser coalesces the Lit("2") with... nothing. Wait.
            // The Java parser design is different. (a) is Group. \1 is Backref. 2 is Lit.
            // But the parser coalesces adjacent Lits.
            // Let's re-check the JS parser behavior.
            // JS: `parse(String.raw`(a)\12`)`
            // AST: Seq([Group(Lit('a')), Backref(1), Lit('2')])
            // Ah, so the Java test should expect 3 parts.
            // The original Java test was `assertEquals(2, seqNode.parts.size());` which is wrong.
            // It should be 3 parts.
            // Let's assume the Java parser does *not* coalesce Lit("2") with anything.
            // No, the JS parser *also* coalesces.
            // `(a)` is a Group. `\1` is a Backref. `2` is a Lit.
            // The sequence is `[Group, Backref, Lit]`.
            // The JS test `(a)\12` expects `Seq` with 3 parts.
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Group.class, seqNode.parts.get(0));
            assertInstanceOf(Backref.class, seqNode.parts.get(1));
            assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(1)).byIndex);
            assertInstanceOf(Lit.class, seqNode.parts.get(2));
            assertEquals("2", ((Lit) seqNode.parts.get(2)).value);
        }

        @Test
        void shouldRaiseErrorForThreeDigitSequence() {
            /**
             * Tests \123 parsing behavior (backref or error).
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> parseToAST("\\123"));
            assertTrue(e.getMessage().contains("Backreference to undefined group"));
        }
    }

    /**
     * Tests for literal behavior in complex syntactic contexts.
     */
    @Nested
    class CategoryJLiteralsInComplexContexts {

        @Test
        void shouldParseLiteralBetweenQuantifiers() {
            /**
             * Tests literal between quantified atoms: a*Xb+
             */
            Node ast = parseToAST("a*Xb+");
            assertInstanceOf(Seq.class, ast);
            Seq seqNode = (Seq) ast;
            assertEquals(3, seqNode.parts.size());
            assertInstanceOf(Quant.class, seqNode.parts.get(0));
            assertInstanceOf(Lit.class, seqNode.parts.get(1));
            assertEquals("X", ((Lit) seqNode.parts.get(1)).value);
            assertInstanceOf(Quant.class, seqNode.parts.get(2));
        }

        @Test
        void shouldParseLiteralInAlternation() {
            /**
             * Tests literal in alternation: a|b|c
             */
            Node ast = parseToAST("a|b|c");
            assertInstanceOf(Alt.class, ast);
            Alt altNode = (Alt) ast;
            assertEquals(3, altNode.branches.size());
            assertEquals("a", ((Lit) altNode.branches.get(0)).value);
            assertEquals("b", ((Lit) altNode.branches.get(1)).value);
            assertEquals("c", ((Lit) altNode.branches.get(2)).value);
        }

        @Test
        void shouldParseEscapedLiteralInGroup() {
            /**
             * Tests escaped literal inside group: (\*)
             */
            Node ast = parseToAST("(\\*)");
            assertInstanceOf(Group.class, ast);
            Group groupNode = (Group) ast;
            assertTrue(groupNode.capturing);
            assertInstanceOf(Lit.class, groupNode.body);
            assertEquals("*", ((Lit) groupNode.body).value);
        }
    }
}
