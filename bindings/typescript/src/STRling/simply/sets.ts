/** Character-set conveniences expressed as canonical Simply set members. */

import type { SimplyCharacterSetMember } from "./preview.js";
import {
    Pattern,
    STRlingError,
    coercePattern,
    createPattern,
} from "./pattern.js";

export function characterSet(
    members: readonly SimplyCharacterSetMember[],
    negated = false,
): Pattern {
    const copied = members.map((member) => ({ ...member }));
    return createPattern(
        (context) =>
            context.builder.characterSet(
                context.next("character-set"),
                copied,
                negated,
            ),
        copied,
    );
}

export function between(
    start: string | number,
    end: string | number,
    minRep?: number,
    maxRep?: number,
): Pattern {
    const pattern = characterSet([
        { kind: "range", start: String(start), end: String(end) },
    ]);
    return minRep === undefined ? pattern : pattern.rep(minRep, maxRep);
}

export function notBetween(
    start: string | number,
    end: string | number,
    minRep?: number,
    maxRep?: number,
): Pattern {
    const pattern = characterSet(
        [{ kind: "range", start: String(start), end: String(end) }],
        true,
    );
    return minRep === undefined ? pattern : pattern.rep(minRep, maxRep);
}

export function inChars(...patterns: (Pattern | string)[]): Pattern {
    return combinedSet(patterns, false);
}

export function notInChars(...patterns: (Pattern | string)[]): Pattern {
    return combinedSet(patterns, true);
}

function combinedSet(
    patterns: readonly (Pattern | string)[],
    negated: boolean,
): Pattern {
    const members: SimplyCharacterSetMember[] = [];
    for (const value of patterns.map(coercePattern)) {
        if (value.characterSetMembers === undefined) {
            throw new STRlingError(
                "character-set composition accepts only literals and character-set patterns",
            );
        }
        members.push(...value.characterSetMembers);
    }
    return characterSet(members, negated);
}
