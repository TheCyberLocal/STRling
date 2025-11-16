package com.strling.tests.unit;

import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Design — ErrorsTest.java
 *
 * <h2>Purpose</h2>
 * This test suite serves as the single source of truth for defining and
 * validating the error-handling contract of the entire STRling pipeline. It
 * ensures that invalid inputs are rejected predictably and that diagnostics are
 * stable, accurate, and helpful across all stages—from the parser to the CLI.
 *
 * <h2>Description</h2>
 * This suite defines the expected behavior for all invalid, malformed, or
 * unsupported inputs. It verifies that errors are raised at the correct stage
 * (e.g., {@code ParseError}), contain a clear, human-readable message, and provide an
 * accurate source location. A key invariant tested is the "first error wins"
 * policy: for an input with multiple issues, only the error at the earliest
 * position is reported.
 *
 * <h2>Scope</h2>
 * <ul>
 *   <li><strong>In scope:</strong></li>
 *   <ul>
 *     <li>{@code ParseError} exceptions raised by the parser for syntactic and lexical issues.</li>
 *     <li>{@code ValidationError} (or equivalent semantic errors) raised for
 *         syntactically valid but semantically incorrect patterns.</li>
 *     <li>Asserting error messages for a stable, recognizable substring and the
 *         correctness of the error's reported position.</li>
 *   </ul>
 *   <li><strong>Out of scope:</strong></li>
 *   <ul>
 *     <li>Correct handling of **valid** inputs (covered in other test suites).</li>
 *     <li>The exact, full wording of error messages (tests assert substrings).</li>
 *   </ul>
 * </ul>
 */
public class ErrorsTest {

    /**
     * Grouping & Lookaround Errors
     * <p>
     * Covers errors related to groups, named groups, and lookarounds.
     */

    static Stream<Arguments> groupingAndLookaroundErrors() {
        return Stream.of(
            Arguments.of("(abc", "Unterminated group", 4, "unterminated_group"),
            Arguments.of("(?<nameabc)", "Unterminated group name", 11, "unterminated_named_group"),
            Arguments.of("(?=abc", "Unterminated lookahead", 6, "unterminated_lookahead"),
            Arguments.of("(?<=abc", "Unterminated lookbehind", 7, "unterminated_lookbehind"),
            Arguments.of("(?i)abc", "Inline modifiers", 1, "unsupported_inline_modifier")
        );
    }

