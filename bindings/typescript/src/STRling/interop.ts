/** Thin host adapter for the governed strling.wasm-abi v1 boundary. */

export const INTEROP_PROTOCOL_VERSION = "1.0.0" as const;
export const WASM_ABI_VERSION = 1 as const;
export const MAX_INTEROP_REQUEST_BYTES = 10_485_760 as const;
export const MAX_INTEROP_RESPONSE_BYTES = 33_554_432 as const;

const STATUS_RESPONSE_WRITTEN = 0;
const DESCRIPTOR_BYTES = 8;
const EXPECTED_EXPORTS = [
    "memory",
    "strling_wasm_abi_version_v1",
    "strling_wasm_alloc_v1",
    "strling_wasm_dealloc_v1",
    "strling_wasm_execute_v1",
    "strling_wasm_owned_bytes_free_v1",
] as const;

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue =
    | JsonPrimitive
    | readonly JsonValue[]
    | { readonly [key: string]: JsonValue };
export type JsonObject = { readonly [key: string]: JsonValue };

export interface InteropErrorRecord {
    readonly code: string;
    readonly path: string;
}

export interface InteropCompleted<T extends JsonValue = JsonValue> {
    readonly interop_protocol_version: typeof INTEROP_PROTOCOL_VERSION;
    readonly operation: string;
    readonly status: "completed";
    readonly result: T;
}

export interface InteropFailure {
    readonly interop_protocol_version: typeof INTEROP_PROTOCOL_VERSION;
    readonly operation?: string;
    readonly status: "error";
    readonly error: InteropErrorRecord;
}

export type InteropResponse<T extends JsonValue = JsonValue> =
    | InteropCompleted<T>
    | InteropFailure;

interface WasmExports extends WebAssembly.Exports {
    readonly memory: WebAssembly.Memory;
    readonly strling_wasm_abi_version_v1: () => number;
    readonly strling_wasm_alloc_v1: (length: number) => number;
    readonly strling_wasm_dealloc_v1: (
        pointer: number,
        length: number,
    ) => number;
    readonly strling_wasm_execute_v1: (
        requestPointer: number,
        requestLength: number,
        descriptorPointer: number,
    ) => number;
    readonly strling_wasm_owned_bytes_free_v1: (
        descriptorPointer: number,
    ) => number;
}

export class WasmAdapterError extends Error {
    public constructor(message: string) {
        super(message);
        this.name = "WasmAdapterError";
    }
}

export class WasmAbiError extends WasmAdapterError {
    public readonly status: number;

    public constructor(message: string, status: number) {
        super(`${message} (status ${status})`);
        this.name = "WasmAbiError";
        this.status = status;
    }
}

export class InteropProtocolError extends WasmAdapterError {
    public readonly code: string;
    public readonly path: string;
    public readonly operation?: string;

    public constructor(response: InteropFailure) {
        super(`${response.error.code} at ${response.error.path}`);
        this.name = "InteropProtocolError";
        this.code = response.error.code;
        this.path = response.error.path;
        this.operation = response.operation;
    }
}

/** One instance-scoped synchronous client. Independent instances may run concurrently. */
export class WasmClient {
    private readonly wasm: WasmExports;
    private active = false;

    public constructor(instance: WebAssembly.Instance) {
        this.wasm = validateExports(instance.exports);
        if (this.wasm.strling_wasm_abi_version_v1() !== WASM_ABI_VERSION) {
            throw new WasmAdapterError("unsupported strling.wasm-abi version");
        }
    }

    public execute(request: JsonObject): InteropResponse {
        return this.executeBytes(
            new TextEncoder().encode(JSON.stringify(request)),
        );
    }

