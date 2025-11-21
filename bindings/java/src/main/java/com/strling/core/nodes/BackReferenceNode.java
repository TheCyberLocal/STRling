package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class BackReferenceNode implements IRNode {
    private final Integer index;
    private final String name;

    @JsonCreator
    public BackReferenceNode(
        @JsonProperty("index") Integer index,
        @JsonProperty("name") String name
    ) {
        this.index = index;
        this.name = name;
    }

    public Integer getIndex() {
        return index;
    }

    public String getName() {
        return name;
    }
}
