/**
 * Test Parser Error Messages - Comprehensive Validation of Rich Error Output
 *
 * This test suite validates that the parser produces rich, instructional error
 * messages in the "Visionary State" format with:
 *   - Context line showing the error location
 *   - Caret (^) pointing to the exact position
 *   - Helpful hints explaining how to fix the error
 *
 * These tests intentionally pass invalid syntax to ensure the error messages
 * are helpful and educational.
 */

import { parse } from "../../src/STRling/core/parser";
import { STRlingParseError } from "../../src/STRling/core/errors";

describe("Rich Error Formatting", () => {
    test("unmatched closing paren shows visionary format", () => {
        expect(() => parse("(a|b))")).toThrow(STRlingParseError);
        
        try {
            parse("(a|b))");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            const formatted = err.toString();
            
            // Check all components of visionary format
            expect(formatted).toContain("STRling Parse Error:");
            expect(formatted).toContain("Unexpected trailing input");
            expect(formatted).toContain("> 1 | (a|b))");
            expect(formatted).toContain("^");
            expect(formatted).toContain("Hint:");
            expect(formatted).toContain("unexpected content after the pattern ended");
        }
    });

    test("unterminated group shows helpful hint", () => {
        try {
            parse("(abc");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("opened with '('");
            expect(err.hint).toContain("Add a matching ')'");
        }
    });

    test("error on second line shows correct line number", () => {
        const pattern = "abc\n(def";
        try {
            parse(pattern);
            fail("Expected STRlingParseError");
        } catch (error) {
            const formatted = (error as STRlingParseError).toString();
            expect(formatted).toContain("> 2 |"); // Should show line 2
            expect(formatted).toContain("(def");
        }
    });

    test("caret points to exact position", () => {
        try {
            parse("abc)");
            fail("Expected STRlingParseError");
        } catch (error) {
            const formatted = (error as STRlingParseError).toString();
            const lines = formatted.split("\n");
            
            // Find the line with the caret
            for (const line of lines) {
                if (line.startsWith(">   |")) {
                    const caretLine = line.substring(6); // Remove ">   | "
                    // Caret should be at position 3 (under ')')
                    expect(caretLine.trim()).toBe("^");
                    const spaces = caretLine.length - caretLine.trimStart().length;
                    expect(spaces).toBe(3);
                }
            }
        }
    });
});

describe("Specific Error Hints", () => {
    test("alternation no lhs hint", () => {
        try {
            parse("|abc");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Alternation lacks left-hand side");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("expression on the left side");
        }
    });

    test("alternation no rhs hint", () => {
        try {
            parse("abc|");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Alternation lacks right-hand side");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("expression on the right side");
        }
    });

    test("unterminated char class hint", () => {
        try {
            parse("[abc");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Unterminated character class");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("opened with '['");
            expect(err.hint).toContain("Add a matching ']'");
        }
    });

    test("cannot quantify anchor hint", () => {
        try {
            parse("^*");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Cannot quantify anchor");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("Anchors");
            expect(err.hint).toContain("match positions");
        }
    });

    test("invalid hex escape hint", () => {
        try {
            parse(String.raw`\xGG`);
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Invalid \\xHH escape");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("hexadecimal digits");
        }
    });

    test("undefined backref hint", () => {
        try {
            parse(String.raw`\1abc`);
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Backreference to undefined group");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("previously captured groups");
            expect(err.hint).toContain("forward references");
        }
    });

    test("duplicate group name hint", () => {
        try {
            parse("(?<name>a)(?<name>b)");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Duplicate group name");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("unique name");
        }
    });

    test("inline modifiers hint", () => {
        try {
            parse("(?i)abc");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Inline modifiers");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("%flags");
            expect(err.hint).toContain("directive");
        }
    });

    test("unterminated unicode property hint", () => {
        try {
            parse(String.raw`[\p{Letter`);
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Unterminated \\p{...}");
            expect(err.hint).not.toBeNull();
            expect(err.hint).toContain("syntax \\p{Property}");
        }
    });
});

describe("Complex Error Scenarios", () => {
    test("nested groups error shows outermost", () => {
        try {
            parse("((abc");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Unterminated group");
        }
    });

    test("error in alternation branch", () => {
        try {
            parse("a|(b");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Unterminated group");
            // Position should point to the end where ')' is expected
            expect(err.pos).toBe(4);
        }
    });

    test("error with free spacing mode", () => {
        const pattern = "%flags x\n(abc\n  def";
        try {
            parse(pattern);
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.hint).not.toBeNull();
        }
    });

    test("error position accuracy", () => {
        try {
            parse("abc{2,");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toContain("Unterminated {m,n}");
            // Position should be at the end where '}' is expected
            expect(err.pos).toBe(6);
        }
    });
});

describe("Error Backward Compatibility", () => {
    test("error has message attribute", () => {
        try {
            parse("(");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.message).toBeDefined();
            expect(err.message).toBe("Unterminated group");
        }
    });

    test("error has pos attribute", () => {
        try {
            parse("abc)");
            fail("Expected STRlingParseError");
        } catch (error) {
            const err = error as STRlingParseError;
            expect(err.pos).toBeDefined();
            expect(err.pos).toBe(3);
        }
    });

    test("error string contains position", () => {
        try {
            parse(")");
            fail("Expected STRlingParseError");
        } catch (error) {
            const formatted = (error as STRlingParseError).toString();
            // Should contain position information in the formatted output
            expect(formatted).toContain(">"); // Line markers
            expect(formatted).toContain("^"); // Caret pointer
        }
    });
});