    public executeBytes(request: Uint8Array): InteropResponse {
        if (this.active) {
            throw new WasmAdapterError(
                "one WebAssembly instance permits only serialized execution",
            );
        }
        if (request.byteLength > MAX_INTEROP_REQUEST_BYTES) {
            throw new WasmAdapterError(
                `interop request exceeds ${MAX_INTEROP_REQUEST_BYTES} bytes`,
            );
        }

        this.active = true;
        let requestPointer = 0;
        let descriptorPointer = 0;
        let primaryError: unknown;
        try {
            if (request.byteLength > 0) {
                requestPointer = this.wasm.strling_wasm_alloc_v1(
                    request.byteLength,
                );
                if (requestPointer === 0) {
                    throw new WasmAdapterError(
                        "WebAssembly request allocation failed",
                    );
                }
            }
            descriptorPointer =
                this.wasm.strling_wasm_alloc_v1(DESCRIPTOR_BYTES);
            if (descriptorPointer === 0 || descriptorPointer % 4 !== 0) {
                throw new WasmAdapterError(
                    "WebAssembly descriptor allocation failed",
                );
            }

            const memory = new Uint8Array(this.wasm.memory.buffer);
            if (requestPointer !== 0) {
                assertRange(
                    requestPointer,
                    request.byteLength,
                    memory.byteLength,
                    "request",
                );
                memory.set(request, requestPointer);
            }
            memory.fill(
                0,
                descriptorPointer,
                descriptorPointer + DESCRIPTOR_BYTES,
            );

            const status = this.wasm.strling_wasm_execute_v1(
                requestPointer,
                request.byteLength,
                descriptorPointer,
            );
            if (status !== STATUS_RESPONSE_WRITTEN) {
                throw new WasmAbiError("WebAssembly execution failed", status);
            }

            const descriptor = new DataView(this.wasm.memory.buffer);
            assertRange(
                descriptorPointer,
                DESCRIPTOR_BYTES,
                descriptor.byteLength,
                "response descriptor",
            );
            const responsePointer = descriptor.getUint32(
                descriptorPointer,
                true,
            );
            const responseLength = descriptor.getUint32(
                descriptorPointer + 4,
                true,
            );
            if (
                responsePointer === 0 ||
                responseLength === 0 ||
                responseLength > MAX_INTEROP_RESPONSE_BYTES
            ) {
                throw new WasmAdapterError(
                    "WebAssembly returned an invalid or oversized response",
                );
            }
            assertRange(
                responsePointer,
                responseLength,
                descriptor.byteLength,
                "response",
            );
            const copied = new Uint8Array(
                this.wasm.memory.buffer,
                responsePointer,
                responseLength,
            ).slice();
            let decoded: unknown;
            try {
                decoded = JSON.parse(
                    new TextDecoder("utf-8", { fatal: true }).decode(copied),
                );
            } catch (error) {
                throw new WasmAdapterError(
                    `WebAssembly response is not strict UTF-8 JSON: ${String(error)}`,
                );
            }
            return decodeInteropResponse(decoded);
        } catch (error) {
            primaryError = error;
            throw error;
        } finally {
            const cleanupError = this.release(
                requestPointer,
                request.byteLength,
                descriptorPointer,
            );
            this.active = false;
            if (primaryError === undefined && cleanupError !== undefined) {
                throw cleanupError;
            }
        }
    }

    public describe(): JsonValue {
        return this.completedResult({
            interop_protocol_version: INTEROP_PROTOCOL_VERSION,
            operation: "describe",
            payload: {},
        });
    }

    public compile(
        compileRequest: JsonObject,
        targetProfile?: JsonObject,
    ): JsonValue {
        return this.completedResult({
            interop_protocol_version: INTEROP_PROTOCOL_VERSION,
            operation: "compile",
            payload: {
                compile_request: compileRequest,
                ...(targetProfile === undefined
                    ? {}
                    : { target_profile: targetProfile }),
            },
        });
    }

    public inspectTargetProfile(targetProfile: JsonObject): JsonValue {
        return this.completedResult({
            interop_protocol_version: INTEROP_PROTOCOL_VERSION,
            operation: "target_profile.inspect",
            payload: { target_profile: targetProfile },
        });
    }

    public simplyCompile(
        builderRequest: JsonObject,
        targetProfile?: JsonObject,
    ): JsonValue {
        return this.completedResult({
            interop_protocol_version: INTEROP_PROTOCOL_VERSION,
            operation: "simply.compile",
            payload: {
                builder_request: builderRequest,
                ...(targetProfile === undefined
                    ? {}
                    : { target_profile: targetProfile }),
            },
        });
    }

    private completedResult(request: JsonObject): JsonValue {
        const response = this.execute(request);
        if (response.status === "error") {
            throw new InteropProtocolError(response);
        }
        return response.result;
    }

