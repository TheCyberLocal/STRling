package com.strling;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.strling.simply.Essential;
import com.strling.simply.Pattern;
import com.strling.simply.STRlingError;
import com.strling.simply.Simply;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

final class CanonicalFacadeTest {
    @Test
    void sourceRequestUsesCanonicalContractsAndNoAmbientTarget() {
        Map<String, Object> request = Compiler.sourceCompileRequest(
                "literal \"hello\"",
                SourceCompileOptions.builder().build(),
                Arrays.asList("semantic", "analysis"));

        assertEquals("1.0.0", request.get("contract_version"));
        assertEquals(Arrays.asList("semantic", "analysis"), request.get("requested_outputs"));
        assertFalse(request.containsKey("target_profile"));
    }

    @Test
    void exactTargetReferenceIsProjectedWithoutSelectingIt() {
        Map<String, Object> reference = Collections.singletonMap("profile_id", "pcre2-10.43");
        SourceCompileOptions options = SourceCompileOptions.builder()
                .targetProfileReference(reference)
                .build();

        Map<String, Object> request = Compiler.sourceCompileRequest(
                "literal \"x\"", options, Collections.singletonList("semantic"));

        assertEquals(reference, request.get("target_profile"));
    }

    @Test
    void simplyRecordsProtocolOperationsInsteadOfRenderingRegex() {
        Pattern pattern = Simply.merge(
                Simply.startsWith("ab"),
                Simply.digit().repeat(2),
                Simply.endsWith(Essential.email()));
        Map<String, Object> request = pattern.buildRequest(compileProjection());

        assertEquals("1.1.0", request.get("protocol_version"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> steps = (List<Map<String, Object>>) request.get("steps");
        assertTrue(steps.stream().anyMatch(step -> "stdlib_helper".equals(step.get("operation"))));
        assertThrows(STRlingError.class, pattern::toString);
        assertThrows(STRlingError.class, () -> pattern.exec("input"));
    }

    @Test
    void lexicalHelperRecordsNullDefaultInsteadOfSemanticValidation() {
        Map<String, Object> request = Essential.ip().buildRequest(compileProjection());
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> steps = (List<Map<String, Object>>) request.get("steps");
        @SuppressWarnings("unchecked")
        Map<String, Object> arguments = (Map<String, Object>) steps.get(0).get("arguments");
        @SuppressWarnings("unchecked")
        Map<String, Object> parameters = (Map<String, Object>) arguments.get("parameters");

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
}
