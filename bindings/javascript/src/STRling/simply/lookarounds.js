import { STRlingError, Pattern, lit } from "./pattern.js";

/**
A positive lookahead checks for the presence of the specified pattern after the current position without including it in the result.
@param {Pattern|string} pattern - The pattern to look ahead for.
@returns {Pattern} An instance of the Pattern class.
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
A negative lookahead checks for the absence of the specified pattern after the current position without including it in the result.
@param {Pattern|string} pattern - The pattern to look ahead for and ensure is absent.
@returns {Pattern} An instance of the Pattern class.
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
A positive lookbehind checks for the presence of the specified pattern before the current position without including it in the result.
@param {Pattern|string} pattern - The pattern to look behind for.
@returns {Pattern} An instance of the Pattern class.
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
A negative lookbehind checks for the absence of the specified pattern before the current position without including it in the result.
@param {Pattern|string} pattern - The pattern to look behind for and ensure is absent.
@returns {Pattern} An instance of the Pattern class.
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
