package com.strling.simply;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Records host-neutral Simply 1.1 operations without evaluating semantics. */
public final class SimplyBuilder {
    private final Object owner = new Object();
    private final String identityNamespace;
    private final String specificationVersion;
    private final Map<String, ?> semanticOptions;
    private final List<Map<String, Object>> steps = new ArrayList<>();

    public SimplyBuilder(String identityNamespace) {
        this(identityNamespace, "1.0-draft.1", defaultSemanticOptions());
    }

    public SimplyBuilder(String identityNamespace, String specificationVersion,
            Map<String, ?> semanticOptions) {
        this.identityNamespace = Objects.requireNonNull(identityNamespace, "identityNamespace");
        this.specificationVersion = Objects.requireNonNull(
                specificationVersion, "specificationVersion");
        this.semanticOptions = Collections.unmodifiableMap(
                new LinkedHashMap<>(Objects.requireNonNull(semanticOptions, "semanticOptions")));
    }

    public Value empty(String stepId) {
        return append(stepId, "empty", Collections.emptyMap());
    }

    public Value literal(String stepId, String text) {
        return append(stepId, "literal", Collections.singletonMap("text", text));
    }

    public Value wildcard(String stepId) {
        return append(stepId, "wildcard", Collections.emptyMap());
    }

    public Value characterSet(String stepId, List<? extends Map<String, ?>> members,
            boolean negated) {
        Map<String, Object> arguments = new LinkedHashMap<>();
        arguments.put("negated", negated);
        arguments.put("members", new ArrayList<>(members));
        return append(stepId, "character_set", arguments);
    }

    public Value sequence(String stepId, List<Value> values) {
        return append(stepId, "sequence",
                Collections.singletonMap("values", stepIds(values)));
    }

    public Value alternation(String stepId, List<Value> values) {
        return append(stepId, "alternation",
                Collections.singletonMap("values", stepIds(values)));
    }

    public Value group(String stepId, Value value) {
        return append(stepId, "group",
                Collections.singletonMap("value", stepId(value)));
    }

    public Value capture(String stepId, String captureKey, Value value, String name) {
        Map<String, Object> arguments = new LinkedHashMap<>();
        arguments.put("value", stepId(value));
        arguments.put("capture_key", captureKey);
        if (name != null) {
            arguments.put("name", name);
        }
        return append(stepId, "capture", arguments);
    }

    public Value backreference(String stepId, String captureKey) {
        return append(stepId, "backreference",
                Collections.singletonMap("capture_key", captureKey));
    }

    public Value position(String stepId, String position) {
        return append(stepId, "position", Collections.singletonMap("position", position));
    }

    public Value lookaround(String stepId, String direction, String polarity, Value value) {
        Map<String, Object> arguments = new LinkedHashMap<>();
        arguments.put("value", stepId(value));
        arguments.put("direction", direction);
        arguments.put("polarity", polarity);
        return append(stepId, "lookaround", arguments);
    }

    public Value atomic(String stepId, Value value) {
        return append(stepId, "atomic", Collections.singletonMap("value", stepId(value)));
    }

    public Value repeat(String stepId, Value value, int minimum, Integer maximum, String mode) {
        Map<String, Object> arguments = new LinkedHashMap<>();
        arguments.put("value", stepId(value));
        arguments.put("min", minimum);
        arguments.put("max", maximum);
        arguments.put("mode", mode);
        return append(stepId, "repeat", arguments);
    }

    public Value stdlibHelper(String stepId, String helperId, Map<String, ?> parameters) {
        Map<String, Object> arguments = new LinkedHashMap<>();
        arguments.put("helper_id", helperId);
        arguments.put("parameters", new LinkedHashMap<>(parameters));
        return append(stepId, "stdlib_helper", arguments);
    }

    public Map<String, Object> buildRequest(Value root, Map<String, ?> compileProjection) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("protocol_version", "1.1.0");
        request.put("contract_version", "1.0.0");
        request.put("specification_version", specificationVersion);
        request.put("identity_namespace", identityNamespace);
        request.put("semantic_options", semanticOptions);
        request.put("steps", Collections.unmodifiableList(new ArrayList<>(steps)));
        request.put("root_step_id", stepId(root));
        request.put("compile", new LinkedHashMap<>(compileProjection));
        return Collections.unmodifiableMap(request);
    }

    public static Map<String, String> defaultSemanticOptions() {
        Map<String, String> options = new LinkedHashMap<>();
        options.put("case_matching", "sensitive");
        options.put("text_model", "unicode_scalar_values");
        options.put("builtin_character_domain", "unicode");
        options.put("wildcard_line_terminators", "exclude");
        return Collections.unmodifiableMap(options);
    }

    private Value append(String stepId, String operation, Map<String, ?> arguments) {
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("step_id", stepId);
        step.put("operation", operation);
        step.put("arguments", new LinkedHashMap<>(arguments));
        steps.add(Collections.unmodifiableMap(step));
        return new Value(stepId, owner);
    }

    private List<String> stepIds(List<Value> values) {
        List<String> result = new ArrayList<>();
        for (Value value : values) {
            result.add(stepId(value));
        }
        return result;
    }

    private String stepId(Value value) {
        if (value == null || value.owner != owner) {
            throw new STRlingError("Simply values belong to exactly one builder");
        }
        return value.stepId;
    }

    /** Opaque reference to one recorded builder step. */
    public static final class Value {
        private final String stepId;
        private final Object owner;

        private Value(String stepId, Object owner) {
            this.stepId = stepId;
            this.owner = owner;
        }

        public String getStepId() {
            return stepId;
        }
    }
}
