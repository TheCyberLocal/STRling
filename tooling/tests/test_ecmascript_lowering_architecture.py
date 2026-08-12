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
LOWERING = "core/src/ecmascript_lowering.rs"
LOWERING_CORPUS = ROOT / "tests" / "conformance" / "ecmascript-lowering.json"
ECMASCRIPT_PROFILE = ROOT / "spec" / "targets" / "profiles" / "ecmascript-2024.json"


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class EcmascriptLoweringMappingTests(unittest.TestCase):
    def test_governed_corpus_names_the_exact_profile_and_closed_boundary(self) -> None:
        corpus = json.loads(LOWERING_CORPUS.read_text(encoding="utf-8"))
        profile = json.loads(ECMASCRIPT_PROFILE.read_text(encoding="utf-8"))

        self.assertEqual(
            set(corpus),
            {
                "corpus_version",
                "target_profile",
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
                "sha256": "5117ff6e6c30da54eb31a4621dce5f4807ab0e95f183848e70a01731a4bb4c9f",
            },
        )
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
                "position",
                "capture",
                "backreference",
                "lookaround",
            ],
        )
        self.assertEqual(
            corpus["certified_rewrites"],
            [
                {
                    "semantic_operation": "atomic_literal",
                    "strategy_id": "rewrite.atomic_literal.elide.v1",
                    "status": "equivalent_rewrite",
                }
            ],
        )
        self.assertEqual(
            corpus["fail_closed"],
            [
                {
                    "semantic_operation": "atomic_non_literal",
                    "diagnostic_code": "STRL-ECMASCRIPT_LOWERING-0011",
                },
                {
                    "semantic_operation": "possessive_repetition",
                    "diagnostic_code": "STRL-ECMASCRIPT_LOWERING-0011",
                },
            ],
        )
        self.assertEqual(
            corpus["resource_limits"],
            {"maximum_nodes": 65536, "maximum_depth": 128},
        )

    def test_consumed_contract_authorities_require_ecmascript_mapping(self) -> None:
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
            entry["rust_modules"].remove("ecmascript_lowering")
            with (
                self.subTest(schema=schema),
                self.assertRaisesRegex(
                    CoreContractError, "ECMAScript|target lowering|target-lowering"
                ),
            ):
                validate_mapping_document(changed, ROOT)


class EcmascriptLoweringBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_valid(self) -> None:
        validate_source_boundaries(source_texts(), ALLOWED_RUNTIME_DEPENDENCIES)

    def test_entrypoint_and_exact_correspondence_are_required(self) -> None:
        for existing, replacement in (
            ("pub fn lower_ecmascript(", "fn lower_ecmascript("),
            ("portability.validate()", "portability.skip_validation()"),
            ("canonical_sha256(input)", "stale_semantic_fingerprint"),
            ("target.reference()", "stale_target_reference"),
            (
                'target.engine.id.as_str() != "ecmascript"',
                'target.engine.id.as_str() != "anything"',
            ),
        ):
            sources = source_texts()
            sources[LOWERING] = sources[LOWERING].replace(existing, replacement, 1)
            with (
                self.subTest(existing=existing),
                self.assertRaisesRegex(
                    CoreContractError, "ECMAScript target[- ]lowering"
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
                self.assertRaisesRegex(CoreContractError, "ECMAScript target lowering"),
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
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "ECMAScript target lowering"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_serialization_runtime_ambient_and_product_dependencies_fail(self) -> None:
        for forbidden in (
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "new RegExp(",
            "RegExp(",
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
            "use crate::emitter;",
            "use crate::kernel;",
        ):
            sources = source_texts()
            sources[LOWERING] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "ECMAScript target lowering|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_neutral_reverse_dependency_and_direct_bypass_fail(self) -> None:
        sources = source_texts()
        sources["core/src/semantic/mod.rs"] += "\n// crate::ecmascript_lowering\n"
        with self.assertRaisesRegex(
            CoreContractError, "target-specific marker|reverse target dependency"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/kernel.rs"] += "\n// lower_ecmascript(\n"
        with self.assertRaisesRegex(CoreContractError, "direct caller"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
