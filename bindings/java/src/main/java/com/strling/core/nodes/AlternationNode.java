package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Collections;

public final class AlternationNode implements IRNode {
    private final List<IRNode> alternatives;

    @JsonCreator
    public AlternationNode(@JsonProperty("alternatives") List<IRNode> alternatives) {
        this.alternatives = alternatives != null ? Collections.unmodifiableList(alternatives) : Collections.emptyList();
    }

    public List<IRNode> getAlternatives() {
        return alternatives;
    }
}
