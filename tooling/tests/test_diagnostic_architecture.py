from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tooling.core_contract_validation import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    CoreContractError,
    load_mapping,
    validate_mapping_document,
    validate_source_boundaries,
)


ROOT = Path(__file__).resolve().parents[2]


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class DiagnosticMappingTests(unittest.TestCase):
    def test_diagnostic_mapping_requires_generation_stage(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        diagnostic = next(
            entry
            for entry in changed["schemas"]
            if entry["schema"] == "spec/contracts/1.0/diagnostic.schema.json"
        )
        diagnostic["rust_modules"] = ["diagnostic"]

        with self.assertRaisesRegex(CoreContractError, "diagnostic generation"):
            validate_mapping_document(changed, ROOT)

    def test_compile_result_mapping_requires_private_pipeline(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        result = next(
            entry
            for entry in changed["schemas"]
            if entry["schema"] == "spec/contracts/1.0/compile-result.schema.json"
        )
        result["rust_modules"] = ["protocol::exchange", "protocol::result"]

        with self.assertRaisesRegex(CoreContractError, "compiler pipeline"):
            validate_mapping_document(changed, ROOT)


class DiagnosticStageBoundaryTests(unittest.TestCase):
    def test_stage_boundary_and_certified_prerequisites_are_required(self) -> None:
        sources = source_texts()
        sources["core/src/diagnostic_generation.rs"] = sources[
            "core/src/diagnostic_generation.rs"
        ].replace("pub fn generate_diagnostics(", "fn generate_diagnostics(")
        with self.assertRaisesRegex(
            CoreContractError, "diagnostic generation stage boundary"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        prerequisites = (
            "crate::diagnostic",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
        )
        for prerequisite in prerequisites:
            sources = source_texts()
            sources["core/src/diagnostic_generation.rs"] = sources[
                "core/src/diagnostic_generation.rs"
            ].replace(prerequisite, "crate::missing_prerequisite", 1)
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "diagnostic generation"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_planner_binding_and_editor_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::target::profile;",
            "use crate::planner;",
            "use crate::bindings;",
            "use crate::editor;",
        ):
            sources = source_texts()
            sources["core/src/diagnostic_generation.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "diagnostic generation"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_quality_proof_substage_is_owned_and_target_neutral(self) -> None:
        sources = source_texts()
        sources.pop("core/src/diagnostic_generation/quality.rs")
        with self.assertRaisesRegex(CoreContractError, "quality proof substage"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for forbidden in (
            "use crate::target::profile;",
            "use crate::portability_planning;",
            'let raw_source = "regex text";',
            'std::process::Command::new("runtime");',
        ):
            sources = source_texts()
            sources["core/src/diagnostic_generation/quality.rs"] += (
                f"\n// {forbidden}\n"
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "diagnostic generation.*boundary|target-neutral stage",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


class CompilerPipelineBoundaryTests(unittest.TestCase):
    def test_stage_boundary_and_target_neutral_stages_are_required(self) -> None:
        sources = source_texts()
        sources["core/src/compiler_pipeline.rs"] = sources[
            "core/src/compiler_pipeline.rs"
        ].replace(
            "pub fn compile_semantic_diagnostics(",
            "fn compile_semantic_diagnostics(",
        )
        with self.assertRaisesRegex(CoreContractError, "compiler pipeline boundary"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for prerequisite in (
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::protocol",
        ):
            sources = source_texts()
            sources["core/src/compiler_pipeline.rs"] = sources[
                "core/src/compiler_pipeline.rs"
            ].replace(prerequisite, "crate::missing_prerequisite", 1)
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "compiler pipeline"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_planner_binding_and_editor_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::target::profile;",
            "use crate::planner;",
            "use crate::bindings;",
            "use crate::editor;",
        ):
            sources = source_texts()
            pipeline = sources["core/src/compiler_pipeline.rs"]
            test_marker = pipeline.find("\n#[cfg(test)]")
            self.assertGreater(test_marker, 0)
            sources["core/src/compiler_pipeline.rs"] = (
                pipeline[:test_marker] + f"\n// {forbidden}\n" + pipeline[test_marker:]
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "compiler pipeline"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
