from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class FrontendOrchestrationArchitectureTests(unittest.TestCase):
    def test_shadow_python_cli_is_removed_and_owned_smokes_use_kernel(self) -> None:
        self.assertFalse((ROOT / "tooling/parse_strl.py").exists())
        for relative in (
            "bindings/python/tests/e2e/test_cli_smoke.py",
            "bindings/typescript/__tests__/e2e/cli_smoke.test.ts",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertIn("strling-kernel", source)
                self.assertIn("contract_version", source)
                self.assertNotIn("parse_strl", source)
                self.assertNotIn("STRling.core", source)

    def test_root_clis_are_only_rust_kernel_transports(self) -> None:
        root_cli = (ROOT / "strling").read_text(encoding="utf-8")
        powershell_cli = (ROOT / "strling.ps1").read_text(encoding="utf-8")
        posix_route = root_cli[
            root_cli.index("PRODUCT_COMMAND=false") : root_cli.index(
                'if ! command -v python3', root_cli.index("PRODUCT_COMMAND=false")
            )
        ]
        powershell_route = powershell_cli[
            powershell_cli.index("$ProductCommand =") : powershell_cli.index(
                "$QualityCommands =", powershell_cli.index("$ProductCommand =")
            )
        ]

        for route in (posix_route, powershell_route):
            with self.subTest(wrapper="powershell" if "$Product" in route else "posix"):
                self.assertIn("cargo", route.lower())
                self.assertIn("strling-kernel", route)
                self.assertIn("--input", route)
                self.assertIn("--request", route)
                for command in (
                    "compile",
                    "import",
                    "explain",
                    "migrate",
                    "simply",
                    "target",
                    "check",
                ):
                    self.assertIn(command, route)
                for forbidden in (
                    "python",
                    "node",
                    "typescript",
                    "regex_frontend",
                    "semantic_frontend",
                    "strling.regex-compat",
                    "strling.semantic",
                    "%flags",
                    "target lowering",
                    "emit",
                ):
                    self.assertNotIn(forbidden, route.lower())

    def test_rust_cli_decodes_contracts_and_calls_only_the_public_facade(self) -> None:
        binary = (ROOT / "core/cli/strling-kernel.rs").read_text(encoding="utf-8")
        self.assertIn("strling_kernel::compile", binary)
        self.assertIn("strling_kernel::validation::from_json", binary)
        self.assertIn("CompileRequest", binary)
        self.assertIn("TargetProfile", binary)

        for forbidden in (
            "regex_frontend",
            "semantic_frontend",
            "::parse(",
            "parse_regex",
            "scan_regex",
            "compile_semantic_diagnostics",
            "compile_semantic_portability",
            "lower_pcre2",
            "lower_ecmascript",
            "lower_python_re",
            "serialize_pcre2",
            "serialize_ecmascript",
            "serialize_python_re",
            "emitters",
            "bindings",
            "std::net",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, binary.lower())

    def test_frontend_dispatch_and_conversion_proof_have_explicit_owners(self) -> None:
        expected = {
            "regex_frontend::parse(": ["core/src/kernel.rs"],
            "semantic_frontend::parse(": [
                "core/src/kernel.rs",
                "core/src/semantic_conversion.rs",
            ],
        }
        for call, expected_owners in expected.items():
            owners = []
            for path in sorted((ROOT / "core/src").rglob("*.rs")):
                source = path.read_text(encoding="utf-8")
                if call in source:
                    owners.append(path.relative_to(ROOT).as_posix())
            with self.subTest(call=call):
                self.assertEqual(owners, expected_owners)

    def test_frontend_module_cannot_lower_targets_or_emit_artifacts(self) -> None:
        for relative in ("core/src/regex_frontend.rs", "core/src/semantic_frontend.rs"):
            frontend = (ROOT / relative).read_text(encoding="utf-8").lower()
            for forbidden in (
                "crate::target",
                "crate::capability_evaluation",
                "crate::portability_planning",
                "targetprofile",
                "targetartifact",
                "emit(",
                "engine_options",
            ):
                with self.subTest(relative=relative, forbidden=forbidden):
                    self.assertNotIn(forbidden, frontend)


if __name__ == "__main__":
    unittest.main()
