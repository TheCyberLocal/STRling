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
            Arguments.of("a", "a"),
            Arguments.of("_", "_"),
            Arguments.of("\\.", "."),
            Arguments.of("\\\\", "\\"),
            Arguments.of("\\n", "\n"),
            Arguments.of("\\t", "\t"),
            Arguments.of("\\x41", "A"),
            Arguments.of("\\x{41}", "A"),
            Arguments.of("\\u0041", "A"),
            Arguments.of("\\u{1f600}", "😀"),
            Arguments.of("\\U0001F600", "😀"),
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
            Arguments.of("\\x{12", "Unterminated \\x{...}", 0),
            Arguments.of("\\xG", "Invalid \\xHH escape", 0),
            Arguments.of("\\u{1F60", "Unterminated \\u{...}", 0),
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

    @Test
    void testOctalLikeBackreferenceErrorsAndDisambiguation() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\1"));
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
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\123"));
    }

    @Test
    void testCoalescingLiterals() {
        Parser.ParseResult r = Parser.parse("abc");
        Node ast = r.ast;
        assertInstanceOf(Lit.class, ast);
        assertEquals("abc", ((Lit) ast).value);

        Parser.ParseResult r2 = Parser.parse("a\\*b\\+c");
        Node ast2 = r2.ast;
        assertInstanceOf(Lit.class, ast2);
        assertEquals("a*b+c", ((Lit) ast2).value);
    }
}
