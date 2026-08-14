import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import process from "node:process";

const STATUS_RESPONSE_WRITTEN = 0;
const STATUS_INVALID_ARGUMENT = 1;
const STATUS_OUTPUT_NOT_EMPTY = 2;
const MAX_REQUEST_BYTES = 10_485_760;
const EXPECTED_EXPORTS = [
    "memory",
    "strling_wasm_abi_version_v1",
    "strling_wasm_alloc_v1",
    "strling_wasm_dealloc_v1",
    "strling_wasm_execute_v1",
    "strling_wasm_owned_bytes_free_v1",
];

const modulePath =
    process.argv[2] ??
    "bindings/interop/target/wasm32-unknown-unknown/release/strling_interop.closed.wasm";
const moduleBytes = await readFile(modulePath);
const module = new WebAssembly.Module(moduleBytes);

assert.deepEqual(WebAssembly.Module.imports(module), []);
assert.deepEqual(
    WebAssembly.Module.exports(module).map(({ name }) => name),
    EXPECTED_EXPORTS,
);

function view(instance) {
    return new DataView(instance.exports.memory.buffer);
}

function bytes(instance) {
    return new Uint8Array(instance.exports.memory.buffer);
}

function readDescriptor(instance, descriptor) {
    const memory = view(instance);
    return {
        data: memory.getUint32(descriptor, true),
        len: memory.getUint32(descriptor + 4, true),
    };
}

function writeDescriptor(instance, descriptor, data, len) {
    const memory = view(instance);
    memory.setUint32(descriptor, data, true);
    memory.setUint32(descriptor + 4, len, true);
}

function execute(instance, requestValue) {
    const request = new TextEncoder().encode(JSON.stringify(requestValue));
    const requestPointer = instance.exports.strling_wasm_alloc_v1(
        request.length,
    );
    assert.notEqual(requestPointer, 0);
    const descriptor = instance.exports.strling_wasm_alloc_v1(8);
    assert.notEqual(descriptor, 0);
    assert.equal(descriptor % 4, 0);
    bytes(instance).set(request, requestPointer);
    assert.equal(
        instance.exports.strling_wasm_execute_v1(
            requestPointer,
            request.length,
            descriptor,
        ),
        STATUS_RESPONSE_WRITTEN,
    );
    const response = readDescriptor(instance, descriptor);
    assert.notEqual(response.data, 0);
    assert.ok(response.len > 0);
    assert.ok(
        response.data + response.len <=
            instance.exports.memory.buffer.byteLength,
    );
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(
        bytes(instance).slice(response.data, response.data + response.len),
    );
    const value = JSON.parse(decoded);
    assert.equal(
        instance.exports.strling_wasm_owned_bytes_free_v1(descriptor),
        STATUS_RESPONSE_WRITTEN,
    );
    assert.deepEqual(readDescriptor(instance, descriptor), { data: 0, len: 0 });
    assert.equal(
        instance.exports.strling_wasm_owned_bytes_free_v1(descriptor),
        STATUS_RESPONSE_WRITTEN,
    );
    assert.equal(
        instance.exports.strling_wasm_dealloc_v1(descriptor, 8),
        STATUS_RESPONSE_WRITTEN,
    );
    assert.equal(
        instance.exports.strling_wasm_dealloc_v1(
            requestPointer,
            request.length,
        ),
        STATUS_RESPONSE_WRITTEN,
    );
    return value;
}

const first = new WebAssembly.Instance(module, {});
assert.equal(first.exports.strling_wasm_abi_version_v1(), 1);
assert.equal(first.exports.strling_wasm_alloc_v1(0), 0);
assert.equal(first.exports.strling_wasm_alloc_v1(MAX_REQUEST_BYTES + 1), 0);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(0, 0),
    STATUS_RESPONSE_WRITTEN,
);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(0, 1),
    STATUS_INVALID_ARGUMENT,
);

const describe = {
    interop_protocol_version: "1.0.0",
    operation: "describe",
    payload: {},
};
const firstResponse = execute(first, describe);
assert.equal(firstResponse.status, "completed");
assert.equal(firstResponse.result.contract_id, "strling.interop");

const malformed = new Uint8Array([0xff]);
const malformedPointer = first.exports.strling_wasm_alloc_v1(malformed.length);
const malformedDescriptor = first.exports.strling_wasm_alloc_v1(8);
bytes(first).set(malformed, malformedPointer);
assert.equal(
    first.exports.strling_wasm_execute_v1(
        malformedPointer,
        malformed.length,
        malformedDescriptor,
    ),
    STATUS_RESPONSE_WRITTEN,
);
const malformedResponse = readDescriptor(first, malformedDescriptor);
assert.equal(
    JSON.parse(
        new TextDecoder().decode(
            bytes(first).slice(
                malformedResponse.data,
                malformedResponse.data + malformedResponse.len,
            ),
        ),
    ).error.code,
    "STRL-INTEROP-0001",
);
assert.equal(
    first.exports.strling_wasm_owned_bytes_free_v1(malformedDescriptor),
    STATUS_RESPONSE_WRITTEN,
);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(malformedDescriptor, 8),
    STATUS_RESPONSE_WRITTEN,
);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(malformedPointer, malformed.length),
    STATUS_RESPONSE_WRITTEN,
);

const invalidStorage = first.exports.strling_wasm_alloc_v1(16);
assert.equal(
    first.exports.strling_wasm_execute_v1(0, 0, invalidStorage + 1),
    STATUS_INVALID_ARGUMENT,
);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(invalidStorage, 16),
    STATUS_RESPONSE_WRITTEN,
);

const rangeDescriptor = first.exports.strling_wasm_alloc_v1(8);
assert.equal(
    first.exports.strling_wasm_execute_v1(0xfffffff0, 64, rangeDescriptor),
    STATUS_INVALID_ARGUMENT,
);
writeDescriptor(first, rangeDescriptor, 1, 1);
assert.equal(
    first.exports.strling_wasm_execute_v1(0, 0, rangeDescriptor),
    STATUS_OUTPUT_NOT_EMPTY,
);
writeDescriptor(first, rangeDescriptor, 0, 0);
assert.equal(
    first.exports.strling_wasm_dealloc_v1(rangeDescriptor, 8),
    STATUS_RESPONSE_WRITTEN,
);

const second = new WebAssembly.Instance(module, {});
const secondResponse = execute(second, describe);
assert.deepEqual(secondResponse, firstResponse);
assert.notEqual(first.exports.memory.buffer, second.exports.memory.buffer);

console.log(
    JSON.stringify({
        status: "passed",
        exports: EXPECTED_EXPORTS.length,
        imports: 0,
        instances: 2,
        lifecycle: "alloc-execute-read-free-dealloc",
    }),
);
