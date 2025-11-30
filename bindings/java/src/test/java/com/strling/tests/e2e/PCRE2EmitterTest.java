package com.strling.tests.e2e;

import com.strling.core.Compiler;
import com.strling.core.IR.IROp;
import com.strling.core.Nodes.Flags;
import com.strling.core.Nodes.Node;
import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import com.strling.emitters.Pcre2Emitter;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — e2e/PCRE2EmitterTest.java
 *
 * <h2>Purpose</h2>
 * This test suite provides end-to-end (E2E) validation of the entire STRling
 * compiler pipeline, from a source DSL string to the final PCRE2 regex string.
 * It serves as a high-level integration test to ensure that the parser,
 * compiler, and emitter work together correctly to produce valid output for a
 * set of canonical "golden" patterns.
 *
 * <h2>Description</h2>
 * Unlike the unit tests which inspect individual components, this E2E suite
 * treats the compiler as a black box. It provides a STRling DSL string as
 * input and asserts that the final emitted string is exactly as expected for
 * the PCRE2 target. These tests are designed to catch regressions and verify the
 * correct integration of all core components, including the handling of
 * PCRE2-specific extension features like atomic groups.
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>The final string output of the full {@code parse -> compile -> emit}
 * pipeline for a curated list of representative patterns.</li>
 * <li>Verification that the emitted string is syntactically correct for
 * the PCRE2 engine.</li>
 * <li>End-to-end testing of PCRE2-supported extension features (e.g.,
 * atomic groups, possessive quantifiers).</li>
 * <li>Verification that flags are correctly translated into the {@code (?imsux)}
 * prefix in the final string.</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Exhaustive testing of every possible DSL feature (this is the role
 * of the unit tests).</li>
 * <li>The runtime behavior of the generated regex string in a live PCRE2
 * engine (this is the purpose of the Sprint 7 conformance suite).</li>
 * <li>Detailed validation of the intermediate AST or IR structures.</li>
 * </ul>
 * </ul>
 */
public class PCRE2EmitterTest {

    // --- Test Suite Setup ---------------------------------------------------

    /**
     * A helper to run the full DSL -> PCRE2 string pipeline.
     */
    private String compileToPcre(String src) {
        Parser.ParseResult result = Parser.parse(src);
        Flags flags = result.flags;
        Node ast = result.ast;
        Compiler compiler = new Compiler();
        IROp irRoot = compiler.compile(ast);
        return Pcre2Emitter.emit(irRoot, flags);
    }

    // --- Test Suite ---------------------------------------------------------

    /**
     * Covers end-to-end compilation of canonical "golden" patterns for core
     * DSL features.
     */
    @Nested
    @TestInstance(TestInstance.Lifecycle.PER_CLASS)
    class CategoryACoreLanguageFeatures {

        Stream<Arguments> testCases() {
            return Stream.of(
                // A.1: Complex pattern with named groups, classes, quantifiers, and flags
                Arguments.of(
                    "%flags x\n(?<area>\\d{3}) - (?<exchange>\\d{3}) - (?<line>\\d{4})",
                    "(?x)(?<area>\\d{3})-(?<exchange>\\d{3})-(?<line>\\d{4})",
                    "golden_phone_number"
                ),
                // A.2: Alternation requiring automatic grouping for precedence
                Arguments.of(
                    "start(?:a|b|c)end",
                    "start(?:a|b|c)end",
                    "golden_alternation_precedence"
                ),
                // A.3: Lookarounds and anchors
                Arguments.of(
                    "(?<=^foo)\\w+",
                    "(?<=^foo)\\w+",
                    "golden_lookaround_anchor"
                ),
                // A.4: Unicode properties with the unicode flag
                Arguments.of(
                    "%flags u\n\\p{L}+",
                    "(?u)\\p{L}+",
                    "golden_unicode_property"
                ),
                // A.5: Backreferences and lazy quantifiers
                Arguments.of(
                    "<(?<tag>\\w+)>.*?</\\k<tag>>",
                    "<(?<tag>\\w+)>.*?</\\k<tag>>",
                    "golden_backreference_lazy_quant"
                )
            );
        }

        @ParameterizedTest(name = "ID: {2}")
        @MethodSource("testCases")
        void testCoreLanguageFeatures(String inputDsl, String expectedRegex, String id) {
            /**
             * Tests that representative DSL patterns compile to the correct PCRE2 string.
             */
            assertEquals(expectedRegex, compileToPcre(inputDsl));
        }
    }

    /**
     * Covers emitter-specific syntax generation, like flags and escaping.
     */
    @Nested
    class CategoryBEmitterSpecificSyntax {

        @Test
        void allFlagsAreGeneratedCorrectly() {
            /**
             * Tests that all supported flags are correctly prepended to the pattern.
             * Note: The 'a' is needed to create a non-empty pattern
             */
            assertEquals("(?imsux)a", compileToPcre("%flags imsux\na"));
        }

        @Test
        void allMetacharactersAreEscaped() {
            /**
             * Tests that all regex metacharacters are correctly escaped when used as
             * literals.
             */
            // To test literal metacharacters, escape them in the DSL source
            String metacharsDsl = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";
            String expectedEscaped = "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\";

            assertEquals(expectedEscaped, compileToPcre(metacharsDsl));
        }
    }

    /**
     * Covers end-to-end compilation of PCRE2-specific extension features.
     */
    @Nested
    @TestInstance(TestInstance.Lifecycle.PER_CLASS)
    class CategoryCExtensionFeatures {

