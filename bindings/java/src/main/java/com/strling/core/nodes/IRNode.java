package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

@JsonTypeInfo(
    use = JsonTypeInfo.Id.NAME,
    include = JsonTypeInfo.As.PROPERTY,
    property = "type"
)
@JsonSubTypes({
    @JsonSubTypes.Type(value = LiteralNode.class, name = "Literal"),
    @JsonSubTypes.Type(value = SequenceNode.class, name = "Sequence"),
    @JsonSubTypes.Type(value = AlternationNode.class, name = "Alternation"),
    @JsonSubTypes.Type(value = QuantifierNode.class, name = "Quantifier"),
    @JsonSubTypes.Type(value = GroupNode.class, name = "Group"),
    @JsonSubTypes.Type(value = CharacterClassNode.class, name = "CharacterClass"),
    @JsonSubTypes.Type(value = AnchorNode.class, name = "Anchor"),
    @JsonSubTypes.Type(value = BackReferenceNode.class, name = "Backreference"),
    @JsonSubTypes.Type(value = LookaheadNode.class, name = "Lookahead"),
    @JsonSubTypes.Type(value = NegativeLookaheadNode.class, name = "NegativeLookahead"),
    @JsonSubTypes.Type(value = LookbehindNode.class, name = "Lookbehind"),
    @JsonSubTypes.Type(value = NegativeLookbehindNode.class, name = "NegativeLookbehind"),
    @JsonSubTypes.Type(value = DotNode.class, name = "Dot")
})
public interface IRNode {
    // Marker interface for IR nodes
}
