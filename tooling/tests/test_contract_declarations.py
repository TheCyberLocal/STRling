from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tooling.contract_declarations import (
    DeclarationError,
    DetectedChange,
    detect_base_changes,
    validate_change_declarations,
)
from tooling.public_contracts import compare_snapshots


def declaration(
    level: str = "none", affected: list[str] | None = None
) -> dict[str, object]:
    evidence = [] if level == "none" else [f"{level} change is intentional"]
    return {
        "level": level,
        "evidence": evidence,
        "affected_surfaces": [] if affected is None else affected,
    }


def task(
    *,
    public: dict[str, object] | None = None,
    schema: dict[str, object] | None = None,
    architecture: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "change_classification": {
            "public_api_change": public or declaration(),
            "schema_change": schema or declaration(),
            "architecture_change": architecture or declaration(),
        }
    }


def change(
    surface: str,
    classification: str,
    declaration_name: str = "public_api_change",
    component: str = "typescript",
) -> DetectedChange:
    return DetectedChange(
        surface,
        component,
        declaration_name,
        classification,
        f"governance/contracts/snapshots/{surface}.json",
    )


class ContractDeclarationTests(unittest.TestCase):
    def test_unchanged_api_with_none_declaration_passes(self) -> None:
        self.assertEqual(validate_change_declarations(task(), []), [])

    def test_compatible_internal_source_change_without_surface_drift_passes(
        self,
    ) -> None:
        self.assertEqual(validate_change_declarations(task(), []), [])

    def test_additive_api_with_exact_declaration_passes(self) -> None:
        findings = validate_change_declarations(
            task(public=declaration("additive", ["typescript-public-api"])),
            [change("typescript-public-api", "additive")],
        )
        self.assertEqual(findings, [])

    def test_breaking_api_with_exact_declaration_passes(self) -> None:
        findings = validate_change_declarations(
            task(public=declaration("breaking", ["typescript-public-api"])),
            [change("typescript-public-api", "breaking")],
        )
        self.assertEqual(findings, [])

    def test_undeclared_api_change_fails(self) -> None:
        findings = validate_change_declarations(
            task(),
            [change("typescript-public-api", "breaking")],
        )
        self.assertTrue(
            any("does not name changed surfaces" in item for item in findings)
        )
        self.assertTrue(any("is none" in item for item in findings))

    def test_broad_breaking_level_does_not_approve_additive_only_drift(self) -> None:
        findings = validate_change_declarations(
            task(public=declaration("breaking", ["typescript-public-api"])),
            [change("typescript-public-api", "additive")],
        )
        self.assertTrue(
            any("does not match detected additive" in item for item in findings)
        )

    def test_mismatched_surface_declaration_fails(self) -> None:
        findings = validate_change_declarations(
            task(public=declaration("additive", ["python-public-api"])),
            [change("typescript-public-api", "additive")],
        )
        self.assertTrue(any("typescript-public-api" in item for item in findings))
        self.assertTrue(any("python-public-api" in item for item in findings))

    def test_additive_schema_with_exact_declaration_passes(self) -> None:
        findings = validate_change_declarations(
            task(schema=declaration("additive", ["schema-target-artifact"])),
            [
                change(
                    "schema-target-artifact",
                    "additive",
                    "schema_change",
                    "spec",
                )
            ],
        )
        self.assertEqual(findings, [])

    def test_breaking_schema_with_additive_declaration_fails(self) -> None:
        findings = validate_change_declarations(
            task(schema=declaration("additive", ["schema-target-artifact"])),
            [
                change(
                    "schema-target-artifact",
                    "breaking",
                    "schema_change",
                    "spec",
                )
            ],
        )
        self.assertTrue(
            any("does not match detected breaking" in item for item in findings)
        )

    def test_intentional_correction_must_still_name_exact_surface(self) -> None:
        findings = validate_change_declarations(
            task(
                schema=declaration("intentional-correction", ["schema-target-artifact"])
            ),
            [
                change(
                    "schema-target-artifact",
                    "breaking",
                    "schema_change",
                    "spec",
                )
            ],
        )
        self.assertEqual(findings, [])

    def test_enforcement_downgrade_requires_breaking_architecture_declaration(
        self,
    ) -> None:
        detected = [
            change(
                "typescript-public-api",
                "breaking",
                "architecture_change",
            )
        ]
        self.assertTrue(validate_change_declarations(task(), detected))
        self.assertEqual(
            validate_change_declarations(
                task(architecture=declaration("breaking", ["typescript-public-api"])),
                detected,
            ),
            [],
        )

    def test_malformed_declaration_fails_closed(self) -> None:
        malformed = task()
        malformed["change_classification"]["public_api_change"] = {
            "level": "additive",
            "evidence": "not-a-list",
        }
        with self.assertRaisesRegex(DeclarationError, "malformed"):
            validate_change_declarations(malformed, [])


class BaseDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.registry_path = self.root / "governance/public-surfaces.json"
        self.snapshot_path = (
            self.root / "governance/contracts/snapshots/sample-api.json"
        )
        self.snapshot_path.parent.mkdir(parents=True)
        self.registry = {
            "surfaces": [
                {
                    "id": "sample-api",
                    "component": "sample",
                    "kind": "host-api",
                    "enforcement": "enforced",
                    "snapshot_path": ("governance/contracts/snapshots/sample-api.json"),
                    "comparison": "declaration-set",
                }
            ]
        }
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(self.registry), encoding="utf-8")
        self.snapshot_path.write_text(
            json.dumps(
                {
                    "surface": "sample-api",
                    "format": "declarations",
                    "symbols": {"a": "a"},
                }
            ),
            encoding="utf-8",
        )
        for arguments in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "tests@strling.dev"],
            ["git", "config", "user.name", "STRling tests"],
            ["git", "add", "."],
            ["git", "commit", "-q", "-m", "baseline"],
        ):
            subprocess.run(arguments, cwd=self.root, check=True)
        self.base = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_base_snapshot_addition_is_detected_as_additive(self) -> None:
        self.snapshot_path.write_text(
            json.dumps(
                {
                    "surface": "sample-api",
                    "format": "declarations",
                    "symbols": {"a": "a", "b": "b"},
                }
            ),
            encoding="utf-8",
        )
        detected = detect_base_changes(
            root=self.root,
            registry_path=self.registry_path,
            registry=self.registry,
            base=self.base,
            compare=compare_snapshots,
        )
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0].classification, "additive")
        self.assertEqual(detected[0].declaration, "public_api_change")

    def test_unchanged_unicode_snapshot_is_not_host_code_page_drift(self) -> None:
        snapshot = {
            "surface": "sample-api",
            "format": "declarations",
            "symbols": {"arrow": "TargetArtifact → PCRE2"},
        }
        self.snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "unicode baseline"],
            cwd=self.root,
            check=True,
        )
        unicode_base = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        detected = detect_base_changes(
            root=self.root,
            registry_path=self.registry_path,
            registry=self.registry,
            base=unicode_base,
            compare=compare_snapshots,
        )
        self.assertEqual(detected, [])

    def test_enforced_surface_downgrade_is_architecture_breaking(self) -> None:
        current = json.loads(json.dumps(self.registry))
        current["surfaces"][0]["enforcement"] = "transitional"
        detected = detect_base_changes(
            root=self.root,
            registry_path=self.registry_path,
            registry=current,
            base=self.base,
            compare=compare_snapshots,
        )
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0].classification, "breaking")
        self.assertEqual(detected[0].declaration, "architecture_change")


if __name__ == "__main__":
    unittest.main()
