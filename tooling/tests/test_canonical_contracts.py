"""Focused certification tests for canonical STRling data contracts."""

from __future__ import annotations

import copy
import json
import unittest

from tooling.contract_validation import (
    CONFORMANCE_ROOT,
    CONTRACT_ROOT,
    PROFILE_ROOT,
    ContractValidationError,
    ContractSuite,
    canonical_json,
    iter_nodes,
    load_json,
)


class CanonicalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = ContractSuite()

    def test_suite_structure_and_local_links(self) -> None:
        self.assertEqual(9, self.suite.validate_suite_structure())

    def test_all_schemas_are_valid_draft_2020_12(self) -> None:
        self.assertEqual(
            {
                "analysis.schema.json",
                "compile-request.schema.json",
                "compile-result.schema.json",
                "conformance-case.schema.json",
                "conformance-manifest.schema.json",
                "diagnostic.schema.json",
                "portability.schema.json",
                "semantic-ir.schema.json",
                "source.schema.json",
                "target-artifact.schema.json",
                "target-profile.schema.json",
            },
            set(self.suite.schemas),
        )

    def test_positive_examples_validate(self) -> None:
        self.assertEqual(60, self.suite.validate_positive_examples())

    def test_controlled_negative_examples_are_rejected(self) -> None:
        self.assertEqual(33, self.suite.validate_negative_examples())

    def test_all_semantic_node_categories_are_exercised(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        kinds = {node["kind"] for node in iter_nodes(example["root"])}
        self.assertEqual(
            {
                "alternation",
                "atomic",
                "backreference",
                "capture",
                "character_set",
                "empty",
                "literal",
                "lookaround",
                "position",
                "repeat",
                "sequence",
                "wildcard",
            },
            kinds,
        )

    def test_constructed_semantics_need_no_source_or_span(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-constructed.json"
        )
        self.suite.validate("semantic-ir.schema.json", example)
        self.assertNotIn("sources", example)
        self.assertTrue(
            all("origin" not in node for node in iter_nodes(example["root"]))
        )

    def test_unicode_example_uses_utf8_byte_boundaries(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        self.suite.validate("semantic-ir.schema.json", example)
        wildcard = next(
            node for node in iter_nodes(example["root"]) if node["kind"] == "wildcard"
        )
        span = wildcard["origin"]["source_spans"][0]
        self.assertEqual((2, 6), (span["start"], span["end"]))
        self.assertEqual(4, len("😀".encode("utf-8")))

    def test_serialization_is_deterministic_and_unicode_preserving(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        first = canonical_json(example)
        second = canonical_json(json.loads(first.decode("utf-8")))
        self.assertEqual(first, second)
        self.assertIn("α".encode(), first)
        self.assertNotIn(b": ", first)
        self.assertNotIn(b", ", first)

    def test_successful_source_compile_exchange(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "source-success.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "success.json"
        )
        self.suite.validate_exchange(request, result)

    def test_unsupported_frontend_is_a_structured_failure(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "unsupported-frontend.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "unsupported-frontend.json"
        )
        self.suite.validate_exchange(request, result)
        self.assertEqual("STRL-PROTOCOL-0002", result["diagnostics"][0]["code"])

    def test_partial_semantics_require_explicit_request(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "partial-failure.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "partial-failure.json"
        )
        self.suite.validate_exchange(request, result)
        self.assertEqual("partial", result["semantic_result"]["status"])

    def test_all_protocol_examples_round_trip(self) -> None:
        for family in (
            "diagnostic",
            "analysis",
            "compile-request",
            "compile-result",
            "portability",
            "target-artifact",
        ):
            for path in sorted((CONTRACT_ROOT / "examples" / family).glob("*.json")):
                value = load_json(path)
                first = canonical_json(value)
                self.assertEqual(
                    first,
                    canonical_json(json.loads(first.decode("utf-8"))),
                    path,
                )
        for path in sorted(PROFILE_ROOT.glob("*.json")):
            value = load_json(path)
            first = canonical_json(value)
            self.assertEqual(
                first,
                canonical_json(json.loads(first.decode("utf-8"))),
                path,
            )
        conformance_paths = [
            CONFORMANCE_ROOT / "manifest.json",
            CONFORMANCE_ROOT / "shared-corpus-v1.json",
            CONFORMANCE_ROOT / "shared-corpus-v1.schema.json",
            *sorted((CONFORMANCE_ROOT / "cases").glob("*.json")),
        ]
        for path in conformance_paths:
            value = load_json(path)
            first = canonical_json(value)
            self.assertEqual(
                first,
                canonical_json(json.loads(first.decode("utf-8"))),
                path,
            )

    def test_diagnostic_attribution_must_resolve_to_exchange_source(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "partial-failure.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "partial-failure.json"
        )
        malformed = copy.deepcopy(result)
        malformed["diagnostics"][0]["primary_location"]["source_id"] = "src:undeclared"
        with self.assertRaises(ContractValidationError):
            self.suite.validate_exchange(request, malformed)

    def test_analysis_node_ids_must_resolve_to_semantic_result(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "source-success.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "success.json"
        )
        malformed = copy.deepcopy(result)
        malformed["analysis"]["node_facts"][0]["node_id"] = "node:undeclared"
        with self.assertRaises(ContractValidationError):
            self.suite.validate_exchange(request, malformed)

    def test_same_engine_versions_have_distinct_capabilities(self) -> None:
        earlier = load_json(PROFILE_ROOT / "pcre2-10.42.json")
        modern = load_json(PROFILE_ROOT / "pcre2-10.43.json")
        earlier_capabilities = {
            item["capability_id"]: item for item in earlier["capabilities"]
        }
        modern_capabilities = {
            item["capability_id"]: item for item in modern["capabilities"]
        }
        capability = "assertions.lookbehind.variable_length"
        self.assertEqual(
            "unavailable", earlier_capabilities[capability]["availability"]
        )
        self.assertEqual("constrained", modern_capabilities[capability]["availability"])
        self.assertNotEqual(
            self.suite.profile_fingerprints[
                (earlier["profile_id"], earlier["profile_version"])
            ],
            self.suite.profile_fingerprints[
                (modern["profile_id"], modern["profile_version"])
            ],
        )

    def test_target_artifact_keeps_options_out_of_pattern_text(self) -> None:
        artifact = load_json(
            CONTRACT_ROOT / "examples" / "target-artifact" / "pcre2-with-options.json"
        )
        self.suite.validate("target-artifact.schema.json", artifact)
        self.assertNotIn("(*UTF)", artifact["pattern"]["text"])
        self.assertNotIn("(*UCP)", artifact["pattern"]["text"])
        self.assertEqual(
            [
                "pcre2.matcher_api",
                "pcre2.max_variable_lookbehind",
                "pcre2.multiline",
                "pcre2.newline",
                "pcre2.ucp",
                "pcre2.utf",
            ],
            [item["option_id"] for item in artifact["engine_options"]],
        )

    def test_target_artifact_compile_exchange(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "target-artifact.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "target-artifact.json"
        )
        self.suite.validate_exchange(request, result)
        self.assertEqual(
            request["target_profile"], result["artifact"]["target_profile"]
        )

    def test_profile_reference_fingerprint_is_verified(self) -> None:
        artifact = load_json(
            CONTRACT_ROOT / "examples" / "target-artifact" / "pcre2-with-options.json"
        )
        malformed = copy.deepcopy(artifact)
        malformed["target_profile"]["sha256"] = "0" * 64
        with self.assertRaises(ContractValidationError):
            self.suite.validate("target-artifact.schema.json", malformed)

    def test_seed_manifest_is_draft_and_specification_owned(self) -> None:
        manifest = load_json(CONFORMANCE_ROOT / "manifest.json")
        self.suite.validate("conformance-manifest.schema.json", manifest)
        self.assertEqual("draft", manifest["authority_status"])
        self.assertNotIn("delegation", manifest)
        for entry in manifest["cases"]:
            case = load_json(CONTRACT_ROOT.parents[2] / entry["path"])
            self.assertEqual("specification_authored", case["authorship"]["kind"])

    def test_case_cannot_self_promote_or_claim_implementation_authorship(self) -> None:
        case = load_json(CONFORMANCE_ROOT / "cases" / "semantic-literal.json")
        self_promoted = copy.deepcopy(case)
        self_promoted["authority_status"] = "delegated_normative"
        with self.assertRaises(ContractValidationError):
            self.suite.validate("conformance-case.schema.json", self_promoted)

        implementation_generated = copy.deepcopy(case)
        implementation_generated["authorship"]["kind"] = "implementation_generated"
        with self.assertRaises(ContractValidationError):
            self.suite.validate(
                "conformance-case.schema.json", implementation_generated
            )

    def test_error_case_cannot_declare_execution_expectations(self) -> None:
        malformed = load_json(
            CONTRACT_ROOT / "invalid" / "conformance-case" / "error-with-matches.json"
        )
        with self.assertRaises(ContractValidationError):
            self.suite.validate("conformance-case.schema.json", malformed)

    def test_seed_cases_cover_independent_expectation_layers(self) -> None:
        cases = [
            load_json(path)
            for path in sorted((CONFORMANCE_ROOT / "cases").glob("*.json"))
        ]
        layers = {layer for case in cases for layer in case["expectations"]}
        self.assertEqual(
            {"semantic", "diagnostics", "matches", "targets"},
            layers,
        )
        lookbehind = next(
            case for case in cases if case["case_id"].startswith("case:targets/")
        )
        self.suite.validate("conformance-case.schema.json", lookbehind)


if __name__ == "__main__":
    unittest.main()
