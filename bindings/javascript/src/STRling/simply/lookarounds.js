/**
 * Lookaround assertions for advanced pattern matching in STRling.
 *
 * This module provides lookahead and lookbehind assertion functions that enable
 * zero-width pattern matching - checking for pattern presence or absence without
 * consuming characters. These are essential for complex validation rules and
 * conditional matching scenarios. Includes both positive and negative assertions
 * in both directions (ahead/behind), plus convenience functions for common patterns.
 */

import { STRlingError, Pattern, lit } from "./pattern.js";

/**
 * Creates a positive lookahead assertion that checks for a pattern ahead without consuming it.
 *
 * A positive lookahead verifies that the specified pattern exists immediately after
 * the current position, but does not include it in the match result. This allows
 * you to enforce conditions on what follows without actually matching it.
 *
 * @param {Pattern|string} pattern - The pattern to look ahead for. Strings are automatically
 *                                    converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the positive lookahead assertion.
 *
 * @throws {STRlingError} If the pattern parameter is not a Pattern or string.
 *
 * @example
 * // Simple Use: Match a digit only if followed by a letter
 * const pattern = s.merge(s.digit(), s.ahead(s.letter()));
 * const match = '5A'.match(new RegExp(pattern));
 * match[0];  // '5'
 * new RegExp(pattern).test('56');  // false
 *
 * @example
 * // Advanced Use: Password validation requiring a digit somewhere
 * const hasDigit = s.ahead(s.merge(s.any(), s.digit()));
 * const passwordPattern = s.merge(hasDigit, s.alphaNum(8, 0));
 * new RegExp(passwordPattern).test('pass1word');  // true
 * new RegExp(passwordPattern).test('password');   // false
 *
 * @see {@link notAhead} For negative lookahead (pattern must NOT be present)
 * @see {@link behind} For positive lookbehind (check what comes before)
 * @see {@link has} For checking pattern existence anywhere in the string
 */
export function ahead(pattern) {
    if (typeof pattern === "string") {
        pattern = lit(pattern);
    }

    if (!(pattern instanceof Pattern)) {
        const message = `
    Method: simply.ahead(pattern)

    The parameter must be an instance of Pattern or string.

    Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
    `;
        throw new STRlingError(message);
    }

    const node = {
        ir: "Look",
        dir: "Ahead",
        neg: false,
        body: pattern.node,
    };

    return new Pattern({
        node,
        namedGroups: pattern.namedGroups,
    });
}

/**
 * Creates a negative lookahead assertion that checks a pattern is NOT ahead.
 *
 * A negative lookahead verifies that the specified pattern does NOT exist
 * immediately after the current position. The match succeeds only if the
 * pattern is absent. Like all lookarounds, it doesn't consume any characters.
 *
 * @param {Pattern|string} pattern - The pattern to check for absence. Strings are automatically
 *                                    converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the negative lookahead assertion.
 *
 * @throws {STRlingError} If the pattern parameter is not a Pattern or string.
 *
 * @example
 * // Simple Use: Match a digit only if NOT followed by a letter
 * const pattern = s.merge(s.digit(), s.notAhead(s.letter()));
 * const match = '56'.match(new RegExp(pattern));
 * match[0];  // '5'
 * new RegExp(pattern).test('5A');  // false
 *
 * @example
 * // Advanced Use: Match identifiers that don't end with '_tmp'
 * const identifier = s.merge(s.letter(), s.alphaNum(0, 0));
 * const notTemp = s.notAhead(s.merge('_tmp', s.wordBoundary()));
 * const validId = s.merge(identifier, notTemp);
 *
 * @see {@link ahead} For positive lookahead (pattern MUST be present)
 * @see {@link notBehind} For negative lookbehind (check what's NOT before)
 * @see {@link hasNot} For checking pattern absence anywhere in the string
 */
