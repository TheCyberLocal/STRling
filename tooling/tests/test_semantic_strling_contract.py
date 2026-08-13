"""Focused certification for the Semantic STRling textual contract."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from tooling.architecture_fitness import frontend_authority_boundary_findings
from tooling.semantic_strling_contract import (
    LANGUAGE_ROOT,
    ROOT,
    SemanticStrlingContractError,
    SemanticStrlingContractSuite,
)

AUTHORITY_CONFIGURATION: Mapping[str, object] = {
    "frontend_contract_sources": ["spec/frontends/semantic/**"],
    "semantic_authority_sources": [
        "core/src/semantic/**",
        "spec/contracts/1.0/semantic-ir.schema.json",
    ],
    "target_authority_sources": [
        "core/src/portability_planning.rs",
        "core/src/target/**",
        "spec/contracts/1.0/target-artifact.schema.json",
        "spec/contracts/1.0/target-profile.schema.json",
        "spec/targets/**",
    ],
    "forbidden_frontend_markers": [
        "strling.semantic",
        "semantic strling 1.0",
        "text/x-strling-semantic",
    ],
    "contract_forbidden_authority_markers": [
        '"canonical_semantic_authority": true',
        '"target_authority": true',
        '"runtime_authority": true',
        '"parser_implementation": true',
        '"formatter_implementation": true',
    ],
}


def matches_any(path: str, patterns: list[str]) -> bool:
    import fnmatch

    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


class SemanticStrlingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = SemanticStrlingContractSuite()

    def copied_suite(
        self, mutation: Callable[[Path], None]
    ) -> SemanticStrlingContractSuite:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "1.0"
        shutil.copytree(LANGUAGE_ROOT, destination)
        mutation(destination)
        return SemanticStrlingContractSuite(destination)

    @staticmethod
    def mutate_json(
        root: Path, relative: str, mutation: Callable[[dict[str, Any]], None]
    ) -> None:
        path = root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        mutation(value)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )

    def test_complete_contract_certification(self) -> None:
        result = self.suite.certify()
        self.assertEqual("1.0.0", result["dialect_version"])
        self.assertEqual(3, result["schemas"])
        self.assertEqual(55, result["productions"])
        self.assertEqual(17, result["mappings"])
        self.assertEqual(27, result["diagnostics"])
        self.assertEqual(10, result["deferred"])
        self.assertEqual(12, result["positive"])
        self.assertEqual(30, result["negative"])
        self.assertRegex(result["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_frontend_authority_is_narrow(self) -> None:
        self.assertEqual(
            {
                "syntax_authority": True,
                "mapping_authority": True,
                "canonical_semantic_authority": False,
                "target_authority": False,
                "runtime_authority": False,
                "parser_implementation": False,
                "formatter_implementation": False,
                "lowering_destination": "semantic-ir",
            },
            self.suite.language["authority"],
        )

    def test_semantic_authority_mutation_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "language.json",
                lambda value: value["authority"].update(
                    {"canonical_semantic_authority": True}
                ),
            )

        with self.assertRaises(SemanticStrlingContractError):
            self.copied_suite(mutation).certify()

    def test_undefined_grammar_production_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            path = root / "grammar.ebnf"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'Empty                   = "empty", Layout, ";" ;',
                    'Empty                   = MissingNode, "empty", Layout, ";" ;',
                ),
                encoding="utf-8",
            )

        with self.assertRaisesRegex(SemanticStrlingContractError, "undefined"):
            self.copied_suite(mutation).certify()

    def test_prefix_ambiguous_construct_phrase_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            def add_prefix(value: dict[str, Any]) -> None:
                value["construct_phrases"].append("any character")
                value["construct_phrases"].sort()

            self.mutate_json(root, "language.json", add_prefix)

        with self.assertRaisesRegex(SemanticStrlingContractError, "prefix-disjoint"):
            self.copied_suite(mutation).certify()

    def test_missing_node_mapping_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "mapping.json",
                lambda value: value["node_mappings"].pop(),
            )

        with self.assertRaises(SemanticStrlingContractError):
            self.copied_suite(mutation).certify()

    def test_production_fixture_coverage_is_required(self) -> None:
        def mutation(root: Path) -> None:
            def remove(value: dict[str, Any]) -> None:
                for case in value["cases"]:
                    if "UnicodeEscape" in case["production_ids"]:
                        case["production_ids"].remove("UnicodeEscape")

            self.mutate_json(root, "fixtures/positive.json", remove)

        with self.assertRaisesRegex(SemanticStrlingContractError, "positive fixtures"):
            self.copied_suite(mutation).certify()

    def test_required_diagnostic_fixture_coverage_is_required(self) -> None:
        def mutation(root: Path) -> None:
            def remove(value: dict[str, Any]) -> None:
                value["cases"] = [
                    case
                    for case in value["cases"]
                    if case["expected"]["diagnostic_code"] != "STRL-DSL-3001"
                ]

            self.mutate_json(root, "fixtures/negative.json", remove)

        with self.assertRaisesRegex(SemanticStrlingContractError, "diagnostics"):
            self.copied_suite(mutation).certify()

    def test_invalid_utf8_fixture_offset_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            def invalidate(value: dict[str, Any]) -> None:
                value["cases"][0]["source"] = "😀"
                value["cases"][0]["expected"]["byte_offset"] = 1

            self.mutate_json(root, "fixtures/negative.json", invalidate)

        with self.assertRaisesRegex(SemanticStrlingContractError, "UTF-8 boundary"):
            self.copied_suite(mutation).certify()

    def test_manifest_fingerprint_change_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "fixtures/manifest.json",
                lambda value: value["files"][0].update(
                    {"sha256": "sha256:" + ("0" * 64)}
                ),
            )

        with self.assertRaisesRegex(SemanticStrlingContractError, "fingerprint"):
            self.copied_suite(mutation).certify()


class SemanticStrlingAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def evaluate(self) -> list[tuple[str, str | None]]:
        return frontend_authority_boundary_findings(
            self.root, AUTHORITY_CONFIGURATION, matches_any
        )

    def test_clean_specification_boundary_passes(self) -> None:
        self.write(
            "spec/frontends/semantic/1.0/language.json",
            '{"canonical_semantic_authority": false, "target_authority": false}',
        )
        self.write("core/src/semantic/mod.rs", "pub struct SemanticNode;")
        self.write("core/src/target/mod.rs", "pub struct TargetProfile;")
        self.assertEqual([], self.evaluate())

    def test_frontend_identity_cannot_enter_canonical_semantics(self) -> None:
        self.write(
            "core/src/semantic/mod.rs", 'const FRONTEND: &str = "strling.semantic";'
        )
        self.assertTrue(self.evaluate())

    def test_frontend_contract_cannot_claim_parser_implementation(self) -> None:
        self.write(
            "spec/frontends/semantic/1.0/language.json",
            '{"parser_implementation": true}',
        )
        self.assertTrue(self.evaluate())

    def test_repository_satisfies_semantic_frontend_boundary(self) -> None:
        findings = frontend_authority_boundary_findings(
            ROOT, AUTHORITY_CONFIGURATION, matches_any
        )
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
