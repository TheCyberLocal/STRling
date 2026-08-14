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
from tooling.core_stage_boundaries import (
    ecmascript_runtime_certification_boundary_violation,
)


ROOT = Path(__file__).resolve().parents[2]
SERIALIZER = "core/src/ecmascript_serialization.rs"
ORCHESTRATOR = ROOT / "tooling" / "ecmascript_runtime_certification.py"
HARNESS = ROOT / "tooling" / "node_regexp_harness.mjs"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class EcmascriptSerializationMappingTests(unittest.TestCase):
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
            entry["rust_modules"].remove("ecmascript_serialization")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "target artifact|serialization|emission|artifact"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class EcmascriptSerializationBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_entrypoint_and_input_output_validation_are_required(self) -> None:
        for existing, replacement in (
            ("pub fn serialize_ecmascript(", "fn serialize_ecmascript("),
            ("plan.validate()", "plan.skip_validation()"),
            ("artifact.validate()", "artifact.skip_validation()"),
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(
                    CoreContractError,
                    "ECMAScript target.serialization|input and output",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_lowering_artifact_profile_and_flag_authorities_are_mandatory(self) -> None:
        for prerequisite in (
            "crate::diagnostic::{",
            "crate::ecmascript_lowering::{",
            "crate::source::{",
            "crate::target::{",
            "crate::validation::Validate",
            "5117ff6e6c30da54eb31a4621dce5f4807ab0e95f183848e70a01731a4bb4c9f",
            "ecmascript.unicode_mode",
            "plan.case_matching",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                prerequisite, "missing_authority"
            )
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(
                    CoreContractError,
                    "ECMAScript target serialization|profile and flag intent",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_policy_recomputation_profile_reinterpretation_and_pcre2_reuse_fail(
        self,
    ) -> None:
        for forbidden in (
            "lower_ecmascript(",
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
            "use crate::target_lowering;",
            "use crate::target_serialization;",
            "serialize_pcre2(",
            "Pcre2Operation::Empty",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "ECMAScript target serialization|ECMAScript target lowering",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_runtime_ambient_product_and_undeclared_global_flags_fail(self) -> None:
        for forbidden in (
            "new RegExp(",
            "RegExp(",
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
            'flags.push("d"',
            'flags.push("g"',
            'flags.push("m"',
            'flags.push("s"',
            'flags.push("v"',
            'flags.push("y"',
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "ECMAScript target serialization|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::ecmascript_serialization\n"
        with self.assertRaisesRegex(
            CoreContractError, "reverse target dependency|target-specific marker"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/stdlib.rs"] = sources["core/src/stdlib.rs"].replace(
            "\n#[cfg(test)]", "\n// serialize_ecmascript(\n#[cfg(test)]", 1
        )
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for path in ("core/src/target_lowering.rs", "core/src/target_serialization.rs"):
            sources = source_texts()
            marker = "\n// crate::ecmascript_serialization\n"
            if "\n#[cfg(test)]" in sources[path]:
                sources[path] = sources[path].replace(
                    "\n#[cfg(test)]", f"{marker}#[cfg(test)]", 1
                )
            else:
                sources[path] += marker
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(
                    CoreContractError,
                    "PCRE2 target lowering|PCRE2 target serialization",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


class EcmascriptRuntimeCertificationBoundaryTests(unittest.TestCase):
    def sources(self) -> tuple[str, str]:
        return (
            ORCHESTRATOR.read_text(encoding="utf-8"),
            HARNESS.read_text(encoding="utf-8"),
        )

    def test_current_runtime_boundary_is_valid(self) -> None:
        orchestrator, harness = self.sources()
        self.assertIsNone(
            ecmascript_runtime_certification_boundary_violation(orchestrator, harness)
        )

    def test_exact_identity_process_and_harness_authority_are_required(self) -> None:
        orchestrator, harness = self.sources()
        for marker in (
            'EXPECTED_NODE = "v22.23.2"',
            "3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327",
            '[str(binary), "--no-warnings", str(HARNESS)]',
            "identity_reader(binary)",
        ):
            changed = orchestrator.replace(marker, "missing_authority", 1)
            with (
                self.subTest(marker=marker),
                self.assertRaisesRegex(
                    AssertionError,
                    "runtime certification",
                ),
            ):
                self.assertIsNone(
                    ecmascript_runtime_certification_boundary_violation(
                        changed, harness
                    )
                )

        for forbidden in ("shell=True", "requests.get(", "os.system("):
            changed = f"{orchestrator}\n# {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(AssertionError, "runtime certification"),
            ):
                self.assertIsNone(
                    ecmascript_runtime_certification_boundary_violation(
                        changed, harness
                    )
                )

    def test_harness_bounds_observation_and_module_isolation_are_required(self) -> None:
        orchestrator, harness = self.sources()
        for marker in (
            "const MAXIMUM_INPUT_BYTES",
            "process.stdin",
            "process.stdout.write",
            'addFlag(flags, "d")',
            'addFlag(flags, "g")',
            "advanceStringIndex(",
        ):
            changed = harness.replace(marker, "missing_authority", 1)
            with (
                self.subTest(marker=marker),
                self.assertRaisesRegex(AssertionError, "runtime harness"),
            ):
                self.assertIsNone(
                    ecmascript_runtime_certification_boundary_violation(
                        orchestrator, changed
                    )
                )

        for forbidden in ("import fs from 'node:fs'", "fetch(", "Math.random"):
            changed = f"{harness}\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(AssertionError, "runtime harness"),
            ):
                self.assertIsNone(
                    ecmascript_runtime_certification_boundary_violation(
                        orchestrator, changed
                    )
                )


if __name__ == "__main__":
    unittest.main()
