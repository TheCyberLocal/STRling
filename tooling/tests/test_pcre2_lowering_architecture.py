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
LOWERING = "core/src/target_lowering.rs"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class Pcre2LoweringMappingTests(unittest.TestCase):
    def test_consumed_contract_authorities_require_target_lowering_mapping(
        self,
    ) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        for schema in (
            "spec/contracts/1.0/diagnostic.schema.json",
            "spec/contracts/1.0/portability.schema.json",
            "spec/contracts/1.0/semantic-ir.schema.json",
            "spec/contracts/1.0/target-profile.schema.json",
        ):
            changed = copy.deepcopy(mapping)
            entry = next(
                item for item in changed["schemas"] if item["schema"] == schema
            )
            entry["rust_modules"].remove("target_lowering")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "target.lowering|target-lowering"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class Pcre2LoweringBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_stage_entrypoint_and_exact_correspondence_checks_are_required(
        self,
    ) -> None:
        for existing, replacement in (
            ("pub fn lower_pcre2(", "fn lower_pcre2("),
            ("portability.validate()", "portability.skip_validation()"),
            ("canonical_sha256(input)", "stale_semantic_fingerprint"),
            ("target.reference()", "stale_target_reference"),
            (
                'target.engine.id.as_str() != "pcre2"',
                'target.engine.id.as_str() != "anything"',
            ),
        ):
            sources = source_texts()
            sources[LOWERING] = sources[LOWERING].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(CoreContractError, "PCRE2 target.lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_certified_inputs_are_mandatory(self) -> None:
        for prerequisite in (
            "crate::capability_evaluation::{",
            "crate::diagnostic::{",
            "crate::portability_planning::{",
            "crate::post_lowering_requirements::{",
            "crate::semantic::{",
            "crate::source::{",
            "crate::target::{",
            "crate::validation::{",
        ):
            sources = source_texts()
            sources[LOWERING] = sources[LOWERING].replace(
                prerequisite, "crate::missing_authority::{", 1
            )
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "PCRE2 target lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_post_lowering_requirement_completeness_is_mandatory(self) -> None:
        for marker in (
            "extract_pcre2_emitted_requirements(",
            "reconcile_emitted_requirements(",
            "classify_introduced_requirements(",
        ):
            sources = source_texts()
            sources[LOWERING] = sources[LOWERING].replace(marker, "missing(", 1)
            with (
                self.subTest(marker=marker),
                self.assertRaisesRegex(
                    CoreContractError, "capability-bearing target operations"
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_capability_and_planning_policy_cannot_be_recomputed(self) -> None:
        for forbidden in (
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "use crate::capability_evaluation;",
            "use crate::semantic_analysis;",
            "use crate::structural_analysis;",
            "use crate::safety_analysis;",
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "PCRE2 target lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_serialization_runtime_ambient_and_product_dependencies_fail(self) -> None:
        for forbidden in (
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "pcre2_compile",
            "pcre2_match",
            "EmittedPattern {",
            "GeneratedSpan {",
            "TargetArtifact {",
            "std::env::var",
            "std::fs::read",
            "std::net::TcpStream",
            "std::process::Command",
            "std::thread::spawn",
            "std::time::SystemTime",
            "thread_rng",
            "use crate::regex_frontend;",
            "use crate::bindings;",
            "use crate::emitter;",
            "use crate::kernel;",
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "PCRE2 target lowering|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::target_lowering\n"
        with self.assertRaisesRegex(CoreContractError, "reverse target dependency"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/stdlib.rs"] = sources["core/src/stdlib.rs"].replace(
            "\n#[cfg(test)]", "\n// lower_pcre2(\n#[cfg(test)]", 1
        )
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_test_only_direct_caller_is_not_a_product_bypass(self) -> None:
        sources = source_texts()
        sources["core/src/stdlib.rs"] += (
            "\n#[cfg(test)]\nmod tests { fn projection() { lower_pcre2(); } }\n"
        )
        validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
