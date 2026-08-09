from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.sync_fixture_projection import (
    projection_findings,
    write_projection,
)


class FixtureProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.source = root / "source"
        self.destination = root / "destination"
        self.source.mkdir()
        self.destination.mkdir()

    def test_exact_projection_passes(self) -> None:
        (self.source / "one.json").write_bytes(b'{"value": 1}')
        write_projection(self.source, self.destination)
        self.assertEqual([], projection_findings(self.source, self.destination))

    def test_stale_output_fails(self) -> None:
        (self.source / "one.json").write_bytes(b"current")
        (self.destination / "one.json").write_bytes(b"stale")
        self.assertEqual(
            ["stale output: one.json"],
            projection_findings(self.source, self.destination),
        )

    def test_missing_and_unexpected_outputs_fail(self) -> None:
        (self.source / "one.json").write_bytes(b"one")
        (self.destination / "extra.json").write_bytes(b"extra")
        self.assertEqual(
            ["missing output: one.json", "unexpected output: extra.json"],
            projection_findings(self.source, self.destination),
        )

    def test_missing_source_fails(self) -> None:
        self.assertIn(
            "no source JSON fixtures found",
            projection_findings(self.source / "missing", self.destination)[0],
        )

    def test_write_removes_stale_files_and_copies_bytes(self) -> None:
        (self.source / "one.json").write_bytes(b"one")
        (self.destination / "extra.json").write_bytes(b"extra")
        write_projection(self.source, self.destination)
        self.assertEqual(
            ["one.json"], [path.name for path in self.destination.iterdir()]
        )
        self.assertEqual(b"one", (self.destination / "one.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
