package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class LookaheadNode implements IRNode {
    private final IRNode body;

    @JsonCreator
    public LookaheadNode(@JsonProperty("body") IRNode body) {
        this.body = body;
    }

    public IRNode getBody() {
        return body;
    }
}
