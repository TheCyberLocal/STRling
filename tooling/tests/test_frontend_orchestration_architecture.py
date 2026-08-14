from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class FrontendOrchestrationArchitectureTests(unittest.TestCase):
    def test_root_cli_is_only_a_rust_kernel_transport(self) -> None:
        root_cli = (ROOT / "strling").read_text(encoding="utf-8")
        start = root_cli.index('if [[ "${1:-}" == "compile" ]]')
        end = root_cli.index("\nfi", start) + len("\nfi")
        compile_route = root_cli[start:end]

        self.assertIn("cargo run", compile_route)
        self.assertIn("--bin strling-kernel", compile_route)
        for forbidden in (
            "python",
            "node",
            "typescript",
            "regex_frontend",
            "semantic_frontend",
            "strling.regex-compat",
            "strling.semantic",
            "%flags",
            "parse",
            "target lowering",
            "emit",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, compile_route.lower())

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
            "target_artifact",
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
