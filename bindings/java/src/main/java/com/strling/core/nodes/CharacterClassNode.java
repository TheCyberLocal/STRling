package com.strling.core.nodes;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import java.util.List;
import java.util.Collections;

public final class CharacterClassNode implements IRNode {
    private final boolean negated;
    private final List<ClassMember> members;

    @JsonCreator
    public CharacterClassNode(
        @JsonProperty("negated") boolean negated,
        @JsonProperty("members") List<ClassMember> members
    ) {
        this.negated = negated;
        this.members = members != null ? Collections.unmodifiableList(members) : Collections.emptyList();
    }

    public boolean isNegated() {
        return negated;
    }

    public List<ClassMember> getMembers() {
        return members;
    }

    @JsonTypeInfo(
        use = JsonTypeInfo.Id.NAME,
        include = JsonTypeInfo.As.PROPERTY,
        property = "type"
    )
    @JsonSubTypes({
        @JsonSubTypes.Type(value = ClassLiteralMember.class, name = "Literal"),
        @JsonSubTypes.Type(value = ClassRangeMember.class, name = "Range"),
        @JsonSubTypes.Type(value = ClassEscapeMember.class, name = "Escape"),
        @JsonSubTypes.Type(value = ClassUnicodePropertyMember.class, name = "UnicodeProperty")
    })
    public interface ClassMember {
    }

    public static final class ClassLiteralMember implements ClassMember {
        private final String value;

        @JsonCreator
        public ClassLiteralMember(@JsonProperty("value") String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    public static final class ClassRangeMember implements ClassMember {
        private final String from;
        private final String to;

        @JsonCreator
        public ClassRangeMember(
            @JsonProperty("from") String from,
            @JsonProperty("to") String to
        ) {
            this.from = from;
            this.to = to;
        }

        public String getFrom() {
            return from;
        }

        public String getTo() {
            return to;
        }
    }

    public static final class ClassEscapeMember implements ClassMember {
        private final String kind;

        @JsonCreator
        public ClassEscapeMember(@JsonProperty("kind") String kind) {
            this.kind = kind;
        }

        public String getKind() {
            return kind;
        }
    }

    public static final class ClassUnicodePropertyMember implements ClassMember {
        private final String name;
        private final String value;
        private final boolean negated;

        @JsonCreator
        public ClassUnicodePropertyMember(
            @JsonProperty("name") String name,
            @JsonProperty("value") String value,
            @JsonProperty("negated") Boolean negated
        ) {
            this.name = name;
            this.value = value;
            this.negated = negated != null ? negated : false;
        }

        public String getName() {
            return name;
        }

        public String getValue() {
            return value;
        }

        public boolean isNegated() {
            return negated;
        }
    }
}
