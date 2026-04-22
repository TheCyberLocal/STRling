/**
 * Predefined character classes and static patterns for STRling.
 *
 * This module provides convenient functions for matching common character types
 * (letters, digits, whitespace, etc.) and special patterns (any character, word
 * boundaries, etc.). These are the most frequently used building blocks for
 * pattern construction, offering a clean alternative to regex shorthand classes
 * like \d, \w, \s, etc.
 */

import { Pattern, nodes } from "./pattern.js";
import { merge, anyOf, may } from "./constructors.js";
import { inChars } from "./sets.js";

/**
Matches any letter (uppercase or lowercase) or digit.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function alphaNum(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [
        new nodes.ClassRange("A", "Z"),
        new nodes.ClassRange("a", "z"),
        new nodes.ClassRange("0", "9"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a letter or digit.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notAlphaNum(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [
        new nodes.ClassRange("A", "Z"),
        new nodes.ClassRange("a", "z"),
        new nodes.ClassRange("0", "9"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any special character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function specialChar(minRep?: number, maxRep?: number): Pattern {
    const specialChars = `!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`;
    const items = Array.from(specialChars).map(
        (char) => new nodes.ClassLiteral(char),
    );

    const node = new nodes.CharClass(false, items);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a special character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notSpecialChar(minRep?: number, maxRep?: number): Pattern {
    const specialChars = `!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`;
    const items = Array.from(specialChars).map(
        (char) => new nodes.ClassLiteral(char),
    );

    const node = new nodes.CharClass(true, items);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any letter (uppercase or lowercase).
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function letter(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [
        new nodes.ClassRange("A", "Z"),
        new nodes.ClassRange("a", "z"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a letter.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notLetter(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [
        new nodes.ClassRange("A", "Z"),
        new nodes.ClassRange("a", "z"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any uppercase letter.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function upper(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassRange("A", "Z")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not an uppercase letter.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notUpper(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [new nodes.ClassRange("A", "Z")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any lowercase letter.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function lower(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassRange("a", "z")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a lowercase letter.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notLower(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [new nodes.ClassRange("a", "z")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any hex-digit character.
A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function hexDigit(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [
        new nodes.ClassRange("A", "F"),
        new nodes.ClassRange("a", "f"),
        new nodes.ClassRange("0", "9"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches anything but a hex-digit character.
A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notHexDigit(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [
        new nodes.ClassRange("A", "F"),
        new nodes.ClassRange("a", "f"),
        new nodes.ClassRange("0", "9"),
    ]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any digit.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function digit(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("d")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a digit.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notDigit(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("D")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any whitespace character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function whitespace(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("s")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notWhitespace(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [new nodes.ClassEscape("s")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a newline character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function newline(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("n")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a newline.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notNewline(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(true, [new nodes.ClassEscape("n")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a tab character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function tab(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("t")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a carriage return character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function carriage(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("r")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches a boundary character.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function bound(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.CharClass(false, [new nodes.ClassEscape("b")]);
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches any character that is not a boundary.
@param minRep - The minimum number of characters to match.
@param maxRep - The maximum number of characters to match, 0 means unlimited, and undefined means exactly match minRep.
@returns An instance of the Pattern class.
*/
export function notBound(minRep?: number, maxRep?: number): Pattern {
    const node = new nodes.Anchor("NotWordBoundary");
    const pattern = Pattern.createModifiedInstance(node, {});
    return minRep !== undefined ? pattern.rep(minRep, maxRep) : pattern;
}

/**
Matches the start of a line.
@returns An instance of the Pattern class.
*/
export function start(): Pattern {
    return Pattern.createModifiedInstance(new nodes.Anchor("Start"), {});
}

/**
Matches the end of a line.
@returns An instance of the Pattern class.
*/
export function end(): Pattern {
    return Pattern.createModifiedInstance(new nodes.Anchor("End"), {});
}

// ============================================================================
// Standard Library — Essential Patterns
//
// The following helpers expose canonical, RFC-grounded patterns for the most
// commonly validated string formats. Each helper composes existing Simply
// primitives so the compiled output flows through the standard pipeline and no
// raw regex leaks into the public API.
// ============================================================================

/**
Matches an email address (RFC 5322 addr-spec, basic structure).

The pattern accepts a local part of letters, digits, and the punctuation
`. _ % + -`, followed by `@`, a domain of letters, digits, dots, and hyphens,
and a top-level domain of two or more letters. Quoted local parts and
internationalized (IDN) labels are intentionally out of scope for this helper.

@returns A Pattern matching an email address.
*/
export function email(): Pattern {
    const local = inChars(letter(), digit(), ".", "_", "%", "+", "-")(1, 0);
    const domainBody = inChars(letter(), digit(), ".", "-")(1, 0);
    const tld = letter(2, 0);
    return merge(local, "@", domainBody, ".", tld);
}

