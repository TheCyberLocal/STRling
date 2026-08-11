"""Canonical validation for standard-library helper guarantee contracts.

This module is an internal component of ``tooling.contract_validation``. It has
no command-line entry point and therefore cannot become a parallel quality
runner.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, MutableMapping, MutableSequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
STDLIB_CONTRACT_ROOT = ROOT / "spec" / "stdlib" / "contracts" / "1.0"
STDLIB_EXAMPLE_ROOT = STDLIB_CONTRACT_ROOT / "examples" / "helper-guarantee"
STDLIB_INVALID_ROOT = STDLIB_CONTRACT_ROOT / "invalid" / "helper-guarantee"
STDLIB_TRANSITION_INVENTORY = (
    ROOT / "spec" / "stdlib" / "validation-guarantee-transition.json"
)


class StandardLibraryContractError(ValueError):
    """A helper-guarantee schema or cross-field invariant was violated."""


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object without accepting a non-object document root."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise StandardLibraryContractError(f"{path}: root value must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    """Return deterministic JSON bytes for definition identity tests."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_path(parts: Any) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _unique_ids(
    items: list[Mapping[str, Any]], key: str, label: str
) -> tuple[list[str], set[str]]:
    values = [str(item[key]) for item in items]
    if len(values) != len(set(values)):
        raise StandardLibraryContractError(f"{label}.unique: duplicate {key}")
    return values, set(values)


