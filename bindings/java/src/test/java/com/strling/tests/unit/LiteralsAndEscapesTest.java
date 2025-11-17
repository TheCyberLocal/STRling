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

public class LiteralsAndEscapesTest {

    static Stream<Arguments> positiveLiterals() {
        return Stream.of(
            // Plain literals
            Arguments.of("a", "a"),
            Arguments.of("_", "_"),
            // Identity escapes
            Arguments.of("\\.", "."),
            Arguments.of("\\(", "("),
            Arguments.of("\\*", "*"),
            Arguments.of("\\\\", "\\"),
            Arguments.of("\\\\\\\\", "\\\\"),
            // Control & whitespace escapes
            Arguments.of("\\n", "\n"),
            Arguments.of("\\t", "\t"),
            Arguments.of("\\r", "\r"),
            Arguments.of("\\f", "\f"),
            Arguments.of("\\v", "\u000B"),
            // Hexadecimal escapes
            Arguments.of("\\x41", "A"),
            Arguments.of("\\x4a", "J"),
            Arguments.of("\\x{41}", "A"),
            Arguments.of("\\x{1F600}", "😀"),
            // Unicode escapes
            Arguments.of("\\u0041", "A"),
            Arguments.of("\\u{41}", "A"),
            Arguments.of("\\u{1f600}", "😀"),
            Arguments.of("\\U0001F600", "😀"),
            // Null byte escape
            Arguments.of("\\0", "\0")
        );
    }

    @ParameterizedTest
    @MethodSource("positiveLiterals")
    void testPositiveLiterals(String input, String expected) {
        Parser.ParseResult r = Parser.parse(input);
        Node ast = r.ast;
        if (ast instanceof Lit) {
            assertEquals(expected, ((Lit) ast).value);
        } else if (ast instanceof Seq) {
            // Some sequences may be returned; join and compare
            StringBuilder sb = new StringBuilder();
            for (Node part : ((Seq) ast).parts) {
                assertInstanceOf(Lit.class, part);
                sb.append(((Lit) part).value);
            }
            assertEquals(expected, sb.toString());
        } else {
            fail("Unexpected AST node type: " + ast.getClass().getName());
        }
    }

    static Stream<Arguments> negativeCases() {
        return Stream.of(
            // Malformed Hex/Unicode
            Arguments.of("\\x{12", "Unterminated \\x{...}", 0),
            Arguments.of("\\xG", "Invalid \\xHH escape", 0),
            Arguments.of("\\u{1F60", "Unterminated \\u{...}", 0),
            Arguments.of("\\u123", "Invalid \\uHHHH", 0),
            Arguments.of("\\U1234567", "Invalid \\UHHHHHHHH", 0),
            // Stray Metacharacters
            Arguments.of(")", "Unmatched ')'", 0),
            Arguments.of("|", "Alternation lacks left-hand side", 0)
        );
    }

    @ParameterizedTest
    @MethodSource("negativeCases")
    void testNegative(String input, String msgPrefix, int pos) {
        try {
            Parser.parse(input);
            fail("Expected parse to throw");
        } catch (STRlingParseError e) {
            if (msgPrefix.equals("Unmatched ')")) {
                assertEquals("Unmatched ')'", e.getMessage());
            } else {
                assertTrue(e.getMessage().contains(msgPrefix));
            }
            assertEquals(pos, e.getPos());
        }
    }

    // Category C: Edge Cases

    @Test
    void testMaxUnicodeValue() {
        Parser.ParseResult r = Parser.parse("\\u{10FFFF}");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\uDBFF\uDFFF", ((Lit) ast).value);
    }

    @Test
    void testZeroValueHexBrace() {
        Parser.ParseResult r = Parser.parse("\\x{0}");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\0", ((Lit) ast).value);
    }

    @Test
    void testEmptyHexBrace() {
        Parser.ParseResult r = Parser.parse("\\x{}");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\0", ((Lit) ast).value);
    }

    @Test
    void testEscapedNullByteNotParsedAsNull() {
        Parser.ParseResult r = Parser.parse("\\\\\\\\0");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertEquals("\\\\", ((Lit) s.parts.get(0)).value);
        assertInstanceOf(Lit.class, s.parts.get(1));
        assertEquals("0", ((Lit) s.parts.get(1)).value);
    }

    // Category D: Interaction Cases

    @Test
    void testIgnoreWhitespaceBetweenLiteralsInFreeSpacing() {
        Parser.ParseResult r = Parser.parse("%flags x\n a b #comment\n c");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertEquals("a", ((Lit) s.parts.get(0)).value);
        assertEquals("b", ((Lit) s.parts.get(1)).value);
        assertEquals("c", ((Lit) s.parts.get(2)).value);
    }

    @Test
    void testRespectEscapedWhitespaceInFreeSpacing() {
        Parser.ParseResult r = Parser.parse("%flags x\n a \\ b ");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertEquals("a", ((Lit) s.parts.get(0)).value);
        assertEquals(" ", ((Lit) s.parts.get(1)).value);
        assertEquals("b", ((Lit) s.parts.get(2)).value);
    }

    // Category E: Literal Sequences And Coalescing

    @Test
    void testMultiplePlainLiteralsInSequence() {
        Parser.ParseResult r = Parser.parse("abc");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("abc", ((Lit) ast).value);
    }

    @Test
    void testLiteralsWithEscapedMetacharSequence() {
        Parser.ParseResult r = Parser.parse("a\\*b\\+c");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("a*b+c", ((Lit) ast).value);
    }

