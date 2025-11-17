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
            // Star quantifiers
            Arguments.of("a*", 0, "Inf", "Greedy"),
            Arguments.of("a*?", 0, "Inf", "Lazy"),
            Arguments.of("a*+", 0, "Inf", "Possessive"),
            // Plus quantifiers
            Arguments.of("a+", 1, "Inf", "Greedy"),
            Arguments.of("a+?", 1, "Inf", "Lazy"),
            Arguments.of("a++", 1, "Inf", "Possessive"),
            // Optional quantifiers
            Arguments.of("a?", 0, 1, "Greedy"),
            Arguments.of("a??", 0, 1, "Lazy"),
            Arguments.of("a?+", 0, 1, "Possessive"),
            // Exact repetition
            Arguments.of("a{3}", 3, 3, "Greedy"),
            Arguments.of("a{3}?", 3, 3, "Lazy"),
            Arguments.of("a{3}+", 3, 3, "Possessive"),
            // At-least repetition
            Arguments.of("a{3,}", 3, "Inf", "Greedy"),
            Arguments.of("a{3,}?", 3, "Inf", "Lazy"),
            Arguments.of("a{3,}+", 3, "Inf", "Possessive"),
            // Range repetition
            Arguments.of("a{3,5}", 3, 5, "Greedy"),
            Arguments.of("a{3,5}?", 3, 5, "Lazy"),
            Arguments.of("a{3,5}+", 3, 5, "Possessive")
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

    // Category C: Edge Cases

    @Test
    void testZeroRepetition() {
        Parser.ParseResult r1 = Parser.parse("a{0}");
        Quant q1 = (Quant) r1.ast;
        assertEquals(0, q1.min);
        assertEquals(0, q1.max);
    }

    @Test
    void testQuantifierOnEmptyGroup() {
        Parser.ParseResult r2 = Parser.parse("(?:)*");
        Quant q2 = (Quant) r2.ast;
        assertInstanceOf(Group.class, q2.child);
        assertEquals(new java.util.ArrayList<>(), ((Seq) ((Group) q2.child).body).parts);
    }

    @Test
    void testZeroRangeQuantifier() {
        Parser.ParseResult r = Parser.parse("a{0,5}");
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals(5, q.max);
    }

    @Test
    void testAtLeastZeroQuantifier() {
        Parser.ParseResult r = Parser.parse("a{0,}");
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
    }

    @Test
    void testQuantifierVsAnchorPrecedence() {
        Parser.ParseResult r = Parser.parse("a?^");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Quant.class, s.parts.get(0));
        Quant q = (Quant) s.parts.get(0);
        assertInstanceOf(Lit.class, q.child);
        assertEquals("a", ((Lit) q.child).value);
        assertInstanceOf(Anchor.class, s.parts.get(1));
        assertEquals("Start", ((Anchor) s.parts.get(1)).at);
    }

    // Category D: Interaction

    @Test
    void testQuantifierPrecedence() {
        Parser.ParseResult r = Parser.parse("ab*");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertInstanceOf(Quant.class, s.parts.get(1));
    }

    @Test
    void testQuantifyShorthand() {
        Parser.ParseResult r1 = Parser.parse("\\d*");
        assertInstanceOf(Quant.class, r1.ast);
        assertInstanceOf(CharClass.class, ((Quant) r1.ast).child);
    }

    @Test
    void testQuantifyDot() {
        Parser.ParseResult r2 = Parser.parse(".*");
        assertInstanceOf(Quant.class, r2.ast);
        assertInstanceOf(Dot.class, ((Quant) r2.ast).child);
    }

    @Test
    void testQuantifyGroup() {
        Parser.ParseResult r3 = Parser.parse("(abc)*");
        assertInstanceOf(Quant.class, r3.ast);
        assertInstanceOf(Group.class, ((Quant) r3.ast).child);
    }

    @Test
    void testQuantifyCharClass() {
        Parser.ParseResult r = Parser.parse("[a-z]*");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertInstanceOf(CharClass.class, q.child);
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
    }

    @Test
    void testQuantifyAlternationInGroup() {
        Parser.ParseResult r = Parser.parse("(?:a|b)+");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(1, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Group.class, q.child);
        Group g = (Group) q.child;
        assertFalse(g.capturing);
        assertInstanceOf(Alt.class, g.body);
    }

    @Test
    void testQuantifyLookaround() {
        Parser.ParseResult r = Parser.parse("(?=a)+");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(1, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Look.class, q.child);
    }

    // Category E: Nested Quantifiers

    @Test
    void testNestedStarOnStar() {
        Parser.ParseResult r = Parser.parse("(a*)*");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Group.class, q.child);
        Group g = (Group) q.child;
        assertInstanceOf(Quant.class, g.body);
        Quant innerQ = (Quant) g.body;
        assertEquals(0, innerQ.min);
        assertEquals("Inf", innerQ.max);
    }

    @Test
    void testNestedPlusOnOptional() {
        Parser.ParseResult r = Parser.parse("(a+)?");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals(1, q.max);
        assertInstanceOf(Group.class, q.child);
        Group g = (Group) q.child;
        assertInstanceOf(Quant.class, g.body);
        Quant innerQ = (Quant) g.body;
        assertEquals(1, innerQ.min);
        assertEquals("Inf", innerQ.max);
    }

    @Test
    void testRedundantPlusOnStar() {
        Parser.ParseResult r = Parser.parse("(a*)+");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(1, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Group.class, q.child);
        assertInstanceOf(Quant.class, ((Group) q.child).body);
    }

    @Test
    void testRedundantStarOnOptional() {
        Parser.ParseResult r = Parser.parse("(a?)*");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Group.class, q.child);
        Group g = (Group) q.child;
        assertInstanceOf(Quant.class, g.body);
        Quant innerQ = (Quant) g.body;
        assertEquals(0, innerQ.min);
        assertEquals(1, innerQ.max);
    }

    @Test
    void testNestedBraceQuantifier() {
        Parser.ParseResult r = Parser.parse("(a{2,3}){1,2}");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(1, q.min);
        assertEquals(2, q.max);
        assertInstanceOf(Group.class, q.child);
        Group g = (Group) q.child;
        assertInstanceOf(Quant.class, g.body);
        Quant innerQ = (Quant) g.body;
        assertEquals(2, innerQ.min);
        assertEquals(3, innerQ.max);
    }

    // Category F: Quantifier On Special Atoms

    @Test
    void testQuantifierOnBackref() {
        Parser.ParseResult r = Parser.parse("(a)\\1*");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Group.class, s.parts.get(0));
        Quant q = (Quant) s.parts.get(1);
        assertInstanceOf(Quant.class, q);
        assertInstanceOf(Backref.class, q.child);
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
    }

    @Test
    void testQuantifierOnMultipleBackrefs() {
        Parser.ParseResult r = Parser.parse("(a)(b)\\1*\\2+");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(4, s.parts.size());

        Quant q1 = (Quant) s.parts.get(2);
        assertInstanceOf(Quant.class, q1);
        assertInstanceOf(Backref.class, q1.child);
        assertEquals(1, ((Backref) q1.child).byIndex);

        Quant q2 = (Quant) s.parts.get(3);
        assertInstanceOf(Quant.class, q2);
        assertInstanceOf(Backref.class, q2.child);
        assertEquals(2, ((Backref) q2.child).byIndex);
    }

    // Category G: Multiple Quantified Sequences

    @Test
    void testMultipleConsecutiveQuantifiedLiterals() {
        Parser.ParseResult r = Parser.parse("a*b+c?");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertTrue(s.parts.stream().allMatch(p -> p instanceof Quant));

        Quant q0 = (Quant) s.parts.get(0);
        assertEquals(0, q0.min);
        assertEquals("Inf", q0.max);

        Quant q1 = (Quant) s.parts.get(1);
        assertEquals(1, q1.min);
        assertEquals("Inf", q1.max);

        Quant q2 = (Quant) s.parts.get(2);
        assertEquals(0, q2.min);
        assertEquals(1, q2.max);
    }

    @Test
    void testMultipleQuantifiedGroups() {
        Parser.ParseResult r = Parser.parse("(ab)*(cd)+(ef)?");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(3, s.parts.size());
        assertTrue(s.parts.stream().allMatch(p -> p instanceof Quant));
        assertTrue(s.parts.stream().allMatch(p -> ((Quant) p).child instanceof Group));
    }

    @Test
    void testQuantifiedAtomsInAlternation() {
        Parser.ParseResult r = Parser.parse("a*|b+");
        Node ast = r.ast;
        assertInstanceOf(Alt.class, ast);
        Alt a = (Alt) ast;
        assertEquals(2, a.branches.size());

        Quant q0 = (Quant) a.branches.get(0);
        assertInstanceOf(Quant.class, q0);
        assertEquals(0, q0.min);

        Quant q1 = (Quant) a.branches.get(1);
        assertInstanceOf(Quant.class, q1);
        assertEquals(1, q1.min);
    }

    // Category H: Brace Quantifier Edge Cases

    @Test
    void testBraceExactOne() {
        Parser.ParseResult r = Parser.parse("a{1}");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(1, q.min);
        assertEquals(1, q.max);
        assertInstanceOf(Lit.class, q.child);
        assertEquals("a", ((Lit) q.child).value);
    }

    @Test
    void testBraceZeroToOne() {
        Parser.ParseResult r = Parser.parse("a{0,1}");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(0, q.min);
        assertEquals(1, q.max);
        assertInstanceOf(Lit.class, q.child);
    }

    @Test
    void testBraceOnAlternationInGroup() {
        Parser.ParseResult r = Parser.parse("(a|b){2,3}");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(2, q.min);
        assertEquals(3, q.max);
        assertInstanceOf(Group.class, q.child);
        assertInstanceOf(Alt.class, ((Group) q.child).body);
    }

    @Test
    void testBraceLargeValues() {
        Parser.ParseResult r = Parser.parse("a{100,200}");
        assertInstanceOf(Quant.class, r.ast);
        Quant q = (Quant) r.ast;
        assertEquals(100, q.min);
        assertEquals(200, q.max);
        assertInstanceOf(Lit.class, q.child);
    }

    // Category I: Quantifier Interaction With Flags

    @Test
    void testQuantifierWithFreeSpacingMode() {
        Parser.ParseResult r = Parser.parse("%flags x\na *");
        Node ast = r.ast;
        assertInstanceOf(Seq.class, ast);
        Seq s = (Seq) ast;
        assertEquals(2, s.parts.size());
        assertInstanceOf(Lit.class, s.parts.get(0));
        assertEquals("a", ((Lit) s.parts.get(0)).value);
        assertInstanceOf(Lit.class, s.parts.get(1));
        assertEquals("*", ((Lit) s.parts.get(1)).value);
    }

    @Test
    void testQuantifierOnEscapedSpaceInFreeSpacing() {
        Parser.ParseResult r = Parser.parse("%flags x\n\\ *");
        Node ast = r.ast;
        assertInstanceOf(Quant.class, ast);
        Quant q = (Quant) ast;
        assertEquals(0, q.min);
        assertEquals("Inf", q.max);
        assertInstanceOf(Lit.class, q.child);
        assertEquals(" ", ((Lit) q.child).value);
    }
}
