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
SERIALIZER = "core/src/target_serialization.rs"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class Pcre2SerializationMappingTests(unittest.TestCase):
    def test_consumed_contracts_require_serializer_mapping(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        for schema in (
            "spec/contracts/1.0/diagnostic.schema.json",
            "spec/contracts/1.0/portability.schema.json",
            "spec/contracts/1.0/target-artifact.schema.json",
            "spec/contracts/1.0/target-profile.schema.json",
        ):
            changed = copy.deepcopy(mapping)
            entry = next(
                item for item in changed["schemas"] if item["schema"] == schema
            )
            entry["rust_modules"].remove("target_serialization")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "target artifact|serialization|emission|artifact"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class Pcre2SerializationBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_entrypoint_and_input_output_validation_are_required(self) -> None:
        for existing, replacement in (
            ("pub fn serialize_pcre2(", "fn serialize_pcre2("),
            ("plan.validate()", "plan.skip_validation()"),
            ("artifact.validate()", "artifact.skip_validation()"),
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(
                    CoreContractError, "PCRE2 target.serialization|input and output"
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_lowering_and_artifact_authorities_are_mandatory(self) -> None:
        for prerequisite in (
            "crate::diagnostic::{",
            "crate::source::{",
            "crate::target::{",
            "crate::target_lowering::{",
            "crate::validation::Validate",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                prerequisite, "crate::missing_authority::{", 1
            )
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(
                    CoreContractError,
                    "PCRE2 target serialization|PCRE2 target lowering",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_policy_recomputation_and_profile_reinterpretation_fail(self) -> None:
        for forbidden in (
            "lower_pcre2(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "use crate::capability_evaluation;",
            "use crate::portability_planning;",
            "use crate::semantic;",
            "use crate::target::TargetProfile;",
            "use crate::target::OptionSelection;",
            "engine.version",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "PCRE2 target serialization|PCRE2 target lowering",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_runtime_ambient_product_and_invalid_unicode_leakage_fail(self) -> None:
        for forbidden in (
            "pcre2_compile",
            "pcre2_match",
            "runtime_probe",
            "std::env::var",
            "std::fs::read",
            "std::net::TcpStream",
            "std::process::Command",
            "std::thread::spawn",
            "std::time::SystemTime",
            "thread_rng",
            "use crate::regex_frontend;",
            "use crate::bindings;",
            "use crate::kernel;",
            "(*UTF)",
            "(*UCP)",
            "PCRE2_CODE_UNIT_WIDTH",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "PCRE2 target serialization|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::target_serialization\n"
        with self.assertRaisesRegex(CoreContractError, "reverse target dependency"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/stdlib.rs"] = sources["core/src/stdlib.rs"].replace(
            "\n#[cfg(test)]", "\n// serialize_pcre2(\n#[cfg(test)]", 1
        )
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
