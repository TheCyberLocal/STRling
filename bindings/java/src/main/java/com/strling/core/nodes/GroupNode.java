package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

public final class GroupNode implements IRNode {
    private final boolean capturing;
    private final IRNode body;
    private final IRNode expression;  // For compatibility with the JSON schema
    private final String name;
    private final boolean atomic;

    @JsonCreator
    public GroupNode(
        @JsonProperty("capturing") boolean capturing,
        @JsonProperty("body") IRNode body,
        @JsonProperty("expression") IRNode expression,
        @JsonProperty("name") String name,
        @JsonProperty("atomic") Boolean atomic
    ) {
        this.capturing = capturing;
        this.body = body;
        this.expression = expression != null ? expression : body;
        this.name = name;
        this.atomic = atomic != null ? atomic : false;
    }

    public boolean isCapturing() {
        return capturing;
    }

    public IRNode getBody() {
        return body;
    }

    public IRNode getExpression() {
        return expression;
    }

    public String getName() {
        return name;
    }

    public boolean isAtomic() {
        return atomic;
    }
}
