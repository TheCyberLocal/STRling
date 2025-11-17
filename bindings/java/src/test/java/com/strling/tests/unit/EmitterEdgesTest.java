package com.strling.tests.unit;

import com.strling.emitters.Pcre2Emitter;
import com.strling.core.Nodes.Flags;
import com.strling.core.IR.*;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Test Design — unit/EmitterEdgesTest
 *
 * ## Purpose
 * This test suite validates the logic of the PCRE2 emitter, focusing on its
 * specific responsibilities: correct character escaping, shorthand optimizations,
 * flag prefix generation, and the critical automatic-grouping logic required to
 * preserve operator precedence.
 *
 * ## Description
 * The emitter (Pcre2Emitter) is the final backend stage in the STRling compiler
 * pipeline. It translates the clean, language-agnostic Intermediate
 * Representation (IR) into a syntactically correct PCRE2 regex string. This suite
 * does not test the IR's correctness but verifies that a given valid IR tree is
 * always transformed into the correct and most efficient string representation,
 * with a heavy focus on edge cases where incorrect output could alter a pattern's
 * meaning.
 *
 * ## Scope
 * -   **In scope:**
 * -   The emitter's character escaping logic, both for general literals and
 * within character classes.
 * -   Shorthand optimizations, such as converting IRCharClass nodes into
 * \d or \P{Letter} where appropriate.
 * -   The automatic insertion of non-capturing groups (?:...) to maintain
 * correct precedence.
 * -   Generation of the flag prefix (?imsux) based on the provided Flags
 * object.
 * -   Correct string generation for all PCRE2-supported extension features.
 *
 * -   **Out of scope:**
 * -   The correctness of the input IR tree (this is covered by CompilerTest).
 * -   The runtime behavior of the generated regex string in a live PCRE2
 * engine (this is covered by end-to-end and conformance tests).
 */
public class EmitterEdgesTest {
    
    // --- Unit Tests for Emitter Helpers ---
    
    @Test
    public void testEscapeLiteralDot() {
        // Expected: \.
        assertEquals("\\.", Pcre2Emitter.escapeLiteral("."));
    }
    
    @Test
    public void testEscapeLiteralBackslash() {
        // Expected: \\
        assertEquals("\\\\", Pcre2Emitter.escapeLiteral("\\"));
    }
    
    @Test
    public void testEscapeLiteralOpenBracket() {
        // Expected: \[
        assertEquals("\\[", Pcre2Emitter.escapeLiteral("["));
    }
    
    @Test
    public void testEscapeLiteralOpenBrace() {
        // Expected: \{
        assertEquals("\\{", Pcre2Emitter.escapeLiteral("{"));
    }
    
    @Test
    public void testEscapeLiteralPlainChar() {
        // Expected: a
        assertEquals("a", Pcre2Emitter.escapeLiteral("a"));
    }
    
    @Test
    public void testEscapeClassCharCloseBracket() {
        // Expected: \]
        assertEquals("\\]", Pcre2Emitter.escapeClassChar("]"));
    }
    
    @Test
    public void testEscapeClassCharBackslash() {
        // Expected: \\
        assertEquals("\\\\", Pcre2Emitter.escapeClassChar("\\"));
    }
    
    @Test
    public void testEscapeClassCharHyphen() {
        // Expected: \-
        assertEquals("\\-", Pcre2Emitter.escapeClassChar("-"));
    }
    
    @Test
    public void testEscapeClassCharCaret() {
        // Expected: \^
        assertEquals("\\^", Pcre2Emitter.escapeClassChar("^"));
    }
    
    @Test
    public void testEscapeClassCharOpenBracket() {
        // Expected: [ (unescaped)
        assertEquals("[", Pcre2Emitter.escapeClassChar("["));
    }
    
    @Test
    public void testEscapeClassCharDot() {
        // Expected: . (unescaped)
        assertEquals(".", Pcre2Emitter.escapeClassChar("."));
    }
    