class StandardLibraryGuaranteeSuite:
    """Validate normative helper metadata and controlled transition evidence."""

    def __init__(self, contract_root: Path = STDLIB_CONTRACT_ROOT) -> None:
        self.contract_root = contract_root
        self.schemas = {
            path.name: load_json(path)
            for path in sorted(contract_root.glob("*.schema.json"))
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        store = {schema["$id"]: schema for schema in self.schemas.values()}
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }

    def validate_suite_structure(self) -> int:
        """Validate schema identity and root strictness."""
        expected = {
            "controlled-invalid-guarantee.schema.json",
            "helper-guarantee.schema.json",
            "transition-inventory.schema.json",
        }
        if set(self.schemas) != expected:
            raise StandardLibraryContractError(
                "stdlib.schemas.complete: schema family does not match contract 1.0"
            )
        schema_ids = [schema["$id"] for schema in self.schemas.values()]
        if len(schema_ids) != len(set(schema_ids)):
            raise StandardLibraryContractError(
                "stdlib.schemas.unique: schema IDs must be unique"
            )
        for name, schema in self.schemas.items():
            expected_id = f"https://strling.dev/spec/stdlib/contracts/1.0/{name}"
            if schema["$id"] != expected_id:
                raise StandardLibraryContractError(
                    f"stdlib.schemas.identity: {name} must use {expected_id}"
                )
            if schema.get("additionalProperties") is not False:
                raise StandardLibraryContractError(
                    f"stdlib.schemas.closed: {name} root must reject unknown fields"
                )
        return len(self.schemas)

    def _schema_validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators[schema_name].iter_errors(value),
            key=lambda error: list(error.path),
        )
        if errors:
            error = errors[0]
            raise StandardLibraryContractError(
                f"helper.schema: {schema_name} {_json_path(error.path)}: "
                f"{error.message}"
            )

    @staticmethod
    def _pointer_tokens(pointer: str) -> list[str]:
        if not pointer.startswith("/"):
            raise StandardLibraryContractError(
                "reference.pointer.malformed: JSON Pointer must start with /"
            )
        return [
            token.replace("~1", "/").replace("~0", "~")
            for token in pointer[1:].split("/")
        ]

    @classmethod
    def _resolve_pointer(cls, value: Any, pointer: str) -> Any:
        current = value
        for token in cls._pointer_tokens(pointer):
            if isinstance(current, list):
                try:
                    current = current[int(token)]
                except (ValueError, IndexError) as exc:
                    raise StandardLibraryContractError(
                        f"reference.pointer.unresolved: {pointer}"
                    ) from exc
            elif isinstance(current, Mapping) and token in current:
                current = current[token]
            else:
                raise StandardLibraryContractError(
                    f"reference.pointer.unresolved: {pointer}"
                )
        return current

    @classmethod
    def _resolve_repository_reference(cls, reference: str) -> Path:
        path_text, separator, fragment = reference.partition("#")
        if (
            not path_text
            or path_text.startswith("/")
            or "\\" in path_text
            or ".." in Path(path_text).parts
            or "/" not in path_text
        ):
            raise StandardLibraryContractError(
                f"evidence.reference.malformed: {reference}"
            )
        path = (ROOT / path_text).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise StandardLibraryContractError(
                f"evidence.reference.unresolved: {reference}"
            )
        if separator:
            if not fragment.startswith("/") or path.suffix != ".json":
                raise StandardLibraryContractError(
                    f"evidence.reference.malformed: {reference}"
                )
            cls._resolve_pointer(load_json(path), fragment)
        return path

    @staticmethod
    def _preflight_claim_rules(value: Mapping[str, Any]) -> None:
        if "guarantee_level" not in value:
            raise StandardLibraryContractError(
                "guarantee_level.required: every guarantee must declare a level"
            )

        standards = value.get("standards")
        if isinstance(standards, Mapping):
            if "scope" not in standards:
                raise StandardLibraryContractError(
                    "standard.scope.required: every standards claim needs scope"
                )
            if standards.get("scope") == "complete" and standards.get(
                "excluded_provisions"
            ):
                raise StandardLibraryContractError(
                    "standard.complete.exclusions_forbidden: complete scope cannot retain subset exclusions"
                )

        checks = value.get("checks")
        if isinstance(checks, Mapping):
            performed = checks.get("performed", [])
            if isinstance(performed, list) and any(
                isinstance(check, Mapping) and check.get("category") == "portability"
                for check in performed
            ):
                raise StandardLibraryContractError(
                    "validation.portability_forbidden: portability is not a validation condition"
                )

        safety = value.get("safety")
        if isinstance(safety, Mapping) and safety.get("claim") != "not_claimed":
            raise StandardLibraryContractError(
                "validation.safety_claim_forbidden: validation metadata cannot claim safety"
            )

        references: list[Any] = []
        evidence = value.get("evidence")
        if isinstance(evidence, Mapping):
            raw_references = evidence.get("references", [])
            if isinstance(raw_references, list):
                references = raw_references
        for reference in references:
            if not isinstance(reference, Mapping):
                continue
            path = reference.get("path")
            if isinstance(path, str) and (
                path.startswith("/")
                or "\\" in path
                or ".." in Path(path.partition("#")[0]).parts
            ):
                raise StandardLibraryContractError(
                    f"evidence.reference.malformed: {path}"
                )

        if value.get("guarantee_level") == "semantic" and not any(
            isinstance(reference, Mapping)
            and reference.get("kind") == "semantic_condition"
            for reference in references
        ):
            raise StandardLibraryContractError(
                "semantic.evidence.required: semantic claims need semantic-condition evidence"
            )

    def validate_guarantee(self, value: Mapping[str, Any]) -> None:
        """Validate one helper guarantee and all cross-field proof obligations."""
        self._preflight_claim_rules(value)
        self._schema_validate("helper-guarantee.schema.json", value)

        level = str(value["guarantee_level"])
        allowed_categories = {
            "lexical_shape": {"lexical"},
            "normalized_structure": {"lexical", "structural"},
            "semantic": {"lexical", "structural", "semantic"},
        }[level]

        definition = value["validation_definition"]
        assert isinstance(definition, Mapping)
        conditions = definition["conditions"]
        assert isinstance(conditions, list)
        _, condition_ids = _unique_ids(conditions, "condition_id", "condition")
        condition_by_id = {item["condition_id"]: item for item in conditions}
        if any(item["category"] not in allowed_categories for item in conditions):
            raise StandardLibraryContractError(
                "guarantee.level.ceiling: definition contains a stronger condition category"
            )

        stages = value["validator_pipeline"]
        assert isinstance(stages, list)
        _, stage_ids = _unique_ids(stages, "stage_id", "validator_stage")
        stage_by_id = {item["stage_id"]: item for item in stages}
        stage_conditions = [
            condition_id
            for stage in stages
            for condition_id in stage["proves_conditions"]
        ]
        if len(stage_conditions) != len(set(stage_conditions)):
            raise StandardLibraryContractError(
                "condition.stage.unique: each condition must have one owning stage"
            )
        if set(stage_conditions) != condition_ids:
            raise StandardLibraryContractError(
                "condition.stage.complete: stages must cover every and only declared condition"
            )
        for stage in stages:
            self._resolve_repository_reference(str(stage["implementation_reference"]))

        checks = value["checks"]
        assert isinstance(checks, Mapping)
        performed = checks["performed"]
        omitted = checks["not_performed"]
        assert isinstance(performed, list)
        assert isinstance(omitted, list)
        _, performed_ids = _unique_ids(performed, "check_id", "performed_check")
        _, omitted_ids = _unique_ids(omitted, "check_id", "omitted_check")
        if performed_ids.intersection(omitted_ids):
            raise StandardLibraryContractError(
                "check.identity.disjoint: a check cannot be performed and omitted"
            )
        performed_condition_ids = [str(item["condition_id"]) for item in performed]
        if len(performed_condition_ids) != len(set(performed_condition_ids)):
            raise StandardLibraryContractError(
                "condition.check.unique: each condition must have one performed check"
            )
        if set(performed_condition_ids) != condition_ids:
            raise StandardLibraryContractError(
                "condition.check.complete: checks must cover every declared condition"
            )
        for check in performed:
            condition_id = str(check["condition_id"])
            if check["category"] not in allowed_categories:
                raise StandardLibraryContractError(
                    "guarantee.level.ceiling: performed check exceeds the guarantee level"
                )
            if check["category"] != condition_by_id[condition_id]["category"]:
                raise StandardLibraryContractError(
                    "condition.category.correspondence: check and condition categories differ"
                )
            for stage_id in check["stage_ids"]:
                if stage_id not in stage_ids:
                    raise StandardLibraryContractError(
                        f"check.stage.unresolved: {stage_id}"
                    )
                if condition_id not in stage_by_id[stage_id]["proves_conditions"]:
                    raise StandardLibraryContractError(
                        "check.stage.correspondence: referenced stage does not prove the condition"
                    )

        evidence = value["evidence"]
        assert isinstance(evidence, Mapping)
        references = evidence["references"]
        bindings = evidence["condition_bindings"]
        assert isinstance(references, list)
        assert isinstance(bindings, list)
        _, evidence_ids = _unique_ids(references, "evidence_id", "evidence")
        evidence_by_id = {item["evidence_id"]: item for item in references}
        _, binding_ids = _unique_ids(bindings, "check_id", "evidence_binding")
        if binding_ids != performed_ids:
            raise StandardLibraryContractError(
                "evidence.binding.complete: every performed check needs exactly one binding"
            )
        for reference in references:
            self._resolve_repository_reference(str(reference["path"]))
        for binding in bindings:
            bound_ids = set(binding["evidence_ids"])
            if not bound_ids.issubset(evidence_ids):
                raise StandardLibraryContractError(
                    "evidence.binding.unresolved: binding references unknown evidence"
                )
            check = next(
                item for item in performed if item["check_id"] == binding["check_id"]
            )
            if check["category"] == "semantic" and not any(
                evidence_by_id[evidence_id]["kind"] == "semantic_condition"
                for evidence_id in bound_ids
            ):
                raise StandardLibraryContractError(
                    "semantic.evidence.correspondence: semantic check lacks semantic evidence"
                )

        evidence_kinds = {str(item["kind"]) for item in references}
        required_kinds = {
            "validator_implementation",
            "acceptance_corpus",
            "rejection_corpus",
        }
        if level in {"normalized_structure", "semantic"}:
            required_kinds.add("boundary_corpus")
        if level == "semantic":
            required_kinds.update({"interaction_corpus", "semantic_condition"})
        standards = value["standards"]
        assert isinstance(standards, Mapping)
        if standards["scope"] in {"subset", "profile", "complete"}:
            required_kinds.add("standard_conformance")
        if not required_kinds.issubset(evidence_kinds):
            missing = sorted(required_kinds.difference(evidence_kinds))
            raise StandardLibraryContractError(
                f"evidence.kind.complete: missing {', '.join(missing)}"
            )
        if standards["scope"] == "complete" and value["excluded_cases"]:
            raise StandardLibraryContractError(
                "standard.complete.exclusions_forbidden: complete scope cannot exclude cases"
            )

        target_support = value["target_support"]
        assert isinstance(target_support, Mapping)
        for reference in target_support["target_profile_references"]:
            self._resolve_repository_reference(str(reference))

        for collection_name, collection in (
            ("excluded_case", value["excluded_cases"]),
            ("known_limitation", value["known_limitations"]),
        ):
            if collection_name == "excluded_case":
                assert isinstance(collection, list)
                _unique_ids(collection, "case_id", collection_name)

    def validate_transition_inventory(self, value: Mapping[str, Any]) -> None:
        """Validate explicit non-grandfathering for every historical helper."""
        self._schema_validate("transition-inventory.schema.json", value)
        entries = value["entries"]
        assert isinstance(entries, list)
        helper_ids, _ = _unique_ids(entries, "helper_id", "transition_helper")
        registry_names, registry_name_set = _unique_ids(
            entries, "registry_name", "transition_registry_name"
        )
        if helper_ids != sorted(helper_ids):
            raise StandardLibraryContractError(
                "transition.order: helper IDs must be canonically sorted"
            )
        for entry in entries:
            for field in (
                "source_references",
                "known_claim_risks",
                "required_later_work",
            ):
                values = entry[field]
                if values != sorted(set(values)):
                    raise StandardLibraryContractError(
                        f"transition.order: {entry['helper_id']} {field} must be unique and sorted"
                    )
            for reference in entry["source_references"]:
                self._resolve_repository_reference(str(reference))

        registry = load_json(ROOT / "spec" / "stdlib" / "registry.json")
        essential = load_json(ROOT / "spec" / "stdlib" / "essential_5.json")
        current_registry_names = {
            str(pattern["name"]) for pattern in registry["patterns"]
        }
        current_essential_names = set(essential["patterns"])
        if (
            registry_name_set != current_registry_names
            or registry_name_set != current_essential_names
        ):
            raise StandardLibraryContractError(
                "transition.coverage: inventory must classify every and only current helper"
            )
        if registry_names != [entry["registry_name"] for entry in entries]:
            raise StandardLibraryContractError(
                "transition.identity: registry names must remain stable"
            )

    def validate_positive_examples(self) -> int:
        """Validate all guarantee examples plus the historical transition inventory."""
        count = 0
        for path in sorted(STDLIB_EXAMPLE_ROOT.glob("*.json")):
            value = load_json(path)
            self.validate_guarantee(value)
            if value["status"] != "example":
                raise StandardLibraryContractError(
                    f"example.status: {path} must not claim ratified status"
                )
            count += 1
        self.validate_transition_inventory(load_json(STDLIB_TRANSITION_INVENTORY))
        return count + 1

    @classmethod
    def _mutate(
        cls, base: Mapping[str, Any], mutation: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = copy.deepcopy(dict(base))
        tokens = cls._pointer_tokens(str(mutation["pointer"]))
        parent: Any = result
        for token in tokens[:-1]:
            if isinstance(parent, list):
                parent = parent[int(token)]
            else:
                parent = parent[token]
        final = tokens[-1]
        operation = mutation["operation"]
        if isinstance(parent, MutableSequence):
            index = int(final)
            if operation == "remove":
                parent.pop(index)
            elif operation == "add":
                parent.insert(index, copy.deepcopy(mutation["value"]))
            else:
                parent[index] = copy.deepcopy(mutation["value"])
        elif isinstance(parent, MutableMapping):
            if operation == "remove":
                del parent[final]
            else:
                parent[final] = copy.deepcopy(mutation["value"])
        else:
            raise StandardLibraryContractError(
                "controlled_invalid.pointer: mutation parent is not a container"
            )
        return result

    def materialize_invalid_case(self, case: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize one deterministic invalid helper definition."""
        self._schema_validate("controlled-invalid-guarantee.schema.json", case)
        base_path = self._resolve_repository_reference(str(case["base_fixture"]))
        if base_path.parent != STDLIB_EXAMPLE_ROOT.resolve():
            raise StandardLibraryContractError(
                "controlled_invalid.base: base must be a helper-guarantee example"
            )
        base = load_json(base_path)
        self.validate_guarantee(base)
        return self._mutate(base, case["mutation"])

    def validate_negative_examples(self) -> int:
        """Materialize and reject every invalid definition for its declared rule."""
        count = 0
        for path in sorted(STDLIB_INVALID_ROOT.glob("*.json")):
            case = load_json(path)
            invalid = self.materialize_invalid_case(case)
            expected = f"{case['expected_rule']}:"
            try:
                self.validate_guarantee(invalid)
            except StandardLibraryContractError as exc:
                if not str(exc).startswith(expected):
                    raise StandardLibraryContractError(
                        f"controlled_invalid.rule: {path} expected {case['expected_rule']}, got {exc}"
                    ) from exc
                count += 1
                continue
            raise StandardLibraryContractError(
                f"controlled invalid helper guarantee unexpectedly passed: {path}"
            )
        return count

    def evidence_fingerprint(self) -> str:
        """Fingerprint authored guarantee evidence for deterministic regression tests."""
        documents = [
            *sorted(STDLIB_EXAMPLE_ROOT.glob("*.json")),
            *sorted(STDLIB_INVALID_ROOT.glob("*.json")),
            STDLIB_TRANSITION_INVENTORY,
        ]
        digest = hashlib.sha256()
        for path in documents:
            digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(canonical_json(load_json(path)))
            digest.update(b"\n")
        return digest.hexdigest()
