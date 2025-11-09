/**
 * @file Test Design — e2e/test_pcre2_emitter.ts
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
 *
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
 *
 * -   Detailed validation of the intermediate AST or IR structures.
 */

// Note: Imports assume a project structure. Update paths as needed.
import { parse, ParseError } from "../../src/STRling/core/parser";
import { Compiler } from "../../src/STRling/core/compiler";
import { emit as emitPcre2 } from "../../src/STRling/emitters/pcre2";

// --- Test Suite Setup -----------------------------------------------------------

function compileToPcre(src: string): string {
    /**A helper to run the full DSL -> PCRE2 string pipeline.*/
    const [flags, ast] = parse(src);
    const irRoot = new Compiler().compile(ast);
    return emitPcre2(irRoot, flags);
}

// Type alias for cleaner test.each
type TestCase = [string, string, string];

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Core Language Features", () => {
    /**
     * Covers end-to-end compilation of canonical "golden" patterns for core
     * DSL features.
     */

    const cases: TestCase[] = [
        // A.1: Complex pattern with named groups, classes, quantifiers, and flags
        [
            "%flags x\n(?<area>\\d{3}) - (?<exchange>\\d{3}) - (?<line>\\d{4})",
            String.raw`(?x)(?<area>\d{3})-(?<exchange>\d{3})-(?<line>\d{4})`,
            "golden_phone_number",
        ],
        // A.2: Alternation requiring automatic grouping for precedence
        [
            "start(?:a|b|c)end",
            String.raw`start(?:a|b|c)end`,
            "golden_alternation_precedence",
        ],
        // A.3: Lookarounds and anchors
        [
            String.raw`(?<=^foo)\w+`,
            String.raw`(?<=^foo)\w+`,
            "golden_lookaround_anchor",
        ],
        // A.4: Unicode properties with the unicode flag
        [
            "%flags u\n\\p{L}+",
            String.raw`(?u)\p{L}+`,
            "golden_unicode_property",
        ],
        // A.5: Backreferences and lazy quantifiers
        [
            String.raw`<(?<tag>\w+)>.*?</\k<tag>>`,
            String.raw`<(?<tag>\w+)>.*?</\k<tag>>`,
            "golden_backreference_lazy_quant",
        ],
    ];

    test.each(cases)("ID: %s", (inputDsl, expectedRegex, id) => {
        /**
         * Tests that representative DSL patterns compile to the correct PCRE2 string.
         */
        expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    });
});

describe("Category B: Emitter-Specific Syntax", () => {
    /**
     * Covers emitter-specific syntax generation, like flags and escaping.
     */

    test("all flags are generated correctly", () => {
        /**
         * Tests that all supported flags are correctly prepended to the pattern.
         */
        // Note: The 'a' is needed to create a non-empty pattern
        expect(compileToPcre("%flags imsux\na")).toBe("(?imsux)a");
    });

    test("all metacharacters are escaped", () => {
        /**
         * Tests that all regex metacharacters are correctly escaped when used as
         * literals.
         */
        // To test literal metacharacters, escape them in the DSL source
        const metacharsDsl = String.raw`\.\^\$\|\(\)\?\*\+\{\}\[\]\\`;
        const metacharsLiteral = ".^$|()?*+{}[]\\";

        // This regex escapes all special PCRE metacharacters for a literal context
        const escapedMetachars = metacharsLiteral.replace(
            /[.^$|()?*+{}\[\]\\]/g,
            "\\$&"
        );

        expect(compileToPcre(metacharsDsl)).toBe(escapedMetachars);
    });
});

describe("Category C: Extension Features", () => {
    /**
     * Covers end-to-end compilation of PCRE2-specific extension features.
     */

    const cases: TestCase[] = [
        [String.raw`(?>a+)`, String.raw`(?>a+)`, "atomic_group"],
        [String.raw`a*+`, String.raw`a*+`, "possessive_quantifier"],
        [String.raw`\Astart\z`, String.raw`\Astart\z`, "absolute_anchors"],
    ];

    test.each(cases)("ID: %s", (inputDsl, expectedRegex, id) => {
        /**
         * Tests that DSL constructs corresponding to PCRE2 extensions are emitted
         * correctly.
         */
        expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    });
});

