"""Architecture fitness tests for the derived portability matrix."""

from __future__ import annotations

import ast
import unittest

from tooling.portability_matrix import MATRIX_PATH, ROOT, SUMMARY_PATH, load_json


class PortabilityMatrixArchitectureTests(unittest.TestCase):
    def test_controller_is_evidence_only_and_cannot_execute_targets(self) -> None:
        path = ROOT / "tooling/portability_matrix.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in (
            "subprocess",
            "os",
            "socket",
            "threading",
            "tooling.pcre2_runtime_certification",
            "tooling.ecmascript_runtime_certification",
            "tooling.python_re_runtime_certification",
        ):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            "target_pattern",
            "emitted_pattern",
            "peer_consensus",
            "majority_vote",
            "run_harness",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_matrix_does_not_enter_product_or_public_paths(self) -> None:
        for path in (
            ROOT / "core/src/kernel.rs",
            ROOT / "core/src/compiler_pipeline.rs",
            ROOT / "core/src/target_lowering.rs",
            ROOT / "core/src/target_serialization.rs",
            ROOT / "bindings/python/src/STRling/core/compiler.py",
            ROOT / "bindings/typescript/src/STRling/compiler.ts",
        ):
            self.assertNotIn("portability_matrix", path.read_text(encoding="utf-8"))

    def test_generated_artifact_has_one_evidence_owner(self) -> None:
        registry = load_json(ROOT / "governance/generated-artifacts.json")
        artifact = next(
            item
            for item in registry["artifacts"]
            if item["id"] == "initial-portability-matrix"
        )
        self.assertEqual("certification-evidence", artifact["authority"])
        self.assertEqual(
            [
                "tests/conformance/evidence/initial-portability-matrix.json",
                "tests/conformance/evidence/initial-portability-matrix.md",
            ],
            artifact["outputs"],
        )
        self.assertIn(
            "tests/conformance/evidence/shared-cross-engine-observations.json",
            artifact["generator_inputs"],
        )
        self.assertFalse(any(path.startswith("spec/") for path in artifact["outputs"]))

    def test_full_and_release_route_matrix_after_shared_certification(self) -> None:
        toolchain = load_json(ROOT / "toolchain.json")
        profiles = toolchain["policy"]["profiles"]
        for profile_id in ("full", "release"):
            operations = [
                item["operation"] for item in profiles[profile_id]["operations"]
            ]
            self.assertEqual(
                operations.index("shared_cross_engine_certification") + 1,
                operations.index("stdlib_runtime_certification"),
            )
            self.assertEqual(
                operations.index("stdlib_runtime_certification") + 1,
                operations.index("portability_matrix_certification"),
            )
        for profile_id in ("local", "pull-request"):
            self.assertNotIn(
                "portability_matrix_certification",
                [item["operation"] for item in profiles[profile_id]["operations"]],
            )

    def test_exact_outputs_are_excluded_from_competing_formatter(self) -> None:
        policy = load_json(ROOT / "governance/formatting.json")
        paths = {
            MATRIX_PATH.relative_to(ROOT).as_posix(),
            SUMMARY_PATH.relative_to(ROOT).as_posix(),
        }
        ownership = [
            item
            for item in policy["generated_or_serialized"]
            if paths.intersection(item["paths"])
        ]
        self.assertEqual(1, len(ownership))
        self.assertEqual(paths, set(ownership[0]["paths"]))


if __name__ == "__main__":
    unittest.main()
