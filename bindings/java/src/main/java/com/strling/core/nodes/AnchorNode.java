package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class AnchorNode implements IRNode {
    private final String at;

    @JsonCreator
    public AnchorNode(@JsonProperty("at") String at) {
        this.at = at;
    }

    public String getAt() {
        return at;
    }
}
