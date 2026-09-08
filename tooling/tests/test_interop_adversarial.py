from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tooling.interop_adversarial import (
    CARGO_FUZZ_VERSION,
    EXIT_CODES,
    FUZZ_DIRECTORY,
    FUZZ_TARGETS,
    LINUX_TARGET,
    NIGHTLY_TOOLCHAIN,
    OPERATION_ID,
    ROOT,
    fuzz_command,
    payload,
    certify,
    sanitizer_command,
    sanitizer_environment,
    supported_host,
    tool_identities,
    wasm_build_command,
)


class InteropAdversarialTests(unittest.TestCase):
    def test_exact_manifest_fuzz_denominator_is_executable(self) -> None:
        self.assertEqual(
            (
                "fuzz-arbitrary-bytes",
                "fuzz-structured-envelope",
                "fuzz-length-boundaries",
                "fuzz-simply-graphs",
                "fuzz-target-profiles",
                "fuzz-ownership-sequences",
            ),
            FUZZ_TARGETS,
        )
        evidence = json.loads(
            (ROOT / "tests" / "interop" / "1.0" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        governed = tuple(
            case["id"] for case in evidence["cases"] if case["runner"] == "cargo-fuzz"
        )
        self.assertEqual(FUZZ_TARGETS, governed)
        fuzz_manifest = tomllib.loads(
            (FUZZ_DIRECTORY / "Cargo.toml").read_text(encoding="utf-8")
        )
        self.assertEqual("Apache-2.0", fuzz_manifest["package"]["license"])
        self.assertFalse(fuzz_manifest["package"]["publish"])
        self.assertTrue(
            set(FUZZ_TARGETS) <= {binary["name"] for binary in fuzz_manifest["bin"]}
        )
        with patch("tooling.interop_adversarial.executable", return_value="cargo"):
            for target in FUZZ_TARGETS:
                command = fuzz_command(target, 123)
                self.assertEqual(["cargo", f"+{NIGHTLY_TOOLCHAIN}"], command[:2])
                self.assertIn(str(FUZZ_DIRECTORY), command)
                self.assertIn(target, command)
                self.assertIn("-runs=123", command)
                self.assertIn("-max_len=16384", command)

    def test_sanitizer_commands_are_pinned_and_target_isolated(self) -> None:
        with patch("tooling.interop_adversarial.executable", return_value="cargo"):
            for kind in ("address", "leak"):
                command = sanitizer_command(kind)
                environment = sanitizer_environment(kind)
                self.assertEqual(["cargo", f"+{NIGHTLY_TOOLCHAIN}"], command[:2])
                self.assertIn("-Zbuild-std", command)
                self.assertIn(LINUX_TARGET, command)
                self.assertIn(f"-Zsanitizer={kind}", environment["RUSTFLAGS"])
                self.assertTrue(
                    Path(environment["CARGO_TARGET_DIR"]).parts[-2:]
                    == ("sanitizer", kind)
                )
        evidence = json.loads(
            (ROOT / "tests" / "interop" / "1.0" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            ("sanitizer-native-address-leak", "sanitizer-wasm-host-memory"),
            tuple(
                case["id"]
                for case in evidence["cases"]
                if case["runner"] == "sanitizer-ci"
            ),
        )

    def test_linux_ci_prefetches_pinned_build_std_dependencies(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        sysroot_fetch = (
            "cargo +nightly-2026-08-01 fetch --locked --target "
            'x86_64-unknown-linux-gnu --manifest-path "$(rustc '
            "+nightly-2026-08-01 --print sysroot)/lib/rustlib/src/rust/library/"
            'Cargo.toml"'
        )
        self.assertEqual(2, workflow.count(sysroot_fetch))
        stable_wasm_prefetch = (
            "cargo +1.75.0 build --manifest-path bindings/interop/Cargo.toml "
            "-p strling-interop --target wasm32-unknown-unknown --release --locked"
        )
        self.assertEqual(3, workflow.count(stable_wasm_prefetch))

    def test_wasm_memory_runner_uses_stable_boundary_toolchain(self) -> None:
        with patch("tooling.interop_adversarial.executable", return_value="cargo"):
            command = wasm_build_command()
        self.assertEqual(["cargo", "+1.75.0", "build"], command[:3])
        self.assertIn("wasm32-unknown-unknown", command)
        self.assertIn("--offline", command)

    def test_host_gate_is_exact(self) -> None:
        self.assertTrue(supported_host("Linux", "x86_64"))
        self.assertTrue(supported_host("Linux", "AMD64"))
        self.assertFalse(supported_host("Windows", "AMD64"))
        self.assertFalse(supported_host("Darwin", "arm64"))

    def test_tool_identity_records_channel_separately_from_commit_date(self) -> None:
        rust_identity = """\
rustc 1.99.0-nightly (fixture 2026-07-31)
commit-hash: fixture
commit-date: 2026-07-31
host: x86_64-unknown-linux-gnu
release: 1.99.0-nightly
"""
        with (
            patch(
                "tooling.interop_adversarial.executable", side_effect=lambda name: name
            ),
            patch(
                "tooling.interop_adversarial.run",
                side_effect=[
                    SimpleNamespace(stdout=rust_identity),
                    SimpleNamespace(stdout="cargo-fuzz 0.13.2\n"),
                ],
            ),
        ):
            identity = tool_identities()
        self.assertEqual(NIGHTLY_TOOLCHAIN, identity["rust_channel"])
        self.assertEqual("2026-07-31", identity["rust_commit_date"])

    def test_tool_identity_rejects_non_nightly_compiler(self) -> None:
        stable_identity = """\
commit-hash: fixture
commit-date: 2026-08-01
host: x86_64-unknown-linux-gnu
release: 1.99.0
"""
        with (
            patch("tooling.interop_adversarial.executable", return_value="rustc"),
            patch(
                "tooling.interop_adversarial.run",
                return_value=SimpleNamespace(stdout=stable_identity),
            ),
            self.assertRaisesRegex(RuntimeError, "not a nightly"),
        ):
            tool_identities()

    def test_structured_result_has_stable_operation_identity(self) -> None:
        result = payload(
            "passed",
            0.0,
            [{"id": f"{OPERATION_ID}.fixture", "status": "passed", "details": {}}],
        )
        self.assertEqual("certification-result-v1", result["schema_version"])
        self.assertEqual(OPERATION_ID, result["operation_id"])
        self.assertEqual("passed", result["status"])
        self.assertEqual(1, len(result["checks"]))
        self.assertEqual("0.13.2", CARGO_FUZZ_VERSION)

    def test_certification_emits_the_exact_six_plus_two_case_denominator(self) -> None:
        contract = SimpleNamespace(
            contract_fingerprint="sha256:" + "1" * 64,
            evidence_fingerprint="sha256:" + "2" * 64,
        )
        with (
            patch("tooling.interop_adversarial.supported_host", return_value=True),
            patch(
                "tooling.interop_adversarial.InteropContractSuite.certify",
                return_value=contract,
            ),
            patch(
                "tooling.interop_adversarial.tool_identities",
                return_value={
                    "cargo_fuzz": "cargo-fuzz 0.13.2",
                    "rust_commit": "fixture",
                    "rust_release": "fixture-nightly",
                    "rust_target": LINUX_TARGET,
                },
            ),
            patch("tooling.interop_adversarial.executable", return_value="cargo"),
            patch("tooling.interop_adversarial.run"),
            patch(
                "tooling.interop_adversarial.certify_runtime",
                return_value={
                    "wasm_exports": 6,
                    "wasm_imports": 0,
                    "wasm_instances": 2,
                    "wasm_lifecycle": "alloc-execute-read-free-dealloc",
                },
            ),
        ):
            result, exit_code = certify(fuzz_runs=7)
        self.assertEqual(EXIT_CODES["passed"], exit_code)
        self.assertEqual("passed", result["status"])
        self.assertEqual(
            [
                *(f"{OPERATION_ID}.{target}" for target in FUZZ_TARGETS),
                f"{OPERATION_ID}.sanitizer-native-address-leak",
                f"{OPERATION_ID}.sanitizer-wasm-host-memory",
            ],
            [check["id"] for check in result["checks"]],
        )
        self.assertTrue(all(check["status"] == "passed" for check in result["checks"]))

    def test_unknown_target_and_sanitizer_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            fuzz_command("fuzz-not-governed", 1)
        with self.assertRaises(ValueError):
            fuzz_command(FUZZ_TARGETS[0], 0)
        with self.assertRaises(ValueError):
            sanitizer_command("memory")
        with self.assertRaises(ValueError):
            sanitizer_environment("memory")


if __name__ == "__main__":
    unittest.main()