describe("Category D: Golden Patterns", () => {
    /**
     * Covers real-world "golden" patterns that validate STRling can solve
     * complete, production-grade validation and parsing problems.
     */

    const cases: [string, string, string][] = [
        // Category 1: Common Validation Patterns
        // Email Address (RFC 5322 subset - simplified)
        [
            String.raw`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`,
            String.raw`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`,
            "Email address validation (simplified RFC 5322)",
        ],
        // UUID v4
        [
            String.raw`[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`,
            String.raw`[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`,
            "UUID v4 validation",
        ],
        // Semantic Version (SemVer)
        [
            String.raw`(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)(?:-(?<prerelease>[0-9A-Za-z-.]+))?(?:\+(?<build>[0-9A-Za-z-.]+))?`,
            String.raw`(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)(?:-(?<prerelease>[0-9A-Za-z\-.]+))?(?:\+(?<build>[0-9A-Za-z\-.]+))?`,
            "Semantic version validation",
        ],
        // URL / URI
        [
            String.raw`(?<scheme>https?)://(?<host>[a-zA-Z0-9.-]+)(?::(?<port>\d+))?(?<path>/\S*)?`,
            String.raw`(?<scheme>https?)://(?<host>[a-zA-Z0-9.\-]+)(?::(?<port>\d+))?(?<path>/\S*)?`,
            "HTTP/HTTPS URL validation",
        ],

        // Category 2: Common Parsing/Extraction Patterns
        // Log File Line (Nginx access log format)
        [
            String.raw`(?<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\ -\ (?<user>\S+)\ \[(?<time>[^\]]+)\]\ "(?<method>\w+)\ (?<path>\S+)\ HTTP/(?<version>[\d.]+)"\ (?<status>\d+)\ (?<size>\d+)`,
            String.raw`(?<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\ -\ (?<user>\S+)\ \[(?<time>[^\]]+)\]\ "(?<method>\w+)\ (?<path>\S+)\ HTTP/(?<version>[\d.]+)"\ (?<status>\d+)\ (?<size>\d+)`,
            "Nginx access log parsing",
        ],
        // ISO 8601 Timestamp
        [
            String.raw`(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})T(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(?:\.(?<fraction>\d+))?(?<tz>Z|[+\-]\d{2}:\d{2})?`,
            String.raw`(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})T(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(?:\.(?<fraction>\d+))?(?<tz>Z|[+\-]\d{2}:\d{2})?`,
            "ISO 8601 timestamp parsing",
        ],

        // Category 3: Advanced Feature Stress Tests
        // Password Policy (multiple lookaheads)
        [
            String.raw`(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}`,
            String.raw`(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}`,
            "Password policy with multiple lookaheads",
        ],
        // ReDoS-Safe Pattern using atomic group
        [
            String.raw`(?>a+)b`,
            String.raw`(?>a+)b`,
            "ReDoS-safe pattern with atomic group",
        ],
        // ReDoS-Safe Pattern using possessive quantifier
        [
            String.raw`a*+b`,
            String.raw`a*+b`,
            "ReDoS-safe pattern with possessive quantifier",
        ],
    ];

    test.each(cases)("ID: %s", (inputDsl, expectedRegex, description) => {
        /**
         * Tests that STRling can compile real-world patterns used in production
         * for validation, parsing, and extraction tasks.
         */
        expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    });
});

describe("Category E: Error Handling", () => {
    /**
     * Covers how errors from the pipeline are propagated.
     */

    test("parse error propagates through the full pipeline", () => {
        /**
         * Tests that an invalid DSL string raises a ParseError when the full
         * compilation is attempted.
         */
        expect(() => compileToPcre("a(b")).toThrow(ParseError);
        expect(() => compileToPcre("a(b")).toThrow("Unterminated group");
    });
});
