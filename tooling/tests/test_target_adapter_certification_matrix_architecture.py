"""Architecture fitness tests for target and adapter matrix derivation."""

from __future__ import annotations

import ast
import unittest

from tooling.target_adapter_certification_matrix import (
    MATRIX_PATH,
    ROOT,
    SOURCE_EVIDENCE_PATH,
    SUMMARY_PATH,
)


class TargetAdapterMatrixArchitectureTests(unittest.TestCase):
    def test_controller_is_evidence_only_and_cannot_execute_certifiers(self) -> None:
        path = ROOT / "tooling/target_adapter_certification_matrix.py"
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
            "tooling.shared_cross_engine_corpus",
            "tooling.stdlib_runtime_certification",
            "tooling.typescript_python_adapter_runtime",
            "tooling.jvm_adapter_runtime",
            "tooling.dotnet_adapter_runtime",
            "tooling.go_dart_swift_adapter_runtime",
            "tooling.dynamic_language_adapter_runtime",
        ):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            "subprocess.run",
            "popen(",
            "system(",
            "run_harness",
            "peer_consensus",
            "majority_vote",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_controller_owns_only_certification_evidence_paths(self) -> None:
        expected_root = ROOT / "tests/certification/target-adapter/1.0"
        for path in (SOURCE_EVIDENCE_PATH, MATRIX_PATH, SUMMARY_PATH):
            self.assertTrue(path.is_relative_to(expected_root))
        self.assertFalse(
            any(
                path.is_relative_to(ROOT / "spec")
                for path in (MATRIX_PATH, SUMMARY_PATH)
            )
        )
        self.assertFalse(
            any(
                path.is_relative_to(ROOT / "bindings")
                for path in (MATRIX_PATH, SUMMARY_PATH)
            )
        )

    def test_product_paths_do_not_import_the_matrix_controller(self) -> None:
        excluded_directories = {
            ".dart_tool",
            ".build",
            ".gradle",
            ".venv",
            "build",
            "dist",
            "node_modules",
            "target",
            "vendor",
        }
        text_suffixes = {
            ".c",
            ".cc",
            ".cs",
            ".dart",
            ".fs",
            ".go",
            ".h",
            ".java",
            ".kt",
            ".lua",
            ".php",
            ".pl",
            ".pm",
            ".py",
            ".r",
            ".rb",
            ".rs",
            ".swift",
            ".ts",
        }
        roots = (
            ROOT / "core/src",
            ROOT / "bindings",
            ROOT / "packages",
        )
        for root in roots:
            for path in root.rglob("*"):
                relative = path.relative_to(root)
                if (
                    excluded_directories.intersection(relative.parts)
                    or not path.is_file()
                    or path.suffix.lower() not in text_suffixes
                ):
                    continue
                source = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    self.assertNotIn("target_adapter_certification_matrix", source)

    def test_controller_has_no_generated_artifact_global_mutation_path(self) -> None:
        source = (ROOT / "tooling/target_adapter_certification_matrix.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("globals()", source)
        self.assertNotIn("monkeypatch", source.lower())


if __name__ == "__main__":
    unittest.main()
