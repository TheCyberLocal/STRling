package com.strling.tests.unit;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.strling.core.CompileResult;
import com.strling.core.IR.IRGroup;
import com.strling.core.IR.IRLit;
import com.strling.core.IR.IRLook;
import com.strling.core.IR.IROp;
import com.strling.core.IR.IRQuant;
import com.strling.core.STRlingCompilationError;
import com.strling.core.STRlingWarning;
import com.strling.emitters.Pcre2Emitter;

import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * Emitter Edges Conformance — Java bridge.
 *
 * <p>Drives the global pathological-AST fixture
 * {@code tests/conformance/inputs/emitter_edges/pathological.json} through
 * the Java {@link Pcre2Emitter} and asserts each safety guard
 * fires:</p>
 *
 * <ol>
 *   <li>Variable-Length Lookbehind Rejection — STRlingCompilationError</li>
 *   <li>AST Depth Limit Exceeded             — STRlingCompilationError</li>
 *   <li>ReDoS Risk Warning (nested {@code (a+)+}) — non-fatal STRlingWarning</li>
 * </ol>
 *
 * <p>The fixture's {@code ast} field is the user-facing AST sketch (e.g.
 * {@code {type: "Lookbehind", content: ...}}), not the post-lowering IR.
 * The local {@code astToIr} adapter mirrors the TypeScript bridge's
 * {@code astToIR} so the test targets the emitter without coupling to
 * the parser/compiler stages. Keep it minimal — supporting only the node
 * types present in {@code pathological.json} — so adapter omissions
 * cannot mask emitter bugs by silently dropping nodes.</p>
 */
public class EmitterEdgesConformanceTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * Path to the global fixture. Maven runs tests with {@code user.dir}
     * pointing at {@code bindings/java}, so we climb two parents to reach
     * the workspace root.
     */
    private static final Path FIXTURE_PATH = Paths.get(
        System.getProperty("user.dir"), "..", "..",
        "tests", "conformance", "inputs", "emitter_edges", "pathological.json"
    ).normalize();

    private static final Pattern ERROR_PREFIX =
        Pattern.compile("^STRlingCompilationError:\\s*(.*)$");
    private static final Pattern WARNING_PREFIX =
        Pattern.compile("^STRlingWarning\\s*\\[[^\\]]+\\]:\\s*(.*)$");

    /**
     * Convert a pathological-fixture AST sketch into Java IR. Supports
     * only the node types currently appearing in {@code pathological.json}.
     * Extend deliberately when new vectors are added so coverage gaps
     * surface as exceptions rather than silent passes.
     */
    private static IROp astToIr(JsonNode node) {
        String type = node.get("type").asText();

        switch (type) {
            case "Literal": {
                String value = node.has("value") ? node.get("value").asText() : "";
                return new IRLit(value);
            }
            case "Group": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("Group node missing 'content'");
                }
                // Pathological fixtures use non-capturing groups for nesting.
                return new IRGroup(false, astToIr(content));
            }
            case "Quantifier": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("Quantifier node missing 'content'");
                }
                IROp child = astToIr(content);
                int min = node.has("min") ? node.get("min").asInt(0) : 0;
                JsonNode maxNode = node.get("max");
                // ``null`` in the user-facing AST means unbounded → IR sentinel "Inf".
                Object max = (maxNode == null || maxNode.isNull())
                    ? "Inf"
                    : (Object) maxNode.asInt();
                String mode = node.has("mode") ? node.get("mode").asText() : "Greedy";
                return new IRQuant(child, min, max, mode);
            }
            case "Lookbehind": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("Lookbehind node missing 'content'");
                }
                return new IRLook("Behind", false, astToIr(content));
            }
            case "NegativeLookbehind": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("NegativeLookbehind node missing 'content'");
                }
                return new IRLook("Behind", true, astToIr(content));
            }
            case "Lookahead": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("Lookahead node missing 'content'");
                }
                return new IRLook("Ahead", false, astToIr(content));
            }
            case "NegativeLookahead": {
                JsonNode content = node.get("content");
                if (content == null) {
                    throw new IllegalArgumentException("NegativeLookahead node missing 'content'");
                }
                return new IRLook("Ahead", true, astToIr(content));
            }
            default:
                throw new IllegalArgumentException(
                    "astToIr: unsupported pathological AST node type \"" + type + "\". "
                  + "Extend the adapter when new pathological vectors are added."
                );
        }
    }

    /**
     * Strip the {@code STRlingCompilationError: } / {@code STRlingWarning [CODE]: }
     * prefix so the remainder can be substring-matched against the actual
     * error message / warning message text.
     */
    private static String expectedSubstring(String prefixed) {
        Matcher em = ERROR_PREFIX.matcher(prefixed);
        if (em.matches()) return em.group(1);
        Matcher wm = WARNING_PREFIX.matcher(prefixed);
        if (wm.matches()) return wm.group(1);
        return prefixed;
    }

    @TestFactory
    public Stream<DynamicTest> pathologicalCases() throws IOException {
        assertTrue(Files.isRegularFile(FIXTURE_PATH),
            "emitter_edges fixture not found at " + FIXTURE_PATH);

        JsonNode root = MAPPER.readTree(Files.readString(FIXTURE_PATH));
        JsonNode tests = root.get("tests");
        assertNotNull(tests, "fixture missing 'tests' array");
        assertTrue(tests.isArray() && tests.size() > 0, "fixture has no test cases");

        List<DynamicTest> dynamic = new ArrayList<>();
        for (JsonNode tc : tests) {
            String name = tc.get("name").asText();
            dynamic.add(DynamicTest.dynamicTest(name, () -> runCase(tc)));
        }
        return dynamic.stream();
    }

    private static void runCase(JsonNode tc) {
        IROp ir = astToIr(tc.get("ast"));
        int maxDepth = tc.has("depth_override_for_test")
            ? tc.get("depth_override_for_test").asInt(0)
            : 0;

        if (tc.has("expected_error")) {
            String needle = expectedSubstring(tc.get("expected_error").asText());
            STRlingCompilationError err = assertThrows(
                STRlingCompilationError.class,
                () -> Pcre2Emitter.emitWithDiagnostics(ir, null, maxDepth),
                "expected STRlingCompilationError"
            );
            assertTrue(err.getMessage().contains(needle),
                "expected error to contain \"" + needle + "\"; got " + err.getMessage());
            return;
        }

        if (tc.has("expected_warning")) {
            String needle = expectedSubstring(tc.get("expected_warning").asText());
            CompileResult result = Pcre2Emitter.emitWithDiagnostics(ir, null, maxDepth);
            // Warnings must NOT abort emission — the pattern is still produced.
            assertNotNull(result.getPattern());
            assertFalse(result.getPattern().isEmpty(),
                "expected non-empty pattern when only a warning fires");
            boolean found = result.getWarnings().stream()
                .anyMatch(w -> w.getMessage().contains(needle));
            assertTrue(found,
                "expected REDOS_RISK warning containing \"" + needle + "\"; got "
                  + result.getWarnings());
            return;
        }

        fail("Test case \"" + tc.get("name").asText()
           + "\" declares neither expected_error nor expected_warning.");
    }

    // --- Negative controls ---------------------------------------------------

    @Test
    public void nonPathologicalPatternEmitsNoWarnings() {
        CompileResult result = Pcre2Emitter.emitWithDiagnostics(new IRLit("abc"), null);
        assertEquals("abc", result.getPattern());
        assertTrue(result.getWarnings().isEmpty(),
            "plain literal must not raise diagnostic warnings");
    }

    @Test
    public void depthCapDoesNotFireUnderLimit() {
        // Two nested groups under a depth cap of 5 must compile cleanly.
        IROp deep = new IRGroup(false, new IRGroup(false, new IRLit("ok")));
        CompileResult result = Pcre2Emitter.emitWithDiagnostics(deep, null, 5);
        assertTrue(result.getWarnings().isEmpty());
        assertTrue(result.getPattern().contains("ok"));
    }
}
