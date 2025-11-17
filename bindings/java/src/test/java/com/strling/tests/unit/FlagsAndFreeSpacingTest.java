package com.strling.tests.unit;

import com.strling.core.Nodes.*;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

public class FlagsAndFreeSpacingTest {

    static Stream<Arguments> flagsPositive() {
        return Stream.of(
            Arguments.of("%flags i", true, false, false, false, false),
            Arguments.of("%flags i, m, x", true, true, false, false, true),
            Arguments.of("%flags u m s", false, true, true, true, false),
            Arguments.of("%flags i,m s,u x", true, true, true, true, true),
            Arguments.of("  %flags i  ", true, false, false, false, false)
        );
    }

    @ParameterizedTest
    @MethodSource("flagsPositive")
    void testFlagsDirective(String input, boolean i, boolean m, boolean s, boolean u, boolean x) {
        Parser.ParseResult res = Parser.parse(input);
        Flags flags = res.flags;
        assertEquals(i, flags.ignoreCase);
        assertEquals(m, flags.multiline);
        assertEquals(s, flags.dotAll);
        assertEquals(u, flags.unicode);
        assertEquals(x, flags.extended);
    }

    @Test
    void testFreeSpacingIgnoresWhitespace() {
        Parser.ParseResult res = Parser.parse("%flags x\na b c");
        Node ast = res.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seq = (Seq) ast;
        assertEquals(3, seq.parts.size());
        assertEquals("a", ((Lit) seq.parts.get(0)).value);
        assertEquals("b", ((Lit) seq.parts.get(1)).value);
        assertEquals("c", ((Lit) seq.parts.get(2)).value);
    }

    @Test
    void testFreeSpacingIgnoresComments() {
        Parser.ParseResult res = Parser.parse("%flags x\na # comment\n b");
        Node ast = res.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seq = (Seq) ast;
        assertEquals(2, seq.parts.size());
        assertEquals("a", ((Lit) seq.parts.get(0)).value);
        assertEquals("b", ((Lit) seq.parts.get(1)).value);
    }

    @Test
    void testEscapedWhitespaceIsLiteral() {
        Parser.ParseResult res = Parser.parse("%flags x\na\\ b");
        Node ast = res.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seq = (Seq) ast;
        assertEquals(3, seq.parts.size());
        assertEquals("a", ((Lit) seq.parts.get(0)).value);
        assertEquals(" ", ((Lit) seq.parts.get(1)).value);
        assertEquals("b", ((Lit) seq.parts.get(2)).value);
    }

    @Test
    void testUnknownFlagRejected() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("%flags z"));
    }

    @Test
    void testMalformedDirectiveRejected() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("%flagg i"));
    }

    @Test
    void testEmptyFlagsDirective() {
        Parser.ParseResult res = Parser.parse("%flags");
        Flags flags = res.flags;
        assertFalse(flags.ignoreCase);
        assertFalse(flags.multiline);
        assertFalse(flags.dotAll);
        assertFalse(flags.unicode);
        assertFalse(flags.extended);
    }

    @Test
    void testDirectiveAfterContentRejected() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("a\n%flags i"));
    }

    @Test
    void testPatternWithOnlyCommentsBecomesEmptySeq() {
        Parser.ParseResult res = Parser.parse("%flags x\n# comment\n  \n# another");
        Node ast = res.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seq = (Seq) ast;
        assertEquals(0, seq.parts.size());
    }

    @Test
    void testWhitespaceLiteralInsideClassWhenX() {
        Parser.ParseResult res = Parser.parse("%flags x\n[a b]");
        Node ast = res.ast;
        assertInstanceOf(com.strling.core.Nodes.CharClass.class, ast);
        com.strling.core.Nodes.CharClass cc = (com.strling.core.Nodes.CharClass) ast;
        assertEquals(3, cc.items.size());
        assertEquals("a", ((ClassLiteral) cc.items.get(0)).ch);
        assertEquals(" ", ((ClassLiteral) cc.items.get(1)).ch);
        assertEquals("b", ((ClassLiteral) cc.items.get(2)).ch);
    }

    @Test
    void testCommentCharLiteralInsideClassWhenX() {
        Parser.ParseResult res = Parser.parse("%flags x\n[a#b]");
        Node ast = res.ast;
        assertInstanceOf(com.strling.core.Nodes.CharClass.class, ast);
        com.strling.core.Nodes.CharClass cc = (com.strling.core.Nodes.CharClass) ast;
        assertEquals(3, cc.items.size());
        assertEquals("a", ((ClassLiteral) cc.items.get(0)).ch);
        assertEquals("#", ((ClassLiteral) cc.items.get(1)).ch);
        assertEquals("b", ((ClassLiteral) cc.items.get(2)).ch);
    }
}
