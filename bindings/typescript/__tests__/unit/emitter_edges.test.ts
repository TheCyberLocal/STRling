/**
 * @file Test Design — unit/emitter_edges.test.ts
 *
 * ## Purpose
 * This test suite validates the logic of the PCRE2 emitter, focusing on its
 * specific responsibilities: correct character escaping, shorthand optimizations,
 * flag prefix generation, and the critical automatic-grouping logic required to
 * preserve operator precedence.
 *
 * ## Description
 * The emitter (`pcre2.ts`) is the final backend stage in the STRling compiler
 * pipeline. It translates the clean, language-agnostic Intermediate
 * Representation (IR) into a syntactically correct PCRE2 regex string. This suite
 * does not test the IR's correctness but verifies that a given valid IR tree is
 * always transformed into the correct and most efficient string representation,
 * with a heavy focus on edge cases where incorrect output could alter a pattern's
 * meaning.
 *
 * ## Scope
 * -   **In scope:**
 * -   The emitter's character escaping logic, both for general literals and
 * within character classes.
 * -   Shorthand optimizations, such as converting `IRCharClass` nodes into
 * `\d` or `\P{Letter}` where appropriate.
 * -   The automatic insertion of non-capturing groups `(?:...)` to maintain
 * correct precedence.
 * -   Generation of the flag prefix `(?imsux)` based on the provided `Flags`
 * object.
 * -   Correct string generation for all PCRE2-supported extension features.
 *
 * -   **Out of scope:**
 * -   The correctness of the input IR tree (this is covered by
 * `test_ir_compiler.ts`).
 * -   The runtime behavior of the generated regex string in a live PCRE2
 * engine (this is covered by end-to-end and conformance tests).
 */

// Note: Adjust paths as needed for your project structure
import {
    emit,
    _escapeLiteral,
    _escapeClassChar,
} from "../../src/STRling/emitters/pcre2";
import { Flags } from "../../src/STRling/core/nodes";
import {
    IRLit,
    IRCharClass,
    IRClassItem,
    IRClassLiteral,
    IRClassEscape,
    IRQuant,
    IRSeq,
    IRAlt,
    IRDot,
    IRGroup,
    IRBackref,
    IRAnchor,
    IROp,
} from "../../src/STRling/core/ir";

// --- Unit Tests for Emitter Helpers (mirroring Python's top-level fns) ---

test("Verify how _escapeLiteral handles '.'", () => {
    // Expected: r'\.'
    expect(_escapeLiteral(".")).toBe(String.raw`\.`);
});

test("Verify how _escapeLiteral handles '\\'", () => {
    // Expected: r'\\'
    expect(_escapeLiteral("\\")).toBe(String.raw`\\`);
});

test("Verify how _escapeLiteral handles '['", () => {
    // Expected: r'\['
    expect(_escapeLiteral("[")).toBe(String.raw`\[`);
});

test("Verify how _escapeLiteral handles '{'", () => {
    // Expected: r'\{'
    expect(_escapeLiteral("{")).toBe(String.raw`\{`);
});

test("Verify how _escapeLiteral handles a plain char 'a'", () => {
    // Expected: 'a'
    expect(_escapeLiteral("a")).toBe("a");
});

test("Verify how _escapeClassChar handles ']' inside class", () => {
    // Expected: \]
    expect(_escapeClassChar("]")).toBe(String.raw`\]`);
});

test("Verify how _escapeClassChar handles '\\' inside class", () => {
    // Expected: \\
    expect(_escapeClassChar("\\")).toBe(String.raw`\\`);
});

test("Verify how _escapeClassChar handles '-' inside class", () => {
    // Expected: \-
    expect(_escapeClassChar("-")).toBe(String.raw`\-`);
});

test("Verify how _escapeClassChar handles '^' inside class", () => {
    // Expected: \^
    expect(_escapeClassChar("^")).toBe(String.raw`\^`);
});

test("Verify how _escapeClassChar handles '[' inside class", () => {
    // Expected: [ (unescaped)
    expect(_escapeClassChar("[")).toBe("[");
});

test("Verify how _escapeClassChar handles '.' inside class", () => {
    // Expected: . (unescaped)
    expect(_escapeClassChar(".")).toBe(".");
});

test("Verify how _escapeClassChar handles '\n' inside class", () => {
    // Expected: \n
    expect(_escapeClassChar("\n")).toBe(String.raw`\n`);
});

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Escaping Logic", () => {
    /**
     * Covers the emitter's character escaping logic.
     */

    test("should escape literal metacharacters", () => {
        /**
         * Tests that all PCRE2 metacharacters are escaped when in an IRLit node.
         */
        const metachars = ".^$|()?*+{}[]\\";
        const expected = String.raw`\.\^\$\|\(\)\?\*\+\{\}\[\]\\`;
        expect(emit(new IRLit(metachars))).toBe(expected);
    });

    test("should escape char class metacharacters", () => {
        /**
         * Tests that special characters inside a character class are escaped.
         */
        const metachars = "]-^";
        const expected = String.raw`[\]\-\^]`;
        const items: IRClassItem[] = metachars
            .split("")
            .map((c) => new IRClassLiteral(c));
        expect(emit(new IRCharClass(false, items))).toBe(expected);
    });
});

