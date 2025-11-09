/**
 * @file Test Design — pcre2_emitter.test.ts
 *
 * ## Purpose
 * This test suite provides end-to-end (E2E) validation of the entire STRling
 * compiler pipeline, from a source DSL string to the final PCRE2 regex string.
 * It serves as a high-level integration test to ensure that the parser,
 * compiler, and emitter work together correctly to produce valid output for a
 * set of canonical "golden" patterns.
 *
 * ## Description
 * Unlike the unit tests which inspect individual components, this E2E suite
 * treats the compiler as a black box. It provides a STRling DSL string as
 * input and asserts that the final emitted string is exactly as expected for
 * the PCRE2 target. These tests are designed to catch regressions and verify the
 * correct integration of all core components, including the handling of
 * PCRE2-specific extension features like atomic groups.
 *
 * ## Scope
 * -   **In scope:**
 * -   The final string output of the full `parse -> compile -> emit`
 * pipeline for a curated list of representative patterns.
 * -   Verification that the emitted string is syntactically correct for
 * the PCRE2 engine.
 * -   End-to-end testing of PCRE2-supported extension features (e.g.,
 * atomic groups, possessive quantifiers).
 * -   Verification that flags are correctly translated into the `(?imsux)`
 * prefix in the final string.
 * -   **Out of scope:**
 * -   Exhaustive testing of every possible DSL feature (this is the role
 * of the unit tests).
 * -   The runtime behavior of the generated regex string in a live PCRE2
 * engine (this is the purpose of the Sprint 7 conformance suite).
 * -   Detailed validation of the intermediate AST or IR structures.
 */

import { parse, ParseError } from "../../src/STRling/core/parser";
import { Compiler } from "../../src/STRling/core/compiler";
import { emit as emitPcre2 } from "../../src/STRling/emitters/pcre2";

// --- Test Suite Setup -----------------------------------------------------------

/**
 * A helper to run the full DSL -> PCRE2 string pipeline.
 *
 */
function compileToPcre(src: string): string {
    const [flags, ast] = parse(src);
    const irRoot = new Compiler().compile(ast);
    return emitPcre2(irRoot, flags);
}

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Core Language Features", () => {
    /**
     * Covers end-to-end compilation of canonical "golden" patterns for core
     * DSL features.
     */
    test.each<[string, string, string]>([
        // A.1: Complex pattern with named groups, classes, quantifiers, and flags
        [
            "%flags x\n(?<area>\\d{3}) - (?<exchange>\\d{3}) - (?<line>\\d{4})",
            "(?x)(?<area>\\d{3})-(?<exchange>\\d{3})-(?<line>\\d{4})",
            "golden_phone_number",
        ],
        // A.2: Alternation requiring automatic grouping for precedence
        [
            "start(?:a|b|c)end",
            "start(?:a|b|c)end",
            "golden_alternation_precedence",
        ],
        // A.3: Lookarounds and anchors
        ["(?<=^foo)\\w+", "(?<=^foo)\\w+", "golden_lookaround_anchor"],
        // A.4: Unicode properties with the unicode flag
        ["%flags u\n\\p{L}+", "(?u)\\p{L}+", "golden_unicode_property"],
        // A.5: Backreferences and lazy quantifiers
        [
            "<(?<tag>\\w+)>.*?</\\k<tag>>",
            "<(?<tag>\\w+)>.*?</\\k<tag>>",
            "golden_backreference_lazy_quant",
        ],
    ])(
        'should compile golden pattern for "%s" correctly (ID: %s)',
        (inputDsl, expectedRegex) => {
            /**
             * Tests that representative DSL patterns compile to the correct PCRE2 string.
             *
             */
            expect(compileToPcre(inputDsl)).toBe(expectedRegex);
        }
    );
});

describe("Category B: Emitter-Specific Syntax", () => {
    /**
     * Covers emitter-specific syntax generation, like flags and escaping.
     *
     */

    test("should generate all flags correctly", () => {
        /**
         * Tests that all supported flags are correctly prepended to the pattern.
         *
         */
        // Note: The 'a' is needed to create a non-empty pattern
        expect(compileToPcre("%flags imsux\na")).toBe("(?imsux)a");
    });

    test("should escape all metacharacters correctly", () => {
        /**
         * Tests that all regex metacharacters are correctly escaped when used as
         * literals.
         */
        // To test literal metacharacters, escape them in the DSL source
        const metachars = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";
        const escapedMetachars = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";
        expect(compileToPcre(metachars)).toBe(escapedMetachars);
    });
});

describe("Category C: Extension Features", () => {
    /**
     * Covers end-to-end compilation of PCRE2-specific extension features.
     *
     */
    test.each<[string, string, string]>([
        ["(?>a+)", "(?>a+)", "atomic_group"],
        ["a*+", "a*+", "possessive_quantifier"],
        ["\\Astart\\z", "\\Astart\\z", "absolute_anchors"],
    ])(
        'should compile PCRE2 extension for "%s" (ID: %s)',
        (inputDsl, expectedRegex) => {
            /**
             * Tests that DSL constructs corresponding to PCRE2 extensions are emitted
             * correctly.
             */
            expect(compileToPcre(inputDsl)).toBe(expectedRegex);
        }
    );
});

describe("Category D: Error Handling", () => {
    /**
     * Covers how errors from the pipeline are propagated.
     *
     */
    test("should propagate a parse error through the pipeline", () => {
        /**
         * Tests that an invalid DSL string raises a ParseError when the full
         * compilation is attempted.
         */
        expect(() => compileToPcre("a(b")).toThrow(ParseError);
        expect(() => compileToPcre("a(b")).toThrow("Unterminated group");
    });
});
