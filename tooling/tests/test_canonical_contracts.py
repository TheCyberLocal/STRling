"""Focused certification tests for canonical STRling data contracts."""

from __future__ import annotations

import copy
import hashlib
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

    @staticmethod
    def _semantic_profile() -> dict[str, object]:
        evidence = ["test_semantic_evidence"]
        return {
            "contract_version": "1.0.0",
            "profile_id": "profile:test/semantic-facts",
            "profile_version": "1.0.0",
            "engine": {
                "id": "test-engine",
                "version": {"scheme": "semver", "value": "1.0.0"},
            },
            "compatible_specification_versions": ["1.0-draft.1"],
            "capability_scope": {
                "kind": "enumerated",
                "unlisted_capabilities": "unknown",
            },
            "capabilities": [
                {
                    "capability_id": "anchors.line_start",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_set",
                            "role": "line_terminators",
                            "fact_id": "line_terminators",
                        }
                    ],
                },
                {
                    "capability_id": "boundaries.word",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_set",
                            "role": "word_characters",
                            "fact_id": "word_characters",
                        }
                    ],
                },
                {
                    "capability_id": "character_classes.unicode",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_set",
                            "role": "word_characters",
                            "fact_id": "word_characters",
                        }
                    ],
                },
                {
                    "capability_id": "character_classes.wildcard",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_algorithm",
                            "role": "matching_unit",
                            "fact_id": "matching_unit",
                        },
                        {
                            "kind": "semantic_set",
                            "role": "wildcard_exclusions",
                            "fact_id": "wildcard_exclusions",
                        },
                    ],
                },
                {
                    "capability_id": "character_semantics.unicode_scalar",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_algorithm",
                            "role": "matching_unit",
                            "fact_id": "matching_unit",
                        }
                    ],
                },
                {
                    "capability_id": "matching.case_insensitive",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_algorithm",
                            "role": "case_folding",
                            "fact_id": "case_folding",
                        }
                    ],
                },
                {
                    "capability_id": "references.backreference",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "semantic_algorithm",
                            "role": "backreference_unset",
                            "fact_id": "backreference_unset",
                        },
                        {
                            "kind": "semantic_algorithm",
                            "role": "capture_reset_on_iteration",
                            "fact_id": "capture_reset_on_iteration",
                        },
                    ],
                },
                {
                    "capability_id": "repetition.bounded",
                    "availability": "available",
                    "constraints": [],
                    "semantic_fact_refs": [
                        {
                            "kind": "target_limit",
                            "role": "compiled_pattern_size",
                            "fact_id": "compiled_pattern_size",
                        }
                    ],
                },
            ],
            "semantic_sets": [
                {
                    "set_id": "line_terminators",
                    "definition": {
                        "kind": "line_terminator_set",
                        "members": ["LF", "VT", "FF", "CR", "CRLF", "NEL"],
                        "sequence_policy": "atomic_longest",
                    },
                    "evidence": evidence,
                },
                {
                    "set_id": "wildcard_exclusions",
                    "definition": {
                        "kind": "character_set",
                        "universe": "unicode_scalar",
                        "scalars": ["U+000A"],
                        "ranges": [],
                        "unicode_general_categories": [],
                    },
                    "evidence": evidence,
                },
                {
                    "set_id": "word_characters",
                    "definition": {
                        "kind": "character_set",
                        "universe": "unicode_scalar",
                        "scalars": ["U+005F"],
                        "ranges": [
                            {"start": "U+0030", "end": "U+0039"},
                            {"start": "U+0041", "end": "U+005A"},
                            {"start": "U+0061", "end": "U+007A"},
                        ],
                        "unicode_general_categories": ["L", "N"],
                    },
                    "unicode_version": {"kind": "fixed", "value": "15.0.0"},
                    "evidence": evidence,
                },
            ],
            "semantic_algorithms": [
                {
                    "algorithm_id": "backreference_unset",
                    "definition": {
                        "kind": "backreference_unset",
                        "behavior": "fail",
                    },
                    "evidence": evidence,
                },
                {
                    "algorithm_id": "capture_reset_on_iteration",
                    "definition": {
                        "kind": "capture_reset_on_iteration",
                        "behavior": "reset",
                    },
                    "evidence": evidence,
                },
                {
                    "algorithm_id": "case_folding",
                    "definition": {
                        "kind": "case_folding",
                        "mode": "simple_unicode",
                        "additional_equivalence_classes": [],
                    },
                    "unicode_version": {"kind": "fixed", "value": "15.0.0"},
                    "evidence": evidence,
                },
                {
                    "algorithm_id": "matching_unit",
                    "definition": {
                        "kind": "matching_unit",
                        "unit": "unicode_code_point",
                    },
                    "evidence": evidence,
                },
            ],
            "target_limits": [
                {
                    "limit_id": "compiled_pattern_size",
                    "scope": "compiled_pattern",
                    "bound": {"kind": "unknown"},
                    "prediction": "artifact_and_configuration_dependent",
                    "evidence": evidence,
                }
            ],
            "options": [],
            "evidence": [
                {
                    "evidence_id": "test_semantic_evidence",
                    "authority": "engine_documentation",
                    "url": "https://example.com/semantic-evidence",
                    "locator": "Test-only semantic profile evidence.",
                }
            ],
        }

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

    def test_semantic_profile_model_accepts_closed_governed_facts(self) -> None:
        profile = self._semantic_profile()
        self.suite.validate("target-profile.schema.json", profile)

        profile["semantic_sets"][2]["unicode_version"] = {
            "kind": "latest_unicode_at_edition",
            "edition": "2024",
        }
        profile["semantic_algorithms"][2]["unicode_version"] = {
            "kind": "latest_unicode_at_edition",
            "edition": "2024",
        }
        self.suite.validate("target-profile.schema.json", profile)

    def test_semantic_profile_facts_and_references_are_required(self) -> None:
        for root_member in (
            "semantic_sets",
            "semantic_algorithms",
            "target_limits",
        ):
            malformed = copy.deepcopy(self._semantic_profile())
            del malformed[root_member]
            with (
                self.subTest(root_member=root_member),
                self.assertRaises(ContractValidationError),
            ):
                self.suite.validate("target-profile.schema.json", malformed)

        malformed = copy.deepcopy(self._semantic_profile())
        del malformed["capabilities"][0]["semantic_fact_refs"]
        with self.assertRaises(ContractValidationError):
            self.suite.validate("target-profile.schema.json", malformed)

    def test_semantic_fact_order_identity_and_evidence_are_enforced(self) -> None:
        mutations = {
            "duplicate set ID": lambda value: value["semantic_sets"].append(
                copy.deepcopy(value["semantic_sets"][-1])
            ),
            "duplicate algorithm ID": lambda value: value["semantic_algorithms"].append(
                copy.deepcopy(value["semantic_algorithms"][-1])
            ),
            "duplicate limit ID": lambda value: value["target_limits"].append(
                copy.deepcopy(value["target_limits"][-1])
            ),
            "unordered set IDs": lambda value: value["semantic_sets"].reverse(),
            "unordered semantic references": lambda value: value["capabilities"][3][
                "semantic_fact_refs"
            ].reverse(),
            "duplicate semantic role": lambda value: value["capabilities"][3][
                "semantic_fact_refs"
            ].append(
                {
                    "kind": "semantic_set",
                    "role": "wildcard_exclusions",
                    "fact_id": "word_characters",
                }
            ),
            "unresolved evidence": lambda value: value["semantic_sets"][0][
                "evidence"
            ].append("unknown_evidence"),
            "evidence-less fact": lambda value: value["semantic_sets"][0].update(
                evidence=[]
            ),
            "unresolved semantic fact": lambda value: value["capabilities"][0][
                "semantic_fact_refs"
            ][0].update(fact_id="missing_set"),
        }
        for name, mutate in mutations.items():
            malformed = copy.deepcopy(self._semantic_profile())
            mutate(malformed)
            with self.subTest(name=name), self.assertRaises(ContractValidationError):
                self.suite.validate("target-profile.schema.json", malformed)

    def test_semantic_set_definitions_fail_closed(self) -> None:
        mutations = {
            "invalid fixed Unicode version": lambda value: value["semantic_sets"][
                2
            ].update(unicode_version={"kind": "fixed", "value": "15"}),
            "invalid Unicode scalar": lambda value: value["semantic_sets"][1][
                "definition"
            ].update(scalars=["U+D800"]),
            "invalid Unicode edition": lambda value: value["semantic_sets"][2].update(
                unicode_version={
                    "kind": "latest_unicode_at_edition",
                    "edition": "24",
                }
            ),
            "noncanonical Unicode scalar": lambda value: value["semantic_sets"][1][
                "definition"
            ].update(scalars=["U+0000A"]),
            "empty character set": lambda value: value["semantic_sets"][1][
                "definition"
            ].update(scalars=[]),
            "overlapping ranges": lambda value: value["semantic_sets"][2][
                "definition"
            ].update(
                ranges=[
                    {"start": "U+0030", "end": "U+0040"},
                    {"start": "U+0039", "end": "U+0050"},
                ]
            ),
            "aggregate and subcategory": lambda value: value["semantic_sets"][2][
                "definition"
            ].update(unicode_general_categories=["L", "Lu"]),
            "CRLF without components": lambda value: value["semantic_sets"][0][
                "definition"
            ].update(members=["CRLF"]),
        }
        for name, mutate in mutations.items():
            malformed = copy.deepcopy(self._semantic_profile())
            mutate(malformed)
            with self.subTest(name=name), self.assertRaises(ContractValidationError):
                self.suite.validate("target-profile.schema.json", malformed)

    def test_semantic_algorithm_definitions_fail_closed(self) -> None:
        mutations = {
            "unknown algorithm behavior": lambda value: value["semantic_algorithms"][0][
                "definition"
            ].update(behavior="unknown"),
            "algorithm ID mismatch": lambda value: value["semantic_algorithms"][
                0
            ].update(algorithm_id="different_algorithm"),
            "Unicode folding without identity": lambda value: value[
                "semantic_algorithms"
            ][2].pop("unicode_version"),
            "ASCII folding with Unicode identity": lambda value: value[
                "semantic_algorithms"
            ][2]["definition"].update(mode="ascii"),
            "noncanonical equivalence class": lambda value: value[
                "semantic_algorithms"
            ][2]["definition"].update(
                additional_equivalence_classes=[["U+212A", "U+004B"]]
            ),
        }
        for name, mutate in mutations.items():
            malformed = copy.deepcopy(self._semantic_profile())
            mutate(malformed)
            with self.subTest(name=name), self.assertRaises(ContractValidationError):
                self.suite.validate("target-profile.schema.json", malformed)

    def test_usable_capabilities_require_their_semantic_roles(self) -> None:
        profile = self._semantic_profile()
        for index, capability in enumerate(profile["capabilities"]):
            malformed = copy.deepcopy(profile)
            malformed["capabilities"][index]["semantic_fact_refs"] = []
            with (
                self.subTest(capability=capability["capability_id"]),
                self.assertRaises(ContractValidationError),
            ):
                self.suite.validate("target-profile.schema.json", malformed)

            unavailable = copy.deepcopy(malformed)
            unavailable["capabilities"][index]["availability"] = "unavailable"
            self.suite.validate("target-profile.schema.json", unavailable)

        for anchor in (
            "anchors.end_before_final_line_terminator",
            "anchors.line_end",
        ):
            malformed = copy.deepcopy(profile)
            malformed["capabilities"][0]["capability_id"] = anchor
            malformed["capabilities"][0]["semantic_fact_refs"] = []
            with (
                self.subTest(capability=anchor),
                self.assertRaises(ContractValidationError),
            ):
                self.suite.validate("target-profile.schema.json", malformed)

        digit_only = copy.deepcopy(profile)
        unicode_class = digit_only["capabilities"][2]
        unicode_class["availability"] = "constrained"
        unicode_class["constraints"] = [
            {"constraint_id": "class", "operator": "equals", "value": "digit"}
        ]
        unicode_class["semantic_fact_refs"] = []
        self.suite.validate("target-profile.schema.json", digit_only)

    def test_target_limit_scope_bound_and_prediction_are_consistent(self) -> None:
        mutations = {
            "syntactic limit without numeric bound": lambda value: value[
                "target_limits"
            ][0].update(scope="syntactic_quantifier", prediction="exact"),
            "compiled limit claiming exact prediction": lambda value: value[
                "target_limits"
            ][0].update(prediction="exact"),
            "compiled limit with resource bound": lambda value: value["target_limits"][
                0
            ].update(bound={"kind": "resource_dependent"}),
            "numeric limit above u64": lambda value: value["target_limits"][0].update(
                scope="syntactic_quantifier",
                bound={
                    "kind": "numeric",
                    "operator": "at_most",
                    "value": 18446744073709551616,
                    "unit": "repetitions",
                },
                prediction="exact",
            ),
            "repetition with only a resource limit": lambda value: (
                value["target_limits"][0].update(
                    limit_id="resource_budget",
                    scope="resource_dependent",
                    bound={"kind": "resource_dependent"},
                    prediction="resource_dependent",
                ),
                value["capabilities"][-1]["semantic_fact_refs"][0].update(
                    role="resource_budget", fact_id="resource_budget"
                ),
            ),
        }
        for name, mutate in mutations.items():
            malformed = copy.deepcopy(self._semantic_profile())
            mutate(malformed)
            with self.subTest(name=name), self.assertRaises(ContractValidationError):
                self.suite.validate("target-profile.schema.json", malformed)

    def test_every_semantic_fact_family_changes_profile_fingerprint(self) -> None:
        profile = self._semantic_profile()
        original = hashlib.sha256(canonical_json(profile)).hexdigest()
        mutations = {
            "word-character set": lambda value: value["semantic_sets"][2][
                "definition"
            ].update(scalars=["U+005F", "U+200C"]),
            "line-terminator set": lambda value: value["semantic_sets"][0][
                "definition"
            ].update(members=["LF", "VT", "FF", "CR", "CRLF", "NEL", "LS"]),
            "wildcard exclusions": lambda value: value["semantic_sets"][1][
                "definition"
            ].update(scalars=["U+000A", "U+000D"]),
            "case-folding algorithm": lambda value: value["semantic_algorithms"][2][
                "definition"
            ].update(mode="full_unicode"),
            "backreference algorithm": lambda value: value["semantic_algorithms"][0][
                "definition"
            ].update(behavior="empty"),
            "capture-reset algorithm": lambda value: value["semantic_algorithms"][1][
                "definition"
            ].update(behavior="retain"),
            "Unicode identity": lambda value: value["semantic_sets"][2].update(
                unicode_version={"kind": "fixed", "value": "15.1.0"}
            ),
            "target limit": lambda value: value["target_limits"][0].update(
                bound={
                    "kind": "numeric",
                    "operator": "at_most",
                    "value": 65535,
                    "unit": "code_units",
                }
            ),
        }
        for name, mutate in mutations.items():
            changed = copy.deepcopy(profile)
            mutate(changed)
            self.suite.validate("target-profile.schema.json", changed)
            with self.subTest(name=name):
                self.assertNotEqual(
                    original, hashlib.sha256(canonical_json(changed)).hexdigest()
                )

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
