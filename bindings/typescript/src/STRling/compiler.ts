/** Canonical request conveniences over a supplied raw-WASM client. */

import type { JsonObject, JsonValue } from "./interop.js";
import { WasmClient } from "./interop.js";

export type RequestedOutput =
    | "semantic"
    | "analysis"
    | "portability"
    | "target_artifact";

export interface SourceCompileOptions {
    readonly sourceId?: string;
    readonly frontendId?: "semantic_strling" | "legacy_regex";
    readonly frontendVersion?: string;
    readonly mediaType?: "text/strling" | "text/x-regex";
    readonly specificationVersion?: string;
    readonly requestedOutputs?: readonly RequestedOutput[];
    readonly compilerOptions?: JsonObject;
    readonly targetProfileReference?: JsonObject;
    readonly targetProfile?: JsonObject;
}

export class Compiler {
    public constructor(private readonly client: WasmClient) {}

    public compile(request: JsonObject, targetProfile?: JsonObject): JsonValue {
        return this.client.compile(request, targetProfile);
    }

    public check(request: JsonObject, targetProfile?: JsonObject): JsonValue {
        return this.compile(request, targetProfile);
    }
}

/** Compatibility name that returns canonical compile data, never a local AST. */
export function parse(
    client: WasmClient,
    source: string,
    options: SourceCompileOptions = {},
): JsonValue {
    return client.compile(
        sourceCompileRequest(source, options, ["semantic"]),
        options.targetProfile,
    );
}

/** Compatibility name that requests a canonical TargetArtifact. */
export function parseToArtifact(
    client: WasmClient,
    source: string,
    options: SourceCompileOptions,
): JsonValue {
    if (
        options.targetProfile === undefined ||
        options.targetProfileReference === undefined
    ) {
        throw new TypeError(
            "parseToArtifact requires an exact target profile and reference",
        );
    }
    return client.compile(
        sourceCompileRequest(source, options, [
            "semantic",
            "portability",
            "target_artifact",
        ]),
        options.targetProfile,
    );
}

export function sourceCompileRequest(
    source: string,
    options: SourceCompileOptions = {},
    fallbackOutputs: readonly RequestedOutput[] = ["semantic", "analysis"],
): JsonObject {
    const specificationVersion = options.specificationVersion ?? "1.0-draft.1";
    const frontendId = options.frontendId ?? "semantic_strling";
    return {
        contract_version: "1.0.0",
        specification_version: specificationVersion,
        input: {
            kind: "source",
            document: {
                contract_version: "1.0.0",
                source_id: options.sourceId ?? "src:typescript.adapter",
                specification_version: specificationVersion,
                frontend: {
                    id: frontendId,
                    dialect_version:
                        options.frontendVersion ?? specificationVersion,
                },
                content: {
                    kind: "inline",
                    encoding: "utf-8",
                    media_type:
                        options.mediaType ??
                        (frontendId === "legacy_regex"
                            ? "text/x-regex"
                            : "text/strling"),
                    text: source,
                },
                provenance: { kind: "authored" },
            },
        },
        ...(options.targetProfileReference === undefined
            ? {}
            : { target_profile: options.targetProfileReference }),
        requested_outputs: options.requestedOutputs ?? fallbackOutputs,
        compiler_options:
            options.compilerOptions ??
            ({
                partial_semantics: "forbid",
                diagnostic_policy: { minimum_severity: "hint" },
            } as const),
    };
}
