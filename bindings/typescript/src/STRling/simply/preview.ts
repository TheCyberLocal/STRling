/**
 * Preview adapter for the host-neutral Simply 1.0.0 builder protocol.
 *
 * This module records protocol data only. Semantic validation, normalization,
 * compilation, target behavior, and diagnostics remain in the Rust kernel.
 */
import { spawnSync } from "node:child_process";

export const SIMPLY_PREVIEW_PROTOCOL_VERSION = "1.0.0" as const;
export const SIMPLY_PREVIEW_STATUS = "preview" as const;

export type SimplyRequestedOutput =
    | "semantic"
    | "analysis"
    | "portability"
    | "target_artifact";

export interface SimplySemanticOptions {
    readonly case_matching: "sensitive" | "insensitive";
    readonly text_model: "unicode_scalar_values";
    readonly builtin_character_domain: "ascii" | "unicode";
    readonly wildcard_line_terminators: "exclude" | "include";
}

export interface SimplyCompilerOptions {
    readonly partial_semantics: "forbid" | "allow_for_diagnostics";
    readonly diagnostic_policy: {
        readonly minimum_severity: "hint" | "info" | "warning" | "error";
    };
    readonly resource_limits?: {
        readonly max_semantic_nodes?: number;
        readonly max_diagnostics?: number;
    };
}

export interface SimplyTargetProfileReference {
    readonly profile_id: string;
    readonly profile_version: string;
    readonly sha256: string;
}

export interface SimplyCompileProjection {
    readonly target_profile?: SimplyTargetProfileReference;
    readonly requested_outputs: readonly SimplyRequestedOutput[];
    readonly compiler_options: SimplyCompilerOptions;
}

export type SimplyCharacterSetMember =
    | { readonly kind: "literal"; readonly value: string }
    | { readonly kind: "range"; readonly start: string; readonly end: string }
    | {
          readonly kind: "builtin";
          readonly name: "digit" | "word" | "whitespace";
          readonly domain?: "ascii" | "unicode";
          readonly negated: boolean;
      }
    | {
          readonly kind: "unicode_property";
          readonly property: string;
          readonly value?: string;
          readonly negated: boolean;
      };

export interface SimplyBuilderStep {
    readonly step_id: string;
    readonly operation: string;
    readonly arguments: Readonly<Record<string, unknown>>;
}

export interface SimplyBuilderRequest {
    readonly protocol_version: typeof SIMPLY_PREVIEW_PROTOCOL_VERSION;
    readonly contract_version: "1.0.0";
    readonly specification_version: string;
    readonly identity_namespace: string;
    readonly semantic_options: SimplySemanticOptions;
    readonly steps: readonly SimplyBuilderStep[];
    readonly root_step_id: string;
    readonly compile: SimplyCompileProjection;
}

export interface SimplyErrorRecord {
    readonly code:
        | "STRL-SIMPLY-0001"
        | "STRL-SIMPLY-0002"
        | "STRL-SIMPLY-0003"
        | "STRL-SIMPLY-0004"
        | "STRL-SIMPLY-0005"
        | "STRL-SIMPLY-0006"
        | "STRL-SIMPLY-0007"
        | "STRL-SIMPLY-0008"
        | "STRL-SIMPLY-0009"
        | "STRL-SIMPLY-0010"
        | "STRL-SIMPLY-0011"
        | "STRL-SIMPLY-0012";
    readonly path: string;
}

export interface SimplyAdapterSuccess {
    readonly status: "success";
    readonly protocol_version: typeof SIMPLY_PREVIEW_PROTOCOL_VERSION;
    readonly compile_request: Readonly<Record<string, unknown>>;
    readonly compile_result: Readonly<Record<string, unknown>>;
}

export interface SimplyAdapterFailure {
    readonly status: "failure";
    readonly protocol_version: typeof SIMPLY_PREVIEW_PROTOCOL_VERSION;
    readonly errors: readonly SimplyErrorRecord[];
}

export type SimplyAdapterResponse = SimplyAdapterSuccess | SimplyAdapterFailure;

export interface SimplyPreviewValue {
    readonly stepId: string;
}

interface ValueState {
    readonly owner: object;
    readonly stepId: string;
}

const VALUE_STATE = new WeakMap<object, ValueState>();

function createValue(owner: object, stepId: string): SimplyPreviewValue {
    const value = Object.freeze({ stepId });
    VALUE_STATE.set(value, { owner, stepId });
    return value;
}

export interface SimplyPreviewTransport {
    execute(request: SimplyBuilderRequest): SimplyAdapterResponse;
}

export class SimplyPreviewError extends Error {
    public readonly errors: readonly SimplyErrorRecord[];

