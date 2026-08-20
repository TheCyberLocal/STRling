package com.strling.simply;

import com.strling.jvm.NativeClient;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/** Immutable recipe that records canonical Simply operations on demand. */
public final class Pattern {
    interface Recipe {
        SimplyBuilder.Value record(Context context);
    }

    static final class Context {
        final SimplyBuilder builder;
        private int sequence;

        Context(SimplyBuilder builder) {
            this.builder = builder;
        }

        String next(String prefix) {
            sequence += 1;
            return prefix + "-" + sequence;
        }
    }

    private final Recipe recipe;
    private final Pattern repeatedValue;
    private final Integer repeatedMinimum;
    private final Integer repeatedMaximum;
    private final String repeatedMode;

    Pattern(Recipe recipe) {
        this(recipe, null, null, null, null);
    }

    private Pattern(Recipe recipe, Pattern repeatedValue, Integer repeatedMinimum,
            Integer repeatedMaximum, String repeatedMode) {
        this.recipe = Objects.requireNonNull(recipe, "recipe");
        this.repeatedValue = repeatedValue;
        this.repeatedMinimum = repeatedMinimum;
        this.repeatedMaximum = repeatedMaximum;
        this.repeatedMode = repeatedMode;
    }

    SimplyBuilder.Value record(Context context) {
        return recipe.record(context);
    }

    public Pattern repeat(int minimum, Integer maximum) {
        if (minimum < 0 || (maximum != null && maximum.intValue() < minimum)) {
            throw new STRlingError("repetition bounds must be non-negative and ordered");
        }
        Pattern source = this;
        Recipe next = context -> context.builder.repeat(
                context.next("repeat"), source.record(context), minimum, maximum, "greedy");
        return new Pattern(next, source, Integer.valueOf(minimum), maximum, "greedy");
    }

    public Pattern repeat(int count) {
        return repeat(count, Integer.valueOf(count));
    }

    public Pattern may() {
        return repeat(0, Integer.valueOf(1));
    }

    public Pattern lazy() {
        if (repeatedValue == null) {
            throw new STRlingError("lazy requires a repeated pattern");
        }
        Recipe next = context -> context.builder.repeat(
                context.next("repeat"), repeatedValue.record(context),
                repeatedMinimum.intValue(), repeatedMaximum, "lazy");
        return new Pattern(next, repeatedValue, repeatedMinimum, repeatedMaximum, "lazy");
    }

    public Pattern asCapture() {
        Pattern source = this;
        return new Pattern(context -> context.builder.capture(
                context.next("capture"), context.next("capture-key"),
                source.record(context), null));
    }

    public Pattern asGroup(String name) {
        if (name == null || name.isEmpty()) {
            throw new STRlingError("capture group name cannot be empty");
        }
        Pattern source = this;
        return new Pattern(context -> context.builder.capture(
                context.next("capture"), name, source.record(context), name));
    }

    public Map<String, Object> buildRequest(Map<String, ?> compileProjection) {
        return buildRequest(compileProjection, "java-simply", null);
    }

    public Map<String, Object> buildRequest(Map<String, ?> compileProjection,
            String identityNamespace, Map<String, ?> semanticOptions) {
        SimplyBuilder builder = semanticOptions == null
                ? new SimplyBuilder(identityNamespace)
                : new SimplyBuilder(identityNamespace, "1.0-draft.1", semanticOptions);
        Context context = new Context(builder);
        return builder.buildRequest(record(context), compileProjection);
    }

    public Object compile(NativeClient client, Map<String, ?> compileProjection,
            Map<String, ?> targetProfile) {
        return client.simplyCompile(buildRequest(compileProjection), targetProfile);
    }

    public Object compile(NativeClient client, Map<String, ?> compileProjection) {
        return compile(client, compileProjection, null);
    }

    public Object exec(String ignoredText) {
        throw new STRlingError(
                "Pattern.exec was retired: canonical adapters do not simulate runtime regex execution");
    }

    @Override
    public String toString() {
        throw new STRlingError(
                "implicit regex rendering was retired: compile through the canonical adapter");
    }

    static Pattern stdlibHelper(String helperId, Map<String, ?> parameters) {
        return new Pattern(context -> context.builder.stdlibHelper(
                context.next("stdlib"), helperId, parameters));
    }
}
