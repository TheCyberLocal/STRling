/**
 * Core Pattern class and error types for STRling.
 *
 * This module defines the fundamental Pattern class that represents all STRling
 * patterns, along with the STRlingError exception class. The Pattern class provides
 * chainable methods for applying quantifiers, repetitions, and other modifiers to
 * patterns. It serves as the foundation for all pattern construction in the Simply API,
 * wrapping internal AST nodes and providing a user-friendly interface for pattern
 * manipulation and compilation.
 */

/**
 * Custom error class for STRling pattern errors.
 *
 * This error class provides formatted, user-friendly error messages when invalid
 * patterns are constructed or invalid arguments are provided to pattern functions.
 * Error messages are automatically formatted with consistent indentation for
 * better readability in console output.
 *
 * @extends {Error}
 *
 * @example
 * // Thrown when invalid arguments are provided
 * try {
 *   s.digit('not a number');
 * } catch (e) {
 *   console.log(e instanceof STRlingError);  // true
 *   console.log(e.toString());  // Formatted error message
 * }
 */
export class STRlingError extends Error {
    /**
     * Creates an instance of STRlingError.
     *
     * The error message is automatically formatted with consistent indentation
     * for improved readability when displayed in terminals or logs.
     *
     * @param {string} message - The error message. Can be multiline and will be reformatted.
     *
     * @example
     * throw new STRlingError('Invalid pattern argument');
     */
    constructor(message) {
        const lines = message.split("\n");
        const match = lines[1].match(/^\s*/);
        const indentedSpaces = match ? match[0].length : 0;
        const formattedMessage = message
            .split("\n")
            .map((line) => {
                return line.replace(
                    new RegExp("\\s".repeat(indentedSpaces)),
                    "        "
                );
            })
            .join("\n");
        super(formattedMessage);
        this.name = "STRlingError";
        this.message = formattedMessage;
    }

    /**
     * Returns the error message as a formatted string.
     *
     * Formats the error message with a clear header and indented content
     * for improved visibility in console output.
     *
     * @returns {string} The formatted error message with header and indentation.
     *
     * @example
     * const err = new STRlingError('Invalid argument');
     * console.log(err.toString());
     * // "\n\nSTRlingError: Invalid Pattern Attempted.\n\n\tInvalid argument"
     */
    toString() {
        return `\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t${this.message}`;
    }
}

/**
 * Creates a literal pattern from a string.
 *
 * This function wraps a plain string in a Pattern object, treating all characters
 * as literals (no special regex meaning). It's the foundation for mixing literal
 * text with pattern-based matching.
 *
 * @param {string} text - The text to use as a literal.
 * @returns {Pattern} A pattern representing the literal text.
 *
 * @example
 * // Simple Use: Match literal text
 * const pattern = lit('hello');
 * /hello/.test('hello world');  // true
 *
 * @example
 * // Advanced Use: Combine literal with patterns
 * const email = s.merge(
 *   s.letter(1, 0),
 *   lit('@'),
 *   s.letter(1, 0),
 *   lit('.'),
 *   s.letter(2, 4)
 * );
 *
 * @see {@link Pattern} The Pattern class that wraps all patterns
 * @see {@link merge} For combining multiple patterns
 */
export const lit = (text) => {
    return new Pattern({ node: { ir: "Lit", value: text } });
};

/**
 * Represents a regex pattern in STRling's Simply API.
 *
 * This is the core class that wraps internal IR nodes and provides a fluent,
 * chainable interface for pattern construction. Pattern objects are immutable -
 * all modifier methods return new Pattern instances rather than mutating the
 * original. Patterns can be combined using functions from the constructors module,
 * and can be compiled to regex strings using the build function.
 *
 * @example
 * // Create and modify patterns
 * const digit = s.digit();        // Single digit
 * const digits = s.digit(3, 5);   // 3 to 5 digits
 * const optional = s.may(s.letter()); // Optional letter
 *
 * @see {@link lit} For creating literal patterns
 * @see {@link merge} For combining patterns sequentially
 * @see {@link anyOf} For alternation between patterns
 */
export class Pattern {
    /**
     * Creates an instance of Pattern.
     *
     * @param {object} options - The options object.
     * @param {object} options.node - The IR node object representing the pattern.
     * @param {Array<string>} [options.namedGroups=[]] - List of named capture groups in this pattern.
     */
    constructor({ node, namedGroups = [] }) {
        this.node = node;
        this.namedGroups = namedGroups;
    }