    @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
    @MethodSource("groupingAndLookaroundErrors")
    void testGroupingAndLookaroundErrors(String invalidDsl, String errorPrefix, int errorPos, String id) {
        /**
         * Tests that various unterminated group/lookaround forms raise ParseError.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        assertTrue(error.getMessage().contains(errorPrefix),
            "Expected error message to contain '" + errorPrefix + "' but got: " + error.getMessage());
        assertEquals(errorPos, error.getPos(),
            "Expected error at position " + errorPos + " but got: " + error.getPos());
    }

    /**
     * Backreference & Naming Errors
     * <p>
     * Covers errors related to invalid backreferences and group naming.
     */

    static Stream<Arguments> backreferenceAndNamingErrors() {
        return Stream.of(
            Arguments.of("\\k<later>(?<later>a)", "Backreference to undefined group <later>", 0, "forward_reference_by_name"),
            Arguments.of("\\2(a)(b)", "Backreference to undefined group \\2", 0, "forward_reference_by_index"),
            Arguments.of("(a)\\2", "Backreference to undefined group \\2", 3, "nonexistent_reference_by_index"),
            Arguments.of("\\k<", "Unterminated named backref", 0, "unterminated_named_backref")
        );
    }

    @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
    @MethodSource("backreferenceAndNamingErrors")
    void testBackreferenceAndNamingErrors(String invalidDsl, String errorPrefix, int errorPos, String id) {
        /**
         * Tests that invalid backreferences are caught at parse time.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        assertTrue(error.getMessage().contains(errorPrefix),
            "Expected error message to contain '" + errorPrefix + "' but got: " + error.getMessage());
        assertEquals(errorPos, error.getPos(),
            "Expected error at position " + errorPos + " but got: " + error.getPos());
    }

    @Test
    void testDuplicateGroupNameRaisesError() {
        /**
         * Tests that duplicate group names raise a semantic error.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("(?<name>a)(?<name>b)");
        });
        assertTrue(error.getMessage().contains("Duplicate group name"));
    }

    /**
     * Character Class Errors
     * <p>
     * Covers errors related to character class syntax.
     */

    static Stream<Arguments> characterClassErrors() {
        return Stream.of(
            Arguments.of("[abc", "Unterminated character class", 4, "unterminated_class"),
            Arguments.of("\\p{L", "Unterminated \\p{...}", 1, "unterminated_unicode_property"),
            Arguments.of("\\pL]", "Expected { after \\p/\\P", 1, "missing_braces_on_unicode_property")
        );
    }

    @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
    @MethodSource("characterClassErrors")
    void testCharacterClassErrors(String invalidDsl, String errorPrefix, int errorPos, String id) {
        /**
         * Tests that malformed character classes raise a ParseError.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        assertTrue(error.getMessage().contains(errorPrefix),
            "Expected error message to contain '" + errorPrefix + "' but got: " + error.getMessage());
        assertEquals(errorPos, error.getPos(),
            "Expected error at position " + errorPos + " but got: " + error.getPos());
    }

    /**
     * Escape & Codepoint Errors
     * <p>
     * Covers errors related to malformed escape sequences.
     */

    static Stream<Arguments> escapeAndCodepointErrors() {
        return Stream.of(
            Arguments.of("\\xG1", "Invalid \\xHH escape", 0, "invalid_hex_digit"),
            Arguments.of("\\u12Z4", "Invalid \\uHHHH", 0, "invalid_unicode_digit"),
            Arguments.of("\\x{", "Unterminated \\x{...}", 0, "unterminated_hex_brace_empty"),
            Arguments.of("\\x{FFFF", "Unterminated \\x{...}", 0, "unterminated_hex_brace_with_digits")
        );
    }

    @ParameterizedTest(name = "should fail for \"{0}\" (ID: {3})")
    @MethodSource("escapeAndCodepointErrors")
    void testEscapeAndCodepointErrors(String invalidDsl, String errorPrefix, int errorPos, String id) {
        /**
         * Tests that malformed hex/unicode escapes raise a ParseError.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        assertTrue(error.getMessage().contains(errorPrefix),
            "Expected error message to contain '" + errorPrefix + "' but got: " + error.getMessage());
        assertEquals(errorPos, error.getPos(),
            "Expected error at position " + errorPos + " but got: " + error.getPos());
    }

    /**
     * Quantifier Errors
     * <p>
     * Covers errors related to malformed quantifiers.
     */

    @Test
    void testUnterminatedBraceQuantifierRaisesError() {
        /**
         * Tests that an unterminated brace quantifier like {m,n raises an error.
         */
        String invalidDsl = "a{2,5";
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        // New, stricter contract: parser should provide an explicit hint
        assertEquals("Incomplete quantifier", error.getMessage());
        assertEquals(5, error.getPos());
    }

    @Test
    void testQuantifyingNonQuantifiableAtomRaisesError() {
        /**
         * Tests that attempting to quantify an anchor raises a semantic error.
         */
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse("^*");
        });
        assertTrue(error.getMessage().contains("Cannot quantify anchor"));
    }

    /**
     * Invariant: First Error Wins
     * <p>
     * Tests the invariant that only the first error in a string is reported.
     */

    @Test
    void testFirstOfMultipleErrorsIsReported() {
        /**
         * In the string '[a|b(', the unterminated class at position 0 should be
         * reported, not the unterminated group at position 4.
         */
        String invalidDsl = "[a|b(";
        STRlingParseError error = assertThrows(STRlingParseError.class, () -> {
            Parser.parse(invalidDsl);
        });
        assertTrue(error.getMessage().contains("Unterminated character class"));
        assertEquals(5, error.getPos());
    }
}
