from __future__ import annotations

import unittest
from pathlib import Path

from tooling.core_stage_boundaries import (
    portability_diagnostics_boundary_violation,
)


ROOT = Path(__file__).resolve().parents[2]
PATH = "core/src/portability_diagnostics.rs"


def source_texts() -> dict[str, str]:
    return {PATH: (ROOT / PATH).read_text(encoding="utf-8")}


def insert_before_tests(source: str, addition: str) -> str:
    marker = source.find("\n#[cfg(test)]")
    if marker < 0:
        return f"{source}\n{addition}\n"
    return source[:marker] + f"\n{addition}\n" + source[marker:]


class PortabilityDiagnosticsArchitectureTests(unittest.TestCase):
    def test_current_evidence_only_stage_passes(self) -> None:
        self.assertIsNone(portability_diagnostics_boundary_violation(source_texts()))

    def test_stage_boundary_and_certified_inputs_are_required(self) -> None:
        sources = source_texts()
        sources[PATH] = sources[PATH].replace(
            "pub fn explain_portability(", "fn explain_portability(", 1
        )
        self.assertRegex(
            portability_diagnostics_boundary_violation(sources) or "",
            "stage boundary",
        )

        for prerequisite in (
            "crate::diagnostic::{",
            "crate::portability_planning::{",
            "crate::semantic::{",
        ):
            sources = source_texts()
            sources[PATH] = sources[PATH].replace(
                prerequisite, "crate::missing_prerequisite::{", 1
            )
            with self.subTest(prerequisite=prerequisite):
                self.assertRegex(
                    portability_diagnostics_boundary_violation(sources) or "",
                    "must consume",
                )

    def test_recomputation_transformation_and_emission_dependencies_fail(self) -> None:
        for forbidden in (
            "evaluate_capabilities(",
            "plan_portability(",
            "apply_semantic_rewrite(",
            "lower_to_target(",
            "emit_target(",
            "use crate::normalization;",
            "use crate::diagnostic_generation;",
            "use crate::emitter;",
            "use crate::bindings;",
            "use crate::frontend;",
            "std::env::var",
            "std::fs::read_to_string",
            "std::process::Command",
            "runtime_probe",
            "target_artifact",
            "emitted_pattern",
        ):
            sources = source_texts()
            sources[PATH] = insert_before_tests(sources[PATH], f"// {forbidden}")
            with self.subTest(forbidden=forbidden):
                self.assertRegex(
                    portability_diagnostics_boundary_violation(sources) or "",
                    "evidence-only explanation boundary",
                )


if __name__ == "__main__":
    unittest.main()
