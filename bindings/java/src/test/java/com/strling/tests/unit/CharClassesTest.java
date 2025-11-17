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
            // Basic Classes
            Arguments.of("[abc]", false, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c"))),
            Arguments.of("[^abc]", true, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c"))),
            // Ranges
            Arguments.of("[a-z]", false, Collections.singletonList(new ClassRange("a", "z"))),
            Arguments.of("[A-Za-z0-9]", false, Arrays.asList(new ClassRange("A","Z"), new ClassRange("a","z"), new ClassRange("0","9"))),
            // Shorthand Escapes
            Arguments.of("[\\d\\s\\w]", false, Arrays.asList(new ClassEscape("d"), new ClassEscape("s"), new ClassEscape("w"))),
            Arguments.of("[\\D\\S\\W]", false, Arrays.asList(new ClassEscape("D"), new ClassEscape("S"), new ClassEscape("W"))),
            // Unicode Property Escapes
            Arguments.of("[\\p{L}]", false, Collections.singletonList(new ClassEscape("p", "L"))),
            Arguments.of("[\\p{Letter}]", false, Collections.singletonList(new ClassEscape("p", "Letter"))),
            Arguments.of("[\\P{Number}]", false, Collections.singletonList(new ClassEscape("P", "Number"))),
            Arguments.of("[\\p{Script=Greek}]", false, Collections.singletonList(new ClassEscape("p", "Script=Greek"))),
            // Special Character Handling
            Arguments.of("[]a]", false, Arrays.asList(new ClassLiteral("]"), new ClassLiteral("a"))),
            Arguments.of("[^]a]", true, Arrays.asList(new ClassLiteral("]"), new ClassLiteral("a"))),
            Arguments.of("[-az]", false, Arrays.asList(new ClassLiteral("-"), new ClassLiteral("a"), new ClassLiteral("z"))),
            Arguments.of("[az-]", false, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("z"), new ClassLiteral("-"))),
            Arguments.of("[a^b]", false, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("^"), new ClassLiteral("b"))),
            Arguments.of("[\\b]", false, Collections.singletonList(new ClassLiteral("\b"))),
            // Edge Cases
            Arguments.of("[a\\-c]", false, Arrays.asList(new ClassLiteral("a"), new ClassLiteral("-"), new ClassLiteral("c"))),
            Arguments.of("[\\x41-\\x5A]", false, Collections.singletonList(new ClassRange("A", "Z"))),
            Arguments.of("[\\n\\t\\d]", false, Arrays.asList(new ClassLiteral("\n"), new ClassLiteral("\t"), new ClassEscape("d"))),
            // Additional cases to reach parity
            Arguments.of("[0-9]", false, Collections.singletonList(new ClassRange("0", "9"))),
            Arguments.of("[\\d]", false, Collections.singletonList(new ClassEscape("d"))),
            Arguments.of("[\\w]", false, Collections.singletonList(new ClassEscape("w"))),
            Arguments.of("[\\s]", false, Collections.singletonList(new ClassEscape("s"))),
            Arguments.of("[a-zA-Z]", false, Arrays.asList(new ClassRange("a","z"), new ClassRange("A","Z"))),
            Arguments.of("[^\\d]", true, Collections.singletonList(new ClassEscape("d"))),
            Arguments.of("[^\\w]", true, Collections.singletonList(new ClassEscape("w"))),
            Arguments.of("[\\p{Nd}]", false, Collections.singletonList(new ClassEscape("p", "Nd"))),
            Arguments.of("[\\p{Lu}]", false, Collections.singletonList(new ClassEscape("p", "Lu"))),
            Arguments.of("[\\p{Ll}]", false, Collections.singletonList(new ClassEscape("p", "Ll"))),
            Arguments.of("[\\P{Lu}]", false, Collections.singletonList(new ClassEscape("P", "Lu"))),
            Arguments.of("[a-z0-9]", false, Arrays.asList(new ClassRange("a", "z"), new ClassRange("0", "9"))),
            Arguments.of("[!@#$]", false, Arrays.asList(new ClassLiteral("!"), new ClassLiteral("@"), new ClassLiteral("#"), new ClassLiteral("$"))),
            Arguments.of("[ \\t]", false, Arrays.asList(new ClassLiteral(" "), new ClassLiteral("\t"))),
            Arguments.of("[\\x20-\\x7E]", false, Collections.singletonList(new ClassRange(" ", "~"))),
            Arguments.of("[\\u0041-\\u005A]", false, Collections.singletonList(new ClassRange("A", "Z"))),
            Arguments.of("[a-f0-9A-F]", false, Arrays.asList(new ClassRange("a", "f"), new ClassRange("0", "9"), new ClassRange("A", "F"))),
            Arguments.of("[\\r\\n]", false, Arrays.asList(new ClassLiteral("\r"), new ClassLiteral("\n"))),
            Arguments.of("[\\.]", false, Collections.singletonList(new ClassLiteral("."))),
            Arguments.of("[\\*\\+\\?]", false, Arrays.asList(new ClassLiteral("*"), new ClassLiteral("+"), new ClassLiteral("?"))),
            Arguments.of("[()\\[\\]]", false, Arrays.asList(new ClassLiteral("("), new ClassLiteral(")"), new ClassLiteral("["), new ClassLiteral("]"))),
            Arguments.of("[{}|]", false, Arrays.asList(new ClassLiteral("{"), new ClassLiteral("}"), new ClassLiteral("|")))
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
            Arguments.of("[^", "Unterminated character class", 2),
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
