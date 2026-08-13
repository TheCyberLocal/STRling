"""Architecture fitness tests for the shared conformance boundary."""

from __future__ import annotations

import ast
import unittest

from tooling.shared_cross_engine_corpus import ROOT


class SharedCrossEngineCorpusArchitectureTests(unittest.TestCase):
    def test_rust_projection_cannot_execute_target_runtimes(self) -> None:
        source = (ROOT / "core/examples/shared_conformance_projection.rs").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "std::process",
            "Command::new",
            "pcre2_match",
            "node_regexp_harness",
            "python_re_harness",
            "STRLING_NODE_22_BINARY",
            "STRLING_CPYTHON_311_BINARY",
        ):
            self.assertNotIn(forbidden, source)

    def test_runtime_process_boundary_is_isolated_to_controller(self) -> None:
        path = ROOT / "tooling/shared_cross_engine_corpus.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertIn("subprocess", imports)
        for product_path in (
            ROOT / "core/src/kernel.rs",
            ROOT / "core/src/compiler_pipeline.rs",
            ROOT / "core/src/target_lowering.rs",
            ROOT / "core/src/target_serialization.rs",
        ):
            self.assertNotIn(
                "shared_cross_engine_corpus", product_path.read_text(encoding="utf-8")
            )

    def test_controller_has_no_peer_majority_or_emitted_text_expectation_path(
        self,
    ) -> None:
        source = (
            (ROOT / "tooling/shared_cross_engine_corpus.py")
            .read_text(encoding="utf-8")
            .lower()
        )
        for forbidden in (
            "majority_vote",
            "peer_consensus",
            "expected_pattern",
            "expected_artifact",
            "golden_emitted_text",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
