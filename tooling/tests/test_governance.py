from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.governance import (
    Change,
    Exemption,
    GovernanceError,
    evaluate_architecture,
    load_json,
    load_yaml,
    parse_name_status,
    path_matches,
    validate_declarations,
    validate_instance,
    validate_scope,
)


ROOT = Path(__file__).resolve().parents[2]


def task_fixture() -> dict[str, object]:
    task = load_yaml(ROOT / "governance/templates/task-record.yaml")
    assert isinstance(task, dict)
    task["scope"]["allowed_paths"] = ["governance/**"]
    task["scope"]["forbidden_paths"] = []
    task["scope"]["expected_files"] = []
    task["scope"]["permitted_generated_changes"] = []
    task["scope"]["expected_generated_outputs"] = []
    return task


def set_level(task: dict[str, object], name: str, level: str) -> None:
    task["change_classification"][name] = {
        "level": level,
        "evidence": [] if level == "none" else ["test evidence"],
    }


class PathMatchingTests(unittest.TestCase):
    def test_globs_are_case_sensitive_and_directory_aware(self) -> None:
        self.assertTrue(path_matches("docs/report.md", "docs/**"))
        self.assertTrue(path_matches("report.md", "**/*.md"))
        self.assertTrue(
            path_matches("bindings/r/v1.rockspec", "bindings/r/v[0-9].rockspec")
        )
        self.assertFalse(path_matches("Docs/report.md", "docs/**"))
        self.assertFalse(path_matches("docs/nested/report.md", "docs/*.md"))

    def test_unsafe_paths_are_rejected(self) -> None:
        for path in ("/absolute", "docs/../spec", "docs\\file"):
            with self.subTest(path=path), self.assertRaises(GovernanceError):
                path_matches(path, "docs/**")

    def test_rename_and_deletion_statuses_preserve_all_paths(self) -> None:
        changes = parse_name_status(
            b"R100\0old/name.py\0new/name.py\0D\0removed/file.py\0"
        )
        self.assertEqual(("old/name.py", "new/name.py"), changes[0].paths)
        self.assertEqual(("removed/file.py",), changes[1].paths)


