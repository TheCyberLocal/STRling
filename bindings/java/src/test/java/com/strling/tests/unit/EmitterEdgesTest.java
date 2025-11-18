package com.strling.tests.unit;

import com.strling.core.Nodes.Flags;
import com.strling.core.IR.IRAlt;
import com.strling.core.IR.IRAnchor;
import com.strling.core.IR.IRBackref;
import com.strling.core.IR.IRCharClass;
import com.strling.core.IR.IRClassEscape;
import com.strling.core.IR.IRClassItem;
import com.strling.core.IR.IRClassLiteral;
import com.strling.core.IR.IRDot;
import com.strling.core.IR.IRGroup;
import com.strling.core.IR.IRLit;
import com.strling.core.IR.IROp;
import com.strling.core.IR.IRQuant;
import com.strling.core.IR.IRSeq;
import com.strling.emitters.Pcre2Emitter;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.List;
import java.util.Collections;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * @file Test Design — EmitterEdgesTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the logic of the PCRE2 emitter, focusing on its
 * specific responsibilities: correct character escaping, shorthand optimizations,
 * flag prefix generation, and the critical automatic-grouping logic required to
 * preserve operator precedence.
 *
 * <h2>Description</h2>
 * The emitter ({@code Pcre2Emitter.java}) is the final backend stage in the STRling compiler
 * pipeline. It translates the clean, language-agnostic Intermediate
 * Representation (IR) into a syntactically correct PCRE2 regex string. This suite
 * does not test the IR's correctness but verifies that a given valid IR tree is
 * always transformed into the correct and most efficient string representation,
 * with a heavy focus on edge cases where incorrect output could alter a pattern's
 * meaning.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>The emitter's character escaping logic, both for general literals and
 * within character classes.</li>
 * <li>Shorthand optimizations, such as converting {@code IRCharClass} nodes into
 * {@code \d} or {@code \P{Letter}} where appropriate.</li>
 * <li>The automatic insertion of non-capturing groups {@code (?:...)} to maintain
 * correct precedence.</li>
 * <li>Generation of the flag prefix {@code (?imsux)} based on the provided {@code Flags}
 * object.</li>
 * <li>Correct string generation for all PCRE2-supported extension features.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>The correctness of the input IR tree (this is covered by
 * {@code IRCompilerTest.java}).</li>
 * <li>The runtime behavior of the generated regex string in a live PCRE2
 * engine (this is covered by end-to-end and conformance tests).</li>
 * </ul>
 * </ul>
 */
public class EmitterEdgesTest {

    // --- Unit Tests for Emitter Helpers ---

    @Test
    void verifyHow_escapeLiteralHandlesDot() {
        // Expected: r'\.'
        assertEquals("\\.", Pcre2Emitter.escapeLiteral("."));
    }

    @Test
    void verifyHow_escapeLiteralHandlesBackslash() {
        // Expected: r'\\'
        assertEquals("\\\\", Pcre2Emitter.escapeLiteral("\\"));
    }

    @Test
    void verifyHow_escapeLiteralHandlesOpenBracket() {
        // Expected: r'\['
        assertEquals("\\[", Pcre2Emitter.escapeLiteral("["));
    }

    @Test
    void verifyHow_escapeLiteralHandlesOpenBrace() {
        // Expected: r'\{'
        assertEquals("\\{", Pcre2Emitter.escapeLiteral("{"));
    }

    @Test
    void verifyHow_escapeLiteralHandlesAPlainCharA() {
        // Expected: 'a'
        assertEquals("a", Pcre2Emitter.escapeLiteral("a"));
    }

    @Test
    void verifyHow_escapeClassCharHandlesCloseBracketInsideClass() {
        // Expected: \]
        assertEquals("\\]", Pcre2Emitter.escapeClassChar("]"));
    }

    @Test
    void verifyHow_escapeClassCharHandlesBackslashInsideClass() {
        // Expected: \\
        assertEquals("\\\\", Pcre2Emitter.escapeClassChar("\\"));
    }

    @Test
    void verifyHow_escapeClassCharHandlesHyphenInsideClass() {
        // Expected: \-
        assertEquals("\\-", Pcre2Emitter.escapeClassChar("-"));
    }

