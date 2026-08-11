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


class CapabilityMappingTests(unittest.TestCase):
    def test_semantic_and_profile_mappings_require_capability_evaluation(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        for schema in (
            "spec/contracts/1.0/semantic-ir.schema.json",
            "spec/contracts/1.0/target-profile.schema.json",
        ):
            changed = copy.deepcopy(mapping)
            entry = next(
                item for item in changed["schemas"] if item["schema"] == schema
            )
            entry["rust_modules"].remove("capability_evaluation")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(CoreContractError, "capability"),
            ):
                validate_mapping_document(changed, ROOT)


class CapabilityStageBoundaryTests(unittest.TestCase):
    def test_stage_boundaries_and_certified_prerequisites_are_required(self) -> None:
        sources = source_texts()
        sources["core/src/capability_evaluation.rs"] = sources[
            "core/src/capability_evaluation.rs"
        ].replace("pub fn evaluate_capabilities(", "fn evaluate_capabilities(", 1)
        with self.assertRaisesRegex(CoreContractError, "capability evaluation stage"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for prerequisite in (
            "use crate::semantic::{",
            "use crate::semantic_analysis::{",
            "use crate::structural_analysis::{",
            "use crate::target::{",
        ):
            sources = source_texts()
            sources["core/src/capability_evaluation.rs"] = sources[
                "core/src/capability_evaluation.rs"
            ].replace(prerequisite, "crate::missing_prerequisite", 1)
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "capability evaluation"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_runtime_emitter_and_binding_dependencies_fail(self) -> None:
        for forbidden in (
            "std::env::var",
            "std::process::Command",
            "std::fs::read_to_string",
            "use crate::emitters;",
            "use crate::bindings;",
            "use crate::planner;",
            "use crate::portability;",
        ):
            sources = source_texts()
            sources["core/src/capability_evaluation.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "capability evaluation|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependencies_fail(self) -> None:
        for path in (
            "core/src/semantic_analysis.rs",
            "core/src/structural_analysis.rs",
            "core/src/safety_analysis.rs",
            "core/src/diagnostic_generation.rs",
        ):
            sources = source_texts()
            sources[path] += "\nuse crate::capability_evaluation;\n"
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(CoreContractError, "reverse target dependency"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


class CapabilityPipelineBoundaryTests(unittest.TestCase):
    def test_target_neutral_stages_must_precede_capability_evaluation(self) -> None:
        sources = source_texts()
        sources["core/src/capability_pipeline.rs"] = sources[
            "core/src/capability_pipeline.rs"
        ].replace(
            "run_target_neutral_stages(input)",
            "run_target_neutral_stages_after_capability(input)",
            1,
        )
        with self.assertRaisesRegex(CoreContractError, "diagnostics before"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_runtime_probe_and_later_target_stage_dependencies_fail(self) -> None:
        for forbidden in (
            "std::env::var",
            "std::process::Command",
            "use crate::emitter;",
            "use crate::planner;",
            "use crate::portability;",
            "use crate::protocol;",
        ):
            sources = source_texts()
            pipeline = sources["core/src/capability_pipeline.rs"]
            test_marker = pipeline.find("\n#[cfg(test)]")
            self.assertGreater(test_marker, 0)
            sources["core/src/capability_pipeline.rs"] = (
                pipeline[:test_marker] + f"\n// {forbidden}\n" + pipeline[test_marker:]
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "capability pipeline"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
