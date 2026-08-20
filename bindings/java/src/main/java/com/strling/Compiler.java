package com.strling;

import com.strling.jvm.NativeClient;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Canonical compile-request conveniences over a supplied native client. */
public final class Compiler {
    private final NativeClient client;

    public Compiler(NativeClient client) {
        this.client = Objects.requireNonNull(client, "client");
    }

    public Object compile(Map<String, ?> request, Map<String, ?> targetProfile) {
        return client.compile(request, targetProfile);
    }

    public Object compile(Map<String, ?> request) {
        return client.compile(request);
    }

    public Object check(Map<String, ?> request, Map<String, ?> targetProfile) {
        return compile(request, targetProfile);
    }

    public Object check(Map<String, ?> request) {
        return compile(request);
    }

    /** Compatibility name returning canonical compile data, never a local AST. */
    public Object parse(String source, SourceCompileOptions options) {
        SourceCompileOptions selected = options == null
                ? SourceCompileOptions.builder().build() : options;
        return client.compile(sourceCompileRequest(source, selected,
                Collections.singletonList("semantic")), selected.getTargetProfile());
    }

    public Object parse(String source) {
        return parse(source, null);
    }

    /** Compatibility name requesting a canonical TargetArtifact. */
    public Object parseToArtifact(String source, SourceCompileOptions options) {
        Objects.requireNonNull(options, "options");
        if (options.getTargetProfile() == null
                || options.getTargetProfileReference() == null) {
            throw new IllegalArgumentException(
                    "parseToArtifact requires an exact target profile and reference");
        }
        return client.compile(sourceCompileRequest(source, options,
                Arrays.asList("semantic", "portability", "target_artifact")),
                options.getTargetProfile());
    }

    public Object describe() {
        return client.describe();
    }

    public Object inspectTargetProfile(Map<String, ?> targetProfile) {
        return client.inspectTargetProfile(targetProfile);
    }

    public static Map<String, Object> sourceCompileRequest(
            String source, SourceCompileOptions options, List<String> fallbackOutputs) {
        Objects.requireNonNull(source, "source");
        SourceCompileOptions selected = options == null
                ? SourceCompileOptions.builder().build() : options;
        String specificationVersion = selected.getSpecificationVersion();
        String frontendId = selected.getFrontendId();

        Map<String, Object> frontend = new LinkedHashMap<>();
        frontend.put("id", frontendId);
        frontend.put("dialect_version", selected.getFrontendVersion());

        Map<String, Object> content = new LinkedHashMap<>();
        content.put("kind", "inline");
        content.put("encoding", "utf-8");
        content.put("media_type", selected.getMediaType());
        content.put("text", source);

        Map<String, Object> document = new LinkedHashMap<>();
        document.put("contract_version", "1.0.0");
        document.put("source_id", selected.getSourceId());
        document.put("specification_version", specificationVersion);
        document.put("frontend", frontend);
        document.put("content", content);
        document.put("provenance", Collections.singletonMap("kind", "authored"));

        Map<String, Object> input = new LinkedHashMap<>();
        input.put("kind", "source");
        input.put("document", document);

        Map<String, Object> request = new LinkedHashMap<>();
        request.put("contract_version", "1.0.0");
        request.put("specification_version", specificationVersion);
        request.put("input", input);
        if (selected.getTargetProfileReference() != null) {
            request.put("target_profile", selected.getTargetProfileReference());
        }
        List<String> requested = selected.getRequestedOutputs() == null
                ? fallbackOutputs : selected.getRequestedOutputs();
        request.put("requested_outputs",
                Collections.unmodifiableList(new ArrayList<>(requested)));
        request.put("compiler_options", selected.getCompilerOptions());
        return Collections.unmodifiableMap(request);
    }
}
