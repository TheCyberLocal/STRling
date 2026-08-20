"""Canonical validation for standard-library helper guarantee contracts.

This module is an internal component of ``tooling.contract_validation``. It has
no command-line entry point and therefore cannot become a parallel quality
runner.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
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
STDLIB_GUARANTEE_AUDIT = ROOT / "spec" / "stdlib" / "stdlib-guarantee-audit.json"
STDLIB_GUARANTEE_AUDIT_FIXTURES = (
    ROOT / "spec" / "stdlib" / "stdlib-guarantee-audit-fixtures.json"
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
        inventory_classification = str(value["classification"])
        expected_entry_classification = {
            "transitional_unclassified": "transitional_unclassified",
            "audited_decisions": "audited",
        }[inventory_classification]
        for entry in entries:
            if entry["classification"] != expected_entry_classification:
                raise StandardLibraryContractError(
                    "transition.classification: root and entry states must correspond"
                )
            ordered_fields = ["source_references"]
            if inventory_classification == "transitional_unclassified":
                ordered_fields.extend(["known_claim_risks", "required_later_work"])
            else:
                ordered_fields.append("remaining_work")
            for field in ordered_fields:
                values = entry[field]
                if values != sorted(set(values)):
                    raise StandardLibraryContractError(
                        f"transition.order: {entry['helper_id']} {field} must be unique and sorted"
                    )
            for reference in entry["source_references"]:
                self._resolve_repository_reference(str(reference))
            if inventory_classification == "audited_decisions":
                audit_reference = str(entry["audit_reference"])
                audit_path = self._resolve_repository_reference(audit_reference)
                _, _, fragment = audit_reference.partition("#")
                audit_helper = self._resolve_pointer(load_json(audit_path), fragment)
                if (
                    audit_helper["helper_id"] != entry["helper_id"]
                    or audit_helper["registry_name"] != entry["registry_name"]
                    or audit_helper["guarantee_level"]
                    != entry["strongest_permitted_claim"]
                ):
                    raise StandardLibraryContractError(
                        f"transition.audit.correspondence: {entry['helper_id']} disagrees with its audit"
                    )

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

    @staticmethod
    def _closed_object(value: Any, required: set[str], label: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise StandardLibraryContractError(f"{label}.object: expected object")
        actual = set(value)
        if actual != required:
            missing = sorted(required - actual)
            unknown = sorted(actual - required)
            raise StandardLibraryContractError(
                f"{label}.fields: missing={missing}, unknown={unknown}"
            )
        return value

    @staticmethod
    def _non_empty_strings(value: Any, label: str) -> list[str]:
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item for item in value)
            or len(value) != len(set(value))
        ):
            raise StandardLibraryContractError(
                f"{label}.strings: expected unique non-empty strings"
            )
        return value

    def validate_audit(
        self, audit: Mapping[str, Any], fixtures: Mapping[str, Any]
    ) -> tuple[int, int, int]:
        """Validate the complete Essential 5 audit and its observed edge corpus."""
        self._closed_object(
            audit,
            {
                "kind",
                "audit_version",
                "baseline_commit",
                "taxonomy_reference",
                "fixture_reference",
                "binding_count",
                "variant_count",
                "bindings",
                "helpers",
            },
            "audit",
        )
        if audit["kind"] != "strling.stdlib-guarantee-audit":
            raise StandardLibraryContractError("audit.kind: unexpected kind")
        if audit["audit_version"] != "1.0.0":
            raise StandardLibraryContractError("audit.version: unsupported version")
        if not re.fullmatch(r"[0-9a-f]{40}", str(audit["baseline_commit"])):
            raise StandardLibraryContractError(
                "audit.baseline: expected full commit SHA"
            )
        for reference_field in ("taxonomy_reference", "fixture_reference"):
            self._resolve_repository_reference(str(audit[reference_field]))

        bindings = audit["bindings"]
        helpers = audit["helpers"]
        if not isinstance(bindings, list) or not isinstance(helpers, list):
            raise StandardLibraryContractError("audit.collections: expected arrays")
        if audit["binding_count"] != len(bindings) or len(bindings) != 17:
            raise StandardLibraryContractError("audit.bindings.count: expected 17")
        if len(helpers) != 5:
            raise StandardLibraryContractError("audit.helpers.count: expected 5")

        binding_ids: list[str] = []
        implementation_paths: list[Path] = []
        public_name_keys = {"email", "url", "uuid", "ip", "date_time"}
        for binding in bindings:
            item = self._closed_object(
                binding,
                {
                    "binding_id",
                    "implementation_references",
                    "test_reference",
                    "public_names",
                },
                "audit.binding",
            )
            binding_id = str(item["binding_id"])
            if not re.fullmatch(r"[a-z][a-z0-9_]*", binding_id):
                raise StandardLibraryContractError(
                    f"audit.binding.id: malformed {binding_id}"
                )
            binding_ids.append(binding_id)
            implementations = self._non_empty_strings(
                item["implementation_references"],
                f"audit.binding.{binding_id}.implementations",
            )
            for reference in [*implementations, str(item["test_reference"])]:
                resolved = self._resolve_repository_reference(reference)
                if reference in implementations:
                    implementation_paths.append(resolved)
            test_text = (ROOT / str(item["test_reference"])).read_text(encoding="utf-8")
            if "essential_5.json" not in test_text:
                raise StandardLibraryContractError(
                    f"audit.binding.fixtures: {binding_id} does not consume essential_5.json"
                )
            names = item["public_names"]
            if not isinstance(names, Mapping) or set(names) != public_name_keys:
                raise StandardLibraryContractError(
                    f"audit.binding.names: {binding_id} must cover every helper"
                )
            for helper_key, spellings in names.items():
                self._non_empty_strings(
                    spellings, f"audit.binding.{binding_id}.{helper_key}.names"
                )
        if binding_ids != sorted(set(binding_ids)):
            raise StandardLibraryContractError(
                "audit.binding.order: binding IDs must be unique and sorted"
            )
        forbidden_public_claims = {
            "canonical, RFC-grounded",
            "RFC-grounded patterns",
            "Matches an email address (RFC 5322",
            "Matches an HTTP or HTTPS URL (RFC 3986",
            "Matches a UUID (RFC 4122",
            "standard 8-4-4-4-12 hexadecimal format (RFC 4122",
            "Matches an IPv4 (RFC 791)",
            "Matches an ISO 8601 / RFC 3339 datetime",
            "ISO 8601 / RFC 3339 datetime pattern",
        }
        for path in implementation_paths:
            source = path.read_text(encoding="utf-8")
            if "lexical" not in source.lower():
                raise StandardLibraryContractError(
                    f"audit.public_claim.scope: {path.relative_to(ROOT)} lacks lexical qualification"
                )
            for claim in forbidden_public_claims:
                if claim in source:
                    raise StandardLibraryContractError(
                        f"audit.public_claim.overstatement: {path.relative_to(ROOT)} retains {claim}"
                    )

        helper_ids: list[str] = []
        registry_names: list[str] = []
        helper_text_models: dict[str, str] = {}
        variant_groups: dict[str, tuple[str, str]] = {}
        for helper in helpers:
            item = self._closed_object(
                helper,
                {
                    "helper_id",
                    "registry_name",
                    "guarantee_level",
                    "text_model",
                    "match_scope",
                    "variants",
                    "accepts",
                    "rejects",
                    "normalizes",
                    "does_not_claim",
                    "standards",
                    "compatibility",
                    "source_references",
                    "target_dependencies",
                },
                "audit.helper",
            )
            helper_id = str(item["helper_id"])
            helper_ids.append(helper_id)
            registry_names.append(str(item["registry_name"]))
            helper_text_models[helper_id] = str(item["text_model"])
            if item["guarantee_level"] != "lexical_shape":
                raise StandardLibraryContractError(
                    f"audit.helper.level: {helper_id} exceeds observed regex behavior"
                )
            if item["text_model"] not in {
                "ascii",
                "ascii_literals_with_target_digit_class",
            }:
                raise StandardLibraryContractError(
                    f"audit.helper.text_model: unsupported for {helper_id}"
                )
            if item["match_scope"] != "whole_value_when_anchored_by_consumer":
                raise StandardLibraryContractError(
                    f"audit.helper.match_scope: incorrect for {helper_id}"
                )
            for field in (
                "accepts",
                "rejects",
                "does_not_claim",
                "source_references",
                "target_dependencies",
            ):
                values = self._non_empty_strings(
                    item[field], f"audit.helper.{helper_id}.{field}"
                )
                if field == "source_references":
                    for reference in values:
                        self._resolve_repository_reference(reference)
            if item["normalizes"] != []:
                raise StandardLibraryContractError(
                    f"audit.helper.normalization: {helper_id} cannot claim normalization"
                )

            compatibility = self._closed_object(
                item["compatibility"],
                {"disposition", "classification", "future_surface"},
                f"audit.helper.{helper_id}.compatibility",
            )
            if (
                compatibility["disposition"] != "retain"
                or compatibility["classification"]
                != "behavior_preserved_claim_narrowed"
            ):
                raise StandardLibraryContractError(
                    f"audit.helper.compatibility: unsupported disposition for {helper_id}"
                )
            if (
                not isinstance(compatibility["future_surface"], str)
                or not compatibility["future_surface"]
            ):
                raise StandardLibraryContractError(
                    f"audit.helper.future_surface: missing for {helper_id}"
                )

            standards = item["standards"]
            if not isinstance(standards, Mapping) or standards.get("scope") not in {
                "inspired",
                "subset",
            }:
                raise StandardLibraryContractError(
                    f"audit.helper.standard_scope: missing for {helper_id}"
                )
            expected_standard_fields = (
                {"scope", "references", "inspired_elements"}
                if standards["scope"] == "inspired"
                else {
                    "scope",
                    "references",
                    "included_provisions",
                    "excluded_provisions",
                }
            )
            self._closed_object(
                standards,
                expected_standard_fields,
                f"audit.helper.{helper_id}.standards",
            )
            standard_references = standards["references"]
            if not isinstance(standard_references, list) or not standard_references:
                raise StandardLibraryContractError(
                    f"audit.helper.standard_references: missing for {helper_id}"
                )
            for reference in standard_references:
                standard = self._closed_object(
                    reference,
                    {"authority_id", "title", "edition", "uri", "provisions"},
                    f"audit.helper.{helper_id}.standard",
                )
                if not all(
                    isinstance(standard[field], str) and standard[field]
                    for field in ("authority_id", "title", "edition", "uri")
                ) or not str(standard["uri"]).startswith(
                    "https://www.rfc-editor.org/rfc/"
                ):
                    raise StandardLibraryContractError(
                        f"audit.helper.standard_identity: malformed for {helper_id}"
                    )
                self._non_empty_strings(
                    standard["provisions"],
                    f"audit.helper.{helper_id}.standard.provisions",
                )
            scope_detail = (
                "inspired_elements"
                if standards["scope"] == "inspired"
                else "included_provisions"
            )
            self._non_empty_strings(
                standards[scope_detail],
                f"audit.helper.{helper_id}.standards.{scope_detail}",
            )
            if standards["scope"] == "subset":
                self._non_empty_strings(
                    standards["excluded_provisions"],
                    f"audit.helper.{helper_id}.standards.excluded_provisions",
                )

            variants = item["variants"]
            if not isinstance(variants, list) or not variants:
                raise StandardLibraryContractError(
                    f"audit.helper.variants: missing for {helper_id}"
                )
            for variant in variants:
                variant_item = self._closed_object(
                    variant,
                    {"variant_id", "selector", "fixture_group"},
                    f"audit.helper.{helper_id}.variant",
                )
                variant_id = str(variant_item["variant_id"])
                group_id = str(variant_item["fixture_group"])
                if variant_id in variant_groups or not all(
                    isinstance(variant_item[field], str) and variant_item[field]
                    for field in ("variant_id", "selector", "fixture_group")
                ):
                    raise StandardLibraryContractError(
                        f"audit.variant.identity: duplicate or malformed {variant_id}"
                    )
                variant_groups[group_id] = (helper_id, str(variant_item["selector"]))

        if helper_ids != sorted(set(helper_ids)):
            raise StandardLibraryContractError(
                "audit.helper.order: helper IDs must be unique and sorted"
            )
        registry = load_json(ROOT / "spec" / "stdlib" / "registry.json")
        essential = load_json(ROOT / "spec" / "stdlib" / "essential_5.json")
        expected_registry_names = {str(item["name"]) for item in registry["patterns"]}
        if set(registry_names) != expected_registry_names or set(registry_names) != set(
            essential["patterns"]
        ):
            raise StandardLibraryContractError(
                "audit.helper.coverage: audit must cover every current helper"
            )
        audit_by_name = {str(item["registry_name"]): item for item in helpers}
        for registry_entry in registry["patterns"]:
            name = str(registry_entry["name"])
            scope = str(audit_by_name[name]["standards"]["scope"])
            scope_prefix = "Subset:" if scope == "subset" else "Lexical inspiration:"
            if not str(registry_entry["rfc"]).startswith(scope_prefix):
                raise StandardLibraryContractError(
                    f"audit.public_claim.registry_scope: {name} lacks {scope_prefix}"
                )
            documentation = str(registry_entry["documentation"])
            if "does not" not in documentation and "do not" not in documentation:
                raise StandardLibraryContractError(
                    f"audit.public_claim.registry_nonclaim: {name} lacks explicit non-claims"
                )
            essential_entry = essential["patterns"][name]
            if not str(essential_entry["rfc"]).startswith(scope_prefix):
                raise StandardLibraryContractError(
                    f"audit.public_claim.essential_scope: {name} lacks {scope_prefix}"
                )
        intelligence_source = (
            ROOT / "tooling" / "lsp-server" / "server" / "canonical_intelligence.py"
        ).read_text(encoding="utf-8")
        if (
            'helper["documentation"]["summary"]' not in intelligence_source
            or "STDLIB_REGISTRY_PATH" not in intelligence_source
        ):
            raise StandardLibraryContractError(
                "audit.public_claim.language_intelligence: editor helper text must derive from the canonical registry"
            )
        if audit["variant_count"] != len(variant_groups) or len(variant_groups) != 8:
            raise StandardLibraryContractError("audit.variant.count: expected 8")

        variant_patterns = {
            "date_time.default": str(essential["patterns"]["dateTime"]["regex"]),
            "email.default": str(essential["patterns"]["email"]["regex"]),
            "ip.v4": str(essential["patterns"]["ip"]["regex_v4"]),
            "ip.v6_full": str(essential["patterns"]["ip"]["regex_v6"]),
            "ip.either": str(essential["patterns"]["ip"]["regex_default"]),
            "url.default": str(essential["patterns"]["url"]["regex"]),
            "uuid.generic": str(essential["patterns"]["uuid"]["regex_default"]),
            "uuid.v4": str(essential["patterns"]["uuid"]["regex_v4"]),
        }
        if set(variant_patterns) != set(variant_groups):
            raise StandardLibraryContractError(
                "audit.variant.pattern_coverage: every variant needs observed regex evidence"
            )

        self._closed_object(
            fixtures,
            {"kind", "fixture_version", "groups"},
            "audit.fixtures",
        )
        if fixtures["kind"] != "strling.stdlib-guarantee-audit-fixtures":
            raise StandardLibraryContractError("audit.fixtures.kind: unexpected kind")
        if fixtures["fixture_version"] != "1.0.0":
            raise StandardLibraryContractError(
                "audit.fixtures.version: unsupported version"
            )
        groups = fixtures["groups"]
        if not isinstance(groups, list):
            raise StandardLibraryContractError("audit.fixtures.groups: expected array")
        seen_groups: set[str] = set()
        seen_cases: set[str] = set()
        helper_classifications: dict[str, set[str]] = {
            helper_id: set() for helper_id in helper_ids
        }
        case_count = 0
        for group in groups:
            group_item = self._closed_object(
                group,
                {"group_id", "helper_id", "selector", "cases"},
                "audit.fixture_group",
            )
            group_id = str(group_item["group_id"])
            if group_id in seen_groups or group_id not in variant_groups:
                raise StandardLibraryContractError(
                    f"audit.fixture_group.identity: unknown or duplicate {group_id}"
                )
            seen_groups.add(group_id)
            if variant_groups[group_id] != (
                str(group_item["helper_id"]),
                str(group_item["selector"]),
            ):
                raise StandardLibraryContractError(
                    f"audit.fixture_group.correspondence: mismatch for {group_id}"
                )
            cases = group_item["cases"]
            if not isinstance(cases, list) or not cases:
                raise StandardLibraryContractError(
                    f"audit.fixture_group.cases: missing for {group_id}"
                )
            outcomes: set[bool] = set()
            for case in cases:
                case_item = self._closed_object(
                    case,
                    {
                        "case_id",
                        "input",
                        "expected_match",
                        "classification",
                        "rationale",
                    },
                    f"audit.fixture.{group_id}",
                )
                case_id = str(case_item["case_id"])
                if case_id in seen_cases:
                    raise StandardLibraryContractError(
                        f"audit.fixture.identity: duplicate {case_id}"
                    )
                seen_cases.add(case_id)
                expected_match = case_item["expected_match"]
                if not isinstance(case_item["input"], str) or (
                    expected_match is not None and not isinstance(expected_match, bool)
                ):
                    raise StandardLibraryContractError(
                        f"audit.fixture.value: malformed {case_id}"
                    )
                if case_item["classification"] not in {
                    "accepted_shape",
                    "rejected_shape",
                    "known_semantic_false_positive",
                    "known_standard_false_negative",
                    "policy_nonclaim",
                    "target_dependent",
                }:
                    raise StandardLibraryContractError(
                        f"audit.fixture.classification: malformed {case_id}"
                    )
                if (
                    not isinstance(case_item["rationale"], str)
                    or not case_item["rationale"]
                ):
                    raise StandardLibraryContractError(
                        f"audit.fixture.rationale: missing {case_id}"
                    )
                if case_item["classification"] == "target_dependent":
                    if expected_match is not None:
                        raise StandardLibraryContractError(
                            f"audit.fixture.target_dependent: {case_id} needs a null outcome"
                        )
                else:
                    if expected_match is None:
                        raise StandardLibraryContractError(
                            f"audit.fixture.outcome: {case_id} needs a boolean outcome"
                        )
                    observed_match = (
                        re.fullmatch(
                            variant_patterns[group_id],
                            str(case_item["input"]),
                            flags=re.ASCII,
                        )
                        is not None
                    )
                    if observed_match != expected_match:
                        raise StandardLibraryContractError(
                            f"audit.fixture.observed_behavior: {case_id} disagrees with the compatibility manifest"
                        )
                    outcomes.add(expected_match)
                helper_classifications[str(group_item["helper_id"])].add(
                    str(case_item["classification"])
                )
                case_count += 1
            if outcomes != {False, True}:
                raise StandardLibraryContractError(
                    f"audit.fixture_group.outcomes: {group_id} needs acceptance and rejection"
                )
        if seen_groups != set(variant_groups):
            raise StandardLibraryContractError(
                "audit.fixture_group.coverage: every variant needs one group"
            )
        for helper_id, classifications in helper_classifications.items():
            if (
                not classifications.intersection(
                    {"known_semantic_false_positive", "policy_nonclaim"}
                )
                or "known_standard_false_negative" not in classifications
            ):
                raise StandardLibraryContractError(
                    f"audit.fixture.claim_boundary: incomplete for {helper_id}"
                )
            if (
                helper_text_models[helper_id]
                == "ascii_literals_with_target_digit_class"
                and "target_dependent" not in classifications
            ):
                raise StandardLibraryContractError(
                    f"audit.fixture.target_dependency: missing for {helper_id}"
                )
        return len(helpers), len(variant_groups), case_count

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
        self.validate_audit(
            load_json(STDLIB_GUARANTEE_AUDIT),
            load_json(STDLIB_GUARANTEE_AUDIT_FIXTURES),
        )
        return count + 3

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
            STDLIB_GUARANTEE_AUDIT,
            STDLIB_GUARANTEE_AUDIT_FIXTURES,
        ]
        digest = hashlib.sha256()
        for path in documents:
            digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(canonical_json(load_json(path)))
            digest.update(b"\n")
        return digest.hexdigest()
