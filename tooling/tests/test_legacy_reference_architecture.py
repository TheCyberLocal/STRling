from __future__ import annotations

import fnmatch
import tempfile
import json
import unittest
from pathlib import Path
from typing import Mapping

from tooling.architecture_fitness import legacy_reference_boundary_findings

CONFIGURATION: Mapping[str, object] = {
    "consumer_sources": ["core/**", "bindings/**"],
    "comparison_sources": [
        "tooling/migration_*.py",
        "tooling/tests/fixtures/migration_comparison/**",
    ],
    "comparison_contract": "tooling/migration_comparison_contract.json",
    "comparison_forbidden_mutation_tokens": [
        "write_text(",
        "write_bytes(",
        ".unlink(",
        ".rename(",
        "open(",
    ],
    "comparison_forbidden_authority_tokens": [
        '"majority_is_authority": true',
        '"historical_consensus_is_normative": true',
        '"unresolved_discrepancy": "passed"',
        '"unresolved_discrepancy": "accepted"',
    ],
    "normative_sources": ["spec/**"],
    "runner_sources": ["tooling/legacy_reference/**"],
    "runner_isolation_boundaries": [
        {
            "id": "typescript-from-python",
            "sources": ["tooling/legacy_reference/corpus.mjs"],
            "forbidden_markers": [
                "python_corpus",
                "python_expected",
            ],
        },
        {
            "id": "python-from-typescript",
            "sources": ["tooling/legacy_reference/python_reference.py"],
            "forbidden_markers": [
                "typescript_expected",
                'with_name("corpus.json")',
            ],
        },
    ],
    "forbidden_evidence_markers": [
        "tooling/legacy_reference",
        "legacy_reference",
        "strling.legacy-reference",
        "migration_comparison",
        "strling.migration-comparison",
        "strling.migration-discrepancy",
        "preserved_behavior",
        "intentional_specification_correction",
        "unsupported_legacy_behavior",
        "unresolved_discrepancy",
        "historical_consensus",
    ],
    "runner_forbidden_roots": ["core", "spec"],
    "runner_forbidden_authority_tokens": [
        "TargetArtifact",
        "PortabilityPlanner",
        "portability_planner",
        "TargetProfile",
        "target_profiles",
        "capability_evaluation",
    ],
    "normative_output_roots": ["spec"],
}


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


class LegacyReferenceArchitectureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def evaluate(
        self, artifact_registry: Mapping[str, object] | None = None
    ) -> list[tuple[str, str | None]]:
        contract = self.root / str(CONFIGURATION["comparison_contract"])
        if not contract.is_file():
            self.write(
                str(CONFIGURATION["comparison_contract"]),
                json.dumps(
                    {
                        "authority_model": {
                            "historical_consensus_is_normative": False,
                            "majority_is_authority": False,
                        },
                        "comparison_relationships": [
                            "equivalent_observation",
                            "differing_observation",
                            "not_comparable",
                        ],
                        "dispositions": [
                            {"id": "preserved_behavior"},
                            {"id": "intentional_specification_correction"},
                            {"id": "unsupported_legacy_behavior"},
                            {"id": "unresolved_discrepancy"},
                        ],
                        "normalization_rules": [{"id": "fixture-rule@1.0.0"}],
                    }
                ),
            )
        return legacy_reference_boundary_findings(
            self.root,
            CONFIGURATION,
            artifact_registry or {"artifacts": []},
            matches_any,
        )

    def test_clean_boundary_passes(self) -> None:
        self.write("core/src/lib.rs", "pub fn compile() {}\n")
        self.write("spec/contracts/README.md", "# Normative contract\n")
        self.write("bindings/typescript/src/index.ts", "export const version = 1;\n")
        self.write(
            "tooling/legacy_reference/runner.mjs",
            'import { readFile } from "node:fs/promises";\n',
        )
        self.write(
            "tooling/legacy_reference/cross_reference.py",
            'PYTHON = "python_corpus.json"\nTYPESCRIPT = "corpus.json"\n',
        )

        self.assertEqual([], self.evaluate())

    def test_runner_specific_expected_outputs_are_isolated(self) -> None:
        self.write(
            "tooling/legacy_reference/corpus.mjs",
            'const python_expected = "./python_corpus.json";\n',
        )
        self.write(
            "tooling/legacy_reference/python_reference.py",
            'typescript_expected = Path(__file__).with_name("corpus.json")\n',
        )
        findings = self.evaluate()
        paths = {path for _, path in findings}
        self.assertEqual(
            {
                "tooling/legacy_reference/corpus.mjs",
                "tooling/legacy_reference/python_reference.py",
            },
            paths,
        )
        self.assertTrue(
            all("cross-runner expectation marker" in message for message, _ in findings)
        )

    def test_product_and_normative_consumers_are_rejected(self) -> None:
        self.write(
            "core/src/lib.rs",
            'const EVIDENCE: &str = "tooling/legacy_reference/corpus.json";\n',
        )
        self.write(
            "spec/contracts/generated.md",
            "Generated from tooling/legacy_reference/corpus.json.\n",
        )
        self.write(
            "bindings/typescript/src/index.ts",
            'import evidence from "../../../tooling/legacy_reference/corpus.json";\n',
        )
        paths = {path for _, path in self.evaluate()}
        self.assertEqual(
            {
                "bindings/typescript/src/index.ts",
                "core/src/lib.rs",
                "spec/contracts/generated.md",
            },
            paths,
        )

    def test_runner_cannot_reach_canonical_or_target_authority(self) -> None:
        self.write(
            "tooling/legacy_reference/authority.mjs",
            'const canonical = "core/src/target/profile.rs";\n'
            'const authority = "TargetProfile";\n',
        )
        findings = self.evaluate()
        self.assertEqual(2, len(findings))
        self.assertTrue(
            any("forbidden authority root core" in message for message, _ in findings)
        )
        self.assertTrue(
            any(
                "forbidden authority token TargetProfile" in message
                for message, _ in findings
            )
        )

    def test_comparison_artifacts_cannot_leak_into_product_or_spec(self) -> None:
        self.write(
            "core/src/target/profile.rs",
            'const SOURCE: &str = "migration_comparison";\n',
        )
        self.write(
            "spec/contracts/authority.md",
            "historical_consensus governs this requirement.\n",
        )
        self.write(
            "bindings/typescript/src/index.ts",
            'export const state = "unresolved_discrepancy";\n',
        )
        paths = {path for _, path in self.evaluate()}
        self.assertEqual(
            {
                "bindings/typescript/src/index.ts",
                "core/src/target/profile.rs",
                "spec/contracts/authority.md",
            },
            paths,
        )

    def test_comparison_cannot_mutate_sources_or_accept_unresolved(self) -> None:
        self.write(
            "tooling/migration_bad.py",
            'source.write_text("changed")\n'
            'mapping = {"unresolved_discrepancy": "accepted"}\n',
        )
        findings = self.evaluate()
        self.assertEqual(2, len(findings))
        self.assertTrue(
            any(
                "source-mutation token write_text(" in message
                for message, _ in findings
            )
        )
        self.assertTrue(
            any("authority or acceptance token" in message for message, _ in findings)
        )

    def test_historical_consensus_cannot_become_contract_authority(self) -> None:
        self.assertEqual([], self.evaluate())
        path = str(CONFIGURATION["comparison_contract"])
        contract = json.loads((self.root / path).read_text(encoding="utf-8"))
        contract["authority_model"]["majority_is_authority"] = True
        self.write(path, json.dumps(contract))
        findings = self.evaluate()
        self.assertEqual(1, len(findings))
        self.assertIn("historical evidence cannot become authority", findings[0][0])

    def test_normative_generated_output_cannot_use_legacy_evidence(self) -> None:
        registry = {
            "artifacts": [
                {
                    "id": "mutated-normative-output",
                    "authoritative_sources": [],
                    "generator_inputs": [
                        "tooling/legacy_reference/corpus.json",
                    ],
                    "generator": {
                        "implementation_paths": [
                            "tooling/legacy_reference/corpus.mjs",
                        ]
                    },
                    "outputs": ["spec/contracts/generated.json"],
                }
            ]
        }
        findings = self.evaluate(registry)
        self.assertEqual(1, len(findings))
        self.assertIn("normative output depends", findings[0][0])


class RepositoryLegacyReferenceArchitectureTests(unittest.TestCase):
    def test_repository_satisfies_registered_boundary(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rules = json.loads(
            (root / "governance/architecture-rules.json").read_text(encoding="utf-8")
        )
        rule = next(
            entry
            for entry in rules["rules"]
            if entry["id"] == "legacy-reference-authority-boundary"
        )
        registry = json.loads(
            (root / "governance/generated-artifacts.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [],
            legacy_reference_boundary_findings(
                root, rule["configuration"], registry, matches_any
            ),
        )


if __name__ == "__main__":
    unittest.main()