    @Test
    void verifyHow_escapeClassCharHandlesCaretInsideClass() {
        // Expected: \^
        assertEquals("\\^", Pcre2Emitter.escapeClassChar("^"));
    }

    @Test
    void verifyHow_escapeClassCharHandlesOpenBracketInsideClass() {
        // Expected: \[ (escaped for Java regex engine compatibility)
        // Java's regex engine requires [ to be escaped inside character classes
        assertEquals("\\[", Pcre2Emitter.escapeClassChar("["));
    }

    @Test
    void verifyHow_escapeClassCharHandlesDotInsideClass() {
        // Expected: . (unescaped)
        assertEquals(".", Pcre2Emitter.escapeClassChar("."));
    }

    @Test
    void verifyHow_escapeClassCharHandlesNewlineInsideClass() {
        // Expected: \n
        assertEquals("\\n", Pcre2Emitter.escapeClassChar("\n"));
    }

    // --- Test Suite (Categories) ---

    /**
     * Covers the emitter's character escaping logic.
     */
    @Nested
    class CategoryAEscapingLogic {

        @Test
        void shouldEscapeLiteralMetacharacters() {
            /**
             * Tests that all PCRE2 metacharacters are escaped when in an IRLit node.
             */
            String metachars = ".^$|()?*+{}[]\\";
            String expected = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";
            assertEquals(expected, Pcre2Emitter.emit(new IRLit(metachars)));
        }

        @Test
        void shouldEscapeCharClassMetacharacters() {
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
    }

    /**
     * Covers the emitter's logic for optimizing character classes.
     */
    @Nested
    class CategoryBShorthandOptimizations {

        static Stream<Arguments> shorthandOptimizationCases() {
            return Stream.of(
                Arguments.of(new IRCharClass(false, Arrays.asList(new IRClassEscape("d"))),
                    "\\d", "positive_d_to_shorthand"),
                Arguments.of(new IRCharClass(true, Arrays.asList(new IRClassEscape("d"))),
                    "\\D", "negated_d_to_D_shorthand"),
                Arguments.of(new IRCharClass(false, Arrays.asList(new IRClassEscape("p", "L"))),
                    "\\p{L}", "positive_p_to_shorthand"),
                Arguments.of(new IRCharClass(true, Arrays.asList(new IRClassEscape("p", "L"))),
                    "\\P{L}", "negated_p_to_P_shorthand"),
                Arguments.of(new IRCharClass(false, Arrays.asList(new IRClassEscape("S"))),
                    "\\S", "positive_neg_shorthand_S"),
                Arguments.of(new IRCharClass(true, Arrays.asList(new IRClassEscape("S"))),
                    "\\s", "negated_neg_shorthand_S_to_s")
            );
        }

        @ParameterizedTest(name = "should apply shorthand optimization for {2}")
        @MethodSource("shorthandOptimizationCases")
        void shouldApplyShorthandOptimization(IRCharClass irNode, String expectedStr, String id) {
            /**
             * Tests that single-item character classes are collapsed into their
             * shorthand equivalents.
             */
            assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
        }

        @Test
        void shouldNotApplyOptimizationForMultiItemClass() {
            /**
             * Tests that the shorthand optimization is correctly skipped for a class
             * with more than one item.
             */
            IRCharClass irNode = new IRCharClass(false, Arrays.asList(
                new IRClassEscape("d"),
                new IRClassLiteral("_")
            ));
            assertEquals("[\\d_]", Pcre2Emitter.emit(irNode));
        }
    }

    /**
     * Covers the critical logic for preserving operator precedence.
     */
    @Nested
    class CategoryCAutomaticGrouping {

        static Stream<Arguments> neededGroupingCases() {
            return Stream.of(
                Arguments.of(new IRQuant(new IRLit("ab"), 0, "Inf", "Greedy"),
                    "(?:ab)*", "quantified_multichar_literal"),
                Arguments.of(new IRQuant(new IRSeq(Arrays.asList(new IRLit("a"))), 1, "Inf", "Greedy"),
                    "a+", "quantified_single_item_sequence"),
                Arguments.of(new IRSeq(Arrays.asList(
                    new IRLit("a"),
                    new IRAlt(Arrays.asList(new IRLit("b"), new IRLit("c")))
                )), "a(?:b|c)", "alternation_in_sequence")
            );
        }

