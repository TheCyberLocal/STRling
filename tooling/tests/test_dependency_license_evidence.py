from __future__ import annotations

import contextlib
import copy
import json
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

from tooling import dependency_license_evidence as evidence


class DependencyLicenseEvidenceTests(unittest.TestCase):
    @contextlib.contextmanager
    def _fixture(self) -> Iterator[dict[Path, str]]:
        paths = (
            evidence.OUTPUT,
            evidence.DART_LOCK,
            evidence.LUA_LOCK,
            evidence.CPAN_LOCK,
            evidence.PYTHON_LOCK,
        )
        contents = {path: path.read_text(encoding="utf-8") for path in paths}

        def read_text(path: Path, *args: object, **kwargs: object) -> str:
            del args, kwargs
            return contents[path]

        with mock.patch.object(Path, "read_text", autospec=True, side_effect=read_text):
            yield contents

    @staticmethod
    def _read(contents: dict[Path, str]) -> dict[str, object]:
        value = json.loads(contents[evidence.OUTPUT])
        assert isinstance(value, dict)
        return value

    @staticmethod
    def _write(contents: dict[Path, str], value: dict[str, object]) -> None:
        value["fingerprint"] = evidence._fingerprint(value)
        contents[evidence.OUTPUT] = (
            json.dumps(value, ensure_ascii=False, indent=4) + "\n"
        )

    def test_check_is_offline_and_accepts_current_hash_bound_evidence(self) -> None:
        with self._fixture():
            with (
                mock.patch.object(
                    evidence,
                    "_get_json",
                    side_effect=AssertionError(
                        "offline check attempted JSON network I/O"
                    ),
                ),
                mock.patch.object(
                    evidence,
                    "_get_bytes",
                    side_effect=AssertionError(
                        "offline check attempted archive network I/O"
                    ),
                ),
            ):
                result = evidence.synchronize(write=False)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["entries"], 54)

    def test_check_rejects_fingerprint_drift(self) -> None:
        with self._fixture() as contents:
            value = self._read(contents)
            value["fingerprint"] = "sha256:" + "0" * 64
            contents[evidence.OUTPUT] = json.dumps(value)
            with self.assertRaisesRegex(
                evidence.LicenseEvidenceError, "fingerprint drifted"
            ):
                evidence.synchronize(write=False)

    def test_check_rejects_hash_bound_lock_drift(self) -> None:
        with self._fixture() as contents:
            value = self._read(contents)
            entries = value["entries"]
            assert isinstance(entries, list)
            dart_entry = next(
                entry
                for entry in entries
                if isinstance(entry, dict) and entry.get("ecosystem") == "dart-pub"
            )
            dart_entry["archive_sha256"] = "0" * 64
            self._write(contents, value)
            with self.assertRaisesRegex(
                evidence.LicenseEvidenceError, "Dart license evidence"
            ):
                evidence.synchronize(write=False)

    def test_check_rejects_duplicate_evidence_identity(self) -> None:
        with self._fixture() as contents:
            value = self._read(contents)
            entries = value["entries"]
            assert isinstance(entries, list)
            entries.append(copy.deepcopy(entries[0]))
            self._write(contents, value)
            with self.assertRaisesRegex(
                evidence.LicenseEvidenceError, "duplicate license evidence"
            ):
                evidence.synchronize(write=False)


if __name__ == "__main__":
    unittest.main()
