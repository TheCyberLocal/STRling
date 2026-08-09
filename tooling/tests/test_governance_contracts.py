from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "governance"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class GovernanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.task_schema = load_json(GOVERNANCE / "schemas/task-record.schema.json")
        cls.artifact_schema = load_json(
            GOVERNANCE / "schemas/generated-artifact-registry.schema.json"
        )
        cls.change_control_schema = load_json(
            GOVERNANCE / "schemas/change-control.schema.json"
        )
        cls.architecture_schema = load_json(
            GOVERNANCE / "schemas/architecture-rules.schema.json"
        )
        cls.public_surface_schema = load_json(
            GOVERNANCE / "schemas/public-surface-registry.schema.json"
        )

        cls.task_validator = Draft202012Validator(cls.task_schema)
        cls.artifact_validator = Draft202012Validator(cls.artifact_schema)
        cls.change_control_validator = Draft202012Validator(cls.change_control_schema)
        cls.architecture_validator = Draft202012Validator(cls.architecture_schema)
        cls.public_surface_validator = Draft202012Validator(cls.public_surface_schema)

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for schema in (
            self.task_schema,
            self.artifact_schema,
            self.change_control_schema,
            self.architecture_schema,
            self.public_surface_schema,
        ):
            Draft202012Validator.check_schema(schema)

    def test_checked_in_contract_instances_validate(self) -> None:
        self.task_validator.validate(
            load_yaml(GOVERNANCE / "templates/task-record.yaml")
        )
        self.task_validator.validate(
            load_yaml(
                ROOT / "docs/migration/records/generated-artifact-change-integrity.yaml"
            )
        )
        self.artifact_validator.validate(
            load_json(GOVERNANCE / "generated-artifacts.json")
        )
        self.change_control_validator.validate(
            load_json(GOVERNANCE / "change-control.json")
        )
        self.architecture_validator.validate(
            load_json(GOVERNANCE / "architecture-rules.json")
        )
        self.public_surface_validator.validate(
            load_json(GOVERNANCE / "public-surfaces.json")
        )

    def test_registry_and_rule_identifiers_are_unique(self) -> None:
        registry = load_json(GOVERNANCE / "generated-artifacts.json")
        rules = load_json(GOVERNANCE / "architecture-rules.json")
        surfaces = load_json(GOVERNANCE / "public-surfaces.json")
        assert isinstance(registry, dict)
        assert isinstance(rules, dict)
        assert isinstance(surfaces, dict)
        artifact_ids = [artifact["id"] for artifact in registry["artifacts"]]
        rule_ids = [rule["id"] for rule in rules["rules"]]
        surface_ids = [surface["id"] for surface in surfaces["surfaces"]]
        self.assertEqual(len(artifact_ids), len(set(artifact_ids)))
        self.assertEqual(len(rule_ids), len(set(rule_ids)))
        self.assertEqual(len(surface_ids), len(set(surface_ids)))

    def test_v2_task_requires_every_change_class(self) -> None:
        task = load_yaml(GOVERNANCE / "templates/task-record.yaml")
        assert isinstance(task, dict)
        invalid = copy.deepcopy(task)
        del invalid["change_classification"]["semantic_change"]
        with self.assertRaises(ValidationError):
            self.task_validator.validate(invalid)

    def test_declared_change_requires_evidence(self) -> None:
        task = load_yaml(GOVERNANCE / "templates/task-record.yaml")
        assert isinstance(task, dict)
        invalid = copy.deepcopy(task)
        invalid["change_classification"]["schema_change"]["level"] = "additive"
        with self.assertRaises(ValidationError):
            self.task_validator.validate(invalid)

    def test_absolute_and_parent_paths_are_rejected(self) -> None:
        task = load_yaml(GOVERNANCE / "templates/task-record.yaml")
        assert isinstance(task, dict)
        for bad_path in ("/absolute/path", "docs/../spec/file"):
            with self.subTest(path=bad_path):
                invalid = copy.deepcopy(task)
                invalid["scope"]["allowed_paths"] = [bad_path]
                with self.assertRaises(ValidationError):
                    self.task_validator.validate(invalid)

    def test_enforced_artifact_must_be_deterministic_and_checkable(self) -> None:
        registry = load_json(GOVERNANCE / "generated-artifacts.json")
        assert isinstance(registry, dict)
        invalid = copy.deepcopy(registry)
        artifact = invalid["artifacts"][0]
        artifact["enforcement"] = "enforced"
        artifact["determinism"] = "nondeterministic"
        with self.assertRaises(ValidationError):
            self.artifact_validator.validate(invalid)

    def test_transitional_rule_requires_retirement_condition(self) -> None:
        rules = load_json(GOVERNANCE / "architecture-rules.json")
        assert isinstance(rules, dict)
        invalid = copy.deepcopy(rules)
        transitional = next(
            rule for rule in invalid["rules"] if rule["status"] == "transitional"
        )
        del transitional["retirement_condition"]
        with self.assertRaises(ValidationError):
            self.architecture_validator.validate(invalid)

    def test_transitional_surface_requires_retirement_condition(self) -> None:
        registry = load_json(GOVERNANCE / "public-surfaces.json")
        assert isinstance(registry, dict)
        invalid = copy.deepcopy(registry)
        transitional = next(
            surface
            for surface in invalid["surfaces"]
            if surface["enforcement"] == "transitional"
        )
        del transitional["retirement_condition"]
        with self.assertRaises(ValidationError):
            self.public_surface_validator.validate(invalid)

    def test_planned_surface_requires_activation_condition(self) -> None:
        registry = load_json(GOVERNANCE / "public-surfaces.json")
        assert isinstance(registry, dict)
        invalid = copy.deepcopy(registry)
        planned = next(
            surface
            for surface in invalid["surfaces"]
            if surface["enforcement"] == "planned"
        )
        del planned["activation_condition"]
        with self.assertRaises(ValidationError):
            self.public_surface_validator.validate(invalid)


if __name__ == "__main__":
    unittest.main()
