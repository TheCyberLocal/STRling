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
    python_re_runtime_certification_boundary_violation,
)

ROOT = Path(__file__).resolve().parents[2]
SERIALIZER = "core/src/python_re_serialization.rs"
ORCHESTRATOR = ROOT / "tooling" / "python_re_runtime_certification.py"
HARNESS = ROOT / "tooling" / "python_re_harness.py"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class PythonReSerializationMappingTests(unittest.TestCase):
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
            entry["rust_modules"].remove("python_re_serialization")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "target artifact|serialization|emission|artifact"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class PythonReSerializationBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_entrypoint_and_input_output_validation_are_required(self) -> None:
        for existing, replacement in (
            ("pub fn serialize_python_re(", "fn serialize_python_re("),
            ("plan.validate()", "plan.skip_validation()"),
            ("artifact.validate()", "artifact.skip_validation()"),
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(
                    CoreContractError,
                    "Python re target.serialization|input and output",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_lowering_artifact_profile_and_flag_authorities_are_mandatory(self) -> None:
        for prerequisite in (
            "crate::diagnostic::{",
            "crate::python_re_lowering::{",
            "crate::source::{",
            "crate::target::{",
            "crate::validation::Validate",
            "55e7f0bc93e2192d5f09f6c4ef65b6bff0dc831571059d80edf9b8b661f80a6c",
            "2ba10d0f9ba00c0f5685fc20a40ae436937952074558d8bba89ffe6bb244dfca",
            "python.pattern_kind",
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
                    "Python re target serialization|profile, pattern-kind",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_policy_recomputation_profile_reinterpretation_and_peer_reuse_fail(
        self,
    ) -> None:
        for forbidden in (
            "lower_python_re(",
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
            "serialize_ecmascript(",
            "EcmascriptOperation::Empty",
            "serialize_pcre2(",
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "Python re target serialization|Python re target lowering",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_runtime_ambient_product_and_undeclared_global_flags_fail(self) -> None:
        for forbidden in (
            "re.compile(",
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
            'flags.push("a"',
            'flags.push("l"',
            'flags.push("m"',
            'flags.push("s"',
            'flags.push("u"',
            'flags.push("x"',
        ):
            sources = source_texts()
            sources[SERIALIZER] = sources[SERIALIZER].replace(
                "\n#[cfg(test)]", f"\n// {forbidden}\n#[cfg(test)]", 1
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "Python re target serialization|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::python_re_serialization\n"
        with self.assertRaisesRegex(
            CoreContractError, "reverse target dependency|target-specific marker"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/stdlib.rs"] = sources["core/src/stdlib.rs"].replace(
            "\n#[cfg(test)]", "\n// serialize_python_re(\n#[cfg(test)]", 1
        )
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


class PythonReRuntimeCertificationBoundaryTests(unittest.TestCase):
    def sources(self) -> tuple[str, str]:
        return (
            ORCHESTRATOR.read_text(encoding="utf-8"),
            HARNESS.read_text(encoding="utf-8"),
        )

    def test_current_runtime_boundary_is_valid(self) -> None:
        orchestrator, harness = self.sources()
        self.assertIsNone(
            python_re_runtime_certification_boundary_violation(orchestrator, harness)
        )

    def test_exact_identity_process_and_profile_authority_are_required(self) -> None:
        orchestrator, harness = self.sources()
        for marker in (
            'EXPECTED_VERSION = "3.11.15"',
            'artifact_sha256("cpython-3.11.15")',
            "2ba10d0f9ba00c0f5685fc20a40ae436937952074558d8bba89ffe6bb244dfca",
            '[str(binary), "-I", "-S", "-B", str(HARNESS)]',
            "identity_reader(binary)",
        ):
            changed = orchestrator.replace(marker, "missing_authority", 1)
            with (
                self.subTest(marker=marker),
                self.assertRaisesRegex(AssertionError, "runtime certification"),
            ):
                self.assertIsNone(
                    python_re_runtime_certification_boundary_violation(changed, harness)
                )

        for forbidden in ("shell=True", "requests.get(", "os.system("):
            changed = f"{orchestrator}\n# {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(AssertionError, "runtime certification"),
            ):
                self.assertIsNone(
                    python_re_runtime_certification_boundary_violation(changed, harness)
                )

    def test_harness_bounds_observation_and_process_isolation_are_required(
        self,
    ) -> None:
        orchestrator, harness = self.sources()
        for marker in (
            "MAXIMUM_INPUT_BYTES",
            "sys.stdin.buffer",
            "re.compile(",
            "compiled.finditer(",
            "sys.implementation.cache_tag",
        ):
            changed = harness.replace(marker, "missing_authority")
            with (
                self.subTest(marker=marker),
                self.assertRaisesRegex(AssertionError, "runtime harness"),
            ):
                self.assertIsNone(
                    python_re_runtime_certification_boundary_violation(
                        orchestrator, changed
                    )
                )

        for forbidden in ("import os", "import subprocess", "open("):
            changed = f"{harness}\n# {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(AssertionError, "runtime harness"),
            ):
                self.assertIsNone(
                    python_re_runtime_certification_boundary_violation(
                        orchestrator, changed
                    )
                )


if __name__ == "__main__":
    unittest.main()
