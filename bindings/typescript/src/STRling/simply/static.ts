/** Legacy ergonomic names mapped to canonical Simply protocol operations. */

import { createPattern, type Pattern } from "./pattern.js";
import { characterSet } from "./sets.js";
import type { SimplyCharacterSetMember } from "./preview.js";

function repeated(pattern: Pattern, minRep?: number, maxRep?: number): Pattern {
    return minRep === undefined ? pattern : pattern.rep(minRep, maxRep);
}

function ranges(
    values: readonly (readonly [string, string])[],
    negated: boolean,
    minRep?: number,
    maxRep?: number,
): Pattern {
    return repeated(
        characterSet(
            values.map(([start, end]) => ({ kind: "range", start, end })),
            negated,
        ),
        minRep,
        maxRep,
    );
}

function builtin(
    name: "digit" | "word" | "whitespace",
    negated: boolean,
    minRep?: number,
    maxRep?: number,
): Pattern {
    return repeated(
        characterSet([{ kind: "builtin", name, domain: "unicode", negated }]),
        minRep,
        maxRep,
    );
}

export function alphaNum(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "Z"],
            ["a", "z"],
            ["0", "9"],
        ],
        false,
        minRep,
        maxRep,
    );
}

export function notAlphaNum(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "Z"],
            ["a", "z"],
            ["0", "9"],
        ],
        true,
        minRep,
        maxRep,
    );
}

const ASCII_PUNCTUATION = Array.from(
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    (value): SimplyCharacterSetMember => ({ kind: "literal", value }),
);

export function specialChar(minRep?: number, maxRep?: number): Pattern {
    return repeated(characterSet(ASCII_PUNCTUATION), minRep, maxRep);
}

export function notSpecialChar(minRep?: number, maxRep?: number): Pattern {
    return repeated(characterSet(ASCII_PUNCTUATION, true), minRep, maxRep);
}

export function letter(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "Z"],
            ["a", "z"],
        ],
        false,
        minRep,
        maxRep,
    );
}

export function notLetter(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "Z"],
            ["a", "z"],
        ],
        true,
        minRep,
        maxRep,
    );
}

export function upper(minRep?: number, maxRep?: number): Pattern {
    return ranges([["A", "Z"]], false, minRep, maxRep);
}

export function notUpper(minRep?: number, maxRep?: number): Pattern {
    return ranges([["A", "Z"]], true, minRep, maxRep);
}

export function lower(minRep?: number, maxRep?: number): Pattern {
    return ranges([["a", "z"]], false, minRep, maxRep);
}

export function notLower(minRep?: number, maxRep?: number): Pattern {
    return ranges([["a", "z"]], true, minRep, maxRep);
}

export function hexDigit(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "F"],
            ["a", "f"],
            ["0", "9"],
        ],
        false,
        minRep,
        maxRep,
    );
}

export function notHexDigit(minRep?: number, maxRep?: number): Pattern {
    return ranges(
        [
            ["A", "F"],
            ["a", "f"],
            ["0", "9"],
        ],
        true,
        minRep,
        maxRep,
    );
}

export function digit(minRep?: number, maxRep?: number): Pattern {
    return builtin("digit", false, minRep, maxRep);
}

export function notDigit(minRep?: number, maxRep?: number): Pattern {
    return builtin("digit", true, minRep, maxRep);
}

export function whitespace(minRep?: number, maxRep?: number): Pattern {
    return builtin("whitespace", false, minRep, maxRep);
}

export function notWhitespace(minRep?: number, maxRep?: number): Pattern {
    return builtin("whitespace", true, minRep, maxRep);
}

function literalSet(
    value: string,
    negated: boolean,
    minRep?: number,
    maxRep?: number,
): Pattern {
    return repeated(
        characterSet([{ kind: "literal", value }], negated),
        minRep,
        maxRep,
    );
}

export function newline(minRep?: number, maxRep?: number): Pattern {
    return literalSet("\n", false, minRep, maxRep);
}

export function notNewline(minRep?: number, maxRep?: number): Pattern {
    return literalSet("\n", true, minRep, maxRep);
}

export function tab(minRep?: number, maxRep?: number): Pattern {
    return literalSet("\t", false, minRep, maxRep);
}

export function carriage(minRep?: number, maxRep?: number): Pattern {
    return literalSet("\r", false, minRep, maxRep);
}

function position(
    value: Parameters<
        import("./preview.js").SimplyPreviewBuilder["position"]
    >[1],
): Pattern {
    return createPattern((context) =>
        context.builder.position(context.next("position"), value),
    );
}

export function bound(_minRep?: number, _maxRep?: number): Pattern {
    return position("word_boundary");
}

export function notBound(_minRep?: number, _maxRep?: number): Pattern {
    return position("not_word_boundary");
}

export function start(): Pattern {
    return position("input_start");
}

export function end(): Pattern {
    return position("input_end");
}

export function email(): Pattern {
    return stdlib("stdlib.email", {});
}

export function url(): Pattern {
    return stdlib("stdlib.url", {});
}

export function uuid(version: number | null = null): Pattern {
    return stdlib("stdlib.uuid", { version });
}

export function ip(version: number | null = null): Pattern {
    return stdlib("stdlib.ip", { version });
}

export function dateTime(): Pattern {
    return stdlib("stdlib.date_time", {});
}

function stdlib(
    helperId: string,
    parameters: Readonly<Record<string, unknown>>,
): Pattern {
    return createPattern((context) =>
        context.builder.stdlibHelper(
            context.next("stdlib-helper"),
            helperId,
            parameters,
        ),
    );
}
