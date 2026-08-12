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


def insert_before_tests(source: str, addition: str) -> str:
    marker = source.find("\n#[cfg(test)]")
    if marker < 0:
        return f"{source}\n{addition}\n"
    return source[:marker] + f"\n{addition}\n" + source[marker:]


class PortabilityMappingTests(unittest.TestCase):
    def test_semantic_profile_and_portability_mappings_require_planning(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        for schema in (
            "spec/contracts/1.0/portability.schema.json",
            "spec/contracts/1.0/semantic-ir.schema.json",
            "spec/contracts/1.0/target-profile.schema.json",
        ):
            changed = copy.deepcopy(mapping)
            entry = next(
                item for item in changed["schemas"] if item["schema"] == schema
            )
            entry["rust_modules"].remove("portability_planning")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(CoreContractError, "portability|planning"),
            ):
                validate_mapping_document(changed, ROOT)

    def test_semantic_diagnostic_and_portability_mappings_require_explanations(
        self,
    ) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        for schema in (
            "spec/contracts/1.0/diagnostic.schema.json",
            "spec/contracts/1.0/portability.schema.json",
            "spec/contracts/1.0/semantic-ir.schema.json",
        ):
            changed = copy.deepcopy(mapping)
            entry = next(
                item for item in changed["schemas"] if item["schema"] == schema
            )
            entry["rust_modules"].remove("portability_diagnostics")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(CoreContractError, "explanation"),
            ):
                validate_mapping_document(changed, ROOT)


class PortabilityPlanningBoundaryTests(unittest.TestCase):
    def test_stage_boundary_and_certified_prerequisites_are_required(self) -> None:
        sources = source_texts()
        path = "core/src/portability_planning.rs"
        sources[path] = sources[path].replace(
            "pub fn plan_portability(", "fn plan_portability(", 1
        )
        with self.assertRaisesRegex(CoreContractError, "planning stage"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for prerequisite in (
            "crate::capability_evaluation::{",
            "crate::semantic::{",
            "crate::semantic_analysis::{",
            "crate::structural_analysis::",
            "crate::target::{",
        ):
            sources = source_texts()
            sources[path] = sources[path].replace(
                prerequisite, "crate::missing_prerequisite", 1
            )
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "portability planning"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_capabilities_and_analyses_cannot_be_recomputed(self) -> None:
        for forbidden in (
            "evaluate_capabilities(",
            "extract_requirements(",
            "use crate::normalization;",
            "use crate::safety_analysis;",
        ):
            sources = source_texts()
            path = "core/src/portability_planning.rs"
            sources[path] = insert_before_tests(sources[path], f"// {forbidden}")
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "portability planning"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_emitter_runtime_binding_and_frontend_dependencies_fail(self) -> None:
        for forbidden in (
            "std::env::var",
            "std::process::Command",
            "std::fs::read_to_string",
            "use crate::emitters;",
            "use crate::bindings;",
            "use crate::frontend;",
            "runtime_probe",
            "target_artifact",
            "capture_numbering",
        ):
            sources = source_texts()
            path = "core/src/portability_planning.rs"
            sources[path] = insert_before_tests(sources[path], f"// {forbidden}")
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "portability planning|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


class PortabilityPipelineBoundaryTests(unittest.TestCase):
    def test_target_neutral_capability_and_planning_order_is_required(self) -> None:
        for existing, replacement in (
            (
                "run_target_neutral_stages(input)",
                "run_target_neutral_stages_after_capability(input)",
            ),
            ("evaluate_capabilities(", "evaluate_capabilities_after_planning("),
            ("plan_portability(", "plan_portability_before_capability("),
            ("explain_portability(", "explain_portability_before_planning("),
        ):
            sources = source_texts()
            path = "core/src/capability_pipeline.rs"
            sources[path] = sources[path].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(CoreContractError, "dependency order"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_emitter_runtime_binding_and_frontend_dependencies_fail(self) -> None:
        for forbidden in (
            "std::env::var",
            "std::process::Command",
            "std::fs::read_to_string",
            "use crate::emitter;",
            "use crate::bindings;",
            "use crate::frontend;",
            "use crate::protocol;",
            "target_artifact",
        ):
            sources = source_texts()
            path = "core/src/capability_pipeline.rs"
            sources[path] = insert_before_tests(sources[path], f"// {forbidden}")
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "portability pipeline|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
