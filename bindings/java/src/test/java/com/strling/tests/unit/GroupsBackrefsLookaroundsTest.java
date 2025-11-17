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

    // =========================================================================
    // Category B: Negative Cases
    // =========================================================================

    static Stream<Arguments> negativeCases() {
        return Stream.of(
            Arguments.of("(a", "Unterminated group", 2),
            Arguments.of("(?<name", "Unterminated group name", 7),
            Arguments.of("(?=a", "Unterminated lookahead", 4),
            Arguments.of("\\k<A", "Unterminated named backref", 0),
            Arguments.of("\\k<A>(?<A>a)", "Backreference to undefined group <A>", 0),
            Arguments.of("\\2(a)(b)", "Backreference to undefined group \\2", 0),
            Arguments.of("(a)\\2", "Backreference to undefined group \\2", 3),
            Arguments.of("(?i)a", "Inline modifiers", 1)
        );
    }

    @ParameterizedTest
    @MethodSource("negativeCases")
    void testNegativeCases(String invalidDsl, String errorPrefix, int errorPos) {
        /** Tests that invalid syntax for groups and backrefs raises a ParseError */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> Parser.parse(invalidDsl));
        assertTrue(error.getMessage().contains(errorPrefix));
        assertEquals(errorPos, error.getPos());
    }

    // =========================================================================
    // Category C: Edge Cases
    // =========================================================================

    static Stream<Arguments> emptyGroups() {
        return Stream.of(
            Arguments.of("()", true, null),
            Arguments.of("(?:)", false, null),
            Arguments.of("(?<A>)", true, "A")
        );
    }

    @ParameterizedTest
    @MethodSource("emptyGroups")
    void testEmptyGroups(String inputDsl, boolean expectedCapturing, String expectedName) {
        /** Tests that empty groups parse into a Group node with an empty body */
        Parser.ParseResult r = Parser.parse(inputDsl);
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group groupNode = (Group) ast;
        assertEquals(expectedCapturing, groupNode.capturing);
        assertEquals(expectedName, groupNode.name);
        assertTrue(((Seq) groupNode.body).parts.isEmpty());
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

    // =========================================================================
    // Category E: Nested Groups
    // =========================================================================

    @Test
    void testNestedCapturingGroups() {
        /** Tests nested capturing groups: ((a)) */
        Parser.ParseResult r = Parser.parse("((a))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertTrue(group1.capturing);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertTrue(group2.capturing);
        assertInstanceOf(Lit.class, group2.body);
        assertEquals("a", ((Lit) group2.body).value);
    }

    @Test
    void testNestedNonCapturingGroups() {
        /** Tests nested non-capturing groups: (?:(?:a)) */
        Parser.ParseResult r = Parser.parse("(?:(?:a))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertFalse(group1.capturing);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertFalse(group2.capturing);
        assertInstanceOf(Lit.class, group2.body);
        assertEquals("a", ((Lit) group2.body).value);
    }

    @Test
    void testNestedAtomicGroups() {
        /** Tests nested atomic groups: (?>(?>(a))) */
        Parser.ParseResult r = Parser.parse("(?>(?>(a)))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertTrue(group1.atomic);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertTrue(group2.atomic);
        assertInstanceOf(Group.class, group2.body);
        Group group3 = (Group) group2.body;
        assertTrue(group3.capturing);
        assertInstanceOf(Lit.class, group3.body);
    }

    @Test
    void testCapturingInsideNonCapturing() {
        /** Tests capturing group inside non-capturing: (?:(a)) */
        Parser.ParseResult r = Parser.parse("(?:(a))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertFalse(group1.capturing);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertTrue(group2.capturing);
        assertInstanceOf(Lit.class, group2.body);
        assertEquals("a", ((Lit) group2.body).value);
    }

    @Test
    void testNamedGroupInsideCapturing() {
        /** Tests named group inside capturing: ((?<name>a)) */
        Parser.ParseResult r = Parser.parse("((?<name>a))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertTrue(group1.capturing);
        assertNull(group1.name);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertTrue(group2.capturing);
        assertEquals("name", group2.name);
        assertInstanceOf(Lit.class, group2.body);
    }

    @Test
    void testAtomicGroupInsideNonCapturing() {
        /** Tests atomic group inside non-capturing: (?:(?>a)) */
        Parser.ParseResult r = Parser.parse("(?:(?>a))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group group1 = (Group) ast;
        assertFalse(group1.capturing);
        assertInstanceOf(Group.class, group1.body);
        Group group2 = (Group) group1.body;
        assertTrue(group2.atomic);
        assertInstanceOf(Lit.class, group2.body);
        assertEquals("a", ((Lit) group2.body).value);
    }

    @Test
    void testDeeplyNestedGroups() {
        /** Tests deeply nested groups (3+ levels): ((?:(?<x>(?>a)))) */
        Parser.ParseResult r = Parser.parse("((?:(?<x>(?>a))))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group level1 = (Group) ast;
        assertTrue(level1.capturing);
        // Level 2
        assertInstanceOf(Group.class, level1.body);
        Group level2 = (Group) level1.body;
        assertFalse(level2.capturing);
        // Level 3
        assertInstanceOf(Group.class, level2.body);
        Group level3 = (Group) level2.body;
        assertTrue(level3.capturing);
        assertEquals("x", level3.name);
        // Level 4
        assertInstanceOf(Group.class, level3.body);
        Group level4 = (Group) level3.body;
        assertTrue(level4.atomic);
        assertInstanceOf(Lit.class, level4.body);
    }

    // =========================================================================
    // Category F: Lookaround With Complex Content
    // =========================================================================

    @Test
    void testLookaheadWithAlternation() {
        /** Tests positive lookahead with alternation: (?=a|b) */
        Parser.ParseResult r = Parser.parse("(?=a|b)");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look lookNode = (Look) ast;
        assertEquals("Ahead", lookNode.dir);
        assertFalse(lookNode.neg);
        assertInstanceOf(Alt.class, lookNode.body);
        assertEquals(2, ((Alt) lookNode.body).branches.size());
    }

    @Test
    void testLookbehindWithAlternation() {
        /** Tests positive lookbehind with alternation: (?<=x|y) */
        Parser.ParseResult r = Parser.parse("(?<=x|y)");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look lookNode = (Look) ast;
        assertEquals("Behind", lookNode.dir);
        assertFalse(lookNode.neg);
        assertInstanceOf(Alt.class, lookNode.body);
        assertEquals(2, ((Alt) lookNode.body).branches.size());
    }

    @Test
    void testNegativeLookaheadWithAlternation() {
        /** Tests negative lookahead with alternation: (?!a|b|c) */
        Parser.ParseResult r = Parser.parse("(?!a|b|c)");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look lookNode = (Look) ast;
        assertEquals("Ahead", lookNode.dir);
        assertTrue(lookNode.neg);
        assertInstanceOf(Alt.class, lookNode.body);
        assertEquals(3, ((Alt) lookNode.body).branches.size());
    }

    @Test
    void testNestedLookaheads() {
        /** Tests nested positive lookaheads: (?=(?=a)) */
        Parser.ParseResult r = Parser.parse("(?=(?=a))");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look outer = (Look) ast;
        assertEquals("Ahead", outer.dir);
        assertInstanceOf(Look.class, outer.body);
        Look inner = (Look) outer.body;
        assertEquals("Ahead", inner.dir);
        assertInstanceOf(Lit.class, inner.body);
    }

    @Test
    void testNestedLookbehinds() {
        /** Tests nested lookbehinds: (?<=(?<!a)) */
        Parser.ParseResult r = Parser.parse("(?<=(?<!a))");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look outer = (Look) ast;
        assertEquals("Behind", outer.dir);
        assertFalse(outer.neg);
        assertInstanceOf(Look.class, outer.body);
        Look inner = (Look) outer.body;
        assertEquals("Behind", inner.dir);
        assertTrue(inner.neg);
        assertInstanceOf(Lit.class, inner.body);
    }

    @Test
    void testMixedNestedLookarounds() {
        /** Tests lookahead inside lookbehind: (?<=a(?=b)) */
        Parser.ParseResult r = Parser.parse("(?<=a(?=b))");
        Node ast = r.ast;
        assertInstanceOf(Look.class, ast);
        Look lookNode = (Look) ast;
        assertEquals("Behind", lookNode.dir);
        assertInstanceOf(Seq.class, lookNode.body);
        Seq seqBody = (Seq) lookNode.body;
        assertEquals(2, seqBody.parts.size());
        assertInstanceOf(Lit.class, seqBody.parts.get(0));
        assertInstanceOf(Look.class, seqBody.parts.get(1));
        assertEquals("Ahead", ((Look) seqBody.parts.get(1)).dir);
    }

    // =========================================================================
    // Category G: Atomic Group Edge Cases
    // =========================================================================

    @Test
    void testAtomicGroupWithAlternation() {
        /** Tests atomic group with alternation: (?>(a|b)) */
        Parser.ParseResult r = Parser.parse("(?>(a|b))");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group atomicGroup = (Group) ast;
        assertTrue(atomicGroup.atomic);
        // The atomic group contains a capturing group with alternation
        assertInstanceOf(Group.class, atomicGroup.body);
        Group innerGroup = (Group) atomicGroup.body;
        assertTrue(innerGroup.capturing);
        assertInstanceOf(Alt.class, innerGroup.body);
        assertEquals(2, ((Alt) innerGroup.body).branches.size());
    }

    @Test
    void testAtomicGroupWithQuantifiedContent() {
        /** Tests atomic group with quantified atoms: (?>a+b*) */
        Parser.ParseResult r = Parser.parse("(?>a+b*)");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group atomicGroup = (Group) ast;
        assertTrue(atomicGroup.atomic);
        assertInstanceOf(Seq.class, atomicGroup.body);
        Seq seqBody = (Seq) atomicGroup.body;
        assertEquals(2, seqBody.parts.size());
        assertInstanceOf(Quant.class, seqBody.parts.get(0));
        assertInstanceOf(Quant.class, seqBody.parts.get(1));
    }

    @Test
    void testEmptyAtomicGroup() {
        /** Tests empty atomic group: (?>) */
        Parser.ParseResult r = Parser.parse("(?>)");
        Node ast = r.ast;
        assertInstanceOf(Group.class, ast);
        Group atomicGroup = (Group) ast;
        assertTrue(atomicGroup.atomic);
        assertInstanceOf(Seq.class, atomicGroup.body);
        assertEquals(0, ((Seq) atomicGroup.body).parts.size());
    }

    // =========================================================================
    // Category H: Multiple Backreferences
    // =========================================================================

    @Test
    void testMultipleNumericBackrefsSequential() {
        /** Tests multiple sequential backreferences: (a)(b)\1\2 */
        Parser.ParseResult r = Parser.parse("(a)(b)\\1\\2");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(4, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        assertInstanceOf(Group.class, seqNode.parts.get(1));
        assertInstanceOf(Backref.class, seqNode.parts.get(2));
        assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
        assertInstanceOf(Backref.class, seqNode.parts.get(3));
        assertEquals(Integer.valueOf(2), ((Backref) seqNode.parts.get(3)).byIndex);
    }

    @Test
    void testMultipleNamedBackrefs() {
        /** Tests multiple named backreferences: (?<x>a)(?<y>b)\k<x>\k<y> */
        Parser.ParseResult r = Parser.parse("(?<x>a)(?<y>b)\\k<x>\\k<y>");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(4, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        assertEquals("x", ((Group) seqNode.parts.get(0)).name);
        assertInstanceOf(Group.class, seqNode.parts.get(1));
        assertEquals("y", ((Group) seqNode.parts.get(1)).name);
        assertInstanceOf(Backref.class, seqNode.parts.get(2));
        assertEquals("x", ((Backref) seqNode.parts.get(2)).byName);
        assertInstanceOf(Backref.class, seqNode.parts.get(3));
        assertEquals("y", ((Backref) seqNode.parts.get(3)).byName);
    }

    @Test
    void testMixedNumericAndNamedBackrefs() {
        /** Tests mixed backreference types: (a)(?<x>b)\1\k<x> */
        Parser.ParseResult r = Parser.parse("(a)(?<x>b)\\1\\k<x>");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(4, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        assertInstanceOf(Group.class, seqNode.parts.get(1));
        assertEquals("x", ((Group) seqNode.parts.get(1)).name);
        assertInstanceOf(Backref.class, seqNode.parts.get(2));
        assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
        assertInstanceOf(Backref.class, seqNode.parts.get(3));
        assertEquals("x", ((Backref) seqNode.parts.get(3)).byName);
    }

    @Test
    void testBackrefInAlternation() {
        /** Tests backreference in alternation: (a)(\1|b) */
        Parser.ParseResult r = Parser.parse("(a)(\\1|b)");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(2, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        Group group2 = (Group) seqNode.parts.get(1);
        assertInstanceOf(Group.class, group2);
        assertInstanceOf(Alt.class, group2.body);
        Alt altBody = (Alt) group2.body;
        assertEquals(2, altBody.branches.size());
        assertInstanceOf(Backref.class, altBody.branches.get(0));
        assertEquals(Integer.valueOf(1), ((Backref) altBody.branches.get(0)).byIndex);
    }

    @Test
    void testBackrefToEarlierAlternationBranch() {
        /** Tests backreference to group in alternation: (a|b)c\1 */
        Parser.ParseResult r = Parser.parse("(a|b)c\\1");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        assertInstanceOf(Alt.class, ((Group) seqNode.parts.get(0)).body);
        assertInstanceOf(Lit.class, seqNode.parts.get(1));
        assertInstanceOf(Backref.class, seqNode.parts.get(2));
        assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
    }

    @Test
    void testRepeatedBackreference() {
        /** Tests same backreference used multiple times: (a)\1\1 */
        Parser.ParseResult r = Parser.parse("(a)\\1\\1");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq seqNode = (Seq) ast;
        assertEquals(3, seqNode.parts.size());
        assertInstanceOf(Group.class, seqNode.parts.get(0));
        assertInstanceOf(Backref.class, seqNode.parts.get(1));
        assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(1)).byIndex);
        assertInstanceOf(Backref.class, seqNode.parts.get(2));
        assertEquals(Integer.valueOf(1), ((Backref) seqNode.parts.get(2)).byIndex);
    }

    @Test
    void testDuplicateGroupNameRaisesError() {
        /** Tests that duplicate group names raise a semantic error */
        assertThrows(STRlingParseError.class, () -> Parser.parse("(?<a>x)(?<a>y)"));
        try {
            Parser.parse("(?<a>x)(?<a>y)");
            fail("Should have thrown STRlingParseError");
        } catch (STRlingParseError e) {
            assertTrue(e.getMessage().contains("Duplicate group name"));
        }
    }

    // =========================================================================
    // Category I: Groups In Alternation
    // =========================================================================

    @Test
    void testGroupsInAlternationBranches() {
        /** Tests capturing groups in alternation: (a)|(b) */
        Parser.ParseResult r = Parser.parse("(a)|(b)");
        Node ast = r.ast;
        assertInstanceOf(Alt.class, ast);
        Alt altNode = (Alt) ast;
        assertEquals(2, altNode.branches.size());
        assertInstanceOf(Group.class, altNode.branches.get(0));
        assertTrue(((Group) altNode.branches.get(0)).capturing);
        assertInstanceOf(Group.class, altNode.branches.get(1));
        assertTrue(((Group) altNode.branches.get(1)).capturing);
    }

    @Test
    void testLookaroundsInAlternation() {
        /** Tests lookarounds in alternation: (?=a)|(?=b) */
        Parser.ParseResult r = Parser.parse("(?=a)|(?=b)");
        Node ast = r.ast;
        assertInstanceOf(Alt.class, ast);
        Alt altNode = (Alt) ast;
        assertEquals(2, altNode.branches.size());
        assertInstanceOf(Look.class, altNode.branches.get(0));
        assertEquals("Ahead", ((Look) altNode.branches.get(0)).dir);
        assertInstanceOf(Look.class, altNode.branches.get(1));
        assertEquals("Ahead", ((Look) altNode.branches.get(1)).dir);
    }

    @Test
    void testMixedGroupTypesInAlternation() {
        /** Tests mixed group types in alternation: (a)|(?:b)|(?<x>c) */
        Parser.ParseResult r = Parser.parse("(a)|(?:b)|(?<x>c)");
        Node ast = r.ast;
        assertInstanceOf(Alt.class, ast);
        Alt altNode = (Alt) ast;
        assertEquals(3, altNode.branches.size());

        Group branch0 = (Group) altNode.branches.get(0);
        assertInstanceOf(Group.class, branch0);
        assertTrue(branch0.capturing);
        assertNull(branch0.name);

        Group branch1 = (Group) altNode.branches.get(1);
        assertInstanceOf(Group.class, branch1);
        assertFalse(branch1.capturing);

        Group branch2 = (Group) altNode.branches.get(2);
        assertInstanceOf(Group.class, branch2);
        assertTrue(branch2.capturing);
        assertEquals("x", branch2.name);
    }
}
