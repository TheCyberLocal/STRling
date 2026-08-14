"""Seal and inspect the closed STRling raw WebAssembly export surface."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


MAGIC_AND_VERSION = b"\x00asm\x01\x00\x00\x00"
GOVERNED_EXPORTS = {
    "memory": 2,
    "strling_wasm_abi_version_v1": 0,
    "strling_wasm_alloc_v1": 0,
    "strling_wasm_dealloc_v1": 0,
    "strling_wasm_execute_v1": 0,
    "strling_wasm_owned_bytes_free_v1": 0,
}
REMOVABLE_LINKER_EXPORTS = {"__data_end", "__heap_base"}


class WasmContractError(RuntimeError):
    """Raised when a module does not satisfy the governed raw ABI surface."""


@dataclass(frozen=True)
class Export:
    name: str
    kind: int
    index: int


def decode_u32(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(5):
        if offset >= len(data):
            raise WasmContractError("truncated unsigned LEB128")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return value, offset
        shift += 7
    raise WasmContractError("u32 LEB128 exceeds five bytes")


def encode_u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF_FFFF:
        raise WasmContractError("value is outside u32")
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        encoded.append(byte)
        if not value:
            return bytes(encoded)


def decode_name(data: bytes, offset: int) -> tuple[str, int]:
    length, offset = decode_u32(data, offset)
    end = offset + length
    if end > len(data):
        raise WasmContractError("truncated export name")
    try:
        return data[offset:end].decode("utf-8"), end
    except UnicodeDecodeError as error:
        raise WasmContractError("export name is not UTF-8") from error


def encode_name(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return encode_u32(len(encoded)) + encoded


def parse_exports(payload: bytes) -> list[Export]:
    count, offset = decode_u32(payload, 0)
    exports: list[Export] = []
    for _ in range(count):
        name, offset = decode_name(payload, offset)
        if offset >= len(payload):
            raise WasmContractError("truncated export kind")
        kind = payload[offset]
        offset += 1
        index, offset = decode_u32(payload, offset)
        exports.append(Export(name, kind, index))
    if offset != len(payload):
        raise WasmContractError("trailing bytes in export section")
    return exports


def encode_exports(exports: list[Export]) -> bytes:
    payload = bytearray(encode_u32(len(exports)))
    for export in exports:
        payload.extend(encode_name(export.name))
        payload.append(export.kind)
        payload.extend(encode_u32(export.index))
    return bytes(payload)


def sections(module: bytes) -> list[tuple[int, bytes]]:
    if not module.startswith(MAGIC_AND_VERSION):
        raise WasmContractError("invalid WebAssembly magic or version")
    parsed: list[tuple[int, bytes]] = []
    offset = len(MAGIC_AND_VERSION)
    while offset < len(module):
        section_id = module[offset]
        offset += 1
        length, offset = decode_u32(module, offset)
        end = offset + length
        if end > len(module):
            raise WasmContractError("truncated WebAssembly section")
        parsed.append((section_id, module[offset:end]))
        offset = end
    return parsed


def validate_exports(exports: list[Export], *, allow_linker_metadata: bool) -> None:
    names = [export.name for export in exports]
    if len(names) != len(set(names)):
        raise WasmContractError("duplicate WebAssembly export name")
    extras = set(names).difference(GOVERNED_EXPORTS)
    allowed_extras = REMOVABLE_LINKER_EXPORTS if allow_linker_metadata else set()
    unexpected = sorted(extras.difference(allowed_extras))
    if unexpected:
        raise WasmContractError(f"unexpected WebAssembly exports: {unexpected!r}")
    for name, kind in GOVERNED_EXPORTS.items():
        matches = [export for export in exports if export.name == name]
        if len(matches) != 1 or matches[0].kind != kind:
            raise WasmContractError(f"missing or mistyped governed export: {name}")
    for export in exports:
        if export.name in REMOVABLE_LINKER_EXPORTS and export.kind != 3:
            raise WasmContractError(
                f"linker metadata export has unexpected kind: {export.name}"
            )


def seal_module(module: bytes) -> bytes:
    rendered = bytearray(MAGIC_AND_VERSION)
    found_exports = False
    for section_id, payload in sections(module):
        if section_id == 2:
            count, _ = decode_u32(payload, 0)
            if count:
                raise WasmContractError("raw interop module must import nothing")
        if section_id == 7:
            if found_exports:
                raise WasmContractError("duplicate WebAssembly export section")
            found_exports = True
            exports = parse_exports(payload)
            validate_exports(exports, allow_linker_metadata=True)
            payload = encode_exports(
                [export for export in exports if export.name in GOVERNED_EXPORTS]
            )
        rendered.append(section_id)
        rendered.extend(encode_u32(len(payload)))
        rendered.extend(payload)
    if not found_exports:
        raise WasmContractError("WebAssembly export section is missing")
    inspect_module(bytes(rendered))
    return bytes(rendered)


def inspect_module(module: bytes) -> list[Export]:
    export_sections = [
        payload for section_id, payload in sections(module) if section_id == 7
    ]
    if len(export_sections) != 1:
        raise WasmContractError("expected exactly one WebAssembly export section")
    for section_id, payload in sections(module):
        if section_id == 2:
            count, _ = decode_u32(payload, 0)
            if count:
                raise WasmContractError("raw interop module must import nothing")
    exports = parse_exports(export_sections[0])
    validate_exports(exports, allow_linker_metadata=False)
    return exports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seal", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        module = args.input.read_bytes()
        if args.seal:
            if args.output is None:
                raise WasmContractError("--seal requires --output")
            sealed = seal_module(module)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(sealed)
            exports = inspect_module(sealed)
        else:
            if args.output is not None:
                raise WasmContractError("--check does not accept --output")
            exports = inspect_module(module)
    except (OSError, WasmContractError) as error:
        print(f"INTEROP_WASM status=failed error={error}")
        return 1
    payload = {
        "status": "passed",
        "exports": [export.name for export in exports],
        "imports": 0,
    }
    if args.json_output:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "INTEROP_WASM "
            + " ".join(f"{key}={value}" for key, value in payload.items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
