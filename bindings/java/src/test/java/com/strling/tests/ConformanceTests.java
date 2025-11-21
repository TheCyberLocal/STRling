package com.strling.tests;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.strling.core.nodes.IRNode;
import com.strling.core.JsonAstCompiler;
import com.strling.core.IR.IROp;
import com.strling.emitters.Pcre2Emitter;
import com.strling.core.Nodes.Flags;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Java Conformance Tests - JSON AST to PCRE2
 *
 * This test suite loads all JSON AST fixtures from tooling/js_to_json_ast/out/
 * and verifies that the Java binding can:
 * 1. Deserialize the JSON AST into Java IR nodes
 * 2. Emit correct PCRE2 patterns matching the expected output
 *
 * This ensures 100% test parity with the JavaScript Gold Standard.
 */
public class ConformanceTests {
    
    private static final ObjectMapper MAPPER = new ObjectMapper();
    
    // Path to fixtures directory - go up from bindings/java/src/test/java/com/strling/tests
    // to the repo root, then to tooling/js_to_json_ast/out/
    private static final Path FIXTURES_DIR = Paths.get(
        System.getProperty("user.dir"), "..", "..", "tooling", "js_to_json_ast", "out"
    ).normalize();
    
    /**
     * Get all JSON fixture files
     */
    private static List<Path> getFixtures() throws IOException {
        if (!Files.exists(FIXTURES_DIR)) {
            throw new IOException("Fixtures directory not found: " + FIXTURES_DIR);
        }
        
        List<Path> fixtures = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(FIXTURES_DIR, 1)) {
            paths.filter(Files::isRegularFile)
                 .filter(p -> p.toString().endsWith(".json"))
                 .sorted()
                 .forEach(fixtures::add);
        }
        return fixtures;
    }
    
    /**
     * Dynamically generate a test for each JSON fixture
     */
    @TestFactory
    public Stream<DynamicTest> testAllConformanceFixtures() throws IOException {
        List<Path> fixtures = getFixtures();
        
        return fixtures.stream().map(fixturePath -> 
            DynamicTest.dynamicTest(
                fixturePath.getFileName().toString(),
                () -> testSingleFixture(fixturePath)
            )
        );
    }
    
    /**
     * Test a single JSON fixture
     */
    private void testSingleFixture(Path fixturePath) throws IOException {
        // Load and parse the JSON fixture
        JsonNode root = MAPPER.readTree(fixturePath.toFile());
        
        // Skip if no expected PCRE output
        if (!root.has("expected") || !root.get("expected").has("pcre")) {
            // This is acceptable - some fixtures may not have expected PCRE
            return;
        }
        
        String expectedPcre = root.get("expected").get("pcre").asText();
        
        // Deserialize the AST pattern
        IRNode astRoot;
        try {
            astRoot = MAPPER.treeToValue(root.get("pattern"), IRNode.class);
        } catch (Exception e) {
            fail("Failed to deserialize AST from " + fixturePath.getFileName() + ": " + e.getMessage(), e);
            return;
        }
        
        // Compile AST to IR
        JsonAstCompiler compiler = new JsonAstCompiler();
        IROp irRoot;
        try {
            irRoot = compiler.compile(astRoot);
        } catch (Exception e) {
            fail("Failed to compile AST to IR for " + fixturePath.getFileName() + ": " + e.getMessage(), e);
            return;
        }
        
        // Extract flags
        Flags flags = null;
        if (root.has("flags")) {
            JsonNode flagsNode = root.get("flags");
            flags = new Flags();
            if (flagsNode.has("ignoreCase")) {
                flags.ignoreCase = flagsNode.get("ignoreCase").asBoolean();
            }
            if (flagsNode.has("multiline")) {
                flags.multiline = flagsNode.get("multiline").asBoolean();
            }
            if (flagsNode.has("dotAll")) {
                flags.dotAll = flagsNode.get("dotAll").asBoolean();
            }
            if (flagsNode.has("unicode")) {
                flags.unicode = flagsNode.get("unicode").asBoolean();
            }
            if (flagsNode.has("extended")) {
                flags.extended = flagsNode.get("extended").asBoolean();
            }
        }
        
        // Emit PCRE2
        String emittedPcre;
        try {
            emittedPcre = Pcre2Emitter.emit(irRoot, flags);
        } catch (Exception e) {
            fail("Failed to emit PCRE2 for " + fixturePath.getFileName() + ": " + e.getMessage(), e);
            return;
        }
        
        // Assert the output matches expected
        assertEquals(expectedPcre, emittedPcre, 
            "PCRE2 output mismatch for " + fixturePath.getFileName());
    }
}
