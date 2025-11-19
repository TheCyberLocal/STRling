package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class LiteralNode implements IRNode {
    private final String value;

    @JsonCreator
    public LiteralNode(@JsonProperty("value") String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
