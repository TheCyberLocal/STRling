/** Lookaround conveniences expressed only as Simply protocol records. */

import { Pattern, coercePattern, createPattern } from "./pattern.js";

function look(
    value: Pattern | string,
    direction: "ahead" | "behind",
    polarity: "positive" | "negative",
): Pattern {
    const pattern = coercePattern(value);
    return createPattern((context) =>
        context.builder.lookaround(
            context.next("lookaround"),
            direction,
            polarity,
            pattern.record(context),
        ),
    );
}

export function ahead(pattern: Pattern | string): Pattern {
    return look(pattern, "ahead", "positive");
}

export function notAhead(pattern: Pattern | string): Pattern {
    return look(pattern, "ahead", "negative");
}

export function behind(pattern: Pattern | string): Pattern {
    return look(pattern, "behind", "positive");
}

export function notBehind(pattern: Pattern | string): Pattern {
    return look(pattern, "behind", "negative");
}

export function has(pattern: Pattern | string): Pattern {
    const value = coercePattern(pattern);
    return createPattern((context) => {
        const wildcard = context.builder.wildcard(context.next("wildcard"));
        const repeated = context.builder.repeat(
            context.next("repeat"),
            wildcard,
            0,
            null,
        );
        const sequence = context.builder.sequence(context.next("sequence"), [
            repeated,
            value.record(context),
        ]);
        return context.builder.lookaround(
            context.next("lookaround"),
            "ahead",
            "positive",
            sequence,
        );
    });
}

export function hasNot(pattern: Pattern | string): Pattern {
    const value = coercePattern(pattern);
    return createPattern((context) => {
        const wildcard = context.builder.wildcard(context.next("wildcard"));
        const repeated = context.builder.repeat(
            context.next("repeat"),
            wildcard,
            0,
            null,
        );
        const sequence = context.builder.sequence(context.next("sequence"), [
            repeated,
            value.record(context),
        ]);
        return context.builder.lookaround(
            context.next("lookaround"),
            "ahead",
            "negative",
            sequence,
        );
    });
}
