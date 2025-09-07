/**
Custom error class for STRling.
@extends {Error}
*/
export class STRlingError extends Error {
    /**
  Creates an instance of STRlingError.
  @param {string} message - The error message.
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
  Returns the error message as a string.
  @returns {string} The error message.
  */
    toString() {
        return `\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t${this.message}`;
    }
}

/**
Creates a literal pattern from a string.
@param {string} text - The text to use as a literal.
@returns {Pattern} A pattern representing the literal text.
*/
export const lit = (text) => {
    return new Pattern({ node: { ir: "Lit", value: text } });
};

/**
Represents a regex pattern.
*/
export class Pattern {
    /**
  Creates an instance of Pattern.
  @param {object} options - The options object.
  @param {object} options.node - The IR node object.
  @param {Array<string>} [options.namedGroups=[]] - List of named groups.
  */
    constructor({ node, namedGroups = [] }) {
        this.node = node;
        this.namedGroups = namedGroups;
    }

    /**
  Applies a repetition pattern to the current pattern.
  @param {number} [minRep] - The minimum number of repetitions.
  @param {number} [maxRep] - The maximum number of repetitions.
  @returns {Pattern} A new Pattern object with the repetition pattern applied.
  @throws {STRlingError} If arguments are invalid.
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
  Returns the pattern object as a JSON string.
  @returns {string} The pattern's IR as a JSON string.
  */
    toString() {
        return JSON.stringify(this.node);
    }

    /**
  Handles automatic string conversion.
  @param {string} hint - The type hint.
  @returns {string|Pattern} The pattern string or object.
  */
    [Symbol.toPrimitive](hint) {
        if (hint === "string") {
            return this.toString();
        }
        return this;
    }

    /**
  Creates a modified instance of the pattern.
  @param {object} newNode - The new node object.
  @param {Object} [kwargs] - Additional properties for the new instance.
  @returns {Pattern} The new Pattern instance.
  */
    static createModifiedInstance(newNode, kwargs = {}) {
        return new Proxy(new Pattern({ node: newNode, ...kwargs }), {
            apply: (target, thisArg, argumentsList) => {
                return target.rep(...argumentsList);
            },
        });
    }
}
