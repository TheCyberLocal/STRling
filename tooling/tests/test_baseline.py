from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Callable

from tooling.baseline import BaselineError, path_set_digest, validate_baselines


ROOT = Path(__file__).resolve().parents[2]


class FingerprintTests(unittest.TestCase):
    def test_path_set_digest_binds_paths_and_file_bytes(self) -> None:
        files = {"a.txt": b"alpha", "b.txt": b"beta"}
        first = path_set_digest(("b.txt", "a.txt"), files.__getitem__)
        second = path_set_digest(("a.txt", "b.txt"), files.__getitem__)
        renamed = path_set_digest(
            ("a.txt", "c.txt"),
            lambda path: files["b.txt"] if path == "c.txt" else files[path],
        )
        changed = path_set_digest(
            ("a.txt", "b.txt"),
            lambda path: b"changed" if path == "b.txt" else files[path],
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, renamed)
        self.assertNotEqual(first, changed)


class FrozenBaselineValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        paths = (
            "governance/baselines/registry.json",
            "governance/baselines/migration-baseline.json",
            "governance/schemas/frozen-baseline-registry.schema.json",
            "governance/schemas/migration-baseline.schema.json",
            "governance/schemas/certification-evidence.schema.json",
            "governance/schemas/donor-inventory.schema.json",
            "governance/schemas/compatibility-preservation.schema.json",
            "docs/migration/baselines/certification.json",
            "docs/migration/baselines/donor-inventory.json",
            "docs/migration/baselines/compatibility-preservation.json",
        )
        for relative in paths:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def load(self, relative: str) -> dict[str, object]:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write(self, relative: str, value: object) -> None:
        (self.root / relative).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8"
        )

    def repin_manifest(self) -> None:
        manifest = self.root / "governance/baselines/migration-baseline.json"
        registry = self.load("governance/baselines/registry.json")
        registry["baselines"][0]["sha256"] = hashlib.sha256(
            manifest.read_bytes()
        ).hexdigest()
        self.write("governance/baselines/registry.json", registry)

    def mutate_manifest(self, mutation: Callable[[dict[str, object]], None]) -> None:
        relative = "governance/baselines/migration-baseline.json"
        manifest = self.load(relative)
        mutation(manifest)
        self.write(relative, manifest)

    def validate(self) -> dict[str, object]:
        return validate_baselines(root=self.root, git_root=ROOT)

    def test_repository_baseline_validates_from_copied_records(self) -> None:
        summary = self.validate()
        self.assertEqual("passed", summary["status"])
        self.assertEqual(27, summary["fingerprints"])
        self.assertEqual(29, summary["donor_capabilities"])

    def test_unpinned_manifest_modification_is_detected(self) -> None:
        self.mutate_manifest(
            lambda manifest: manifest["identity"].update({"certified_commit": "0" * 40})
        )
        with self.assertRaisesRegex(BaselineError, "manifest hash mismatch"):
            self.validate()

    def test_rehashed_fingerprint_modification_is_detected(self) -> None:
        self.mutate_manifest(
            lambda manifest: manifest["fingerprints"][0].update({"sha256": "0" * 64})
        )
        self.repin_manifest()
        with self.assertRaisesRegex(BaselineError, "fingerprint .* mismatch"):
            self.validate()

    def test_rehashed_identity_modification_is_detected(self) -> None:
        self.mutate_manifest(
            lambda manifest: manifest["identity"].update(
                {"certified_commit": manifest["identity"]["donor_commit"]}
            )
        )
        self.repin_manifest()
        with self.assertRaises(BaselineError):
            self.validate()

    def test_frozen_evidence_modification_is_detected(self) -> None:
        inventory = self.load("docs/migration/baselines/donor-inventory.json")
        inventory["summary"]["port"] = 999
        self.write("docs/migration/baselines/donor-inventory.json", inventory)
        with self.assertRaisesRegex(BaselineError, "donor-inventory mismatch"):
            self.validate()

    def test_transition_drift_is_detected_after_explicit_repinning(self) -> None:
        def remove_transition(manifest: dict[str, object]) -> None:
            manifest["active_transitions"].pop()

        self.mutate_manifest(remove_transition)
        self.repin_manifest()
        with self.assertRaisesRegex(BaselineError, "transitions differ"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
