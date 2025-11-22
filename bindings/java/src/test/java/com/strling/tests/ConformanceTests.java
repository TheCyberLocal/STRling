package com.strling.tests;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.core.type.TypeReference;
import com.strling.core.nodes.IRNode;
import com.strling.core.JsonAstCompiler;
import com.strling.core.IR.IROp;
import com.strling.emitters.Pcre2Emitter;
import com.strling.core.Nodes.Flags;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Java Conformance Tests - Shared JSON AST Suite
 *
 * This test suite loads all JSON AST fixtures from tests/spec/
 * and verifies that the Java binding can:
 * 1. Deserialize the JSON AST into Java AST nodes
 * 2. Compile AST to IR and match expected_ir
 * 3. Emit correct PCRE2 patterns matching expected_codegen
 */
public class ConformanceTests {
    
    private static final ObjectMapper MAPPER = new ObjectMapper();
    
    // Path to fixtures directory - go up from bindings/java/src/test/java/com/strling/tests
    // to the repo root, then to tests/spec/
    private static final Path FIXTURES_DIR = Paths.get(
        System.getProperty("user.dir"), "..", "..", "tests", "spec"
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
        
        // 1. Deserialize Flags
        Flags flags = new Flags();
        if (root.has("flags")) {
            JsonNode flagsNode = root.get("flags");
            if (flagsNode.has("ignoreCase") && flagsNode.get("ignoreCase").asBoolean()) flags.ignoreCase = true;
            if (flagsNode.has("multiline") && flagsNode.get("multiline").asBoolean()) flags.multiline = true;
            if (flagsNode.has("dotAll") && flagsNode.get("dotAll").asBoolean()) flags.dotAll = true;
            if (flagsNode.has("unicode") && flagsNode.get("unicode").asBoolean()) flags.unicode = true;
            if (flagsNode.has("extended") && flagsNode.get("extended").asBoolean()) flags.extended = true;
        }

        // 2. Deserialize AST
        if (!root.has("input_ast")) {
            return; // Skip if no input_ast
        }
        
        IRNode astRoot;
        try {
            astRoot = MAPPER.treeToValue(root.get("input_ast"), IRNode.class);
        } catch (Exception e) {
            fail("Failed to deserialize AST from " + fixturePath.getFileName() + ": " + e.getMessage(), e);
            return;
        }
        
        // 3. Compile to IR
        JsonAstCompiler compiler = new JsonAstCompiler();
        IROp irOp = compiler.compile(astRoot);
        
        // 4. Verify IR (if expected_ir exists)
        if (root.has("expected_ir")) {
            Map<String, Object> expectedIr = MAPPER.convertValue(root.get("expected_ir"), new TypeReference<Map<String, Object>>(){});
            Map<String, Object> actualIr = irOp.toDict();
            assertEquals(expectedIr, actualIr, "IR mismatch for " + fixturePath.getFileName());
        }

        // 5. Verify Codegen (if expected_codegen exists)
        if (root.has("expected_codegen") && root.get("expected_codegen").has("pcre")) {
            String expectedPcre = root.get("expected_codegen").get("pcre").asText();
            String actualPcre = Pcre2Emitter.emit(irOp, flags);
            assertEquals(expectedPcre, actualPcre, "PCRE mismatch for " + fixturePath.getFileName());
        }
    }
}
