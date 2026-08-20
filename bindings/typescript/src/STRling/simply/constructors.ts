/** Composite Simply conveniences that only record protocol operations. */

import { Pattern, coercePattern, createPattern } from "./pattern.js";

function values(patterns: readonly (Pattern | string)[]): Pattern[] {
    return patterns.map(coercePattern);
}

function body(patterns: readonly (Pattern | string)[]): Pattern {
    const prepared = values(patterns);
    if (prepared.length === 1) {
        return prepared[0];
    }
    return createPattern((context) =>
        context.builder.sequence(
            context.next("sequence"),
            prepared.map((pattern) => pattern.record(context)),
        ),
    );
}

export function anyOf(...patterns: (Pattern | string)[]): Pattern {
    const prepared = values(patterns);
    return createPattern((context) =>
        context.builder.alternation(
            context.next("alternation"),
            prepared.map((pattern) => pattern.record(context)),
        ),
    );
}

export function may(...patterns: (Pattern | string)[]): Pattern {
    return body(patterns).rep(0, 1);
}

export function merge(...patterns: (Pattern | string)[]): Pattern {
    return body(patterns);
}

export function capture(...patterns: (Pattern | string)[]): Pattern {
    const value = body(patterns);
    return createPattern((context) => {
        const captureKey = context.next("capture");
        return context.builder.capture(
            context.next("capture-step"),
            captureKey,
            value.record(context),
        );
    });
}

export function group(
    name: string,
    ...patterns: (Pattern | string)[]
): Pattern {
    const value = body(patterns);
    return createPattern((context) =>
        context.builder.capture(
            context.next("capture-step"),
            context.next("capture"),
            value.record(context),
            name,
        ),
    );
}
