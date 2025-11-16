package com.strling.tests.unit;

import com.strling.core.Nodes.*;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

public class CharClassesTest {

    static Stream<Arguments> positiveCases() {
        return Stream.of(
            Arguments.of("[abc]", false, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c"))),
            Arguments.of("[^abc]", true, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c"))),
            Arguments.of("[a-z]", false, Collections.singletonList(new ClassRange("a", "z"))),
            Arguments.of("[A-Za-z0-9]", false, Arrays.asList(new ClassRange("A","Z"), new ClassRange("a","z"), new ClassRange("0","9"))),
            Arguments.of("[\\d\\s\\w]", false, Arrays.asList(new ClassEscape("d"), new ClassEscape("s"), new ClassEscape("w")))
        );
    }

    @ParameterizedTest
    @MethodSource("positiveCases")
    void testPositive(String input, boolean expectedNegated, List<ClassItem> expectedItems) {
        Parser.ParseResult res = Parser.parse(input);
        Node ast = res.ast;
        assertInstanceOf(com.strling.core.Nodes.CharClass.class, ast);
        com.strling.core.Nodes.CharClass cc = (com.strling.core.Nodes.CharClass) ast;
        assertEquals(expectedNegated, cc.negated);
        assertEquals(expectedItems.size(), cc.items.size());
        for (int i = 0; i < expectedItems.size(); i++) {
            ClassItem exp = expectedItems.get(i);
            ClassItem got = cc.items.get(i);
            if (exp instanceof ClassLiteral) {
                assertInstanceOf(ClassLiteral.class, got);
                assertEquals(((ClassLiteral) exp).ch, ((ClassLiteral) got).ch);
            } else if (exp instanceof ClassRange) {
                assertInstanceOf(ClassRange.class, got);
                assertEquals(((ClassRange) exp).fromCh, ((ClassRange) got).fromCh);
                assertEquals(((ClassRange) exp).toCh, ((ClassRange) got).toCh);
            } else if (exp instanceof ClassEscape) {
                assertInstanceOf(ClassEscape.class, got);
                assertEquals(((ClassEscape) exp).type, ((ClassEscape) got).type);
                assertEquals(((ClassEscape) exp).property, ((ClassEscape) got).property);
            }
        }
    }

    static Stream<Arguments> negativeCases() {
        return Stream.of(
            Arguments.of("[abc", "Unterminated character class", 4),
            Arguments.of("[", "Unterminated character class", 1),
            Arguments.of("[\\p{L", "Unterminated \\p{...}", 1),
            Arguments.of("[\\pL]", "Expected { after \\p/\\P", 1)
        );
    }

    @ParameterizedTest
    @MethodSource("negativeCases")
    void testNegative(String input, String msgPrefix, int pos) {
        STRlingParseError err = assertThrows(STRlingParseError.class, () -> Parser.parse(input));
        assertTrue(err.getMessage().contains(msgPrefix));
        assertEquals(pos, err.getPos());
    }

    @Test
    void testEscapedMetacharsInClass() {
        Parser.ParseResult res = Parser.parse("[\\.\\*\\+\\?]");
        Node ast = res.ast;
        assertInstanceOf(com.strling.core.Nodes.CharClass.class, ast);
        com.strling.core.Nodes.CharClass cc = (com.strling.core.Nodes.CharClass) ast;
        assertEquals(4, cc.items.size());
        assertTrue(cc.items.stream().allMatch(it -> it instanceof ClassLiteral));
    }
}
