package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class QuantifierNode implements IRNode {
    private final IRNode target;
    private final int min;
    private final Integer max;  // null represents infinity
    private final boolean greedy;
    private final boolean lazy;
    private final boolean possessive;

    @JsonCreator
    public QuantifierNode(
        @JsonProperty("target") IRNode target,
        @JsonProperty("min") int min,
        @JsonProperty("max") Integer max,
        @JsonProperty("greedy") boolean greedy,
        @JsonProperty("lazy") boolean lazy,
        @JsonProperty("possessive") boolean possessive
    ) {
        this.target = target;
        this.min = min;
        this.max = max;
        this.greedy = greedy;
        this.lazy = lazy;
        this.possessive = possessive;
    }

    public IRNode getTarget() {
        return target;
    }

    public int getMin() {
        return min;
    }

    public Integer getMax() {
        return max;
    }

    public boolean isGreedy() {
        return greedy;
    }

    public boolean isLazy() {
        return lazy;
    }

    public boolean isPossessive() {
        return possessive;
    }
}
