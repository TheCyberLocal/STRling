import { parse, ParseError } from "../../src/STRling/core/parser";
import { STRlingParseError } from "../../src/STRling/core/errors";

describe("IEH Audit Gap Remediation (ported from Python)", () => {
    describe("Group name validation", () => {
        test("group name cannot start with digit", () => {
            expect(() => parse("(?<1a>)")).toThrow(STRlingParseError);
            try {
                parse("(?<1a>)");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid group name/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/IDENTIFIER/);
            }
        });

        test("group name cannot be empty", () => {
            expect(() => parse("(?<>)")).toThrow(STRlingParseError);
            try {
                parse("(?<>)");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid group name/);
                expect(e.hint).toBeTruthy();
            }
        });

        test("group name cannot contain hyphens", () => {
            expect(() => parse("(?<name-bad>)")).toThrow(STRlingParseError);
            try {
                parse("(?<name-bad>)");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid group name/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/IDENTIFIER/);
            }
        });
    });

    describe("Quantifier range validation", () => {
        test("quantifier range min cannot exceed max", () => {
            expect(() => parse("a{5,2}")).toThrow(STRlingParseError);
            try {
                parse("a{5,2}");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid quantifier range/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/m.*<=.*n|m <= n|m ≤ n/);
            }
        });
    });

    describe("Character class range validation", () => {
        test("reversed letter ranges are rejected", () => {
            expect(() => parse("[z-a]")).toThrow(STRlingParseError);
            try {
                parse("[z-a]");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid character range/);
                expect(e.hint).toBeTruthy();
            }
        });

        test("reversed digit ranges are rejected", () => {
            expect(() => parse("[9-0]")).toThrow(STRlingParseError);
            try {
                parse("[9-0]");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid character range/);
                expect(e.hint).toBeTruthy();
            }
        });
    });

    describe("Empty alternation validation", () => {
        test("empty alternation branch is rejected", () => {
            expect(() => parse("a||b")).toThrow(STRlingParseError);
            try {
                parse("a||b");
            } catch (e: any) {
                expect(e.message).toMatch(/Empty alternation/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/a\|b/);
            }
        });
    });

    describe("Flag directive validation", () => {
        test("invalid flag letters are rejected", () => {
            expect(() => parse("%flags foo")).toThrow(STRlingParseError);
            try {
                parse("%flags foo");
            } catch (e: any) {
                expect(e.message).toMatch(/Invalid flag/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/i/);
                expect(e.hint).toMatch(/m/);
            }
        });

        test("directive after pattern is rejected", () => {
            expect(() => parse("abc%flags i")).toThrow(STRlingParseError);
            try {
                parse("abc%flags i");
            } catch (e: any) {
                expect(e.message).toMatch(/Directive after pattern/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/start of the pattern/);
            }
        });
    });

    describe("Incomplete named backref hint", () => {
        test("incomplete named backref has hint", () => {
            expect(() => parse(String.raw`\k`)).toThrow(STRlingParseError);
            try {
                parse(String.raw`\k`);
            } catch (e: any) {
                expect(e.message).toMatch(/Expected '<' after \\k/);
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/\\k<name>/);
            }
        });
    });

    describe("Context-aware quantifier hints", () => {
        test("plus quantifier hint mentions plus", () => {
            expect(() => parse("+")).toThrow(STRlingParseError);
            try {
                parse("+");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/'\+'/);
            }
        });

        test("question quantifier hint mentions question", () => {
            expect(() => parse("?")).toThrow(STRlingParseError);
            try {
                parse("?");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/'\?'/);
            }
        });

        test("brace quantifier hint mentions brace", () => {
            expect(() => parse("{5}")).toThrow(STRlingParseError);
            try {
                parse("{5}");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/'\{'/);
            }
        });
    });

    describe("Context-aware escape hints", () => {
        test("unknown escape \\q has dynamic hint", () => {
            expect(() => parse(String.raw`\q`)).toThrow(STRlingParseError);
            try {
                parse(String.raw`\q`);
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/\\q|q/);
            }
        });

        test("unknown escape \\z suggests \\Z", () => {
            expect(() => parse(String.raw`\z`)).toThrow(STRlingParseError);
            try {
                parse(String.raw`\z`);
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/\\z/);
                expect(e.hint).toMatch(/\\Z/);
            }
        });
    });

    describe("Valid patterns still work", () => {
        test("valid group names still work", () => {
            expect(() => parse("(?<name>abc)")).not.toThrow();
            expect(() => parse("(?<_name>abc)")).not.toThrow();
            expect(() => parse("(?<name123>abc)")).not.toThrow();
            expect(() => parse("(?<Name_123>abc)")).not.toThrow();
        });

        test("valid quantifier ranges still work", () => {
            expect(() => parse("a{2,5}")).not.toThrow();
            expect(() => parse("a{2,2}")).not.toThrow();
            expect(() => parse("a{0,10}")).not.toThrow();
        });

        test("valid character ranges still work", () => {
            expect(() => parse("[a-z]")).not.toThrow();
            expect(() => parse("[0-9]")).not.toThrow();
            expect(() => parse("[A-Z]")).not.toThrow();
        });

        test("single alternation still works", () => {
            expect(() => parse("a|b")).not.toThrow();
            expect(() => parse("a|b|c")).not.toThrow();
        });

        test("valid flags still work", () => {
            expect(() => parse("%flags i\nabc")).not.toThrow();
            expect(() => parse("%flags imsux\nabc")).not.toThrow();
        });

        test("brace quantifier rejects non-digits", () => {
            expect(() => parse("a{foo}")).toThrow(STRlingParseError);
            try {
                parse("a{foo}");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/digit|number|digits/);
            }
        });

        test("unterminated brace quantifier reports hint", () => {
            expect(() => parse("a{5")).toThrow(STRlingParseError);
            try {
                parse("a{5");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/closing '\}'|Unterminated brace/);
            }
        });

        test("empty character class reports hint", () => {
            expect(() => parse("[]")).toThrow(STRlingParseError);
            try {
                parse("[]");
            } catch (e: any) {
                expect(e.hint).toBeTruthy();
                expect(e.hint).toMatch(/empty|add characters/);
            }
        });
    });
});