    @Test
    public void testEscapeClassCharNewline() {
        // Expected: \n
        assertEquals("\\n", Pcre2Emitter.escapeClassChar("\n"));
    }
    
    // --- Category A: Escaping Logic ---
    
    @Test
    public void testEscapeLiteralMetacharacters() {
        /**
         * Tests that all PCRE2 metacharacters are escaped when in an IRLit node.
         */
        String metachars = ".^$|()?*+{}[]\\";
        String expected = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";
        assertEquals(expected, Pcre2Emitter.emit(new IRLit(metachars)));
    }
    
    @Test
    public void testEscapeCharClassMetacharacters() {
        /**
         * Tests that special characters inside a character class are escaped.
         */
        String metachars = "]-^";
        String expected = "[\\]\\-\\^]";
        List<IRClassItem> items = Arrays.asList(
            new IRClassLiteral("]"),
            new IRClassLiteral("-"),
            new IRClassLiteral("^")
        );
        assertEquals(expected, Pcre2Emitter.emit(new IRCharClass(false, items)));
    }
    
    // --- Category B: Shorthand Optimizations ---
    
    private static Stream<Arguments> shorthandOptimizationTestCases() {
        return Stream.of(
            Arguments.of(
                new IRCharClass(false, List.of(new IRClassEscape("d", null))),
                "\\d",
                "positive_d_to_shorthand"
            ),
            Arguments.of(
                new IRCharClass(true, List.of(new IRClassEscape("d", null))),
                "\\D",
                "negated_d_to_D_shorthand"
            ),
            Arguments.of(
                new IRCharClass(false, List.of(new IRClassEscape("p", "L"))),
                "\\p{L}",
                "positive_p_to_shorthand"
            ),
            Arguments.of(
                new IRCharClass(true, List.of(new IRClassEscape("p", "L"))),
                "\\P{L}",
                "negated_p_to_P_shorthand"
            ),
            Arguments.of(
                new IRCharClass(false, List.of(new IRClassEscape("S", null))),
                "\\S",
                "positive_neg_shorthand_S"
            ),
            Arguments.of(
                new IRCharClass(true, List.of(new IRClassEscape("S", null))),
                "\\s",
                "negated_neg_shorthand_S_to_s"
            )
        );
    }
    
    @ParameterizedTest(name = "{2}")
    @MethodSource("shorthandOptimizationTestCases")
    public void testShorthandOptimization(IRCharClass irNode, String expectedStr, String id) {
        /**
         * Tests that single-item character classes are collapsed into their
         * shorthand equivalents.
         */
        assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
    }
    
    @Test
    public void testNoOptimizationForMultiItemClass() {
        /**
         * Tests that the shorthand optimization is correctly skipped for a class
         * with more than one item.
         */
        IRCharClass irNode = new IRCharClass(false, Arrays.asList(
            new IRClassEscape("d", null),
            new IRClassLiteral("_")
        ));
        assertEquals("[\\d_]", Pcre2Emitter.emit(irNode));
    }
    
    // --- Category C: Automatic Grouping ---
    
    private static Stream<Arguments> groupingNeededTestCases() {
        return Stream.of(
            Arguments.of(
                new IRQuant(new IRLit("ab"), 0, "Inf", "Greedy"),
                "(?:ab)*",
                "quantified_multichar_literal"
            ),
            Arguments.of(
                new IRQuant(new IRSeq(List.of(new IRLit("a"))), 1, "Inf", "Greedy"),
                "a+",
                "quantified_single_item_sequence"
            ),
            Arguments.of(
                new IRSeq(Arrays.asList(
                    new IRLit("a"),
                    new IRAlt(Arrays.asList(new IRLit("b"), new IRLit("c")))
                )),
                "a(?:b|c)",
                "alternation_in_sequence"
            )
        );
    }
    