    @Test
    void testSequenceOfOnlyEscapes() {
        Parser.ParseResult r = Parser.parse("\\n\\t\\r");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        for (Node part : s.parts) {
            assertInstanceOf(Lit.class, part);
        }
    }

    @Test
    void testMixedEscapeTypesInSequence() {
        Parser.ParseResult r = Parser.parse("\\x41\\u0042\\n");
        Node ast = r.ast;
        assertTrue(ast instanceof Seq || ast instanceof Lit);
        if (ast instanceof Seq) {
            for (Node part : ((Seq) ast).parts) {
                assertInstanceOf(Lit.class, part);
            }
        }
    }

    // Category F: Escape Interactions

    @Test
    void testLiteralAfterControlEscape() {
        Parser.ParseResult r = Parser.parse("\\na");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertEquals("\n", ((Lit) s.parts.get(0)).value);
        assertInstanceOf(Lit.class, s.parts.get(1));
        assertEquals("a", ((Lit) s.parts.get(1)).value);
    }

    @Test
    void testLiteralAfterHexEscape() {
        Parser.ParseResult r = Parser.parse("\\x41b");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("Ab", ((Lit) ast).value);
    }

    @Test
    void testEscapeAfterEscape() {
        Parser.ParseResult r = Parser.parse("\\n\\t");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        for (Node part : ((Seq) ast).parts) {
            assertInstanceOf(Lit.class, part);
        }
    }

    @Test
    void testIdentityEscapeAfterLiteral() {
        Parser.ParseResult r = Parser.parse("a\\*");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("a*", ((Lit) ast).value);
    }

    // Category G: Backslash Escape Combinations

    @Test
    void testDoubleBackslash() {
        Parser.ParseResult r = Parser.parse("\\\\");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\\", ((Lit) ast).value);
    }

    @Test
    void testQuadrupleBackslash() {
        Parser.ParseResult r = Parser.parse("\\\\\\\\");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\\\\", ((Lit) ast).value);
    }

    @Test
    void testBackslashBeforeLiteral() {
        Parser.ParseResult r = Parser.parse("\\\\a");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\\a", ((Lit) ast).value);
    }

    // Category H: Escape Edge Cases Expanded

    @Test
    void testHexEscapeMinValue() {
        Parser.ParseResult r = Parser.parse("\\x00");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\0", ((Lit) ast).value);
    }

    @Test
    void testHexEscapeMaxValue() {
        Parser.ParseResult r = Parser.parse("\\xFF");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\u00FF", ((Lit) ast).value);
    }

    @Test
    void testUnicodeEscapeBMPBoundary() {
        Parser.ParseResult r = Parser.parse("\\uFFFF");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\uFFFF", ((Lit) ast).value);
    }

    @Test
    void testUnicodeEscapeSupplementaryPlane() {
        Parser.ParseResult r = Parser.parse("\\U00010000");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("\uD800\uDC00", ((Lit) ast).value);
    }

    // Category I: Octal And Backref Disambiguation

    @Test
    void testSingleDigitBackslashWithNoGroups() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\1"));
        try {
            Parser.parse("\\1");
            fail("Expected parse to throw");
        } catch (STRlingParseError e) {
            assertTrue(e.getMessage().contains("Backreference to undefined group"));
        }
    }

    @Test
    void testTwoDigitSequenceWithOneGroup() {
        Parser.ParseResult r = Parser.parse("(a)\\12");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertInstanceOf(Group.class, s.parts.get(0));
        assertInstanceOf(Backref.class, s.parts.get(1));
        assertEquals(Integer.valueOf(1), ((Backref) s.parts.get(1)).byIndex);
        assertInstanceOf(Lit.class, s.parts.get(2));
        assertEquals("2", ((Lit) s.parts.get(2)).value);
    }

    @Test
    void testThreeDigitSequenceUndefinedBackref() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\123"));
        try {
            Parser.parse("\\123");
            fail("Expected parse to throw");
        } catch (STRlingParseError e) {
            assertTrue(e.getMessage().contains("Backreference to undefined group"));
        }
    }

    // Category J: Literals In Complex Contexts

    @Test
    void testLiteralBetweenQuantifiers() {
        Parser.ParseResult r = Parser.parse("a*Xb+");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertInstanceOf(Quant.class, s.parts.get(0));
        assertInstanceOf(Lit.class, s.parts.get(1));
        assertEquals("X", ((Lit) s.parts.get(1)).value);
        assertInstanceOf(Quant.class, s.parts.get(2));
    }

    @Test
    void testLiteralInAlternation() {
        Parser.ParseResult r = Parser.parse("a|b|c");
        Node ast = r.ast;
        assertInstanceOf(Alt.class, ast);
        Alt a = (Alt) ast;
        assertEquals(3, a.branches.size());
        assertInstanceOf(Lit.class, a.branches.get(0));
        assertEquals("a", ((Lit) a.branches.get(0)).value);
        assertInstanceOf(Lit.class, a.branches.get(1));
        assertEquals("b", ((Lit) a.branches.get(1)).value);
        assertInstanceOf(Lit.class, a.branches.get(2));
        assertEquals("c", ((Lit) a.branches.get(2)).value);
    }

    @Test
    void testEscapedLiteralInGroup() {
        Parser.ParseResult r = Parser.parse("(\\*)");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group g = (Group) ast;
        assertTrue(g.capturing);
        assertInstanceOf(Lit.class, g.body);
        assertEquals("*", ((Lit) g.body).value);
    }
}
