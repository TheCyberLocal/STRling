package com.strling.jvm;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

final class NativeClientIntegrationTest {
    @Test
    void executesAllFourOperationsAgainstTheGovernedNativeLibrary() {
        try (NativeClient client = loadConfigured()) {
            assertTrue(client.describe() instanceof Map);

            Object compile = client.compile(sourceCompileRequest());
            assertTrue(compile instanceof Map);

            Object inspected = client.inspectTargetProfile(pcre2Profile());
            assertTrue(inspected instanceof Map);

            Object simply = client.simplyCompile(emptySimplyRequest());
            assertTrue(simply instanceof Map);
        }
    }

    @Test
    void actualNativeClientIsReentrantAndClosedUseIsDistinct() throws Exception {
        NativeClient client = loadConfigured();
        ExecutorService executor = Executors.newFixedThreadPool(8);
        try {
            List<Callable<Object>> calls = new ArrayList<>();
            for (int index = 0; index < 64; index += 1) {
                calls.add(client::describe);
            }
            List<Future<Object>> results = executor.invokeAll(calls);
            for (Future<Object> result : results) {
                assertTrue(result.get() instanceof Map);
            }
        } finally {
            executor.shutdownNow();
            client.close();
        }
        assertThrows(ClosedClientException.class, client::describe);
    }

    private static NativeClient loadConfigured() {
        String configured = System.getenv("STRLING_NATIVE_LIBRARY");
        Assumptions.assumeTrue(configured != null && !configured.isEmpty(),
                "STRLING_NATIVE_LIBRARY is required for governed integration execution");
        Path path = Paths.get(configured).toAbsolutePath().normalize();
        return NativeClient.load(path);
    }

    private static Map<String, Object> sourceCompileRequest() {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("kind", "inline");
        content.put("encoding", "utf-8");
        content.put("media_type", "text/strling");
        content.put("text", "literal \"hello\"");

        Map<String, Object> frontend = new LinkedHashMap<>();
        frontend.put("id", "semantic_strling");
        frontend.put("dialect_version", "1.0-draft.1");

        Map<String, Object> document = new LinkedHashMap<>();
        document.put("contract_version", "1.0.0");
        document.put("source_id", "src:jvm.integration");
        document.put("specification_version", "1.0-draft.1");
        document.put("frontend", frontend);
        document.put("content", content);
        document.put("provenance", Collections.singletonMap("kind", "authored"));

        Map<String, Object> input = new LinkedHashMap<>();
        input.put("kind", "source");
        input.put("document", document);

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("contract_version", "1.0.0");
        request.put("specification_version", "1.0-draft.1");
        request.put("input", input);
        request.put("requested_outputs", Collections.singletonList("semantic"));
        request.put("compiler_options", compilerOptions());
        return request;
    }

    private static Map<String, Object> emptySimplyRequest() {
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("step_id", "empty-1");
        step.put("operation", "empty");
        step.put("arguments", Collections.emptyMap());

        Map<String, Object> compile = new LinkedHashMap<>();
        compile.put("requested_outputs", Collections.singletonList("semantic"));
        compile.put("compiler_options", compilerOptions());

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("protocol_version", "1.1.0");
        request.put("contract_version", "1.0.0");
        request.put("specification_version", "1.0-draft.1");
        request.put("identity_namespace", "jvm-integration");
        request.put("semantic_options", Map.of(
                "case_matching", "sensitive",
                "text_model", "unicode_scalar_values",
                "builtin_character_domain", "unicode",
                "wildcard_line_terminators", "exclude"));
        request.put("steps", Collections.singletonList(step));
        request.put("root_step_id", "empty-1");
        request.put("compile", compile);
        return request;
    }

    private static Map<String, Object> pcre2Profile() {
        Path cursor = Paths.get("").toAbsolutePath().normalize();
        while (cursor != null) {
            Path profile = cursor.resolve("spec/targets/profiles/pcre2-10.43.json");
            if (Files.isRegularFile(profile)) {
                try {
                    return new ObjectMapper().readValue(
                            Files.readAllBytes(profile),
                            new TypeReference<Map<String, Object>>() {});
                } catch (IOException exception) {
                    throw new IllegalStateException("cannot read governed target profile", exception);
                }
            }
            cursor = cursor.getParent();
        }
        throw new IllegalStateException("cannot locate governed pcre2-10.43 profile");
    }

    private static Map<String, Object> compilerOptions() {
        return Map.of(
                "partial_semantics", "forbid",
                "diagnostic_policy", Map.of("minimum_severity", "hint"));
    }
}
