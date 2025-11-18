package com.strling.tests.unit;

import com.strling.core.Nodes.CharClass;
import com.strling.core.Nodes.ClassItem;
import com.strling.core.Nodes.ClassLiteral;
import com.strling.core.Nodes.Flags;
import com.strling.core.Nodes.Lit;
import com.strling.core.Nodes.Node;
import com.strling.core.Nodes.Seq;
import com.strling.core.Parser;
import com.strling.core.Parser.ParseResult;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — FlagsAndFreeSpacingTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the correct parsing of the {@code %flags} directive and the
 * behavioral changes it induces, particularly the free-spacing ({@code x}) mode. It
 * ensures that flags are correctly identified and stored in the {@code Flags} object
 * and that the parser correctly handles whitespace and comments when the
 * extended mode is active.
 *
 * <h2>Description</h2>
 * The {@code %flags} directive is a top-level command in a {@code .strl} file that modifies
 * the semantics of the entire pattern. This suite tests the parser's ability to
 * correctly consume this directive and apply its effects. The primary focus is
 * on the <strong>{@code x} flag (extended/free-spacing mode)</strong>, which dramatically alters
 * how the parser handles whitespace and comments. The tests will verify that the
 * parser correctly ignores insignificant characters outside of character classes
 * while treating them as literals inside character classes.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>Parsing the {@code %flags} directive with single and multiple flags ({@code i},
 * {@code m}, {@code s}, {@code u}, {@code x}).</li>
 * <li>Handling of various separators (commas, spaces) within the flag
 * list.</li>
 * <li>The parser's behavior in free-spacing mode: ignoring whitespace and
 * comments outside character classes.</li>
 * <li>The parser's behavior inside a character class when free-spacing mode
 * is active (i.e., treating whitespace and {@code #} as literals).</li>
 * <li>The structure of the {@code Flags} object produced by the parser.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>The runtime <em>effect</em> of the {@code i}, {@code m}, {@code s}, and {@code u} flags on the regex
 * engine's matching behavior.</li>
 * <li>The parsing of other directives.</li>
 * </ul>
 * </ul>
 */
public class FlagsAndFreeSpacingTest {

    // Helper to create a Flags object for comparison
    private static Flags createFlags(boolean i, boolean m, boolean s, boolean u, boolean x) {
        Flags f = new Flags();
        f.ignoreCase = i;
        f.multiline = m;
        f.dotAll = s;
        f.unicode = u;
        f.extended = x;
        return f;
    }

    /**
     * Covers all positive cases for parsing flags and applying free-spacing mode.
     */
    @Nested
    class CategoryAPositiveCases {

        static Stream<Arguments> flagsDirectiveCases() {
            return Stream.of(
                Arguments.of("%flags i", createFlags(true, false, false, false, false), "single_flag"),
                Arguments.of("%flags i, m, x", createFlags(true, true, false, false, true), "multiple_flags_with_commas"),
                Arguments.of("%flags u m s", createFlags(false, true, true, true, false), "multiple_flags_with_spaces"),
                Arguments.of("%flags i,m s,u x", createFlags(true, true, true, true, true), "multiple_flags_mixed_separators"),
                Arguments.of("  %flags i  ", createFlags(true, false, false, false, false), "leading_trailing_whitespace")
            );
        }

        @ParameterizedTest(name = "should parse flag directive \"{0}\" correctly (ID: {2})")
        @MethodSource("flagsDirectiveCases")
        void shouldParseFlagDirectiveCorrectly(String inputDsl, Flags expectedFlags, String id) {
            /**
             * Tests that the %flags directive is correctly parsed into a Flags object.
             */
            ParseResult result = Parser.parse(inputDsl);
            assertEquals(expectedFlags.toDict(), result.flags.toDict());
        }

        static Stream<Arguments> freeSpacingCases() {
            return Stream.of(
                Arguments.of("%flags x\na b c",
                    new Seq(Arrays.asList(new Lit("a"), new Lit("b"), new Lit("c"))),
                    "whitespace_is_ignored"),
                Arguments.of("%flags x\na # comment\n b",
                    new Seq(Arrays.asList(new Lit("a"), new Lit("b"))),
                    "comments_are_ignored"),
                Arguments.of("%flags x\na\\ b",
                    new Seq(Arrays.asList(new Lit("a"), new Lit(" "), new Lit("b"))),
                    "escaped_whitespace_is_literal")
            );
        }

        @ParameterizedTest(name = "should handle free-spacing mode (ID: {2})")
        @MethodSource("freeSpacingCases")
        void shouldHandleFreeSpacingModeFor(String inputDsl, Seq expectedAst, String id) {
            /**
             * Tests that the parser correctly handles whitespace and comments when the
             * 'x' flag is active.
             */
            ParseResult result = Parser.parse(inputDsl);
            assertEquals(expectedAst.toDict(), result.ast.toDict());
        }
    }

    /**
     * Covers lenient handling of malformed or unknown directives.
     */
    @Nested
    class CategoryBNegativeCases {

        static Stream<Arguments> badDirectiveCases() {
            return Stream.of(
                Arguments.of("%flags z", "unknown_flag"),
                Arguments.of("%flagg i", "malformed_directive")
            );
        }

        @ParameterizedTest(name = "should reject bad directive \"{0}\" (ID: {1})")
        @MethodSource("badDirectiveCases")
        void shouldRejectBadDirective(String inputDsl, String id) {
            /**
             * IEH audit requires unknown flags to be rejected. Expect a parse error.
             */
            assertThrows(STRlingParseError.class, () -> Parser.parse(inputDsl));
        }
    }

    /**
     * Covers edge cases for flag parsing and free-spacing mode.
     */
    @Nested
    class CategoryCEdgeCases {

        @Test
        void shouldHandleAnEmptyFlagsDirective() {
            /** Tests that an empty %flags directive results in default flags. */
            ParseResult result = Parser.parse("%flags");
            // A default Flags object has all fields as false
            assertEquals(new Flags().toDict(), result.flags.toDict());
        }

        @Test
        void shouldRejectADirectiveThatAppearsAfterContent() {
            /**
             * IEH audit requires directives appearing after pattern content to be
             * rejected. Expect a parse error indicating the directive must appear
             * at the start of the pattern.
             */
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse("a\n%flags i"));
            assertTrue(e.getMessage().contains("Directive must appear at the start"));
        }

        @Test
        void shouldHandleAPatternWithOnlyCommentsAndWhitespace() {
            /**
             * Tests that a pattern which becomes empty in free-spacing mode results
             * in an empty AST.
             */
            ParseResult result = Parser.parse("%flags x\n# comment\n  \n# another");
            Node ast = result.ast;
            assertInstanceOf(Seq.class, ast);
            assertTrue(((Seq) ast).parts.isEmpty(), "AST should be an empty sequence");
        }
    }

    /**
     * Covers the critical interaction between free-spacing mode and character classes.
     */
    @Nested
    class CategoryDInteractionCases {

        static Stream<Arguments> charClassInteractionCases() {
            return Stream.of(
                Arguments.of("%flags x\n[a b]",
                    Arrays.asList(new ClassLiteral("a"), new ClassLiteral(" "), new ClassLiteral("b")),
                    "whitespace_is_literal_in_class"),
                Arguments.of("%flags x\n[a#b]",
                    Arrays.asList(new ClassLiteral("a"), new ClassLiteral("#"), new ClassLiteral("b")),
                    "comment_char_is_literal_in_class")
            );
        }

        @ParameterizedTest(name = "should disable free-spacing inside char class (ID: {2})")
        @MethodSource("charClassInteractionCases")
        void shouldDisableFreeSpacingInsideCharClassFor(String inputDsl, List<ClassItem> expectedItems, String id) {
            /**
             * Tests that in free-spacing mode, whitespace and '#' are treated as
             * literal characters inside a class, per the specification.
             */
            ParseResult result = Parser.parse(inputDsl);
            Node ast = result.ast;
            assertInstanceOf(CharClass.class, ast);
            CharClass ccNode = (CharClass) ast;

            // Compare list contents using toDict() for structural equality
            List<Object> expectedDicts = expectedItems.stream().map(ClassItem::toDict).collect(Collectors.toList());
            List<Object> actualDicts = ccNode.items.stream().map(ClassItem::toDict).collect(Collectors.toList());
            assertEquals(expectedDicts, actualDicts);
        }
    }
}
