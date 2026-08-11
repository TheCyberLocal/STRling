from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tooling.documentation_integrity import (
    OPERATION_ID,
    Check,
    build_result,
    check_executable_examples,
    run,
    scan_markdown_links,
    validate_result,
)


ROOT = Path(__file__).resolve().parents[2]


class DocumentationLinkTests(unittest.TestCase):
    def test_local_inline_reference_and_html_links_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs/target.md").write_text("target\n", encoding="utf-8")
            source = root / "docs/source.md"
            source.write_text(
                "[inline](target.md)\n"
                "[reference][target]\n"
                '<a href="target.md">html</a>\n'
                "[target]: target.md\n",
                encoding="utf-8",
            )
            result = scan_markdown_links(root, [source])
        self.assertEqual("passed", result.status)
        self.assertEqual((), result.findings)

    def test_missing_link_is_a_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            result = scan_markdown_links(root, [source])
        self.assertEqual("failed", result.status)
        self.assertEqual("DOC-LINK-MISSING", result.findings[0].code)

    def test_undefined_reference_is_a_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text("[missing][definition]\n", encoding="utf-8")
            result = scan_markdown_links(root, [source])
        self.assertEqual("failed", result.status)
        self.assertEqual("DOC-REFERENCE-UNDEFINED", result.findings[0].code)

    def test_code_and_template_placeholders_are_deliberately_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text(
                "`[inline](missing.md)`\n```md\n[fenced](missing.md)\n```\n",
                encoding="utf-8",
            )
            template = root / "docs/templates/example.md"
            template.parent.mkdir(parents=True)
            template.write_text("[placeholder](missing.md)\n", encoding="utf-8")
            result = scan_markdown_links(root, [source, template])
        self.assertEqual("passed", result.status)


class ExecutableExampleTests(unittest.TestCase):
    @staticmethod
    def _fixture_root(directory: str) -> Path:
        root = Path(directory)
        examples = root / "tooling/lsp-server/examples"
        (examples / "errors").mkdir(parents=True)
        (examples / "valid_patterns.strl").write_text("valid\n", encoding="utf-8")
        (examples / "invalid_patterns.strl").write_text("invalid\n", encoding="utf-8")
        (examples / "errors/invalid.strl").write_text("invalid\n", encoding="utf-8")
        (examples / "README.md").write_text(
            "python3 tooling/parse_strl.py tooling/lsp-server/examples/valid_patterns.strl\n"
            "python3 tooling/parse_strl.py - < tooling/lsp-server/examples/valid_patterns.strl\n",
            encoding="utf-8",
        )
        return root

    def test_governed_examples_preserve_expected_exit_semantics(self) -> None:
        def execute(
            command: list[str], **_kwargs: Any
        ) -> subprocess.CompletedProcess[str]:
            returncode = 0 if Path(command[-1]).name == "valid_patterns.strl" else 2
            return subprocess.CompletedProcess(command, returncode, "", "")

        with tempfile.TemporaryDirectory() as directory:
            result = check_executable_examples(self._fixture_root(directory), execute)
        self.assertEqual("passed", result.status)

    def test_unexpected_example_exit_is_a_controlled_failure(self) -> None:
        def execute(
            command: list[str], **_kwargs: Any
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as directory:
            result = check_executable_examples(self._fixture_root(directory), execute)
        self.assertEqual("failed", result.status)
        self.assertTrue(
            all(finding.code == "DOC-EXAMPLE-EXIT" for finding in result.findings)
        )


class DocumentationResultContractTests(unittest.TestCase):
    def test_result_contract_rejects_aggregate_tampering(self) -> None:
        result = build_result(
            (Check("documentation.fixture", "passed", "fixture passed"),)
        )
        result["status"] = "failed"
        self.assertIn("status must aggregate to passed", validate_result(result))

    def test_actual_repository_operation_passes_without_mutation(self) -> None:
        before = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        result = run(ROOT)
        after = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(OPERATION_ID, result["operation_id"])
        self.assertEqual("passed", result["status"])
        self.assertEqual([], validate_result(result))
        self.assertEqual(before, after)
        coverage = result["coverage"]
        assert isinstance(coverage, dict)
        self.assertEqual(3, len(coverage["limitations"]))
        self.assertEqual(2, len(coverage["delegated_operations"]))


if __name__ == "__main__":
    unittest.main()