    @ParameterizedTest(name = "{2}")
    @MethodSource("groupingNeededTestCases")
    public void testGroupingWhenNeeded(IROp irNode, String expectedStr, String id) {
        /**
         * Tests that non-capturing groups are added to preserve precedence.
         */
        assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
    }
    
    private static Stream<Arguments> noGroupingNeededTestCases() {
        return Stream.of(
            Arguments.of(
                new IRQuant(
                    new IRCharClass(false, List.of(new IRClassLiteral("a"))),
                    0,
                    "Inf",
                    "Greedy"
                ),
                "[a]*",
                "quantified_char_class"
            ),
            Arguments.of(
                new IRQuant(new IRDot(), 1, "Inf", "Greedy"),
                ".+",
                "quantified_dot"
            ),
            Arguments.of(
                new IRQuant(new IRGroup(true, new IRLit("a"), null, false), 0, 1, "Greedy"),
                "(a)?",
                "quantified_group"
            )
        );
    }
    
    @ParameterizedTest(name = "{2}")
    @MethodSource("noGroupingNeededTestCases")
    public void testNoUnnecessaryGrouping(IROp irNode, String expectedStr, String id) {
        /**
         * Tests that quantifiers on single atoms do not get extra grouping.
         */
        assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
    }
    
    // --- Category D: Flags and Emitter Directives ---
    
    private static Stream<Arguments> flagsTestCases() {
        Flags flags1 = new Flags();
        flags1.ignoreCase = true;
        flags1.multiline = true;
        
        Flags flags2 = new Flags();
        flags2.dotAll = true;
        flags2.unicode = true;
        flags2.extended = true;
        
        return Stream.of(
            Arguments.of(
                flags1,
                "(?im)",
                "im_flags"
            ),
            Arguments.of(
                flags2,
                "(?sux)",
                "sux_flags"
            ),
            Arguments.of(
                new Flags(),
                "",
                "default_flags"
            ),
            Arguments.of(
                null,
                "",
                "no_flags_object"
            )
        );
    }
    
    @ParameterizedTest(name = "{2}")
    @MethodSource("flagsTestCases")
    public void testFlagPrefixGeneration(Flags flags, String expectedPrefix, String id) {
        /**
         * Tests that the correct (?...) prefix is generated from a Flags object.
         */
        assertEquals(expectedPrefix + "a", Pcre2Emitter.emit(new IRLit("a"), flags));
    }
    
    @Test
    public void testPcre2NamedGroupAndBackrefSyntax() {
        /**
         * Tests that PCRE2-specific named group syntax is generated.
         */
        IROp ir = new IRSeq(Arrays.asList(
            new IRGroup(true, new IRLit("a"), "x", false),
            new IRBackref(null, "x")
        ));
        assertEquals("(?<x>a)\\k<x>", Pcre2Emitter.emit(ir));
    }
    
    // --- Category E: Extension Features ---
    
    private static Stream<Arguments> extensionFeaturesTestCases() {
        return Stream.of(
            Arguments.of(
                new IRGroup(false, new IRQuant(new IRLit("a"), 1, "Inf", "Greedy"), null, true),
                "(?>a+)",
                "atomic_group"
            ),
            Arguments.of(
                new IRQuant(new IRLit("a"), 0, "Inf", "Possessive"),
                "a*+",
                "possessive_star"
            ),
            Arguments.of(
                new IRQuant(new IRCharClass(false, List.of()), 1, "Inf", "Possessive"),
                "[]++",
                "possessive_plus"
            ),
            Arguments.of(
                new IRAnchor("AbsoluteStart"),
                "\\A",
                "absolute_start_anchor"
            )
        );
    }
    
    @ParameterizedTest(name = "{2}")
    @MethodSource("extensionFeaturesTestCases")
    public void testExtensionFeatures(IROp irNode, String expectedStr, String id) {
        /**
         * Tests that extension features like atomic groups and possessive
         * quantifiers are emitted with the correct PCRE2 syntax.
         */
        assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
    }
}
