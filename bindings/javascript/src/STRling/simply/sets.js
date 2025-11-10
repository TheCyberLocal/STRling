/**
 * Character set and range functions for pattern matching in STRling.
 *
 * This module provides functions for creating character class patterns, including
 * ranges (between), custom sets (customSet), and utilities for combining sets.
 * Character sets are fundamental building blocks for matching specific groups of
 * characters, and these functions make it easy to define complex character matching
 * rules without dealing with raw regex character class syntax.
 */

import { STRlingError, Pattern, lit, createPattern, nodes } from "./pattern.js";

/**
Matches all characters within and including the start and end of a letter or digit range.
@param {string|number} start - The starting character or digit of the range.
@param {string|number} end - The ending character or digit of the range.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any digit from 0 to 9.
const myPattern1 = s.between(0, 9);

// Matches any lowercase letter from 'a' to 'z'.
const myPattern2 = s.between('a', 'z');

// Matches any uppercase letter from 'A' to 'Z'.
const myPattern3 = s.between('A', 'Z');
*/
export function between(start, end, minRep, maxRep) {
    if (
        (typeof start !== "string" || typeof end !== "string") &&
        (typeof start !== "number" || typeof end !== "number")
    ) {
        const message = `
    Method: simply.between(start, end)

    The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
    `;
        throw new STRlingError(message);
    }

    let rangeNode;

    if (typeof start === "number") {
        if (start > end) {
            const message = `
      Method: simply.between(start, end)

      The 'start' integer must not be greater than the 'end' integer.
      `;
            throw new STRlingError(message);
        }

        if (start < 0 || start > 9 || end < 0 || end > 9) {
            const message = `
      Method: simply.between(start, end)

      The 'start' and 'end' integers must be single digits (0-9).
      `;
            throw new STRlingError(message);
        }

        rangeNode = new nodes.ClassRange(start.toString(), end.toString(),
        );
    }

    if (typeof start === "string") {
        if (!/^[a-zA-Z]$/.test(start) || !/^[a-zA-Z]$/.test(end)) {
            const message = `
      Method: simply.between(start, end)

      The 'start' and 'end' must be alphabetical characters.
      `;
            throw new STRlingError(message);
        }

        if (start.length !== 1 || end.length !== 1) {
            const message = `
      Method: simply.between(start, end)

      The 'start' and 'end' characters must be single letters.
      `;
            throw new STRlingError(message);
        }

        if (
            (start.toLowerCase() === start && end.toLowerCase() !== end) ||
            (start.toUpperCase() === start && end.toUpperCase() !== end)
        ) {
            const message = `
      Method: simply.between(start, end)

      The 'start' and 'end' characters must be of the same case.
      `;
            throw new STRlingError(message);
        }

        if (start > end) {
            const message = `
      Method: simply.between(start, end)

      The 'start' character must not be lexicographically greater than the 'end' character.
      `;
            throw new STRlingError(message);
        }

        rangeNode = new nodes.ClassRange(start, end,
        );
    }

    const node = new nodes.CharClass(false, [rangeNode]);

    const pattern = createPattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character not within or including the start and end of a letter or digit range.
@param {string|number} start - The starting character or digit of the range.
@param {string|number} end - The ending character or digit of the range.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any character that is not a digit from 0 to 9.
const myPattern1 = s.notBetween(0, 9);

// Matches any character that is not a lowercase letter from 'a' to 'z'.
const myPattern2 = s.notBetween('a', 'z');

// Matches any character that is not a uppercase letter from 'A' to 'Z'.
const myPattern3 = s.notBetween('A', 'Z');
*/
export function notBetween(start, end, minRep, maxRep) {
    if (
        (typeof start !== "string" || typeof end !== "string") &&
        (typeof start !== "number" || typeof end !== "number")
    ) {
        const message = `
    Method: simply.notBetween(start, end)

    The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
    `;
        throw new STRlingError(message);
    }

    let startChar, endChar;

    if (typeof start === "number") {
        if (start > end) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' integer must not be greater than the 'end' integer.
      `;
            throw new STRlingError(message);
        }

        if (start < 0 || start > 9 || end < 0 || end > 9) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' and 'end' integers must be single digits (0-9).
      `;
            throw new STRlingError(message);
        }

        startChar = String(start);
        endChar = String(end);
    }

    if (typeof start === "string") {
        if (!/^[a-zA-Z]$/.test(start) || !/^[a-zA-Z]$/.test(end)) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' and 'end' must be alphabetical characters.
      `;
            throw new STRlingError(message);
        }

        if (start.length !== 1 || end.length !== 1) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' and 'end' characters must be single letters.
      `;
            throw new STRlingError(message);
        }

        if (
            (start.toLowerCase() === start && end.toLowerCase() !== end) ||
            (start.toUpperCase() === start && end.toUpperCase() !== end)
        ) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' and 'end' characters must be of the same case.
      `;
            throw new STRlingError(message);
        }

        if (start > end) {
            const message = `
      Method: simply.notBetween(start, end)

      The 'start' character must not be lexicographically greater than the 'end' character.
      `;
            throw new STRlingError(message);
        }

        startChar = start;
        endChar = end;
    }

    const node = new nodes.CharClass(true, [new nodes.ClassRange(startChar, endChar)]);
    const pattern = createPattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any provided patterns, but they can't include subpatterns.
@param {...(Pattern|string)} patterns - One or more non-composite patterns to match.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any letter, digit, comma, and period.
const myPattern = s.inChars(s.letter(), s.digit(), ',.');
*/
export function inChars(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
        }

        if (!(pattern instanceof Pattern)) {
            const message = `
      Method: simply.inChars(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
            throw new STRlingError(message);
        }

        return pattern;
    });

    // Check if any pattern is composite (Seq, Alt, Group, Quant, Look, etc.)
    const compositeNodeTypes = ["Seq", "Alt", "Group", "Quant", "Look"];
    for (const p of cleanPatterns) {
        const nodeType = p.node.constructor.name;
        if (compositeNodeTypes.includes(nodeType)) {
            const message = `
    Method: simply.inChars(...patterns)

    All patterns must be non-composite.
    `;
            throw new STRlingError(message);
        }
    }

    // Build the character class items by extracting them from input patterns
    let items = [];
    for (const pattern of cleanPatterns) {
        if (pattern.node.constructor.name === "Lit") {
            // For literals, add each character as a ClassLiteral item
            items = items.concat(
                Array.from(pattern.node.value).map((c) => new nodes.ClassLiteral(c))
            );
        } else if (pattern.node.constructor.name === "CharClass") {
            // For character classes, add their items directly
            items = items.concat(pattern.node.items);
        }
        // Handle other node types as needed
    }

    const node = new nodes.CharClass(false, items);

    return createPattern({ node });
}

/**
Matches anything but the provided patterns, but they can't include subpatterns.
@param {...(Pattern|string)} patterns - One or more non-composite patterns to avoid.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any character that is not a letter, digit, comma, and period.
const myPattern = s.notInChars(s.letter(), s.digit(), ',.');
*/
export function notInChars(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
        }

        if (!(pattern instanceof Pattern)) {
            const message = `
      Method: simply.notInChars(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
            throw new STRlingError(message);
        }

        return pattern;
    });

    if (cleanPatterns.some((p) => p.composite)) {
        const message = `
    Method: simply.notInChars(...patterns)

    All patterns must be non-composite.
    `;
        throw new STRlingError(message);
    }

    // Build the character class items by extracting them from input patterns
    let items = [];
    for (const pattern of cleanPatterns) {
        if (pattern.node.constructor.name === "Lit") {
            // For literals, add each character as a Char item
            items = items.concat(
                Array.from(pattern.node.value).map((c) => new nodes.ClassLiteral(c))
            );
        } else if (pattern.node.constructor.name === "CharClass") {
            // For character classes, add their items directly
            items = items.concat(pattern.node.items);
        }
        // Handle other node types as needed
    }

    const node = new nodes.CharClass(true, items);

    return createPattern({ node });
}
