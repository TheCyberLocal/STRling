from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from hygiene import Entry, load_policy, normalize_text, scan, tracked_entries  # noqa: E402


def fixture_policy() -> dict[str, object]:
    return {
        "schema_version": 1,
        "scope": "tracked_files",
        "maximum_file_size_bytes": 1024,
        "prohibited_patterns": [
            {
                "id": "temporary-copies",
                "patterns": ["*.tmp", "**/*.tmp"],
            },
            {
                "id": "archives-and-packages",
                "patterns": ["*.jar", "**/*.jar"],
            },
        ],
        "allowed_intentional_artifacts": [],
        "generated_paths": [],
        "binary_allowlist": [],
        "text_policy": {
            "encoding": "utf-8",
            "default_line_ending": "lf",
            "crlf_paths": ["windows.txt"],
            "require_final_newline": True,
            "forbid_trailing_whitespace": True,
            "extensions": [".txt", ".tmp"],
            "special_files": [],
            "excluded_paths": [],
        },
        "credential_marker_exclusions": [],
        "private_key_markers": ["-----BEGIN TEST PRIVATE KEY-----"],
        "executable_allowlist": [],
        "case_collision_waivers": [],
    }


def rules(findings) -> set[str]:
    return {finding.rule for finding in findings}


class HygieneScannerTests(unittest.TestCase):
    def test_repository_policy_and_inventory_load(self) -> None:
        policy = load_policy()
        self.assertEqual("tracked_files", policy["scope"])
        self.assertGreater(len(tracked_entries()), 100)

    def test_prohibited_temporary_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scratch.tmp").write_text("scratch\n", encoding="utf-8")
            findings = scan(
                fixture_policy(),
                [Entry("scratch.tmp", "100644")],
                root,
            )
        self.assertIn("temporary-copies", rules(findings))

    def test_unexpected_binary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "artifact.bin").write_bytes(b"\x7fELF\x00fixture")
            findings = scan(
                fixture_policy(),
                [Entry("artifact.bin", "100644")],
                root,
            )
        self.assertIn("unexpected-binary", rules(findings))

    def test_exact_intentional_artifact_can_waive_maximum_file_size(self) -> None:
        policy = fixture_policy()
        policy["allowed_intentional_artifacts"] = [
            {
                "path": "frozen-baseline.txt",
                "rule": "maximum-file-size",
                "rationale": "Exact immutable certification denominator.",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frozen-baseline.txt").write_text(
                "x" * 1025,
                encoding="utf-8",
            )
            findings = scan(
                policy,
                [Entry("frozen-baseline.txt", "100644")],
                root,
            )
        self.assertNotIn("maximum-file-size", rules(findings))

    def test_text_normalization_failures_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.txt").write_bytes(b"first \r\nlast")
            findings = scan(
                fixture_policy(),
                [Entry("bad.txt", "100644")],
                root,
            )
        self.assertTrue(
            {"line-endings", "trailing-whitespace", "final-newline"}.issubset(
                rules(findings)
            )
        )

    def test_unexpected_executable_and_case_collision_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("Readme.txt", "README.txt"):
                (root / path).write_text("fixture\n", encoding="utf-8")
            findings = scan(
                fixture_policy(),
                [
                    Entry("Readme.txt", "100755"),
                    Entry("README.txt", "100644"),
                ],
                root,
            )
        self.assertIn("executable-mode", rules(findings))
        self.assertIn("case-collision", rules(findings))

    def test_case_collision_waiver_is_exact(self) -> None:
        policy = fixture_policy()
        policy["case_collision_waivers"] = [
            {
                "waiver": "fixture",
                "paths": ["Readme.txt", "README.txt"],
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("Readme.txt", "README.txt"):
                (root / path).write_text("fixture\n", encoding="utf-8")
            findings = scan(
                policy,
                [
                    Entry("Readme.txt", "100644"),
                    Entry("README.txt", "100644"),
                ],
                root,
            )
        self.assertNotIn("case-collision", rules(findings))

    def test_exact_binary_allowlist_checks_digest_and_archive_rule(self) -> None:
        data = b"PK\x03\x04fixture"
        policy = fixture_policy()
        policy["binary_allowlist"] = [
            {
                "path": "wrapper.jar",
                "sha256": hashlib.sha256(data).hexdigest(),
                "kind": "fixture",
                "rationale": "fixture",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "wrapper.jar").write_bytes(data)
            findings = scan(
                policy,
                [Entry("wrapper.jar", "100644")],
                root,
            )
        self.assertEqual([], findings)

    def test_private_key_marker_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "secret.txt").write_text(
                "-----BEGIN TEST PRIVATE KEY-----\n",
                encoding="utf-8",
            )
            findings = scan(
                fixture_policy(),
                [Entry("secret.txt", "100644")],
                root,
            )
        self.assertIn("private-key-marker", rules(findings))

    def test_normalize_text_fixes_only_governed_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.txt").write_bytes(b"first  \r\nlast")
            (root / "windows.txt").write_bytes(b"first \nlast")
            changed = normalize_text(
                fixture_policy(),
                [
                    Entry("bad.txt", "100644"),
                    Entry("windows.txt", "100644"),
                ],
                root,
            )
            self.assertEqual(b"first\nlast\n", (root / "bad.txt").read_bytes())
            self.assertEqual(
                b"first\r\nlast\r\n",
                (root / "windows.txt").read_bytes(),
            )
        self.assertEqual(["bad.txt", "windows.txt"], changed)


if __name__ == "__main__":
    unittest.main()
