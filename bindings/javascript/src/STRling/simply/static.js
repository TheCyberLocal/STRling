import { Pattern, lit } from "./pattern.js";

/**
Matches any letter (uppercase or lowercase) or digit.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function alphaNum(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [
            { ir: "Range", from: "A", to: "Z" },
            { ir: "Range", from: "a", to: "z" },
            { ir: "Range", from: "0", to: "9" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a letter or digit.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notAlphaNum(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [
            { ir: "Range", from: "A", to: "Z" },
            { ir: "Range", from: "a", to: "z" },
            { ir: "Range", from: "0", to: "9" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any special character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function specialChar(minRep, maxRep) {
    const specialChars = `!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`;
    const items = Array.from(specialChars).map((char) => ({
        ir: "Char",
        value: char,
    }));

    const node = {
        ir: "CharClass",
        negated: false,
        items: items,
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a special character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notSpecialChar(minRep, maxRep) {
    const specialChars = `!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`;
    const items = Array.from(specialChars).map((char) => ({
        ir: "Char",
        value: char,
    }));

    const node = {
        ir: "CharClass",
        negated: true,
        items: items,
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any letter (uppercase or lowercase).
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function letter(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [
            { ir: "Range", from: "A", to: "Z" },
            { ir: "Range", from: "a", to: "z" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a letter.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notLetter(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [
            { ir: "Range", from: "A", to: "Z" },
            { ir: "Range", from: "a", to: "z" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any uppercase letter.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function upper(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Range", from: "A", to: "Z" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not an uppercase letter.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notUpper(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [{ ir: "Range", from: "A", to: "Z" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any lowercase letter.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function lower(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Range", from: "a", to: "z" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a lowercase letter.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notLower(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [{ ir: "Range", from: "a", to: "z" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any hex-digit character.
A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function hexDigit(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [
            { ir: "Range", from: "A", to: "F" },
            { ir: "Range", from: "a", to: "f" },
            { ir: "Range", from: "0", to: "9" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches anything but a hex-digit character.
A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notHexDigit(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [
            { ir: "Range", from: "A", to: "F" },
            { ir: "Range", from: "a", to: "f" },
            { ir: "Range", from: "0", to: "9" },
        ],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any digit.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function digit(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "d" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a digit.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notDigit(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "D" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any whitespace character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function whitespace(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "s" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notWhitespace(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [{ ir: "Esc", type: "s" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a newline character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function newline(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "n" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a newline.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notNewline(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [{ ir: "Esc", type: "n" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a tab character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function tab(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "t" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a carriage return character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function carriage(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "r" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a boundary character.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function bound(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: false,
        items: [{ ir: "Esc", type: "b" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a boundary.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns {Pattern} An instance of the Pattern class.
*/
export function notBound(minRep, maxRep) {
    const node = {
        ir: "CharClass",
        negated: true,
        items: [{ ir: "Esc", type: "b" }],
    };
    const pattern = new Pattern({ node });
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches the start of a line.
@returns {Pattern} An instance of the Pattern class.
*/
export function start() {
    return new Pattern({ node: { ir: "Anchor", type: "Start" } });
}

/**
Matches the end of a line.
@returns {Pattern} An instance of the Pattern class.
*/
export function end() {
    return new Pattern({ node: { ir: "Anchor", type: "End" } });
}
