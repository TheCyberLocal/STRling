package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Collections;

public final class SequenceNode implements IRNode {
    private final List<IRNode> parts;

    @JsonCreator
    public SequenceNode(@JsonProperty("parts") List<IRNode> parts) {
        this.parts = parts != null ? Collections.unmodifiableList(parts) : Collections.emptyList();
    }

    public List<IRNode> getParts() {
        return parts;
    }
}
