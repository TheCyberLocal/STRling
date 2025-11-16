package com.strling.simply;
import java.util.Arrays;

import com.strling.core.Nodes.*;

/**
 * Lookaround assertions for advanced pattern matching in STRling.
 *
 * <p>This module provides lookahead and lookbehind assertion functions that enable
 * zero-width pattern matching - checking for pattern presence or absence without
 * consuming characters. These are essential for complex validation rules and
 * conditional matching scenarios. Includes both positive and negative assertions
 * in both directions (ahead/behind), plus convenience functions for common patterns.
 */
public class Lookarounds {

    /**
     * Creates a positive lookahead assertion that checks for a pattern ahead without consuming it.
     *
     * <p>A positive lookahead verifies that the specified pattern exists immediately after
     * the current position, but does not include it in the match result. This allows
     * you to enforce conditions on what follows without actually matching it.
     *
     * @param pattern The pattern to look ahead for. Strings are automatically converted to
     *                literal patterns.
     * @return A new Pattern object representing the positive lookahead assertion.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> Lookaheads are zero-width assertions: they don't consume any characters.
     * The regex engine position remains at the same spot after a lookahead check.
     *
     * <p>Lookaheads can contain capturing groups, but those groups will still be
     * captured even though the lookahead doesn't consume characters.
     */
    public static Pattern ahead(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.ahead(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        Node node = new Look("Ahead", false, ((Pattern) pattern).node);
        return new Pattern(node, false, false, true);
    }

    /**
     * Creates a negative lookahead assertion that checks a pattern is NOT ahead.
     *
     * <p>A negative lookahead verifies that the specified pattern does NOT exist
     * immediately after the current position. The match succeeds only if the
     * pattern is absent. Like all lookarounds, it doesn't consume any characters.
     *
     * @param pattern The pattern to check for absence. Strings are automatically converted
     *                to literal patterns.
     * @return A new Pattern object representing the negative lookahead assertion.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> Negative lookaheads are particularly useful for:
     * <ul>
     * <li>Excluding certain patterns from matches</li>
     * <li>Implementing "not followed by" logic</li>
     * <li>Password validation (e.g., "must not contain spaces")</li>
     * </ul>
     *
     * <p>Remember that lookaheads are zero-width: they verify conditions without
     * consuming characters from the input.
     */
    public static Pattern notAhead(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.notAhead(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        Node node = new Look("Ahead", true, ((Pattern) pattern).node);
        return new Pattern(node, false, false, true);
    }

    /**
     * Creates a positive lookbehind assertion that checks for a pattern behind without consuming it.
     *
     * <p>A positive lookbehind verifies that the specified pattern exists immediately
     * before the current position, but does not include it in the match result.
     * This allows you to enforce conditions on what precedes a match.
     *
     * @param pattern The pattern to look behind for. Strings are automatically converted to
     *                literal patterns.
     * @return A new Pattern object representing the positive lookbehind assertion.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> Lookbehinds are zero-width assertions: they don't consume any characters.
     * The regex engine position remains unchanged after a lookbehind check.
     *
     * <p>Some regex engines (including Java's) require lookbehinds to have a
     * fixed width. Variable-length lookbehinds may not be supported in all contexts.
     */
    public static Pattern behind(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.behind(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        Node node = new Look("Behind", false, ((Pattern) pattern).node);
        return new Pattern(node, false, false, true);
    }

    /**
     * Creates a negative lookbehind assertion that checks a pattern is NOT behind.
     *
     * <p>A negative lookbehind verifies that the specified pattern does NOT exist
     * immediately before the current position. The match succeeds only if the
     * pattern is absent. Like all lookarounds, it doesn't consume any characters.
     *
     * @param pattern The pattern to check for absence before the current position. Strings
     *                are automatically converted to literal patterns.
     * @return A new Pattern object representing the negative lookbehind assertion.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> Some regex engines (including Java's) require lookbehinds to have a
     * fixed width. Variable-length lookbehinds may not be supported in all contexts.
     */
    public static Pattern notBehind(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.notBehind(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        Node node = new Look("Behind", true, ((Pattern) pattern).node);
        return new Pattern(node, false, false, true);
    }

    /**
     * Creates a lookahead that checks for pattern presence anywhere in the remaining string.
     *
     * <p>This function creates a lookahead assertion that succeeds if the specified
     * pattern can be found anywhere in the string after the current position. It's
     * useful for validating that certain content exists without consuming it.
     *
     * @param pattern The pattern to search for in the remaining string. Strings are
     *                automatically converted to literal patterns.
     * @return A new Pattern object representing the presence check.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> This is implemented as a positive lookahead containing `.*pattern`, which
     * means it checks from the current position to the end of the string.
     *
     * <p>Since this is a lookahead, it doesn't consume any characters. You can use
     * multiple `has()` assertions to check for multiple required patterns.
     */
    public static Pattern has(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.has(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        // Create a Look node with dir="Ahead" and a body that matches .*pattern
        Node dotStarNode = new Quant(new Dot(), 0, 0, "Greedy"); // 0,0 means 0 to infinity
        Node seqNode = new Seq(new Node[]{dotStarNode, ((Pattern) pattern).node});

        Node node = new Look("Ahead", false, seqNode);
        return new Pattern(node, false, false, true);
    }

    /**
     * Creates a lookahead that checks for pattern absence anywhere in the remaining string.
     *
     * <p>This function creates a lookahead assertion that succeeds only if the specified
     * pattern cannot be found anywhere in the string after the current position. It's
     * useful for validation that certain content does NOT exist.
     *
     * @param pattern The pattern to verify is absent from the remaining string. Strings are
     *                automatically converted to literal patterns.
     * @return A new Pattern object representing the absence check.
     * @throws STRlingError If the pattern parameter is not a Pattern or string.
     *
     * <p><b>Notes:</b> This is implemented as a negative lookahead containing `.*pattern`, which
     * means it checks from the current position to the end of the string.
     *
     * <p>Since this is a lookahead, it doesn't consume any characters. You can use
     * multiple `hasNot()` assertions to check for multiple forbidden patterns.
     */
    public static Pattern hasNot(Object pattern) {
        if (pattern instanceof String) {
            pattern = Pattern.lit((String) pattern);
        }

        if (!(pattern instanceof Pattern)) {
            String message = "\n" +
                "Method: simply.hasNot(pattern)\n\n" +
                "The parameter must be an instance of `Pattern` or `str`.\n\n" +
                "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
            throw new STRlingError(message);
        }

        // Create a Look node with dir="Ahead", neg=True and a body that matches .*pattern
        Node dotStarNode = new Quant(new Dot(), 0, 0, "Greedy"); // 0,0 means 0 to infinity
        Node seqNode = new Seq(new Node[]{dotStarNode, ((Pattern) pattern).node});

        Node node = new Look("Ahead", true, seqNode);
        return new Pattern(node, false, false, true);
    }
}
