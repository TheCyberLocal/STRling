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

public class QuantifiersTest {

    static Stream<Arguments> quantifierCases() {
        return Stream.of(
            Arguments.of("a*", 0, "Inf", "Greedy"),
            Arguments.of("a*?", 0, "Inf", "Lazy"),
            Arguments.of("a*+", 0, "Inf", "Possessive"),
            Arguments.of("a+", 1, "Inf", "Greedy"),
            Arguments.of("a?", 0, 1, "Greedy"),
            Arguments.of("a{3}", 3, 3, "Greedy"),
            Arguments.of("a{3,}", 3, "Inf", "Greedy"),
            Arguments.of("a{3,5}", 3, 5, "Greedy")
        );
    }

    @ParameterizedTest
    @MethodSource("quantifierCases")
    void testQuantifiers(String input, int min, Object max, String mode) {
        Parser.ParseResult r = Parser.parse(input);
        Node ast = r.ast;
        assertInstanceOf(Quant.class, ast);
        Quant q = (Quant) ast;
        assertEquals(min, q.min);
        assertEquals(max, q.max);
        assertEquals(mode, q.mode);
        assertInstanceOf(Lit.class, q.child);
    }

    static Stream<Arguments> malformedBrace() {
        return Stream.of(
            Arguments.of("a{1", "Incomplete quantifier", 3),
            Arguments.of("a{1,", "Incomplete quantifier", 4)
        );
    }

    @ParameterizedTest
    @MethodSource("malformedBrace")
    void testMalformedBraceQuantifiers(String input, String msg, int pos) {
        STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse(input));
        assertTrue(e.getMessage().contains(msg));
        assertEquals(pos, e.getPos());
    }

    @Test
    void testMalformedBraceParsedAsLiteral() {
        Parser.ParseResult r = Parser.parse("a{,5}");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertEquals("a", ((Lit) s.parts.get(0)).value);
        assertEquals("{,5}", ((Lit) s.parts.get(1)).value);
    }

    @Test
    void testZeroRepetitionAndGroupQuantifiers() {
        Parser.ParseResult r1 = Parser.parse("a{0}");
        Quant q1 = (Quant) r1.ast;
        assertEquals(0, q1.min);
        assertEquals(0, q1.max);

        Parser.ParseResult r2 = Parser.parse("(?:)*");
        Quant q2 = (Quant) r2.ast;
        assertInstanceOf(Group.class, q2.child);
        assertEquals(new java.util.ArrayList<>(), ((Seq) ((Group) q2.child).body).parts);
    }

    @Test
    void testQuantifierPrecedenceAndAtomTypes() {
        Parser.ParseResult r = Parser.parse("ab*");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertInstanceOf(Quant.class, s.parts.get(1));

        Parser.ParseResult r2 = Parser.parse("(a*)*");
        assertInstanceOf(Quant.class, r2.ast);
    }

    @Test
    void testQuantifierOnVariousAtoms() {
        Parser.ParseResult r1 = Parser.parse("\\d*");
        assertInstanceOf(Quant.class, r1.ast);
        assertInstanceOf(CharClass.class, ((Quant) r1.ast).child);

        Parser.ParseResult r2 = Parser.parse(".*");
        assertInstanceOf(Quant.class, r2.ast);
        assertInstanceOf(Dot.class, ((Quant) r2.ast).child);

        Parser.ParseResult r3 = Parser.parse("(abc)*");
        assertInstanceOf(Quant.class, r3.ast);
        assertInstanceOf(Group.class, ((Quant) r3.ast).child);
    }

    @Test
    void testQuantifiersWithBackrefsAndFreeSpacing() {
        Parser.ParseResult r = Parser.parse("(a)\\1*");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertInstanceOf(Group.class, s.parts.get(0));
        assertInstanceOf(Quant.class, s.parts.get(1));
        assertInstanceOf(Backref.class, ((Quant) s.parts.get(1)).child);

        Parser.ParseResult r2 = Parser.parse("%flags x\na *");
        Node ast2 = r2.ast;
        assertInstanceOf(Seq.class, ast2);
        Seq s2 = (Seq) ast2;
        assertEquals(2, s2.parts.size());
        assertInstanceOf(Lit.class, s2.parts.get(0));
        assertEquals("*", ((Lit) s2.parts.get(1)).value);

        Parser.ParseResult r3 = Parser.parse("%flags x\\ *");
        Node ast3 = r3.ast;
        assertInstanceOf(Quant.class, ast3);
        Quant q3 = (Quant) ast3;
        assertEquals(0, q3.min);
        assertEquals("Inf", q3.max);
        assertInstanceOf(Lit.class, q3.child);
        assertEquals(" ", ((Lit) q3.child).value);
    }
}