/**
Matches an HTTP or HTTPS URL with scheme, authority, optional path, query,
and fragment (RFC 3986 generic syntax).

Components recognised:
  - scheme: `http` or `https`
  - authority: host of letters, digits, dots, and hyphens, with optional `:port`
  - path: optional, beginning with `/`
  - query: optional, beginning with `?`
  - fragment: optional, beginning with `#`

@returns A Pattern matching a URL.
*/
export function url(): Pattern {
    const scheme = merge("http", may("s"));
    const host = inChars(letter(), digit(), ".", "-")(1, 0);
    const port = may(merge(":", digit(1, 0)));
    const path = may(
        merge(
            "/",
            inChars(
                letter(),
                digit(),
                "/",
                "_",
                "-",
                ".",
                "~",
                "%",
                "&",
                "=",
                ":",
                "@",
                "!",
                "$",
                "'",
                "(",
                ")",
                "*",
                "+",
                ",",
                ";",
            )(0, 0),
        ),
    );
    const query = may(
        merge(
            "?",
            inChars(
                letter(),
                digit(),
                "/",
                "_",
                "-",
                ".",
                "~",
                "%",
                "&",
                "=",
                ":",
                "@",
                "!",
                "$",
                "'",
                "(",
                ")",
                "*",
                "+",
                ",",
                ";",
                "?",
            )(0, 0),
        ),
    );
    const fragment = may(
        merge(
            "#",
            inChars(
                letter(),
                digit(),
                "/",
                "_",
                "-",
                ".",
                "~",
                "%",
                "&",
                "=",
                ":",
                "@",
                "!",
                "$",
                "'",
                "(",
                ")",
                "*",
                "+",
                ",",
                ";",
                "?",
                "#",
            )(0, 0),
        ),
    );
    return merge(scheme, "://", host, port, path, query, fragment);
}

/**
Matches a UUID in the standard 8-4-4-4-12 hexadecimal format (RFC 4122).

When `version` is `4`, the pattern additionally enforces the version-4 layout:
the third group's first hex digit is `4` and the fourth group's first hex
digit is one of `8`, `9`, `a`, `b` (the variant nibble).

@param version - Optional UUID version. Currently `4` is recognised for
                 version-specific validation; any other value (or omission)
                 yields the generic 8-4-4-4-12 pattern.
@returns A Pattern matching a UUID.
*/
export function uuid(version?: number): Pattern {
    const dash = "-";
    if (version === 4) {
        return merge(
            hexDigit(8),
            dash,
            hexDigit(4),
            dash,
            "4",
            hexDigit(3),
            dash,
            inChars("89ABab"),
            hexDigit(3),
            dash,
            hexDigit(12),
        );
    }
    return merge(
        hexDigit(8),
        dash,
        hexDigit(4),
        dash,
        hexDigit(4),
        dash,
        hexDigit(4),
        dash,
        hexDigit(12),
    );
}

/**
Matches an IP address in either IPv4 dot-decimal notation (RFC 791) or
the full eight-group IPv6 colon-hex notation (RFC 4291).

@param version - Optional IP version. `4` restricts to IPv4, `6` restricts to
                 IPv6, and omitting the argument accepts either. Compressed
                 IPv6 forms (`::`) are out of scope for this basic helper.
@returns A Pattern matching an IP address.
*/
export function ip(version?: number): Pattern {
    const ipv4 = merge(
        digit(1, 3),
        ".",
        digit(1, 3),
        ".",
        digit(1, 3),
        ".",
        digit(1, 3),
    );
    const ipv6 = merge(
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
        ":",
        hexDigit(1, 4),
    );
    if (version === 4) return ipv4;
    if (version === 6) return ipv6;
    return anyOf(ipv4, ipv6);
}

/**
Matches an ISO 8601 / RFC 3339 datetime: `YYYY-MM-DDTHH:MM:SS` with
optional fractional seconds and timezone designator (`Z` or `±HH:MM`).

@returns A Pattern matching an ISO 8601 datetime.
*/
export function dateTime(): Pattern {
    return merge(
        digit(4),
        "-",
        digit(2),
        "-",
        digit(2),
        "T",
        digit(2),
        ":",
        digit(2),
        ":",
        digit(2),
        may(merge(".", digit(1, 0))),
        may(anyOf("Z", merge(inChars("+-"), digit(2), ":", digit(2)))),
    );
}