class ScopeValidationTests(unittest.TestCase):
    def test_allowed_change_passes(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("M", None, "governance/policy.json")]
        )
        self.assertEqual("passed", result.status)

    def test_forbidden_path_fails_even_when_allowed(self) -> None:
        task = task_fixture()
        task["scope"]["forbidden_paths"] = ["governance/private/**"]
        result = validate_scope(
            task, [Change("M", None, "governance/private/policy.json")]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("forbidden", result.findings[0])

    def test_undeclared_path_fails(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("M", None, "tooling/new_check.py")]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("outside every allowed path", result.findings[0])

    def test_both_sides_of_rename_are_validated(self) -> None:
        result = validate_scope(
            task_fixture(),
            [Change("R100", "tooling/old.py", "governance/new.py")],
        )
        self.assertEqual("failed", result.status)
        self.assertIn("tooling/old.py", result.findings[0])

    def test_deleted_path_is_validated(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("D", "tooling/removed.py", None)]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("tooling/removed.py", result.findings[0])

    def test_exact_bounded_exemption_can_cover_one_scope_rule(self) -> None:
        exemption = Exemption(
            "WVR-TEST-001",
            "scope-undeclared-path",
            ("tooling/one.py",),
        )
        result = validate_scope(
            task_fixture(),
            [Change("M", None, "tooling/one.py")],
            [exemption],
        )
        self.assertEqual("passed", result.status)


class DeclarationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.control = load_json(ROOT / "governance/change-control.json")
        cls.registry = load_json(ROOT / "governance/generated-artifacts.json")
        cls.generated_patterns = ["tests/spec/**", "docs/generated/**"]
        assert isinstance(cls.control, dict)
        assert isinstance(cls.registry, dict)

    def test_generated_output_requires_declaration_and_permission(self) -> None:
        task = task_fixture()
        task["scope"]["allowed_paths"] = ["tests/spec/**"]
        result = validate_declarations(
            task,
            [Change("M", None, "tests/spec/example.json")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any(
                "generated_output_change is undeclared" in item
                for item in result.findings
            )
        )
        self.assertTrue(any("is not permitted" in item for item in result.findings))

        set_level(task, "semantic_change", "compatible")
        set_level(task, "generated_output_change", "compatible")
        task["scope"]["permitted_generated_changes"] = ["shared-semantic-fixtures"]
        task["scope"]["expected_generated_outputs"] = ["shared-semantic-fixtures"]
        result = validate_declarations(
            task,
            [Change("M", None, "tests/spec/example.json")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("passed", result.status)

    def test_inconsistent_semantic_declaration_fails(self) -> None:
        task = task_fixture()
        task["scope"]["allowed_paths"] = ["spec/**"]
        result = validate_declarations(
            task,
            [Change("M", None, "spec/grammar/dsl.ebnf")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("semantic_change is undeclared" in item for item in result.findings)
        )

    def test_unregistered_generated_output_fails(self) -> None:
        task = task_fixture()
        result = validate_declarations(
            task,
            [Change("M", None, "docs/generated/unknown.txt")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertTrue(
            any("unregistered generated output" in item for item in result.findings)
        )

    def test_documentation_only_does_not_require_semantic_change(self) -> None:
        task = task_fixture()
        task["change_classification"]["documentation_only"] = True
        task["change_classification"]["internal_implementation"] = False
        result = validate_declarations(
            task,
            [Change("M", None, "docs/guide.md")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("passed", result.status)


class ArchitectureValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "tooling").mkdir()
        self.task = task_fixture()
        self.control = {
            "active_task": "docs/migration/records/task.yaml",
        }
        self.registry = {"registry_version": 1, "artifacts": []}

    def evaluate(self, rule: dict[str, object], changes=()):
        return evaluate_architecture(
            {"registry_version": 1, "rules": [rule]},
            root=self.root,
            task=self.task,
            changes=list(changes),
            control=self.control,
            artifact_registry=self.registry,
        )[0]

    def test_forbidden_dependency_violation_fails(self) -> None:
        (self.root / "tooling/governance.py").write_text(
            "import bindings.python.compiler\n", encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "governance-boundary",
                "status": "enforced",
                "kind": "forbidden-dependency",
                "configuration": {
                    "sources": ["tooling/governance.py"],
                    "forbidden_dependencies": ["bindings"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("bindings.python.compiler", result.findings[0])

    def test_valid_transition_is_reported_without_failing(self) -> None:
        result = self.evaluate(
            {
                "id": "binding-transition",
                "status": "transitional",
                "kind": "tracked-transition",
                "configuration": {"tracked_paths": ["bindings/**"]},
                "rationale": "Legacy bindings remain.",
                "retirement_condition": "Migrate them.",
            }
        )
        self.assertEqual("transitional", result.status)
        self.assertEqual([], result.findings)

    def test_new_top_level_directory_requires_architecture_declaration(self) -> None:
        rule = {
            "id": "top-level",
            "status": "enforced",
            "kind": "new-top-level-directory",
            "configuration": {
                "allowed_top_level_directories": ["tooling"],
                "requires_declaration": "architecture_change",
            },
        }
        change = Change("A", None, "newcore/compiler.py")
        self.assertEqual("failed", self.evaluate(rule, [change]).status)
        set_level(self.task, "architecture_change", "additive")
        self.assertEqual("passed", self.evaluate(rule, [change]).status)

    def test_malformed_task_record_is_rejected(self) -> None:
        schema = load_json(ROOT / "governance/schemas/task-record.schema.json")
        invalid = task_fixture()
        del invalid["change_classification"]["semantic_change"]
        with self.assertRaises(GovernanceError):
            validate_instance(invalid, schema, "task record")


if __name__ == "__main__":
    unittest.main()
