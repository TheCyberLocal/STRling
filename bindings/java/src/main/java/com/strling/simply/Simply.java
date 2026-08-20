package com.strling.simply;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Idiomatic Java constructors for canonical Simply recipes. */
public final class Simply {
    private Simply() {}

    public static Pattern empty() {
        return new Pattern(context -> context.builder.empty(context.next("empty")));
    }

    public static Pattern literal(String text) {
        if (text == null) {
            throw new STRlingError("literal text cannot be null");
        }
        if (text.isEmpty()) {
            return empty();
        }
        return new Pattern(context -> context.builder.literal(context.next("literal"), text));
    }

    public static Pattern anything() {
        return new Pattern(context -> context.builder.wildcard(context.next("wildcard")));
    }

    public static Pattern digit() {
        return builtin("digit");
    }

    public static Pattern word() {
        return builtin("word");
    }

    public static Pattern whitespace() {
        return builtin("whitespace");
    }

    public static Pattern between(char start, char end) {
        if (start > end || Character.isSurrogate(start) || Character.isSurrogate(end)) {
            throw new STRlingError("character range must be ordered Unicode scalars");
        }
        Map<String, Object> member = new LinkedHashMap<>();
        member.put("kind", "range");
        member.put("start", String.valueOf(start));
        member.put("end", String.valueOf(end));
        return characterSet(Collections.singletonList(member), false);
    }

    public static Pattern anyOfChars(String characters) {
        if (characters == null || characters.isEmpty()) {
            throw new STRlingError("character set cannot be empty");
        }
        List<Map<String, ?>> members = new ArrayList<>();
        characters.codePoints().forEach(codePoint -> {
            Map<String, Object> member = new LinkedHashMap<>();
            member.put("kind", "literal");
            member.put("value", new String(Character.toChars(codePoint)));
            members.add(member);
        });
        return characterSet(members, false);
    }

    public static Pattern merge(Object... values) {
        List<Pattern> patterns = patterns(values);
        if (patterns.size() == 1) {
            return patterns.get(0);
        }
        return new Pattern(context -> {
            List<SimplyBuilder.Value> recorded = new ArrayList<>();
            for (Pattern pattern : patterns) {
                recorded.add(pattern.record(context));
            }
            return context.builder.sequence(context.next("sequence"), recorded);
        });
    }

    public static Pattern anyOf(Object... values) {
        List<Pattern> patterns = patterns(values);
        return new Pattern(context -> {
            List<SimplyBuilder.Value> recorded = new ArrayList<>();
            for (Pattern pattern : patterns) {
                recorded.add(pattern.record(context));
            }
            return context.builder.alternation(context.next("alternation"), recorded);
        });
    }

    public static Pattern may(Object... values) {
        return merge(values).may();
    }

    public static Pattern capture(Object... values) {
        return merge(values).asCapture();
    }

    public static Pattern group(String name, Object... values) {
        return merge(values).asGroup(name);
    }

    public static Pattern ref(String captureKey) {
        return new Pattern(context -> context.builder.backreference(
                context.next("backreference"), captureKey));
    }

    public static Pattern startsWith(Object... values) {
        return merge(position("start_of_text"), merge(values));
    }

    public static Pattern endsWith(Object... values) {
        return merge(merge(values), position("end_of_text"));
    }

    public static Pattern followedBy(Object... values) {
        return lookaround("ahead", "positive", merge(values));
    }

    public static Pattern notFollowedBy(Object... values) {
        return lookaround("ahead", "negative", merge(values));
    }

    public static Pattern precededBy(Object... values) {
        return lookaround("behind", "positive", merge(values));
    }

    public static Pattern notPrecededBy(Object... values) {
        return lookaround("behind", "negative", merge(values));
    }

    public static Pattern atomic(Object... values) {
        Pattern pattern = merge(values);
        return new Pattern(context -> context.builder.atomic(
                context.next("atomic"), pattern.record(context)));
    }

    private static Pattern builtin(String name) {
        Map<String, Object> member = new LinkedHashMap<>();
        member.put("kind", "builtin");
        member.put("name", name);
        member.put("domain", "target_native");
        member.put("negated", false);
        return characterSet(Collections.singletonList(member), false);
    }

    private static Pattern characterSet(List<? extends Map<String, ?>> members,
            boolean negated) {
        return new Pattern(context -> context.builder.characterSet(
                context.next("character-set"), members, negated));
    }

    private static Pattern position(String position) {
        return new Pattern(context -> context.builder.position(
                context.next("position"), position));
    }

    private static Pattern lookaround(String direction, String polarity, Pattern value) {
        return new Pattern(context -> context.builder.lookaround(
                context.next("lookaround"), direction, polarity, value.record(context)));
    }

    private static List<Pattern> patterns(Object... values) {
        if (values == null || values.length == 0) {
            throw new STRlingError("at least one Pattern or literal string is required");
        }
        List<Pattern> patterns = new ArrayList<>();
        for (Object value : Arrays.asList(values)) {
            if (value instanceof Pattern) {
                patterns.add((Pattern) value);
            } else if (value instanceof String) {
                patterns.add(literal((String) value));
            } else {
                throw new STRlingError("expected a Pattern or literal string");
            }
        }
        return patterns;
    }
}
