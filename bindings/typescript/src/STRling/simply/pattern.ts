/** Fluent request-recording conveniences for the canonical Simply protocol. */

import type { JsonObject } from "../interop.js";
import { WasmClient } from "../interop.js";
import {
    SimplyPreviewBuilder,
    WasmSimplyPreviewTransport,
    type SimplyAdapterSuccess,
    type SimplyCharacterSetMember,
    type SimplyCompileProjection,
    type SimplyPreviewValue,
    type SimplySemanticOptions,
} from "./preview.js";

interface RecordingContext {
    readonly builder: SimplyPreviewBuilder;
    next(prefix: string): string;
}

type Recipe = (context: RecordingContext) => SimplyPreviewValue;

export class STRlingError extends Error {
    public constructor(message: string) {
        super(message);
        this.name = "STRlingError";
    }
}

export interface Pattern {
    (minRep?: number, maxRep?: number): Pattern;
}

export class Pattern {
    public readonly characterSetMembers?: readonly SimplyCharacterSetMember[];
    private recipe!: Recipe;

    private constructor(
        recipe: Recipe,
        characterSetMembers?: readonly SimplyCharacterSetMember[],
    ) {
        this.recipe = recipe;
        this.characterSetMembers = characterSetMembers;
    }

    public static create(
        recipe: Recipe,
        characterSetMembers?: readonly SimplyCharacterSetMember[],
    ): Pattern {
        const state = new Pattern(recipe, characterSetMembers);
        const callable = ((minRep?: number, maxRep?: number) =>
            callable.rep(minRep, maxRep)) as Pattern;
        Object.setPrototypeOf(callable, Pattern.prototype);
        Object.assign(callable, state);
        return callable;
    }

    public record(context: RecordingContext): SimplyPreviewValue {
        return this.recipe(context);
    }

    public rep(minRep?: number, maxRep?: number): Pattern {
        if (minRep === undefined && maxRep === undefined) {
            return this;
        }
        const minimum = minRep ?? 0;
        if (
            !Number.isInteger(minimum) ||
            minimum < 0 ||
            (maxRep !== undefined && (!Number.isInteger(maxRep) || maxRep < 0))
        ) {
            throw new STRlingError(
                "repetition bounds must be non-negative integers",
            );
        }
        const maximum = maxRep === 0 ? null : (maxRep ?? minimum);
        return Pattern.create((context) =>
            context.builder.repeat(
                context.next("repeat"),
                this.record(context),
                minimum,
                maximum,
            ),
        );
    }

    public buildRequest(
        compile: SimplyCompileProjection,
        identityNamespace = "typescript-simply",
        semanticOptions?: SimplySemanticOptions,
    ): JsonObject {
        const { builder, root } = this.build(
            identityNamespace,
            semanticOptions,
        );
        return builder.buildRequest(root, compile) as unknown as JsonObject;
    }

    public compile(
        client: WasmClient,
        compile: SimplyCompileProjection,
        targetProfile?: JsonObject,
        identityNamespace = "typescript-simply",
        semanticOptions?: SimplySemanticOptions,
    ): SimplyAdapterSuccess {
        const { builder, root } = this.build(
            identityNamespace,
            semanticOptions,
        );
        return builder.compile(
            root,
            compile,
            new WasmSimplyPreviewTransport(client, targetProfile),
        );
    }

    public exec(_text: string): never {
        throw new STRlingError(
            "Pattern.exec was retired: canonical adapters do not simulate runtime regex execution",
        );
    }

    public toRegExp(): never {
        throw new STRlingError(
            "Pattern.toRegExp was retired: request an explicit canonical target artifact",
        );
    }

    public toString(): never {
        throw new STRlingError(
            "implicit regex rendering was retired: compile through the canonical adapter",
        );
    }

    private build(
        identityNamespace: string,
        semanticOptions?: SimplySemanticOptions,
    ): { builder: SimplyPreviewBuilder; root: SimplyPreviewValue } {
        const builder = new SimplyPreviewBuilder(
            identityNamespace,
            "1.0-draft.1",
            semanticOptions,
        );
        let sequence = 0;
        const context: RecordingContext = {
            builder,
            next(prefix: string): string {
                sequence += 1;
                return `${prefix}-${sequence}`;
            },
        };
        return { builder, root: this.record(context) };
    }
}

export function createPattern(
    recipe: Recipe,
    characterSetMembers?: readonly SimplyCharacterSetMember[],
): Pattern {
    return Pattern.create(recipe, characterSetMembers);
}

export function coercePattern(value: Pattern | string): Pattern {
    if (typeof value === "string") {
        return lit(value);
    }
    if (!(value instanceof Pattern)) {
        throw new STRlingError("expected a Pattern or literal string");
    }
    return value;
}

export function lit(text: string): Pattern {
    if (typeof text !== "string") {
        throw new STRlingError("literal text must be a string");
    }
    const members = Array.from(text, (value) => ({
        kind: "literal" as const,
        value,
    }));
    return createPattern(
        (context) => context.builder.literal(context.next("literal"), text),
        members,
    );
}
