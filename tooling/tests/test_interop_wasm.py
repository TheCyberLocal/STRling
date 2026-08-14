from __future__ import annotations

import unittest

from tooling.interop_wasm import (
    Export,
    WasmContractError,
    encode_exports,
    encode_u32,
    inspect_module,
    seal_module,
)


def module_with(exports: list[Export], imports: int = 0) -> bytes:
    module = bytearray(b"\x00asm\x01\x00\x00\x00")
    if imports:
        payload = encode_u32(imports)
        module.extend(b"\x02" + encode_u32(len(payload)) + payload)
    payload = encode_exports(exports)
    module.extend(b"\x07" + encode_u32(len(payload)) + payload)
    return bytes(module)


def governed_exports() -> list[Export]:
    return [
        Export("memory", 2, 0),
        Export("strling_wasm_abi_version_v1", 0, 0),
        Export("strling_wasm_alloc_v1", 0, 1),
        Export("strling_wasm_dealloc_v1", 0, 2),
        Export("strling_wasm_execute_v1", 0, 3),
        Export("strling_wasm_owned_bytes_free_v1", 0, 4),
    ]


class InteropWasmTests(unittest.TestCase):
    def test_seal_removes_only_known_linker_metadata_exports(self) -> None:
        source = module_with(
            governed_exports()
            + [Export("__data_end", 3, 0), Export("__heap_base", 3, 1)]
        )
        sealed = seal_module(source)
        self.assertEqual(governed_exports(), inspect_module(sealed))

    def test_seal_rejects_an_unexpected_export(self) -> None:
        source = module_with(governed_exports() + [Export("hidden_native", 0, 5)])
        with self.assertRaisesRegex(WasmContractError, "unexpected"):
            seal_module(source)

    def test_check_rejects_linker_metadata_that_was_not_sealed(self) -> None:
        source = module_with(governed_exports() + [Export("__heap_base", 3, 1)])
        with self.assertRaisesRegex(WasmContractError, "unexpected"):
            inspect_module(source)

    def test_imports_are_rejected(self) -> None:
        with self.assertRaisesRegex(WasmContractError, "import nothing"):
            seal_module(module_with(governed_exports(), imports=1))

    def test_missing_or_mistyped_governed_export_is_rejected(self) -> None:
        exports = governed_exports()
        exports[0] = Export("memory", 0, 0)
        with self.assertRaisesRegex(WasmContractError, "mistyped"):
            seal_module(module_with(exports))


if __name__ == "__main__":
    unittest.main()
