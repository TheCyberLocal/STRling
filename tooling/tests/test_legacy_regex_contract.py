"""Focused certification for the regex-compatible frontend contract."""

from __future__ import annotations

import fnmatch
import json
import shutil
import tempfile
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from tooling.architecture_fitness import frontend_authority_boundary_findings
from tooling.legacy_regex_contract import (
    DIALECT_ROOT,
    ROOT,
    LegacyRegexContractError,
    LegacyRegexContractSuite,
)

AUTHORITY_CONFIGURATION: Mapping[str, object] = {
    "frontend_contract_sources": ["spec/frontends/legacy-regex/**"],
    "semantic_authority_sources": [
        "core/src/semantic/**",
        "spec/contracts/1.0/semantic-ir.schema.json",
        "spec/drafts/**",
    ],
    "target_authority_sources": [
        "core/src/portability_planning.rs",
        "core/src/target/**",
        "spec/contracts/1.0/target-artifact.schema.json",
        "spec/contracts/1.0/target-profile.schema.json",
        "spec/targets/**",
    ],
    "forbidden_frontend_markers": [
        "%flags",
        "legacy-regex",
        "strling.regex-compat",
        "text/x-strling-regex-compat",
    ],
    "contract_forbidden_authority_markers": [
        '"raw_fragment_model": "opaque-passthrough"',
        '"semantic_authority": true',
        '"target_assumption": "inferred"',
        '"target_authority": true',
    ],
}


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


class LegacyRegexContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = LegacyRegexContractSuite()

    def copied_suite(
        self, mutation: Callable[[Path], None]
    ) -> LegacyRegexContractSuite:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "1.0"
        shutil.copytree(DIALECT_ROOT, destination)
        mutation(destination)
        return LegacyRegexContractSuite(destination)

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
        self.assertEqual("1.0.0", result["contract_version"])
        self.assertEqual(2, result["schemas"])
        self.assertEqual(51, result["features"])
        self.assertEqual(
            {"accepted": 32, "compatibility-only": 6, "rejected": 13},
            result["feature_statuses"],
        )
        self.assertEqual(45, result["diagnostics"])
        self.assertEqual(30, result["positive"])
        self.assertEqual(45, result["negative"])
        self.assertEqual(
            "sha256:0cb32dd3ed534d13ce6d4278a2723898ac40bc374fa6d40c5ac43c553a2265ad",
            result["fingerprint"],
        )

    def test_frontend_authority_is_syntax_only(self) -> None:
        self.assertEqual(
            {
                "syntax_authority": True,
                "semantic_authority": False,
                "target_authority": False,
                "lowering_destination": "semantic-ir",
            },
            self.suite.dialect["authority"],
        )
        self.assertEqual(
            "none", self.suite.dialect["source_model"]["target_assumption"]
        )
        self.assertEqual(
            "structured-source-only",
            self.suite.dialect["source_model"]["raw_fragment_model"],
        )

    def test_semantic_authority_mutation_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "dialect.json",
                lambda value: value["authority"].update({"semantic_authority": True}),
            )

        with self.assertRaises(LegacyRegexContractError):
            self.copied_suite(mutation).certify()

    def test_unknown_positive_feature_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            def add_unknown(value: dict[str, Any]) -> None:
                feature_ids = value["cases"][0]["feature_ids"]
                feature_ids.append("unknown.feature")
                feature_ids.sort()

            self.mutate_json(
                root,
                "fixtures/positive.json",
                add_unknown,
            )

        with self.assertRaisesRegex(LegacyRegexContractError, "unknown feature"):
            self.copied_suite(mutation).certify()

    def test_rejected_feature_cannot_enter_positive_fixtures(self) -> None:
        def mutation(root: Path) -> None:
            def add_rejected(value: dict[str, Any]) -> None:
                feature_ids = value["cases"][0]["feature_ids"]
                feature_ids.append("extension.target-directive")
                feature_ids.sort()

            self.mutate_json(
                root,
                "fixtures/positive.json",
                add_rejected,
            )

        with self.assertRaisesRegex(LegacyRegexContractError, "positive case"):
            self.copied_suite(mutation).certify()

    def test_fixture_required_diagnostic_cannot_lose_coverage(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "fixtures/negative.json",
                lambda value: value["cases"].__setitem__(
                    slice(None),
                    [
                        case
                        for case in value["cases"]
                        if case["expected"]["diagnostic_id"] != "STRL-FRONTEND-2003"
                    ],
                ),
            )

        with self.assertRaisesRegex(
            LegacyRegexContractError, "fixture-required diagnostics"
        ):
            self.copied_suite(mutation).certify()

    def test_rejected_feature_cannot_lose_negative_coverage(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "fixtures/negative.json",
                lambda value: value["cases"].__setitem__(
                    slice(None),
                    [
                        case
                        for case in value["cases"]
                        if "extension.posix-class" not in case["feature_ids"]
                    ],
                ),
            )

        with self.assertRaisesRegex(LegacyRegexContractError, "rejected features"):
            self.copied_suite(mutation).certify()

    def test_missing_grammar_rule_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            path = root / "grammar.ebnf"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Lookbehind      =", "RemovedLookbehind ="
                ),
                encoding="utf-8",
            )

        with self.assertRaisesRegex(LegacyRegexContractError, "Lookbehind"):
            self.copied_suite(mutation).certify()

    def test_non_boundary_fixture_offset_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            self.mutate_json(
                root,
                "fixtures/negative.json",
                lambda value: value["cases"][0]["expected"].update(
                    {"byte_offset": 999}
                ),
            )

        with self.assertRaisesRegex(LegacyRegexContractError, "UTF-8 boundary"):
            self.copied_suite(mutation).certify()

    def test_duplicate_case_identity_is_rejected(self) -> None:
        def mutation(root: Path) -> None:
            def duplicate(value: dict[str, Any]) -> None:
                value["cases"][1]["id"] = value["cases"][0]["id"]

            self.mutate_json(root, "fixtures/positive.json", duplicate)

        with self.assertRaisesRegex(LegacyRegexContractError, "sorted"):
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

        with self.assertRaisesRegex(LegacyRegexContractError, "fingerprint"):
            self.copied_suite(mutation).certify()


class RegexFrontendAuthorityTests(unittest.TestCase):
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

    def test_clean_syntax_only_boundary_passes(self) -> None:
        self.write(
            "spec/frontends/legacy-regex/1.0/dialect.json",
            '{"semantic_authority": false, "target_authority": false}',
        )
        self.write("core/src/semantic/mod.rs", "pub struct SemanticNode;")
        self.write("core/src/target/mod.rs", "pub struct TargetProfile;")
        self.assertEqual([], self.evaluate())

    def test_frontend_marker_cannot_enter_semantic_authority(self) -> None:
        self.write(
            "core/src/semantic/mod.rs",
            'const AUTHORITY: &str = "strling.regex-compat";',
        )
        self.assertTrue(self.evaluate())

    def test_frontend_marker_cannot_enter_target_authority(self) -> None:
        self.write("core/src/target/mod.rs", 'const FLAGS: &str = "%flags";')
        self.assertTrue(self.evaluate())

    def test_frontend_contract_cannot_self_promote(self) -> None:
        self.write(
            "spec/frontends/legacy-regex/1.0/dialect.json",
            '{"semantic_authority": true}',
        )
        self.assertTrue(self.evaluate())

    def test_repository_satisfies_frontend_authority_boundary(self) -> None:
        findings = frontend_authority_boundary_findings(
            ROOT, AUTHORITY_CONFIGURATION, matches_any
        )
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
