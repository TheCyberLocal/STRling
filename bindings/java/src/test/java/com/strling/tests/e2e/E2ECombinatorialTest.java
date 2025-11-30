package com.strling.tests.e2e;

import com.strling.core.Compiler;
import com.strling.core.IR.IROp;
import com.strling.core.Nodes.Flags;
import com.strling.core.Nodes.Node;
import com.strling.core.Parser;
import com.strling.emitters.Pcre2Emitter;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * @file Test Design — e2e/E2ECombinatorialTest.java
 *
 * <h2>Purpose</h2>
 * This test suite provides systematic combinatorial E2E validation to ensure that
 * different STRling features work correctly when combined. It follows a risk-based,
 * tiered approach to manage test complexity while achieving comprehensive coverage.
 *
 * <h2>Description</h2>
 * Unlike unit tests that test individual features in isolation, this suite tests
 * feature interactions using two strategies:
 * <ol>
 * <li><strong>Tier 1 (Pairwise):</strong> Tests all N=2 combinations of core features</li>
 * <li><strong>Tier 2 (Strategic Triplets):</strong> Tests N=3 combinations of high-risk features</li>
 * </ol>
 *
 * <p>The tests verify that the full compile pipeline (parse -&gt; compile -&gt; emit)
 * correctly handles feature interactions.</p>
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Pairwise (N=2) combinations of all core features</li>
 * <li>Strategic triplet (N=3) combinations of high-risk features</li>
 * <li>End-to-end validation from DSL to PCRE2 output</li>
 * <li>Detection of interaction bugs between features</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Exhaustive N³ or higher combinations</li>
 * <li>Runtime behavior validation (covered by conformance tests)</li>
 * <li>Individual feature testing (covered by unit tests)</li>
 * </ul>
 * </ul>
 */
public class E2ECombinatorialTest {

    // --- Helper Function --------------------------------------------------------

    /**
     * A helper to run the full DSL -> PCRE2 string pipeline.
     * This single helper is used by all nested test classes.
     */
    private String compileToPcre(String src) {
        Parser.ParseResult result = Parser.parse(src);
        Flags flags = result.flags;
        Node ast = result.ast;
        Compiler compiler = new Compiler();
        IROp irRoot = compiler.compile(ast);
        return Pcre2Emitter.emit(irRoot, flags);
    }

    // --- Tier 1: Pairwise Combinatorial Tests (N=2) -----------------------------

    /**
     * Tests all pairwise (N=2) combinations of core STRling features.
     */
    @Nested
    class Tier1PairwiseTests {

