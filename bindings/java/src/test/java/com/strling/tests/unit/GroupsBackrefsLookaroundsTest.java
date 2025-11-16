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

public class GroupsBackrefsLookaroundsTest {

    static Stream<Arguments> groupTypes() {
        return Stream.of(
            Arguments.of("(a)", true, null, null),
            Arguments.of("(?:a)", false, null, null),
            Arguments.of("(?<name>a)", true, "name", null),
            Arguments.of("(?>a)", false, null, true)
        );
    }

    @ParameterizedTest
    @MethodSource("groupTypes")
    void testGroupTypes(String input, boolean capturing, String name, Boolean atomic) {
        Parser.ParseResult res = Parser.parse(input);
        Node ast = res.ast;
        assertInstanceOf(Group.class, ast);
        Group g = (Group) ast;
        assertEquals(capturing, g.capturing);
        assertEquals(name, g.name);
        assertEquals(atomic, g.atomic);
        assertTrue(g.body instanceof Lit);
    }

    @Test
    void testNumericAndNamedBackrefs() {
        Parser.ParseResult r1 = Parser.parse("(a)\\1");
        Node ast1 = r1.ast;
        assertInstanceOf(Seq.class, ast1);
        Seq s1 = (Seq) ast1;
        assertInstanceOf(Backref.class, s1.parts.get(1));
        assertEquals(Integer.valueOf(1), ((Backref) s1.parts.get(1)).byIndex);

        Parser.ParseResult r2 = Parser.parse("(?<A>a)\\k<A>");
        Node ast2 = r2.ast;
        assertInstanceOf(Seq.class, ast2);
        Seq s2 = (Seq) ast2;
        assertInstanceOf(Backref.class, s2.parts.get(1));
        assertEquals("A", ((Backref) s2.parts.get(1)).byName);
    }

    static Stream<Arguments> lookarounds() {
        return Stream.of(
            Arguments.of("a(?=b)", "Ahead", false),
            Arguments.of("a(?!b)", "Ahead", true),
            Arguments.of("(?<=a)b", "Behind", false),
            Arguments.of("(?<!a)b", "Behind", true)
        );
    }

    @ParameterizedTest
    @MethodSource("lookarounds")
    void testLookarounds(String input, String dir, boolean neg) {
        Parser.ParseResult r = Parser.parse(input);
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        Look l;
        if (dir.equals("Ahead")) {
            l = (Look) s.parts.get(1);
        } else {
            l = (Look) s.parts.get(0);
        }
        assertEquals(dir, l.dir);
        assertEquals(neg, l.neg);
    }

    @Test
    void testUnterminatedAndInvalidBackrefs() {
        assertThrows(STRlingParseError.class, () -> Parser.parse("(a"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("(?<name"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("(?=a"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\k<A"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\k<A>(?<A>a)"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("\\2(a)(b)"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("(a)\\2"));
        assertThrows(STRlingParseError.class, () -> Parser.parse("(?i)a"));
    }

    @Test
    void testEmptyGroupsEdgeCases() {
        Parser.ParseResult r1 = Parser.parse("()");
        Node a1 = r1.ast;
        assertInstanceOf(Group.class, a1);
        Group g1 = (Group) a1;
        assertTrue(g1.capturing);
        assertEquals(new java.util.ArrayList<>(), ((Seq) g1.body).parts);

        Parser.ParseResult r2 = Parser.parse("(?:)");
        Group g2 = (Group) r2.ast;
        assertFalse(g2.capturing);

        Parser.ParseResult r3 = Parser.parse("(?<A>)");
        Group g3 = (Group) r3.ast;
        assertTrue(g3.capturing);
        assertEquals("A", g3.name);
        assertTrue(((Seq) g3.body).parts.isEmpty());
    }

    @Test
    void testBackrefToOptionalGroupAndNullByte() {
        Parser.ParseResult r = Parser.parse("(a)?\\1");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertInstanceOf(Quant.class, s.parts.get(0));
        assertInstanceOf(Backref.class, s.parts.get(1));

        Parser.ParseResult r2 = Parser.parse("\\0");
        Node n2 = r2.ast;
        assertInstanceOf(Lit.class, n2);
        assertEquals("\0", ((Lit) n2).value);
    }

    @Test
    void testBackrefInsideLookaroundAndFreeSpacingInGroups() {
        Parser.ParseResult r = Parser.parse("(?<A>a)(?=\\k<A>)");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertInstanceOf(Group.class, s.parts.get(0));
        Look look = (Look) s.parts.get(1);
        assertInstanceOf(Backref.class, look.body);
        assertEquals("A", ((Backref) look.body).byName);

        Parser.ParseResult r2 = Parser.parse("%flags x\n(?<name> a #comment\n b)");
        Node ast2 = r2.ast;
        assertInstanceOf(Group.class, ast2);
        Group g = (Group) ast2;
        assertEquals("name", g.name);
        assertInstanceOf(Seq.class, g.body);
        Seq body = (Seq) g.body;
        assertEquals(2, body.parts.size());
        assertEquals("a", ((Lit) body.parts.get(0)).value);
        assertEquals("b", ((Lit) body.parts.get(1)).value);
    }
}