    public constructor(errors: readonly SimplyErrorRecord[]) {
        super(`${errors.length} Simply construction error(s)`);
        this.name = "SimplyPreviewError";
        this.errors = Object.freeze(
            errors.map((error) => Object.freeze({ ...error })),
        );
    }
}

export class SimplyPreviewTransportError extends Error {
    public constructor(message: string) {
        super(message);
        this.name = "SimplyPreviewTransportError";
    }
}

export class CliSimplyPreviewTransport implements SimplyPreviewTransport {
    private readonly command: string;
    private readonly arguments: readonly string[];
    private readonly targetProfilePath?: string;

    public constructor(
        command: string,
        args: readonly string[] = ["simply"],
        targetProfilePath?: string,
    ) {
        if (!command) {
            throw new SimplyPreviewTransportError(
                "an explicit CLI command is required",
            );
        }
        this.command = command;
        this.arguments = Object.freeze([...args]);
        this.targetProfilePath = targetProfilePath;
    }

    public execute(request: SimplyBuilderRequest): SimplyAdapterResponse {
        const args = [...this.arguments];
        if (this.targetProfilePath !== undefined) {
            args.push("--target-profile", this.targetProfilePath);
        }
        const completed = spawnSync(this.command, args, {
            input: serializeSimplyBuilderRequest(request),
            encoding: "utf8",
            maxBuffer: 16 * 1024 * 1024,
        });
        if (completed.error !== undefined) {
            throw new SimplyPreviewTransportError(completed.error.message);
        }
        if (completed.status !== 0 && completed.status !== 2) {
            const detail = completed.stderr.trim();
            throw new SimplyPreviewTransportError(
                `Simply transport exited with ${completed.status}${
                    detail ? `: ${detail}` : ""
                }`,
            );
        }
        let decoded: unknown;
        try {
            decoded = JSON.parse(completed.stdout);
        } catch (error) {
            throw new SimplyPreviewTransportError(
                `Simply transport returned invalid JSON: ${String(error)}`,
            );
        }
        return decodeResponse(decoded);
    }
}

export class SimplyPreviewBuilder {
    private readonly owner = Object.freeze({});
    private readonly identityNamespace: string;
    private readonly specificationVersion: string;
    private readonly semanticOptions: SimplySemanticOptions;
    private readonly steps: SimplyBuilderStep[] = [];

    public constructor(
        identityNamespace: string,
        specificationVersion = "1.0-draft.1",
        semanticOptions: SimplySemanticOptions = defaultSimplySemanticOptions(),
    ) {
        this.identityNamespace = identityNamespace;
        this.specificationVersion = specificationVersion;
        this.semanticOptions = copy(semanticOptions);
    }

    public empty(stepId: string): SimplyPreviewValue {
        return this.append(stepId, "empty", {});
    }

    public literal(stepId: string, text: string): SimplyPreviewValue {
        return this.append(stepId, "literal", { text });
    }

    public wildcard(
        stepId: string,
        lineTerminators?: "exclude" | "include",
    ): SimplyPreviewValue {
        return this.append(
            stepId,
            "wildcard",
            lineTerminators === undefined
                ? {}
                : { line_terminators: lineTerminators },
        );
    }

    public characterSet(
        stepId: string,
        members: readonly SimplyCharacterSetMember[],
        negated = false,
    ): SimplyPreviewValue {
        return this.append(stepId, "character_set", {
            negated,
            members: copy(members),
        });
    }

    public sequence(
        stepId: string,
        values: readonly SimplyPreviewValue[],
    ): SimplyPreviewValue {
        return this.append(stepId, "sequence", {
            values: values.map((value) => this.valueStep(value)),
        });
    }

    public alternation(
        stepId: string,
        values: readonly SimplyPreviewValue[],
    ): SimplyPreviewValue {
        return this.append(stepId, "alternation", {
            values: values.map((value) => this.valueStep(value)),
        });
    }

    public group(
        stepId: string,
        value: SimplyPreviewValue,
    ): SimplyPreviewValue {
        return this.append(stepId, "group", {
            value: this.valueStep(value),
        });
    }

    public capture(
        stepId: string,
        captureKey: string,
        value: SimplyPreviewValue,
        name?: string,
    ): SimplyPreviewValue {
        return this.append(stepId, "capture", {
            value: this.valueStep(value),
            capture_key: captureKey,
            ...(name === undefined ? {} : { name }),
        });
    }

    public backreference(
        stepId: string,
        captureKey: string,
    ): SimplyPreviewValue {
        return this.append(stepId, "backreference", {
            capture_key: captureKey,
        });
    }

