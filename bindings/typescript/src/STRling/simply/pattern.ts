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

import { Compiler } from "../core/compiler.js";
import { emit as emitPCRE2 } from "../emitters/pcre2.js";
import * as nodes from "../core/nodes.js";

// Create a compiler instance
const compiler = new Compiler();

// Export nodes so other simply modules can use them
export { nodes };

/**
 * Custom error class for STRling pattern errors.
 *
 * This error class provides formatted, user-friendly error messages when invalid
 * patterns are constructed or invalid arguments are provided to pattern functions.
 * Error messages are automatically formatted with consistent indentation for
 * better readability in console output.
 */
export class STRlingError extends Error {
    /**
     * Creates an instance of STRlingError.
     *
     * The error message is automatically formatted with consistent indentation
     * for improved readability when displayed in terminals or logs.
     *
     * @param message - The error message. Can be multiline and will be reformatted.
     */
    constructor(message: string) {
        const lines = message.split("\n");
        const match = lines[1] ? lines[1].match(/^\s*/) : null;
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
     * @returns The formatted error message with header and indentation.
     */
    toString(): string {
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
 * @param text - The text to use as a literal.
 * @returns A pattern representing the literal text.
 */
export const lit = (text: string): Pattern => {
    return Pattern.createModifiedInstance(new nodes.Lit(text), {});
};

export interface PatternOptions {
    node: nodes.Node;
    namedGroups?: string[];
    numberedGroup?: boolean;
}

/**
 * Helper function to create a callable Pattern instance.
 *
 * This is used internally by all pattern creation functions to ensure
 * patterns are callable (can be invoked as functions to apply repetitions).
 *
 * @param options - The options object.
 * @param options.node - The IR node object.
 * @param options.namedGroups - List of named capture groups.
 * @returns A callable Pattern instance.
 */
export const createPattern = ({
    node,
    namedGroups = [],
}: PatternOptions): Pattern => {
    return Pattern.createModifiedInstance(node, { namedGroups });
};

/**
 * Represents a regex pattern in STRling's Simply API.
 *
 * This is the core class that wraps internal IR nodes and provides a fluent,
 * chainable interface for pattern construction. Pattern objects are immutable -
 * all modifier methods return new Pattern instances rather than mutating the
 * original. Patterns can be combined using functions from the constructors module,
 * and can be compiled to regex strings using the build function.
 */
export interface Pattern {
    (minRep?: number, maxRep?: number): Pattern;
}

export class Pattern {
    node: nodes.Node;
    namedGroups: string[];

    /**
     * Creates an instance of Pattern.
     *
     * @param options - The options object.
     * @param options.node - The IR node object representing the pattern.
     * @param options.namedGroups - List of named capture groups in this pattern.
     */
    constructor({ node, namedGroups = [] }: PatternOptions) {
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
     * @param minRep - The minimum number of repetitions.
     * @param maxRep - The maximum number of repetitions. Use 0 for unlimited.
     *                            If omitted, matches exactly minRep times.
     * @returns A new Pattern object with the repetition pattern applied.
     *
     * @throws {STRlingError} If arguments are not integers, are negative, or if
     *                        attempting to repeat a pattern with named groups.
     */
    rep(minRep?: number, maxRep?: number): Pattern {
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

        // A group already assigned a specified range cannot be reassigned
        if (this.node instanceof nodes.Quant) {
            const message = `
    Method: Pattern.rep(minRep, maxRep)

    Cannot re-invoke pattern to specify range that already exists.

    Examples of invalid syntax:
        simply.letter(1, 2)(3, 4) # double invoked range is invalid
        my_pattern = simply.letter(1, 2) # my_pattern was set range (1, 2) # valid
        my_new_pattern = my_pattern(3, 4) # my_pattern was reinvoked (3, 4) # invalid

    Set the range on the first invocation, don't reassign it.

    Examples of valid syntax:
        You can either specify the range now:
            my_pattern = simply.letter(1, 2)

        Or you can specify the range later:
            my_pattern = simply.letter() # my_pattern was never assigned a range
            my_new_pattern = my_pattern(1, 2) # my_pattern was invoked with (1, 2) for the first time.
    `;
            throw new STRlingError(message);
        }

        // Create a Quant node that wraps the current node
        const qMin = minRep ?? 0;
        const qMax =
            maxRep === 0 ? "Inf" : maxRep !== undefined ? maxRep : qMin;

        const newNode = new nodes.Quant(this.node, qMin, qMax, "Greedy");

        return Pattern.createModifiedInstance(newNode, {
            namedGroups: this.namedGroups,
        });
    }

    /**
     * Returns the pattern object as a compiled regex string.
     *
     * Compiles the internal IR node structure to a PCRE2 regex string that can
     * be used with JavaScript's RegExp. This method is called automatically when
     * a Pattern is converted to a string.
     *
     * @returns The compiled regex pattern string.
     */
    toString(): string {
        const ir = compiler.compile(this.node);
        return emitPCRE2(ir);
    }

    /**
     * Handles automatic string conversion for implicit string coercion.
     *
     * This special method is called when JavaScript tries to convert a Pattern
     * to a primitive value. It enables patterns to be used in string contexts.
     *
     * @param hint - The type hint ('string', 'number', or 'default').
     * @returns The pattern's JSON string representation if hint is 'string',
     *                           otherwise returns the pattern itself.
     */
    [Symbol.toPrimitive](hint: string): string | Pattern {
        if (hint === "string") {
            return this.toString();
        }
        return this;
    }

    /**
     * Creates a modified instance of the pattern (internal factory method).
     *
     * This static method creates new Pattern instances with modified IR nodes,
     * wrapped in a callable function to support function-like syntax for
     * applying repetitions. Used internally by pattern transformation methods.
     *
     * @param newNode - The new IR node object.
     * @param kwargs - Additional properties for the new instance (e.g., namedGroups).
     * @returns The new Pattern instance wrapped in a callable function.
     */
    static createModifiedInstance(
        newNode: nodes.Node,
        kwargs: Partial<PatternOptions> = {}
    ): Pattern {
        const instance = new Pattern({ node: newNode, ...kwargs });

        // Create a callable function that also has Pattern's properties
        const callable = function (this: any, ...args: [number?, number?]) {
            return instance.rep(...args);
        } as unknown as Pattern;

        // Copy all instance properties to the callable function
        Object.assign(callable, instance);

        // Set the prototype so instanceof checks work
        Object.setPrototypeOf(callable, Pattern.prototype);

        return callable;
    }
}