        Stream<Arguments> testCases() {
            return Stream.of(
                Arguments.of("(?>a+)", "(?>a+)", "atomic_group"),
                Arguments.of("a*+", "a*+", "possessive_quantifier")
            );
        }

        @ParameterizedTest(name = "ID: {2}")
        @MethodSource("testCases")
        void testExtensionFeatures(String inputDsl, String expectedRegex, String id) {
            /**
             * Tests that DSL constructs corresponding to PCRE2 extensions are emitted
             * correctly.
             */
            assertEquals(expectedRegex, compileToPcre(inputDsl));
        }
    }

    /**
     * Covers real-world "golden" patterns that validate STRling can solve
     * complete, production-grade validation and parsing problems.
     */
    @Nested
    @TestInstance(TestInstance.Lifecycle.PER_CLASS)
    class CategoryDGoldenPatterns {

        Stream<Arguments> testCases() {
            return Stream.of(
                // Category 1: Common Validation Patterns
                // Email Address (RFC 5322 subset - simplified)
                Arguments.of(
                    "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
                    "[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}",
                    "Email address validation (simplified RFC 5322)"
                ),
                // UUID v4
                Arguments.of(
                    "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                    "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                    "UUID v4 validation"
                ),
                // Semantic Version (SemVer)
                Arguments.of(
                    "(?<major>\\d+)\\.(?<minor>\\d+)\\.(?<patch>\\d+)(?:-(?<prerelease>[0-9A-Za-z-.]+))?(?:\\+(?<build>[0-9A-Za-z-.]+))?",
                    "(?<major>\\d+)\\.(?<minor>\\d+)\\.(?<patch>\\d+)(?:-(?<prerelease>[0-9A-Za-z\\-.]+))?(?:\\+(?<build>[0-9A-Za-z\\-.]+))?",
                    "Semantic version validation"
                ),
                // URL / URI
                Arguments.of(
                    "(?<scheme>https?)://(?<host>[a-zA-Z0-9.-]+)(?::(?<port>\\d+))?(?<path>/\\S*)?",
                    "(?<scheme>https?)://(?<host>[a-zA-Z0-9.\\-]+)(?::(?<port>\\d+))?(?<path>/\\S*)?",
                    "HTTP/HTTPS URL validation"
                ),
                // ISO 8601 Timestamp
                Arguments.of(
                    "(?<year>\\d{4})-(?<month>\\d{2})-(?<day>\\d{2})T(?<hour>\\d{2}):(?<minute>\\d{2}):(?<second>\\d{2})(?:\\.(?<fraction>\\d+))?(?<tz>Z|[+\\-]\\d{2}:\\d{2})?",
                    "(?<year>\\d{4})-(?<month>\\d{2})-(?<day>\\d{2})T(?<hour>\\d{2}):(?<minute>\\d{2}):(?<second>\\d{2})(?:\\.(?<fraction>\\d+))?(?<tz>Z|[+\\-]\\d{2}:\\d{2})?",
                    "ISO 8601 timestamp parsing"
                ),
                // Password Policy (multiple lookaheads)
                Arguments.of(
                    "(?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}",
                    "(?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}",
                    "Password policy with multiple lookaheads"
                ),
                // ReDoS-Safe Pattern using atomic group
                Arguments.of(
                    "(?>a+)b",
                    "(?>a+)b",
                    "ReDoS-safe pattern with atomic group"
                ),
                // ReDoS-Safe Pattern using possessive quantifier
                Arguments.of(
                    "a*+b",
                    "a*+b",
                    "ReDoS-safe pattern with possessive quantifier"
                )
            );
        }

        @ParameterizedTest(name = "ID: {2}")
        @MethodSource("testCases")
        void testGoldenPatterns(String inputDsl, String expectedRegex, String description) {
            /**
             * Tests that STRling can compile real-world patterns used in production
             * for validation, parsing, and extraction tasks.
             */
            assertEquals(expectedRegex, compileToPcre(inputDsl));
        }

        @Test
        void nginxAccessLogPatternRaisesOnEscapedSpace() {
            /**
             * Nginx access log pattern raises on escaped space
             */
            String nginx = "(?<ip>\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})\\ -\\ (?<user>\\S+)\\ \\[(?<time>[^\\]]+)\\]\\ \"(?<method>\\w+)\\ (?<path>\\S+)\\ HTTP/(?<version>[\\d.]+)\"\\ (?<status>\\d+)\\ (?<size>\\d+)";
            
            STRlingParseError error = assertThrows(
                STRlingParseError.class, 
                () -> compileToPcre(nginx)
            );
            assertTrue(error.getMessage().contains("Unknown escape sequence"));
        }
    }

    /**
     * Covers how errors from the pipeline are propagated.
     */
    @Nested
    class CategoryEErrorHandling {

        @Test
        void parseErrorPropagatesThroughTheFullPipeline() {
            /**
             * Tests that an invalid DSL string raises a ParseError when the full
             * compilation is attempted.
             */
            STRlingParseError error = assertThrows(
                STRlingParseError.class, 
                () -> compileToPcre("a(b")
            );
            assertTrue(error.getMessage().contains("Unterminated group"));
        }

        @Test
        void zEscapeInExtensionFeaturesShouldRaise() {
            /**
             * Ensure a pattern containing lowercase \z raises through the pipeline
             */
            STRlingParseError error = assertThrows(
                STRlingParseError.class, 
                () -> compileToPcre("\\Astart\\z")
            );
            assertTrue(error.getMessage().contains("Unknown escape sequence \\z"));
        }
    }
}
