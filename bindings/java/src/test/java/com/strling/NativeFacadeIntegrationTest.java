package com.strling;

import static org.junit.jupiter.api.Assertions.assertTrue;

import com.strling.jvm.NativeClient;
import com.strling.simply.Essential;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.Map;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

final class NativeFacadeIntegrationTest {
    @Test
    void sourceAndSimplyFacadesDelegateToTheSameNativeClient() {
        String configured = System.getenv("STRLING_NATIVE_LIBRARY");
        Assumptions.assumeTrue(configured != null && !configured.isEmpty(),
                "STRLING_NATIVE_LIBRARY is required for governed integration execution");
        try (NativeClient client = NativeClient.load(
                Paths.get(configured).toAbsolutePath().normalize())) {
            Object describe = client.describe();
            Object source = new Compiler(client).parse(
                    "literal \"hello\"",
                    SourceCompileOptions.builder().sourceId("src:jvm.parity").build());
            assertTrue(source instanceof Map);

            Object simply = client.simplyCompile(Essential.ip().buildRequest(
                    compileProjection(), "jvm-parity", null));
            assertTrue(simply instanceof Map);
            writeEvidence(describe, source, simply);
        }
    }

    private static Map<String, Object> compileProjection() {
        return Map.of(
                "requested_outputs", Collections.singletonList("semantic"),
                "compiler_options", Map.of(
                        "partial_semantics", "forbid",
                        "diagnostic_policy", Map.of("minimum_severity", "hint")));
    }

    private static void writeEvidence(Object describe, Object compile, Object simply) {
        String configured = System.getenv("STRLING_JVM_EVIDENCE_DIR");
        if (configured == null || configured.isEmpty()) {
            return;
        }
        Path directory = Paths.get(configured).resolve("java");
        ObjectMapper mapper = new ObjectMapper();
        try {
            Files.createDirectories(directory);
            mapper.writeValue(directory.resolve("describe.json").toFile(), describe);
            mapper.writeValue(directory.resolve("compile.json").toFile(), compile);
            mapper.writeValue(directory.resolve("simply.json").toFile(), simply);
        } catch (IOException exception) {
            throw new IllegalStateException("cannot write Java adapter evidence", exception);
        }
    }
}
