package com.strling;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.strling.simply.Essential;
import com.strling.simply.Pattern;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

final class Essential5Test {
    @Test
    void exposesAllFiveCanonicalRegistryIdentities() {
        String compatibilityFixture = essential5Fixture();
        assertEquals("1.0.0", Essential.REGISTRY_VERSION);
        assertEquals(Arrays.asList(
                "stdlib.date_time",
                "stdlib.email",
                "stdlib.ip",
                "stdlib.url",
                "stdlib.uuid"), Essential.HELPER_IDS);
        for (String name : Arrays.asList("dateTime", "email", "ip", "url", "uuid")) {
            assertTrue(compatibilityFixture.contains("\"" + name + "\""));
        }
    }

    @Test
    void recordsLexicalHelpersWithoutHostSemanticValidation() {
        List<Pattern> helpers = Arrays.asList(
                Essential.dateTime(),
                Essential.email(),
                Essential.ip(),
                Essential.url(),
                Essential.uuid());

        for (int index = 0; index < helpers.size(); index += 1) {
            Map<String, Object> request = helpers.get(index).buildRequest(compileProjection());
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> steps =
                    (List<Map<String, Object>>) request.get("steps");
            @SuppressWarnings("unchecked")
            Map<String, Object> arguments =
                    (Map<String, Object>) steps.get(0).get("arguments");
            assertEquals("stdlib_helper", steps.get(0).get("operation"));
            assertEquals(Essential.HELPER_IDS.get(index), arguments.get("helper_id"));
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> ipSteps = (List<Map<String, Object>>)
                Essential.ip().buildRequest(compileProjection()).get("steps");
        @SuppressWarnings("unchecked")
        Map<String, Object> ipArguments =
                (Map<String, Object>) ipSteps.get(0).get("arguments");
        @SuppressWarnings("unchecked")
        Map<String, Object> parameters =
                (Map<String, Object>) ipArguments.get("parameters");
        assertTrue(parameters.containsKey("version"));
        assertEquals(null, parameters.get("version"));
    }

    private static Map<String, Object> compileProjection() {
        return Map.of(
                "requested_outputs", Collections.singletonList("semantic"),
                "compiler_options", Map.of(
                        "partial_semantics", "forbid",
                        "diagnostic_policy", Map.of("minimum_severity", "hint")));
    }

    private static String essential5Fixture() {
        Path current = Path.of("").toAbsolutePath();
        while (current != null) {
            Path candidate = current.resolve("spec/stdlib/essential_5.json");
            if (Files.isRegularFile(candidate)) {
                try {
                    return Files.readString(candidate);
                } catch (IOException exception) {
                    throw new AssertionError("cannot read " + candidate, exception);
                }
            }
            current = current.getParent();
        }
        throw new AssertionError("spec/stdlib/essential_5.json not found");
    }
}