    /**
     * Applies a repetition pattern to the current pattern.
     *
     * This method creates a new pattern that matches the current pattern
     * repeated a specified number of times. It's the internal method used
     * by pattern constructors when repetition parameters are provided.
     *
     * @param {number} [minRep] - The minimum number of repetitions.
     * @param {number} [maxRep] - The maximum number of repetitions. Use 0 for unlimited.
     *                            If omitted, matches exactly minRep times.
     * @returns {Pattern} A new Pattern object with the repetition pattern applied.
     *
     * @throws {STRlingError} If arguments are not integers, are negative, or if
     *                        attempting to repeat a pattern with named groups.
     *
     * @example
     * // Match exactly 3 digits
     * const pattern = s.digit().rep(3);
     * /\d{3}/.test('123');  // true
     *
     * @example
     * // Match 2 to 4 letters
     * const pattern = s.letter().rep(2, 4);
     * /[a-zA-Z]{2,4}/.test('abc');  // true
     *
     * @example
     * // Match 1 or more digits (unlimited max)
     * const pattern = s.digit().rep(1, 0);
     * /\d+/.test('12345');  // true
     *
     * @pitfall
     * Named groups cannot be repeated as they must be unique. Use merge() or
     * capture() without names instead.
     *
     * @see {@link digit} For creating digit patterns with repetition
     * @see {@link letter} For creating letter patterns with repetition
     */
    rep(minRep, maxRep) {
        if (minRep === undefined && maxRep === undefined) {
            return this;
        }

        if (
            (minRep !== undefined && !Number.isInteger(minRep)) ||
            (maxRep !== undefined && !Number.isInteger(maxRep))
        ) {
            const message = `
    Method: Pattern.rep(minRep, maxRep)

    The minRep and maxRep arguments must be integers (0-9).
    `;
            throw new STRlingError(message);
        }

        if (
            (minRep !== undefined && minRep < 0) ||
            (maxRep !== undefined && maxRep < 0)
        ) {
            const message = `
    Method: Pattern.rep(minRep, maxRep)

    The minRep and maxRep must be 0 or greater.
    `;
            throw new STRlingError(message);
        }

        if (
            this.namedGroups.length &&
            minRep !== undefined &&
            maxRep !== undefined
        ) {
            const message = `
    Method: Pattern.rep(minRep, maxRep)

    Named groups cannot be repeated as they must be unique.

    Consider using an unlabeled group (merge) or a numbered group (capture).
    `;
            throw new STRlingError(message);
        }

        // Create a Quant node that wraps the current node
        const qMin = minRep;
        const qMax =
            maxRep === 0 ? "Inf" : maxRep !== undefined ? maxRep : minRep;

        const newNode = {
            ir: "Quant",
            child: this.node,
            min: qMin,
            max: qMax,
            mode: "Greedy", // Default mode
        };

        return Pattern.createModifiedInstance(newNode, {
            namedGroups: this.namedGroups,
        });
    }

    /**
     * Returns the pattern object as a JSON string.
     *
     * Serializes the internal IR node structure to JSON format. Mainly used
     * for debugging and internal operations.
     *
     * @returns {string} The pattern's IR as a JSON string.
     *
     * @example
     * const pattern = s.digit(3);
     * console.log(pattern.toString());
     * // '{"ir":"Quant","child":{"ir":"CharClass",...},"min":3,"max":3,"mode":"Greedy"}'
     */
    toString() {
        return JSON.stringify(this.node);
    }

    /**
     * Handles automatic string conversion for implicit string coercion.
     *
     * This special method is called when JavaScript tries to convert a Pattern
     * to a primitive value. It enables patterns to be used in string contexts.
     *
     * @param {string} hint - The type hint ('string', 'number', or 'default').
     * @returns {string|Pattern} The pattern's JSON string representation if hint is 'string',
     *                           otherwise returns the pattern itself.
     *
     * @example
     * const pattern = s.digit();
     * console.log(`Pattern: ${pattern}`);  // Calls toString() automatically
     */
    [Symbol.toPrimitive](hint) {
        if (hint === "string") {
            return this.toString();
        }
        return this;
    }

    /**
     * Creates a modified instance of the pattern (internal factory method).
     *
     * This static method creates new Pattern instances with modified IR nodes,
     * wrapped in a Proxy to support callable patterns (function-like syntax for
     * applying repetitions). Used internally by pattern transformation methods.
     *
     * @param {object} newNode - The new IR node object.
     * @param {Object} [kwargs] - Additional properties for the new instance (e.g., namedGroups).
     * @returns {Pattern} The new Pattern instance wrapped in a Proxy.
     *
     * @example
     * // Internal use - creates a pattern that can be called as a function
     * const newPattern = Pattern.createModifiedInstance(irNode, { namedGroups: [] });
     */
    static createModifiedInstance(newNode, kwargs = {}) {
        return new Proxy(new Pattern({ node: newNode, ...kwargs }), {
            apply: (target, thisArg, argumentsList) => {
                return target.rep(...argumentsList);
            },
        });
    }
}