        @ParameterizedTest(name = "should add grouping when needed (ID: {2})")
        @MethodSource("neededGroupingCases")
        void shouldAddGroupingWhenNeeded(IROp irNode, String expectedStr, String id) {
            /**
             * Tests that non-capturing groups are added to preserve precedence.
             */
            assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
        }

        static Stream<Arguments> unnecessaryGroupingCases() {
            return Stream.of(
                Arguments.of(new IRQuant(
                    new IRCharClass(false, Arrays.asList(new IRClassLiteral("a"))), 0, "Inf", "Greedy"
                ), "[a]*", "quantified_char_class"),
                Arguments.of(new IRQuant(new IRDot(), 1, "Inf", "Greedy"),
                    ".+", "quantified_dot"),
                Arguments.of(new IRQuant(new IRGroup(true, new IRLit("a"), null), 0, 1, "Greedy"),
                    "(a)?", "quantified_group")
            );
        }

        @ParameterizedTest(name = "should not add unnecessary grouping (ID: {2})")
        @MethodSource("unnecessaryGroupingCases")
        void shouldNotAddUnnecessaryGrouping(IROp irNode, String expectedStr, String id) {
            /**
             * Tests that quantifiers on single atoms do not get extra grouping.
             */
            assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
        }
    }

    /**
     * Covers flag prefixes and other PCRE2-specific syntax.
     */
    @Nested
    class CategoryDFlagsAndEmitterDirectives {

        static Stream<Arguments> flagCases() {
            Flags im = new Flags();
            im.ignoreCase = true;
            im.multiline = true;

            Flags sux = new Flags();
            sux.dotAll = true;
            sux.unicode = true;
            sux.extended = true;

            return Stream.of(
                Arguments.of(im, "(?im)", "im_flags"),
                Arguments.of(sux, "(?sux)", "sux_flags"),
                Arguments.of(new Flags(), "", "default_flags"),
                Arguments.of(null, "", "no_flags_object")
            );
        }

        @ParameterizedTest(name = "should generate correct flag prefix for {2}")
        @MethodSource("flagCases")
        void shouldGenerateCorrectFlagPrefix(Flags flags, String expectedPrefix, String id) {
            /** Tests that the correct (?...) prefix is generated from a Flags object. */
            assertEquals(expectedPrefix + "a", Pcre2Emitter.emit(new IRLit("a"), flags));
        }

        @Test
        void shouldGeneratePCRE2SpecificNamedGroupAndBackrefSyntax() {
            /** Tests that PCRE2-specific named group syntax is generated. */
            IRSeq ir = new IRSeq(Arrays.asList(
                new IRGroup(true, new IRLit("a"), "x"),
                new IRBackref(null, "x")
            ));
            assertEquals("(?<x>a)\\k<x>", Pcre2Emitter.emit(ir));
        }
    }

    /**
     * Covers the emission of PCRE2 extension features.
     */
    @Nested
    class CategoryEExtensionFeatures {

        static Stream<Arguments> extensionFeatureCases() {
            return Stream.of(
                Arguments.of(new IRGroup(
                    false, new IRQuant(new IRLit("a"), 1, "Inf", "Greedy"), null, true
                ), "(?>a+)", "atomic_group"),
                Arguments.of(new IRQuant(new IRLit("a"), 0, "Inf", "Possessive"),
                    "a*+", "possessive_star"),
                Arguments.of(new IRQuant(new IRCharClass(false, Collections.emptyList()), 1, "Inf", "Possessive"),
                    "[]++", "possessive_plus"),
                Arguments.of(new IRAnchor("AbsoluteStart"),
                    "\\A", "absolute_start_anchor")
            );
        }

        @ParameterizedTest(name = "should emit extension feature correctly (ID: {2})")
        @MethodSource("extensionFeatureCases")
        void shouldEmitExtensionFeatureCorrectly(IROp irNode, String expectedStr, String id) {
            /**
             * Tests that extension features like atomic groups and possessive
             * quantifiers are emitted with the correct PCRE2 syntax.
             */
            assertEquals(expectedStr, Pcre2Emitter.emit(irNode));
        }
    }
}
