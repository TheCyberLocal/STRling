from __future__ import annotations

import copy
import json
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
LOWERING = "core/src/python_re_lowering.rs"
LOWERING_CORPUS = ROOT / "tests" / "conformance" / "python-re-lowering.json"
PYTHON_RE_PROFILE = ROOT / "spec" / "targets" / "profiles" / "python-re-3.11.json"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class PythonReLoweringMappingTests(unittest.TestCase):
    def test_governed_corpus_names_the_exact_profile_and_closed_boundary(self) -> None:
        corpus = json.loads(LOWERING_CORPUS.read_text(encoding="utf-8"))
        profile = json.loads(PYTHON_RE_PROFILE.read_text(encoding="utf-8"))

        self.assertEqual(
            set(corpus),
            {
                "corpus_version",
                "target_profile",
                "pattern_kinds",
                "native_operations",
                "certified_rewrites",
                "fail_closed",
                "resource_limits",
            },
        )
        self.assertEqual(corpus["corpus_version"], "1.0.0")
        self.assertEqual(
            corpus["target_profile"],
            {
                "profile_id": profile["profile_id"],
                "profile_version": profile["profile_version"],
                "sha256": "5808a05beb86acf1577ab4b10055c65c0ee81eb7a167e1f6762c421e7043b751",
            },
        )
        self.assertEqual(corpus["pattern_kinds"], ["str", "bytes"])
        self.assertEqual(
            corpus["native_operations"],
            [
                "empty",
                "sequence",
                "alternation",
                "literal",
                "wildcard",
                "character_set",
                "repeat_greedy",
                "repeat_lazy",
                "repeat_possessive",
                "position",
                "capture",
                "backreference",
                "lookaround",
                "atomic",
            ],
        )
        self.assertEqual(corpus["certified_rewrites"], [])
        self.assertEqual(
            corpus["fail_closed"],
            [
                {
                    "semantic_operation": "variable_length_lookbehind",
                    "diagnostic_code": "STRL-PYTHON_RE_LOWERING-0011",
                },
                {
                    "semantic_operation": "unicode_property",
                    "diagnostic_code": "STRL-PYTHON_RE_LOWERING-0011",
                },
                {
                    "semantic_operation": "unicode_semantics_in_bytes_pattern",
                    "diagnostic_code": "STRL-PYTHON_RE_LOWERING-0014",
                },
            ],
        )
        self.assertEqual(
            corpus["resource_limits"],
            {"maximum_nodes": 65536, "maximum_depth": 128},
        )

    def test_consumed_contract_authorities_require_python_re_mapping(self) -> None:
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
            entry["rust_modules"].remove("python_re_lowering")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "Python re|target lowering|target-lowering"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class PythonReLoweringBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_entrypoint_and_exact_correspondence_are_required(self) -> None:
        for existing, replacement in (
            ("pub fn lower_python_re(", "fn lower_python_re("),
            ("portability.validate()", "portability.skip_validation()"),
            ("canonical_sha256(input)", "stale_semantic_fingerprint"),
            ("target.reference()", "stale_target_reference"),
            (
                'target.engine.id.as_str() != "python_re"',
                'target.engine.id.as_str() != "anything"',
            ),
            ("target.runtime.as_ref()", "target.runtime.skip_reference()"),
            (
                'runtime.id.as_str() != "cpython"',
                'runtime.id.as_str() != "anything"',
            ),
        ):
            sources = source_texts()
            sources[LOWERING] = sources[LOWERING].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(
                    CoreContractError, "Python re target[- ]lowering"
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_neutral_certified_inputs_are_mandatory(self) -> None:
        for prerequisite in (
            "crate::diagnostic::{",
            "crate::portability_planning::{",
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
                self.assertRaisesRegex(CoreContractError, "Python re target lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_policy_recomputation_and_pcre2_reuse_fail(self) -> None:
        for forbidden in (
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "use crate::capability_evaluation;",
            "use crate::semantic_analysis;",
            "use crate::structural_analysis;",
            "use crate::target_lowering;",
            "use crate::target_serialization;",
            "Pcre2Operation::Empty",
            "Pcre2LoweringPlan",
            "serialize_pcre2(",
            "EcmascriptOperation::Empty",
            "EcmascriptLoweringPlan",
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "use crate::python_reference;",
            "use crate::legacy_reference;",
            "STRling.core",
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "Python re target lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_serialization_runtime_ambient_and_product_dependencies_fail(self) -> None:
        for forbidden in (
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "re.compile(",
            "TargetArtifact {",
            "GeneratedSpan {",
            "std::env::var",
            "std::fs::read",
            "std::net::TcpStream",
            "std::process::Command",
            "std::thread::spawn",
            "std::time::SystemTime",
            "thread_rng",
            "use crate::regex_frontend;",
            "use crate::bindings;",
            "bindings::python",
            "use crate::emitter;",
            "use crate::kernel;",
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "Python re target lowering|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::python_re_lowering\n"
        with self.assertRaisesRegex(
            CoreContractError, "target-specific marker|reverse target dependency"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/stdlib.rs"] = sources["core/src/stdlib.rs"].replace(
            "\n#[cfg(test)]", "\n// lower_python_re(\n#[cfg(test)]", 1
        )
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