describe("Category B: Shorthand Optimizations", () => {
    /**
     * Covers the emitter's logic for optimizing character classes.
     */

    test.each<[IRCharClass, string, string]>([
        [
            new IRCharClass(false, [new IRClassEscape("d")]),
            String.raw`\d`,
            "positive_d_to_shorthand",
        ],
        [
            new IRCharClass(true, [new IRClassEscape("d")]),
            String.raw`\D`,
            "negated_d_to_D_shorthand",
        ],
        [
            new IRCharClass(false, [new IRClassEscape("p", "L")]),
            String.raw`\p{L}`,
            "positive_p_to_shorthand",
        ],
        [
            new IRCharClass(true, [new IRClassEscape("p", "L")]),
            String.raw`\P{L}`,
            "negated_p_to_P_shorthand",
        ],
        [
            new IRCharClass(false, [new IRClassEscape("S")]),
            String.raw`\S`,
            "positive_neg_shorthand_S",
        ],
        [
            new IRCharClass(true, [new IRClassEscape("S")]),
            String.raw`\s`,
            "negated_neg_shorthand_S_to_s",
        ],
    ])(
        "should apply shorthand optimization for %s (ID: %s)",
        (irNode, expectedStr, id) => {
            /**
             * Tests that single-item character classes are collapsed into their
             * shorthand equivalents.
             */
            expect(emit(irNode)).toBe(expectedStr);
        }
    );

    test("should not apply optimization for multi-item class", () => {
        /**
         * Tests that the shorthand optimization is correctly skipped for a class
         * with more than one item.
         */
        const irNode = new IRCharClass(false, [
            new IRClassEscape("d"),
            new IRClassLiteral("_"),
        ]);
        expect(emit(irNode)).toBe(String.raw`[\d_]`);
    });
});

describe("Category C: Automatic Grouping", () => {
    /**
     * Covers the critical logic for preserving operator precedence.
     */

    test.each<[IROp, string, string]>([
        [
            new IRQuant(new IRLit("ab"), 0, "Inf", "Greedy"),
            "(?:ab)*",
            "quantified_multichar_literal",
        ],
        [
            new IRQuant(new IRSeq([new IRLit("a")]), 1, "Inf", "Greedy"),
            "a+",
            "quantified_single_item_sequence",
        ],
        [
            new IRSeq([
                new IRLit("a"),
                new IRAlt([new IRLit("b"), new IRLit("c")]),
            ]),
            "a(?:b|c)",
            "alternation_in_sequence",
        ],
    ])(
        'should add grouping when needed for "%s" (ID: %s)',
        (irNode, expectedStr, id) => {
            /**
             * Tests that non-capturing groups are added to preserve precedence.
             */
            expect(emit(irNode)).toBe(expectedStr);
        }
    );

    test.each<[IROp, string, string]>([
        [
            new IRQuant(
                new IRCharClass(false, [new IRClassLiteral("a")]),
                0,
                "Inf",
                "Greedy"
            ),
            "[a]*",
            "quantified_char_class",
        ],
        [new IRQuant(new IRDot(), 1, "Inf", "Greedy"), ".+", "quantified_dot"],
        [
            new IRQuant(new IRGroup(true, new IRLit("a")), 0, 1, "Greedy"),
            "(a)?",
            "quantified_group",
        ],
    ])(
        'should not add unnecessary grouping for "%s" (ID: %s)',
        (irNode, expectedStr, id) => {
            /**
             * Tests that quantifiers on single atoms do not get extra grouping.
             */
            expect(emit(irNode)).toBe(expectedStr);
        }
    );
});

describe("Category D: Flags and Emitter Directives", () => {
    /**
     * Covers flag prefixes and other PCRE2-specific syntax.
     */

    test.each<[Flags | null, string, string]>([
        [new Flags({ ignoreCase: true, multiline: true }), "(?im)", "im_flags"],
        [
            new Flags({ dotAll: true, unicode: true, extended: true }),
            "(?sux)",
            "sux_flags",
        ],
        [new Flags(), "", "default_flags"],
        [null, "", "no_flags_object"],
    ])(
        "should generate correct flag prefix for %s (ID: %s)",
        (flags, expectedPrefix, id) => {
            /** Tests that the correct (?...) prefix is generated from a Flags object. */
            expect(emit(new IRLit("a"), flags)).toBe(`${expectedPrefix}a`);
        }
    );

    test("should generate PCRE2-specific named group and backref syntax", () => {
        /** Tests that PCRE2-specific named group syntax is generated. */
        const ir = new IRSeq([
            new IRGroup(true, new IRLit("a"), "x"),
            new IRBackref(undefined, "x"),
        ]);
        expect(emit(ir)).toBe(String.raw`(?<x>a)\k<x>`);
    });
});

describe("Category E: Extension Features", () => {
    /**
     * Covers the emission of PCRE2 extension features.
     */

    test.each<[IROp, string, string]>([
        [
            new IRGroup(
                false,
                new IRQuant(new IRLit("a"), 1, "Inf", "Greedy"),
                undefined,
                true
            ),
            "(?>a+)",
            "atomic_group",
        ],
        [
            new IRQuant(new IRLit("a"), 0, "Inf", "Possessive"),
            "a*+",
            "possessive_star",
        ],
        [
            new IRQuant(new IRCharClass(false, []), 1, "Inf", "Possessive"),
            "[]++",
            "possessive_plus",
        ],
        [
            new IRAnchor("AbsoluteStart"),
            String.raw`\A`,
            "absolute_start_anchor",
        ],
    ])(
        'should emit extension feature "%s" correctly (ID: %s)',
        (irNode, expectedStr, id) => {
            /**
             * Tests that extension features like atomic groups and possessive
             * quantifiers are emitted with the correct PCRE2 syntax.
             */
            expect(emit(irNode)).toBe(expectedStr);
        }
    );
});