export function notAhead(pattern) {
    if (typeof pattern === "string") {
        pattern = lit(pattern);
    }

    if (!(pattern instanceof Pattern)) {
        const message = `
    Method: simply.notAhead(pattern)

    The parameter must be an instance of Pattern or string.

    Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
    `;
        throw new STRlingError(message);
    }

    const node = {
        ir: "Look",
        dir: "Ahead",
        neg: true,
        body: pattern.node,
    };

    return new Pattern({
        node,
        namedGroups: pattern.namedGroups,
    });
}

/**
 * Creates a positive lookbehind assertion that checks for a pattern behind without consuming it.
 *
 * A positive lookbehind verifies that the specified pattern exists immediately
 * before the current position, but does not include it in the match result.
 * This allows you to enforce conditions on what precedes a match.
 *
 * @param {Pattern|string} pattern - The pattern to look behind for. Strings are automatically
 *                                    converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the positive lookbehind assertion.
 *
 * @throws {STRlingError} If the pattern parameter is not a Pattern or string.
 *
 * @example
 * // Simple Use: Match a letter only if preceded by a digit
 * const pattern = s.merge(s.behind(s.digit()), s.letter());
 * const match = '5A'.match(new RegExp(pattern));
 * match[0];  // 'A'
 * new RegExp(pattern).test('BA');  // false
 *
 * @example
 * // Advanced Use: Match prices with currency symbol
 * const price = s.merge(s.behind(s.lit('$')), s.digit(1, 0));
 * const text = "Item costs $42.50 or 50 euros";
 * const match = text.match(new RegExp(price));
 * match[0];  // '42'
 *
 * @see {@link notBehind} For negative lookbehind (pattern must NOT be before)
 * @see {@link ahead} For positive lookahead (check what comes after)
 */
export function behind(pattern) {
    if (typeof pattern === "string") {
        pattern = lit(pattern);
    }

    if (!(pattern instanceof Pattern)) {
        const message = `
    Method: simply.behind(pattern)

    The parameter must be an instance of Pattern or string.

    Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
    `;
        throw new STRlingError(message);
    }

    const node = {
        ir: "Look",
        dir: "Behind",
        neg: false,
        body: pattern.node,
    };

    return new Pattern({
        node,
        namedGroups: pattern.namedGroups,
    });
}

/**
 * Creates a negative lookbehind assertion that checks a pattern is NOT behind.
 *
 * A negative lookbehind verifies that the specified pattern does NOT exist
 * immediately before the current position. The match succeeds only if the
 * pattern is absent. Like all lookarounds, it doesn't consume any characters.
 *
 * @param {Pattern|string} pattern - The pattern to check for absence before the current position.
 *                                    Strings are automatically converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the negative lookbehind assertion.
 *
 * @throws {STRlingError} If the pattern parameter is not a Pattern or string.
 *
 * @example
 * // Simple Use: Match a letter only if NOT preceded by a digit
 * const pattern = s.merge(s.notBehind(s.digit()), s.letter());
 * const match = 'AB'.match(new RegExp(pattern));
 * match[0];  // 'A'
 * new RegExp(pattern).test('5A');  // false
 *
 * @example
 * // Advanced Use: Match words not preceded by negation
 * const word = s.merge(s.notBehind(s.lit('im')), s.lit('possible'));
 * new RegExp(word).test('possible');    // true
 * new RegExp(word).test('impossible');  // false
 *
 * @see {@link behind} For positive lookbehind (pattern MUST be before)
 * @see {@link notAhead} For negative lookahead (check what's NOT after)
 */
export function notBehind(pattern) {
    if (typeof pattern === "string") {
        pattern = lit(pattern);
    }

    if (!(pattern instanceof Pattern)) {
        const message = `
    Method: simply.notBehind(pattern)

    The parameter must be an instance of Pattern or string.

    Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
    `;
        throw new STRlingError(message);
    }

    const node = {
        ir: "Look",
        dir: "Behind",
        neg: true,
        body: pattern.node,
    };

    return new Pattern({
        node,
        namedGroups: pattern.namedGroups,
    });
}
