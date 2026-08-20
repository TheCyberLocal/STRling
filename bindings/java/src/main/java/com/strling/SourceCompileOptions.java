package com.strling;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Immutable host projection used to construct canonical source CompileRequests. */
public final class SourceCompileOptions {
    private final String sourceId;
    private final String frontendId;
    private final String frontendVersion;
    private final String mediaType;
    private final String specificationVersion;
    private final List<String> requestedOutputs;
    private final Map<String, Object> compilerOptions;
    private final Map<String, Object> targetProfileReference;
    private final Map<String, Object> targetProfile;

    private SourceCompileOptions(Builder builder) {
        specificationVersion = builder.specificationVersion;
        sourceId = builder.sourceId;
        frontendId = builder.frontendId;
        frontendVersion = builder.frontendVersion == null
                ? specificationVersion : builder.frontendVersion;
        mediaType = builder.mediaType == null
                ? ("legacy_regex".equals(frontendId) ? "text/x-regex" : "text/strling")
                : builder.mediaType;
        requestedOutputs = builder.requestedOutputs == null ? null
                : Collections.unmodifiableList(new ArrayList<>(builder.requestedOutputs));
        compilerOptions = immutableCopy(builder.compilerOptions);
        targetProfileReference = nullableCopy(builder.targetProfileReference);
        targetProfile = nullableCopy(builder.targetProfile);
    }

    public static Builder builder() {
        return new Builder();
    }

    public String getSourceId() {
        return sourceId;
    }

    public String getFrontendId() {
        return frontendId;
    }

    public String getFrontendVersion() {
        return frontendVersion;
    }

    public String getMediaType() {
        return mediaType;
    }

    public String getSpecificationVersion() {
        return specificationVersion;
    }

    public List<String> getRequestedOutputs() {
        return requestedOutputs;
    }

    public Map<String, Object> getCompilerOptions() {
        return compilerOptions;
    }

    public Map<String, Object> getTargetProfileReference() {
        return targetProfileReference;
    }

    public Map<String, Object> getTargetProfile() {
        return targetProfile;
    }

    private static Map<String, Object> nullableCopy(Map<String, ?> value) {
        return value == null ? null : immutableCopy(value);
    }

    private static Map<String, Object> immutableCopy(Map<String, ?> value) {
        return Collections.unmodifiableMap(new LinkedHashMap<>(value));
    }

    /** Builder with deterministic canonical defaults and no ambient target. */
    public static final class Builder {
        private String sourceId = "src:java.adapter";
        private String frontendId = "semantic_strling";
        private String frontendVersion;
        private String mediaType;
        private String specificationVersion = "1.0-draft.1";
        private List<String> requestedOutputs;
        private Map<String, ?> compilerOptions = defaultCompilerOptions();
        private Map<String, ?> targetProfileReference;
        private Map<String, ?> targetProfile;

        private Builder() {}

        public Builder sourceId(String value) {
            sourceId = value;
            return this;
        }

        public Builder frontend(String id, String version) {
            frontendId = id;
            frontendVersion = version;
            return this;
        }

        public Builder mediaType(String value) {
            mediaType = value;
            return this;
        }

        public Builder specificationVersion(String value) {
            specificationVersion = value;
            return this;
        }

        public Builder requestedOutputs(List<String> value) {
            requestedOutputs = value;
            return this;
        }

        public Builder compilerOptions(Map<String, ?> value) {
            compilerOptions = value;
            return this;
        }

        public Builder targetProfileReference(Map<String, ?> value) {
            targetProfileReference = value;
            return this;
        }

        public Builder targetProfile(Map<String, ?> value) {
            targetProfile = value;
            return this;
        }

        public SourceCompileOptions build() {
            return new SourceCompileOptions(this);
        }

        private static Map<String, Object> defaultCompilerOptions() {
            Map<String, Object> values = new LinkedHashMap<>();
            values.put("partial_semantics", "forbid");
            values.put("diagnostic_policy",
                    Collections.singletonMap("minimum_severity", "hint"));
            return values;
        }
    }
}