        /**
         * Flags + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class FlagsAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Flags + Literals
                    Arguments.of("flags_literals_case_insensitive", "%flags i\nhello", "(?i)hello"),
                    Arguments.of("flags_literals_free_spacing", "%flags x\na b c", "(?x)abc"),
                    // Flags + Character Classes
                    Arguments.of("flags_charclass_case_insensitive", "%flags i\n[a-z]+", "(?i)[a-z]+"),
                    Arguments.of("flags_charclass_unicode", "%flags u\n\\p{L}+", "(?u)\\p{L}+"),
                    // Flags + Anchors
                    Arguments.of("flags_anchor_multiline_start", "%flags m\n^start", "(?m)^start"),
                    Arguments.of("flags_anchor_multiline_end", "%flags m\nend$", "(?m)end$"),
                    // Flags + Quantifiers
                    Arguments.of("flags_quantifier_dotall", "%flags s\na*", "(?s)a*"),
                    Arguments.of("flags_quantifier_free_spacing", "%flags x\na{2,5}", "(?x)a{2,5}"),
                    // Flags + Groups
                    Arguments.of("flags_group_case_insensitive", "%flags i\n(hello)", "(?i)(hello)"),
                    Arguments.of("flags_group_named_free_spacing", "%flags x\n(?<name>\\d+)", "(?x)(?<name>\\d+)"),
                    // Flags + Lookarounds
                    Arguments.of("flags_lookahead_case_insensitive", "%flags i\n(?=test)", "(?i)(?=test)"),
                    Arguments.of("flags_lookbehind_multiline", "%flags m\n(?<=^foo)", "(?m)(?<=^foo)"),
                    // Flags + Alternation
                    Arguments.of("flags_alternation_case_insensitive", "%flags i\na|b|c", "(?i)a|b|c"),
                    Arguments.of("flags_alternation_free_spacing", "%flags x\nfoo | bar", "(?x)foo|bar"),
                    // Flags + Backreferences
                    Arguments.of("flags_backref_case_insensitive", "%flags i\n(\\w+)\\s+\\1", "(?i)(\\w+)\\s+\\1")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testFlagsCombinations(String id, String input, String expected) {
                /** Tests flags combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Literals + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class LiteralsAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Literals + Character Classes
                    Arguments.of("literals_charclass", "abc[xyz]", "abc[xyz]"),
                    Arguments.of("literals_charclass_mixed", "\\d\\d\\d-[0-9]", "\\d\\d\\d-[0-9]"),
                    // Literals + Anchors
                    Arguments.of("literals_anchor_start", "^hello", "^hello"),
                    Arguments.of("literals_anchor_end", "world$", "world$"),
                    Arguments.of("literals_anchor_word_boundary", "\\bhello\\b", "\\bhello\\b"),
                    // Literals + Quantifiers
                    Arguments.of("literals_quantifier_plus", "a+bc", "a+bc"),
                    Arguments.of("literals_quantifier_brace", "test\\d{3}", "test\\d{3}"),
                    // Literals + Groups
                    Arguments.of("literals_group_capturing", "hello(world)", "hello(world)"),
                    Arguments.of("literals_group_noncapturing", "test(?:group)", "test(?:group)"),
                    // Literals + Lookarounds
                    Arguments.of("literals_lookahead", "hello(?=world)", "hello(?=world)"),
                    Arguments.of("literals_lookbehind", "(?<=test)result", "(?<=test)result"),
                    // Literals + Alternation
                    Arguments.of("literals_alternation_words", "hello|world", "hello|world"),
                    Arguments.of("literals_alternation_chars", "a|b|c", "a|b|c"),
                    // Literals + Backreferences
                    Arguments.of("literals_backref", "(\\w+)=\\1", "(\\w+)=\\1")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testLiteralsCombinations(String id, String input, String expected) {
                /** Tests literals combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Character classes + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class CharClassesAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Character Classes + Anchors
                    Arguments.of("charclass_anchor_start", "^[a-z]+", "^[a-z]+"),
                    Arguments.of("charclass_anchor_end", "[0-9]+$", "[0-9]+$"),
                    // Character Classes + Quantifiers
                    Arguments.of("charclass_quantifier_star", "[a-z]*", "[a-z]*"),
                    Arguments.of("charclass_quantifier_brace", "[0-9]{2,4}", "[0-9]{2,4}"),
                    Arguments.of("charclass_quantifier_lazy", "\\w+?", "\\w+?"),
                    // Character Classes + Groups
                    Arguments.of("charclass_group_capturing", "([a-z]+)", "([a-z]+)"),
                    Arguments.of("charclass_group_noncapturing", "(?:[0-9]+)", "(?:[0-9]+)"),
                    // Character Classes + Lookarounds
                    Arguments.of("charclass_lookahead", "(?=[a-z])", "(?=[a-z])"),
                    Arguments.of("charclass_lookbehind", "(?<=\\d)", "(?<=\\d)"),
                    // Character Classes + Alternation
                    Arguments.of("charclass_alternation_classes", "[a-z]|[0-9]", "[a-z]|[0-9]"),
                    Arguments.of("charclass_alternation_shorthands", "\\w|\\s", "\\w|\\s"),
                    // Character Classes + Backreferences
                    Arguments.of("charclass_backref", "([a-z])\\1", "([a-z])\\1")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testCharClassesCombinations(String id, String input, String expected) {
                /** Tests character classes combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Anchors + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class AnchorsAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Anchors + Quantifiers
                    Arguments.of("anchor_quantifier_start", "^a+", "^a+"),
                    Arguments.of("anchor_quantifier_boundary", "\\b\\w+", "\\b\\w+"),
                    // Anchors + Groups
                    Arguments.of("anchor_group_start", "^(test)", "^(test)"),
                    Arguments.of("anchor_group_end", "(start)$", "(start)$"),
                    // Anchors + Lookarounds
                    Arguments.of("anchor_lookahead", "^(?=test)", "^(?=test)"),
                    Arguments.of("anchor_lookbehind", "(?<=^foo)", "(?<=^foo)"),
                    // Anchors + Alternation
                    Arguments.of("anchor_alternation", "^a|b$", "^a|b$"),
                    // Anchors + Backreferences
                    Arguments.of("anchor_backref", "^(\\w+)\\s+\\1$", "^(\\w+)\\s+\\1$")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testAnchorsCombinations(String id, String input, String expected) {
                /** Tests anchors combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Quantifiers + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class QuantifiersAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Quantifiers + Groups
                    Arguments.of("quantifier_group_capturing", "(abc)+", "(abc)+"),
                    Arguments.of("quantifier_group_noncapturing", "(?:test)*", "(?:test)*"),
                    Arguments.of("quantifier_group_named", "(?<name>\\d)+", "(?<name>\\d)+"),
                    // Quantifiers + Lookarounds
                    Arguments.of("quantifier_lookahead", "(?=a)+", "(?:(?=a))+"),
                    Arguments.of("quantifier_lookbehind", "test(?<=\\d)*", "test(?:(?<=\\d))*"),
                    // Quantifiers + Alternation
                    Arguments.of("quantifier_alternation_group", "(a|b)+", "(a|b)+"),
                    Arguments.of("quantifier_alternation_noncapturing", "(?:foo|bar)*", "(?:foo|bar)*"),
                    // Quantifiers + Backreferences
                    Arguments.of("quantifier_backref_repeated", "(\\w)\\1+", "(\\w)\\1+"),
                    Arguments.of("quantifier_backref_specific", "(\\d+)-\\1{2}", "(\\d+)-\\1{2}")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testQuantifiersCombinations(String id, String input, String expected) {
                /** Tests quantifiers combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Groups + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class GroupsAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Groups + Lookarounds
                    Arguments.of("group_lookahead_inside", "((?=test)abc)", "((?=test)abc)"),
                    Arguments.of("group_lookbehind_inside", "(?:(?<=\\d)result)", "(?:(?<=\\d)result)"),
                    // Groups + Alternation
                    Arguments.of("group_alternation_capturing", "(a|b|c)", "(a|b|c)"),
                    Arguments.of("group_alternation_noncapturing", "(?:foo|bar)", "(?:foo|bar)"),
                    // Groups + Backreferences
                    Arguments.of("group_backref_numbered", "(\\w+)\\s+\\1", "(\\w+)\\s+\\1"),
                    Arguments.of("group_backref_named", "(?<tag>\\w+)\\k<tag>", "(?<tag>\\w+)\\k<tag>")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testGroupsCombinations(String id, String input, String expected) {
                /** Tests groups combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Lookarounds + other features
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class LookaroundsAndOtherFeatures {
            Stream<Arguments> testCases() {
                return Stream.of(
                    // Lookarounds + Alternation
                    Arguments.of("lookahead_alternation", "(?=a|b)", "(?=a|b)"),
                    Arguments.of("lookbehind_alternation", "(?<=foo|bar)", "(?<=foo|bar)"),
                    // Lookarounds + Backreferences
                    Arguments.of("lookahead_backref", "(\\w+)(?=\\1)", "(\\w+)(?=\\1)")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testLookaroundsCombinations(String id, String input, String expected) {
                /** Tests lookarounds combined with each other core feature. */
                assertEquals(expected, compileToPcre(input));
            }
        }

        /**
         * Alternation + backreferences
         */
        @Nested
        @TestInstance(TestInstance.Lifecycle.PER_CLASS)
        class AlternationAndBackreferences {
            Stream<Arguments> testCases() {
                return Stream.of(
                    Arguments.of("alternation_backref", "(a)\\1|(b)\\2", "(a)\\1|(b)\\2")
                );
            }

            @ParameterizedTest(name = "{0}")
            @MethodSource("testCases")
            void testAlternationBackrefCombinations(String id, String input, String expected) {
                /** Tests alternation combined with backreferences. */
                assertEquals(expected, compileToPcre(input));
            }
        }
    }

    // --- Tier 2: Strategic Triplet Tests (N=3) ----------------------------------

    /**
     * Tests strategic triplet (N=3) combinations of high-risk features where
     * bugs are most likely to hide: Flags, Groups, Quantifiers, Lookarounds,
     * and Alternation.
     */
    @Nested
    @TestInstance(TestInstance.Lifecycle.PER_CLASS)
    class Tier2StrategicTripletTests {

        Stream<Arguments> strategicTriplets() {
            return Stream.of(
                // Flags + Groups + Quantifiers
                Arguments.of("flags_groups_quantifiers_case", "%flags i\n(hello)+", "(?i)(hello)+"),
                Arguments.of("flags_groups_quantifiers_spacing", "%flags x\n(?:a b)+", "(?x)(?:ab)+"),
                Arguments.of("flags_groups_quantifiers_named", "%flags i\n(?<name>\\w)+", "(?i)(?<name>\\w)+"),
                // Flags + Groups + Lookarounds
                Arguments.of("flags_groups_lookahead", "%flags i\n((?=test)result)", "(?i)((?=test)result)"),
                Arguments.of("flags_groups_lookbehind", "%flags m\n(?:(?<=^)start)", "(?m)(?:(?<=^)start)"),
                // Flags + Quantifiers + Lookarounds
                Arguments.of("flags_quantifiers_lookahead", "%flags i\n(?=test)+", "(?i)(?:(?=test))+"),
                Arguments.of("flags_quantifiers_lookbehind", "%flags s\n.*(?<=end)", "(?s).*(?<=end)"),
                // Flags + Alternation + Groups
                Arguments.of("flags_alternation_groups_case", "%flags i\n(a|b|c)", "(?i)(a|b|c)"),
                Arguments.of("flags_alternation_groups_spacing", "%flags x\n(?:foo | bar | baz)", "(?x)(?:foo|bar|baz)"),
                // Groups + Quantifiers + Lookarounds
                Arguments.of("groups_quantifiers_lookahead", "((?=\\d)\\w)+", "((?=\\d)\\w)+"),
                Arguments.of("groups_quantifiers_lookbehind", "(?:(?<=test)\\w+)*", "(?:(?<=test)\\w+)*"),
                // Groups + Quantifiers + Alternation
                Arguments.of("groups_quantifiers_alternation", "(a|b)+", "(a|b)+"),
                Arguments.of("groups_quantifiers_alternation_brace", "(?:foo|bar){2,5}", "(?:foo|bar){2,5}"),
                // Quantifiers + Lookarounds + Alternation
                Arguments.of("quantifiers_lookahead_alternation", "(?=a|b)+", "(?:(?=a|b))+"),
                Arguments.of("quantifiers_lookbehind_alternation", "(foo|bar)(?<=test)*", "(foo|bar)(?:(?<=test))*")
            );
        }

        @ParameterizedTest(name = "{0}")
        @MethodSource("strategicTriplets")
        void testStrategicTriplets(String id, String input, String expected) {
            /** Tests strategic triplets of high-risk feature interactions. */
            assertEquals(expected, compileToPcre(input));
        }
    }

    // --- Complex Nested Feature Tests -------------------------------------------

    /**
     * Tests complex nested combinations that are especially prone to bugs.
     */
    @Nested
    @TestInstance(TestInstance.Lifecycle.PER_CLASS)
    class ComplexNestedFeatureTests {

        Stream<Arguments> complexNestedFeatures() {
            return Stream.of(
                // Deeply nested groups with quantifiers
                Arguments.of("deeply_nested_quantifiers", "((a+)+)+", "((a+)+)+"),
                // Multiple lookarounds in sequence
                Arguments.of("multiple_lookarounds", "(?=test)(?!fail)result", "(?=test)(?!fail)result"),
                // Nested alternation with groups
                Arguments.of("nested_alternation", "(a|(b|c))", "(a|(b|c))"),
                // Quantified lookaround with backreference
                Arguments.of("quantified_lookaround_backref", "(\\w)(?=\\1)+", "(\\w)(?:(?=\\1))+"),
                // Complex free spacing with all features
                Arguments.of("complex_free_spacing", "%flags x\n(?<tag> \\w+ ) \\s* = \\s* (?<value> [^>]+ ) \\k<tag>",
                    "(?x)(?<tag>\\w+)\\s*=\\s*(?<value>[^>]+)\\k<tag>"),
                // Atomic group with quantifiers
                Arguments.of("atomic_group_quantifier", "(?>a+)b", "(?>a+)b"),
                // Possessive quantifiers in groups
                Arguments.of("possessive_in_group", "(a*+)b", "(a*+)b")
            );
        }

        @ParameterizedTest(name = "{0}")
        @MethodSource("complexNestedFeatures")
        void testComplexNestedFeatures(String id, String input, String expected) {
            /** Tests complex nested feature combinations. */
            assertEquals(expected, compileToPcre(input));
        }
    }
}