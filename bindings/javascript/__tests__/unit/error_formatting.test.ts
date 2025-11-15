/**
 * Test the STRlingParseError class and hint engine.
 */

import { STRlingParseError } from "../../src/STRling/core/errors";
import { getHint } from "../../src/STRling/core/hint_engine";

describe("STRlingParseError", () => {
    test("simple error without text", () => {
        const err = new STRlingParseError("Test error", 5);
        expect(err.toString()).toContain("Test error at position 5");
    });

    test("error with text and hint", () => {
        const text = "(a|b))";
        const err = new STRlingParseError(
            "Unmatched ')'",
            5,
            text,
            "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
        );
        const formatted = err.toString();

        // Check that it contains the expected parts
        expect(formatted).toContain("STRling Parse Error: Unmatched ')'");
        expect(formatted).toContain("> 1 | (a|b))");
        expect(formatted).toContain("^");
        expect(formatted).toContain("Hint:");
        expect(formatted).toContain("does not have a matching opening '('");
    });

    test("error position indicator", () => {
        const text = "abc def";
        const err = new STRlingParseError("Error at d", 4, text);
        const formatted = err.toString();

        // The caret should be under 'd' (position 4)
        const lines = formatted.split("\n");
        for (const line of lines) {
            if (line.startsWith(">   |")) {
                // Count spaces before ^
                const caretLine = line.substring(6); // Remove ">   | "
                const spacesBeforeCaret = caretLine.length - caretLine.trimStart().length;
                expect(spacesBeforeCaret).toBe(4);
                break;
            }
        }
    });

    test("multiline error", () => {
        const text = "abc\ndef\nghi";
        const err = new STRlingParseError("Error on line 2", 5, text);
        const formatted = err.toString();

        // Should show line 2
        expect(formatted).toContain("> 2 | def");
    });

    test("toFormattedString method", () => {
        const err = new STRlingParseError("Test", 0, "abc");
        expect(err.toFormattedString()).toBe(err.toString());
    });
});

describe("HintEngine", () => {
    test("unterminated group hint", () => {
        const hint = getHint("Unterminated group", "(abc", 4);
        expect(hint).not.toBeNull();
        expect(hint).toContain("opened with '('");
        expect(hint).toContain("Add a matching ')'");
    });

    test("unterminated character class hint", () => {
        const hint = getHint("Unterminated character class", "[abc", 4);
        expect(hint).not.toBeNull();
        expect(hint).toContain("opened with '['");
        expect(hint).toContain("Add a matching ']'");
    });

    test("unexpected token hint - closing paren", () => {
        const hint = getHint("Unexpected token", "abc)", 3);
        expect(hint).not.toBeNull();
        expect(hint).toContain("does not have a matching opening '('");
        expect(hint).toContain("escape it with '\\)'");
    });

    test("cannot quantify anchor hint", () => {
        const hint = getHint("Cannot quantify anchor", "^*", 1);
        expect(hint).not.toBeNull();
        expect(hint).toContain("Anchors");
        expect(hint).toContain("match positions");
        expect(hint).toContain("cannot be quantified");
    });

    test("inline modifiers hint", () => {
        const hint = getHint("Inline modifiers `(?imsx)` are not supported", "(?i)abc", 1);
        expect(hint).not.toBeNull();
        expect(hint).toContain("%flags");
        expect(hint).toContain("directive");
    });

    test("no hint for unknown error", () => {
        const hint = getHint("Some unknown error message", "abc", 0);
        expect(hint).toBeNull();
    });
});