    private release(
        requestPointer: number,
        requestLength: number,
        descriptorPointer: number,
    ): WasmAbiError | undefined {
        let error: WasmAbiError | undefined;
        if (descriptorPointer !== 0) {
            const freeStatus =
                this.wasm.strling_wasm_owned_bytes_free_v1(descriptorPointer);
            if (freeStatus !== STATUS_RESPONSE_WRITTEN) {
                error = new WasmAbiError(
                    "WebAssembly response release failed",
                    freeStatus,
                );
            }
            const descriptorStatus = this.wasm.strling_wasm_dealloc_v1(
                descriptorPointer,
                DESCRIPTOR_BYTES,
            );
            if (
                descriptorStatus !== STATUS_RESPONSE_WRITTEN &&
                error === undefined
            ) {
                error = new WasmAbiError(
                    "WebAssembly descriptor release failed",
                    descriptorStatus,
                );
            }
        }
        if (requestPointer !== 0) {
            const requestStatus = this.wasm.strling_wasm_dealloc_v1(
                requestPointer,
                requestLength,
            );
            if (
                requestStatus !== STATUS_RESPONSE_WRITTEN &&
                error === undefined
            ) {
                error = new WasmAbiError(
                    "WebAssembly request release failed",
                    requestStatus,
                );
            }
        }
        return error;
    }
}

export async function instantiateWasm(
    source: BufferSource | WebAssembly.Module,
): Promise<WasmClient> {
    if (source instanceof WebAssembly.Module) {
        return new WasmClient(await WebAssembly.instantiate(source, {}));
    }
    const result = await WebAssembly.instantiate(source, {});
    return new WasmClient(result.instance);
}

export async function instantiateWasmResponse(
    response: Response | Promise<Response>,
): Promise<WasmClient> {
    const resolved = await response;
    if (!resolved.ok) {
        throw new WasmAdapterError(
            `caller-supplied WebAssembly response failed with ${resolved.status}`,
        );
    }
    return instantiateWasm(await resolved.arrayBuffer());
}

/** Resolve the packaged artifact without fetching or selecting a target. */
export function wasmArtifactUrl(): URL {
    return new URL("../strling_interop.wasm", import.meta.url);
}

function validateExports(exports: WebAssembly.Exports): WasmExports {
    const names = Object.keys(exports).sort();
    const expected = [...EXPECTED_EXPORTS].sort();
    if (
        names.length !== expected.length ||
        names.some((name, index) => name !== expected[index])
    ) {
        throw new WasmAdapterError(
            `unexpected strling.wasm-abi exports: ${names.join(", ")}`,
        );
    }
    if (!(exports.memory instanceof WebAssembly.Memory)) {
        throw new WasmAdapterError("strling.wasm-abi memory export is missing");
    }
    for (const name of EXPECTED_EXPORTS.slice(1)) {
        if (typeof exports[name] !== "function") {
            throw new WasmAdapterError(
                `strling.wasm-abi function export is missing: ${name}`,
            );
        }
    }
    return exports as WasmExports;
}

function assertRange(
    pointer: number,
    length: number,
    memoryLength: number,
    label: string,
): void {
    const end = pointer + length;
    if (
        !Number.isSafeInteger(pointer) ||
        !Number.isSafeInteger(length) ||
        pointer < 0 ||
        length < 0 ||
        end < pointer ||
        end > memoryLength
    ) {
        throw new WasmAdapterError(`${label} lies outside WebAssembly memory`);
    }
}

function decodeInteropResponse(value: unknown): InteropResponse {
    if (typeof value !== "object" || value === null) {
        throw new WasmAdapterError("interop response must be an object");
    }
    const response = value as Record<string, unknown>;
    if (
        response.interop_protocol_version !== INTEROP_PROTOCOL_VERSION ||
        (response.status !== "completed" && response.status !== "error")
    ) {
        throw new WasmAdapterError(
            "interop response has an unsupported version or status",
        );
    }
    if (response.status === "completed" && !("result" in response)) {
        throw new WasmAdapterError("completed interop response has no result");
    }
    if (response.status === "error") {
        const error = response.error;
        if (
            typeof error !== "object" ||
            error === null ||
            typeof (error as Record<string, unknown>).code !== "string" ||
            typeof (error as Record<string, unknown>).path !== "string"
        ) {
            throw new WasmAdapterError(
                "failed interop response has no stable code and path",
            );
        }
    }
    return value as InteropResponse;
}
