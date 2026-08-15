from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tooling.interop_certification import (
    NATIVE_SYMBOLS,
    cargo_target_directory,
    native_library,
    normalize_symbol,
    result,
)


class InteropCertificationTests(unittest.TestCase):
    def test_native_library_names_follow_the_host_triple(self) -> None:
        with (
            patch("tooling.interop_certification.ROOT", Path("repository")),
            patch.dict("os.environ", {}, clear=True),
        ):
            self.assertEqual(
                Path("repository/bindings/interop/target/release/strling_interop.dll"),
                native_library("x86_64-pc-windows-msvc"),
            )
            self.assertEqual(
                Path(
                    "repository/bindings/interop/target/release/libstrling_interop.dylib"
                ),
                native_library("aarch64-apple-darwin"),
            )
            self.assertEqual(
                Path(
                    "repository/bindings/interop/target/release/libstrling_interop.so"
                ),
                native_library("x86_64-unknown-linux-gnu"),
            )

    def test_cargo_target_directory_honors_absolute_and_relative_overrides(
        self,
    ) -> None:
        absolute = Path.cwd() / "shared-target"
        with patch("tooling.interop_certification.ROOT", Path("repository")):
            with patch.dict(
                "os.environ", {"CARGO_TARGET_DIR": "shared-target"}, clear=True
            ):
                self.assertEqual(
                    Path("repository/shared-target"), cargo_target_directory()
                )
            with patch.dict(
                "os.environ", {"CARGO_TARGET_DIR": str(absolute)}, clear=True
            ):
                self.assertEqual(absolute, cargo_target_directory())

    def test_structured_result_has_stable_operation_and_check_identity(self) -> None:
        payload = result(
            "passed",
            0.0,
            {"native_symbols": sorted(NATIVE_SYMBOLS)},
        )
        self.assertEqual("certification-result-v1", payload["schema_version"])
        self.assertEqual("certification.interop", payload["operation_id"])
        self.assertEqual("passed", payload["status"])
        self.assertEqual(
            "certification.interop.native-wasm-boundary",
            payload["checks"][0]["id"],
        )

    def test_mach_o_c_symbol_prefix_is_normalized_only_for_apple_hosts(self) -> None:
        symbol = "_strling_interop_execute_v1"
        self.assertEqual(
            "strling_interop_execute_v1",
            normalize_symbol("aarch64-apple-darwin", symbol),
        )
        self.assertEqual(symbol, normalize_symbol("x86_64-unknown-linux-gnu", symbol))


if __name__ == "__main__":
    unittest.main()