    public position(
        stepId: string,
        position:
            | "input_start"
            | "input_end"
            | "line_start"
            | "line_end"
            | "word_boundary"
            | "not_word_boundary"
            | "end_before_final_line_terminator",
    ): SimplyPreviewValue {
        return this.append(stepId, "position", { position });
    }

    public lookaround(
        stepId: string,
        direction: "ahead" | "behind",
        polarity: "positive" | "negative",
        value: SimplyPreviewValue,
    ): SimplyPreviewValue {
        return this.append(stepId, "lookaround", {
            value: this.valueStep(value),
            direction,
            polarity,
        });
    }

    public atomic(
        stepId: string,
        value: SimplyPreviewValue,
    ): SimplyPreviewValue {
        return this.append(stepId, "atomic", {
            value: this.valueStep(value),
        });
    }

    public repeat(
        stepId: string,
        value: SimplyPreviewValue,
        min: number,
        max: number | null,
        mode: "greedy" | "lazy" | "possessive" = "greedy",
    ): SimplyPreviewValue {
        return this.append(stepId, "repeat", {
            value: this.valueStep(value),
            min,
            max,
            mode,
        });
    }

    public importNode(
        stepId: string,
        node: Readonly<Record<string, unknown>>,
        sources?: readonly Readonly<Record<string, unknown>>[],
    ): SimplyPreviewValue {
        return this.append(stepId, "import_node", {
            node: copy(node),
            ...(sources === undefined ? {} : { sources: copy(sources) }),
        });
    }

    public importProgram(
        stepId: string,
        program: Readonly<Record<string, unknown>>,
    ): SimplyPreviewValue {
        return this.append(stepId, "import_program", {
            program: copy(program),
        });
    }

    public buildRequest(
        root: SimplyPreviewValue,
        compile: SimplyCompileProjection,
    ): SimplyBuilderRequest {
        const request: SimplyBuilderRequest = {
            protocol_version: SIMPLY_PREVIEW_PROTOCOL_VERSION,
            contract_version: "1.0.0",
            specification_version: this.specificationVersion,
            identity_namespace: this.identityNamespace,
            semantic_options: copy(this.semanticOptions),
            steps: copy(this.steps),
            root_step_id: this.valueStep(root),
            compile: copy(compile),
        };
        return copy(request);
    }

    public compile(
        root: SimplyPreviewValue,
        compile: SimplyCompileProjection,
        transport: SimplyPreviewTransport,
    ): SimplyAdapterSuccess {
        const response = transport.execute(this.buildRequest(root, compile));
        if (response.status === "failure") {
            throw new SimplyPreviewError(response.errors);
        }
        return response;
    }

    private append(
        stepId: string,
        operation: string,
        args: Readonly<Record<string, unknown>>,
    ): SimplyPreviewValue {
        this.steps.push(
            Object.freeze({
                step_id: stepId,
                operation,
                arguments: copy(args),
            }),
        );
        return createValue(this.owner, stepId);
    }

    private valueStep(value: SimplyPreviewValue): string {
        const state = VALUE_STATE.get(value as object);
        if (state === undefined || state.owner !== this.owner) {
            throw new SimplyPreviewTransportError(
                "Simply values belong to exactly one Preview builder",
            );
        }
        return state.stepId;
    }
}

export function defaultSimplySemanticOptions(): SimplySemanticOptions {
    return Object.freeze({
        case_matching: "sensitive",
        text_model: "unicode_scalar_values",
        builtin_character_domain: "unicode",
        wildcard_line_terminators: "exclude",
    });
}

export function serializeSimplyBuilderRequest(
    request: SimplyBuilderRequest,
): string {
    return JSON.stringify(request);
}

function decodeResponse(value: unknown): SimplyAdapterResponse {
    if (typeof value !== "object" || value === null) {
        throw new SimplyPreviewTransportError(
            "Simply transport response must be an object",
        );
    }
    const response = value as Record<string, unknown>;
    if (
        response.protocol_version !== SIMPLY_PREVIEW_PROTOCOL_VERSION ||
        (response.status !== "success" && response.status !== "failure")
    ) {
        throw new SimplyPreviewTransportError(
            "Simply transport response has an unsupported protocol or status",
        );
    }
    if (response.status === "failure") {
        if (!Array.isArray(response.errors)) {
            throw new SimplyPreviewTransportError(
                "Simply failure response must contain errors",
            );
        }
        return copy(value as SimplyAdapterFailure);
    }
    if (
        typeof response.compile_request !== "object" ||
        response.compile_request === null ||
        typeof response.compile_result !== "object" ||
        response.compile_result === null
    ) {
        throw new SimplyPreviewTransportError(
            "Simply success response must contain canonical request and result objects",
        );
    }
    return copy(value as SimplyAdapterSuccess);
}

function copy<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}
