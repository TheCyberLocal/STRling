#!/usr/bin/env python3
"""Validate and project the canonical STRling standard-library registry."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = ROOT / "spec" / "stdlib" / "registry" / "1.0"
REGISTRY_PATH = REGISTRY_ROOT / "registry.json"
REGISTRY_SCHEMA_PATH = REGISTRY_ROOT / "stdlib-registry.schema.json"
INVALID_SCHEMA_PATH = REGISTRY_ROOT / "controlled-invalid-registry.schema.json"
INVALID_ROOT = REGISTRY_ROOT / "fixtures" / "invalid"
AUDIT_PATH = ROOT / "spec" / "stdlib" / "stdlib-guarantee-audit.json"
AUDIT_FIXTURES_PATH = ROOT / "spec" / "stdlib" / "stdlib-guarantee-audit-fixtures.json"
TRANSITION_PATH = ROOT / "spec" / "stdlib" / "validation-guarantee-transition.json"
ESSENTIAL_OUTPUT = ROOT / "spec" / "stdlib" / "essential_5.json"
LSP_OUTPUT = ROOT / "spec" / "stdlib" / "registry.json"


class StandardLibraryRegistryError(ValueError):
    """The canonical registry or one of its declared derivations is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path*."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StandardLibraryRegistryError(
            f"reference.unresolved: cannot read {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise StandardLibraryRegistryError(
            f"schema.invalid: {path} root must be an object"
        )
    return value


def canonical_json(value: Any) -> bytes:
    """Return the canonical bytes used for fingerprints and equality checks."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def serialized_json(value: Any, *, sort_keys: bool = False) -> str:
    """Return the checked-in deterministic JSON representation."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=4,
            sort_keys=sort_keys,
            allow_nan=False,
        )
        + "\n"
    )


def registry_fingerprint(registry: Mapping[str, Any]) -> str:
    """Hash registry content while excluding its self-describing fingerprint."""
    payload = copy.deepcopy(dict(registry))
    payload.pop("fingerprint", None)
    return "sha256:" + hashlib.sha256(canonical_json(payload)).hexdigest()


def _json_path(parts: Sequence[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _pointer_tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise StandardLibraryRegistryError(
            f"reference.unresolved: JSON pointer must start with '/': {pointer}"
        )
    return [
        token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")
    ]


def resolve_pointer(value: Any, pointer: str) -> Any:
    """Resolve one RFC 6901 pointer with fail-closed array handling."""
    current = value
    for token in _pointer_tokens(pointer):
        try:
            if isinstance(current, list):
                current = current[int(token)]
            elif isinstance(current, dict):
                current = current[token]
            else:
                raise KeyError(token)
        except (KeyError, IndexError, ValueError) as exc:
            raise StandardLibraryRegistryError(
                f"reference.unresolved: JSON pointer {pointer} does not resolve"
            ) from exc
    return current


def _set_pointer(value: Any, pointer: str, replacement: Any) -> None:
    tokens = _pointer_tokens(pointer)
    parent = value
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    final = tokens[-1]
    if isinstance(parent, list):
        parent[int(final)] = replacement
    else:
        parent[final] = replacement


def _remove_pointer(value: Any, pointer: str) -> None:
    tokens = _pointer_tokens(pointer)
    parent = value
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    final = tokens[-1]
    if isinstance(parent, list):
        del parent[int(final)]
    else:
        del parent[final]


def _unique(values: Sequence[str], rule: str) -> None:
    if len(values) != len(set(values)):
        raise StandardLibraryRegistryError(rule)


class StandardLibraryRegistrySuite:
    """Schema, graph, reference, audit, and projection certification."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.registry_path = root / REGISTRY_PATH.relative_to(ROOT)
        self.registry_schema_path = root / REGISTRY_SCHEMA_PATH.relative_to(ROOT)
        self.invalid_schema_path = root / INVALID_SCHEMA_PATH.relative_to(ROOT)
        self.invalid_root = root / INVALID_ROOT.relative_to(ROOT)
        self.audit_path = root / AUDIT_PATH.relative_to(ROOT)
        self.audit_fixtures_path = root / AUDIT_FIXTURES_PATH.relative_to(ROOT)
        self.transition_path = root / TRANSITION_PATH.relative_to(ROOT)
        self.essential_output = root / ESSENTIAL_OUTPUT.relative_to(ROOT)
        self.lsp_output = root / LSP_OUTPUT.relative_to(ROOT)

        self.registry_schema = load_json(self.registry_schema_path)
        self.invalid_schema = load_json(self.invalid_schema_path)
        try:
            Draft202012Validator.check_schema(self.registry_schema)
            Draft202012Validator.check_schema(self.invalid_schema)
        except SchemaError as exc:
            raise StandardLibraryRegistryError(
                f"schema.invalid: malformed registry schema: {exc.message}"
            ) from exc
        self.registry_validator = Draft202012Validator(
            self.registry_schema, format_checker=FormatChecker()
        )
        self.invalid_validator = Draft202012Validator(self.invalid_schema)

    def validate_suite_structure(self) -> int:
        """Validate the closed, versioned schema family."""
        expected = {
            "https://strling.dev/spec/stdlib/registry/1.0/stdlib-registry.schema.json",
            "https://strling.dev/spec/stdlib/registry/1.0/controlled-invalid-registry.schema.json",
        }
        actual = {self.registry_schema["$id"], self.invalid_schema["$id"]}
        if actual != expected:
            raise StandardLibraryRegistryError(
                "schema.family.closed: unexpected registry schema identity"
            )
        if self.registry_schema.get("additionalProperties") is not False:
            raise StandardLibraryRegistryError(
                "schema.root.closed: registry root must reject unknown properties"
            )
        return len(actual)

    def _preflight_required_evidence(self, registry: Mapping[str, Any]) -> None:
        helpers = registry.get("helpers")
        if not isinstance(helpers, list):
            return
        for helper in helpers:
            if not isinstance(helper, Mapping):
                continue
            if not helper.get("examples") or not helper.get("counterexamples"):
                raise StandardLibraryRegistryError(
                    "helper.examples.required: every helper needs accepted and rejected examples"
                )
            if not helper.get("evidence"):
                raise StandardLibraryRegistryError(
                    "helper.evidence.required: every helper needs evidence references"
                )

    def _schema_validate(self, registry: Mapping[str, Any]) -> None:
        errors = sorted(
            self.registry_validator.iter_errors(registry),
            key=lambda error: list(error.path),
        )
        if errors:
            error = errors[0]
            raise StandardLibraryRegistryError(
                f"schema.invalid: {_json_path(list(error.path))}: {error.message}"
            )

    def _resolve_repository_reference(self, reference: str) -> Any:
        path_text, separator, fragment = reference.partition("#")
        path = (self.root / path_text).resolve()
        try:
            path.relative_to(self.root.resolve())
        except ValueError as exc:
            raise StandardLibraryRegistryError(
                f"reference.unresolved: reference escapes repository: {reference}"
            ) from exc
        if not path.is_file():
            raise StandardLibraryRegistryError(
                f"reference.unresolved: missing repository file: {reference}"
            )
        if not separator:
            return path
        if path.suffix != ".json":
            raise StandardLibraryRegistryError(
                f"reference.unresolved: fragment requires JSON source: {reference}"
            )
        return resolve_pointer(load_json(path), fragment)

    def _validate_references(self, registry: Mapping[str, Any]) -> None:
        self._resolve_repository_reference(str(registry["audit_reference"]))
        self._resolve_repository_reference(str(registry["taxonomy_reference"]))
        target_catalog = registry["target_catalog"]
        assert isinstance(target_catalog, Mapping)
        for profile in target_catalog["profiles"]:
            self._resolve_repository_reference(str(profile["reference"]))
        for helper in registry["helpers"]:
            for evidence in helper["evidence"]:
                self._resolve_repository_reference(str(evidence["reference"]))
        for binding in registry["host_bindings"]:
            for reference in binding["implementation_references"]:
                self._resolve_repository_reference(str(reference))
            self._resolve_repository_reference(str(binding["test_reference"]))

    def _validate_helper_identity(self, registry: Mapping[str, Any]) -> None:
        helpers = registry["helpers"]
        helper_ids = [str(helper["id"]) for helper in helpers]
        _unique(helper_ids, "helper.id.unique: helper IDs must be unique")
        for field in ("canonical", "registry", "simply"):
            names = [str(helper["names"][field]) for helper in helpers]
            _unique(
                names,
                f"helper.name.unique: {field} helper names must be unique",
            )
        for helper in helpers:
            expected = f"registry://{helper['id']}"
            if helper["semantic_definition"]["construction_identity"] != expected:
                raise StandardLibraryRegistryError(
                    "helper.construction.identity: construction identity must match helper ID"
                )

    def _validate_target_catalog(self, registry: Mapping[str, Any]) -> None:
        catalog = registry["target_catalog"]
        profiles = [str(profile["profile_id"]) for profile in catalog["profiles"]]
        constraints = [
            str(constraint["constraint_id"]) for constraint in catalog["constraints"]
        ]
        _unique(profiles, "target.profile.unique: target profiles must be unique")
        _unique(
            constraints,
            "target.constraint.unique: target constraints must be unique",
        )
        profile_ids = set(profiles)
        constraint_ids = set(constraints)
        for helper in registry["helpers"]:
            unknown_profiles = set(helper["targeting"]["profiles"]) - profile_ids
            if unknown_profiles:
                raise StandardLibraryRegistryError(
                    "target.profile.supported: helper references unsupported target profile"
                )
            unknown_constraints = (
                set(helper["targeting"]["constraint_ids"]) - constraint_ids
            )
            if unknown_constraints:
                raise StandardLibraryRegistryError(
                    "target.constraint.supported: helper references unsupported target constraint"
                )

    def _validate_derivations(self, registry: Mapping[str, Any]) -> None:
        derivations = registry["derivations"]
        ids = [str(item["derivation_id"]) for item in derivations]
        _unique(ids, "derivation.id.unique: derivation IDs must be unique")
        by_id = {str(item["derivation_id"]): item for item in derivations}
        for item in derivations:
            for dependency in item["depends_on"]:
                if dependency not in by_id:
                    raise StandardLibraryRegistryError(
                        "derivation.reference.unresolved: missing derivation dependency"
                    )
        outputs = [str(output) for item in derivations for output in item["outputs"]]
        _unique(
            outputs,
            "derivation.output.ambiguous: one output cannot have multiple derivations",
        )

        state: dict[str, int] = {}

        def visit(derivation_id: str) -> None:
            marker = state.get(derivation_id, 0)
            if marker == 1:
                raise StandardLibraryRegistryError(
                    "derivation.cycle: derivation graph must be acyclic"
                )
            if marker == 2:
                return
            state[derivation_id] = 1
            for dependency in by_id[derivation_id]["depends_on"]:
                visit(str(dependency))
            state[derivation_id] = 2

        for derivation_id in ids:
            visit(derivation_id)

        canonical = by_id.get("canonical.registry")
        if canonical is None or canonical["kind"] != "authored_source":
            raise StandardLibraryRegistryError(
                "derivation.authority: canonical.registry must be the authored source"
            )
        if canonical["depends_on"] or canonical["normative"] is not True:
            raise StandardLibraryRegistryError(
                "derivation.authority: canonical registry must be independent and normative"
            )
        for helper in registry["helpers"]:
            derivation_id = str(helper["semantic_definition"]["derivation_id"])
            if derivation_id != "canonical.registry":
                raise StandardLibraryRegistryError(
                    "derivation.helper.authority: helper definitions must derive from canonical.registry"
                )

    def _validate_host_bindings(self, registry: Mapping[str, Any]) -> None:
        helper_ids = {str(helper["id"]) for helper in registry["helpers"]}
        binding_ids = [
            str(binding["binding_id"]) for binding in registry["host_bindings"]
        ]
        _unique(binding_ids, "binding.id.unique: binding IDs must be unique")
        for binding in registry["host_bindings"]:
            exposures = binding["exposures"]
            exposure_ids = [str(exposure["helper_id"]) for exposure in exposures]
            _unique(
                exposure_ids,
                "binding.helper.unique: a binding cannot expose a helper twice",
            )
            if set(exposure_ids) != helper_ids:
                raise StandardLibraryRegistryError(
                    "binding.helper.complete: every binding must map every registry helper"
                )
            public_names = [
                str(name) for exposure in exposures for name in exposure["public_names"]
            ]
            _unique(
                public_names,
                "binding.name.unique: public names must be unambiguous within a binding",
            )

    def _validate_examples(self, registry: Mapping[str, Any]) -> None:
        case_ids: list[str] = []
        for helper in registry["helpers"]:
            variants = helper["semantic_definition"]["variants"]
            variant_ids = [str(variant["variant_id"]) for variant in variants]
            fixture_groups = [str(variant["fixture_group"]) for variant in variants]
            _unique(
                variant_ids,
                "helper.variant.unique: variant IDs must be unique within a helper",
            )
            _unique(
                fixture_groups,
                "helper.fixture-group.unique: fixture groups must be unique within a helper",
            )
            known_groups = set(fixture_groups)
            for field, expected in (
                ("examples", True),
                ("counterexamples", False),
                ("target_dependent_examples", None),
            ):
                for example in helper[field]:
                    case_ids.append(str(example["case_id"]))
                    if example["expected_match"] is not expected:
                        raise StandardLibraryRegistryError(
                            "helper.example.outcome: example collection contradicts expected_match"
                        )
                    if example["fixture_group"] not in known_groups:
                        raise StandardLibraryRegistryError(
                            "helper.example.variant: example references unknown fixture group"
                        )
        _unique(case_ids, "helper.example.id.unique: example IDs must be unique")

    def _validate_audit_reconciliation(self, registry: Mapping[str, Any]) -> None:
        audit = load_json(self.audit_path)
        fixtures = load_json(self.audit_fixtures_path)
        transition = load_json(self.transition_path)
        audit_helpers = {item["helper_id"]: item for item in audit["helpers"]}
        registry_helpers = {item["id"]: item for item in registry["helpers"]}
        if set(registry_helpers) != set(audit_helpers):
            raise StandardLibraryRegistryError(
                "audit.helper.complete: registry helper set must equal ratified audit"
            )
        groups = {item["group_id"]: item for item in fixtures["groups"]}
        transition_ids = {item["helper_id"] for item in transition["entries"]}
        if set(registry_helpers) != transition_ids:
            raise StandardLibraryRegistryError(
                "audit.transition.complete: registry must cover every audited transition"
            )

        for helper_id, helper in registry_helpers.items():
            audited = audit_helpers[helper_id]
            expected_guarantee = {
                "accepts": audited["accepts"],
                "level": audited["guarantee_level"],
                "match_scope": audited["match_scope"],
                "non_guarantees": audited["does_not_claim"],
                "normalizes": audited["normalizes"],
                "rejects": audited["rejects"],
                "standards": audited["standards"],
                "text_model": audited["text_model"],
            }
            if canonical_json(helper["guarantee"]) != canonical_json(
                expected_guarantee
            ):
                raise StandardLibraryRegistryError(
                    "audit.guarantee.correspondence: registry guarantee differs from audit"
                )
            if helper["names"]["registry"] != audited["registry_name"]:
                raise StandardLibraryRegistryError(
                    "audit.name.correspondence: registry name differs from audit"
                )
            if (
                helper["targeting"]["text_assumptions"]
                != audited["target_dependencies"]
            ):
                raise StandardLibraryRegistryError(
                    "audit.target.correspondence: target assumptions differ from audit"
                )
            expected_migration = {"aliases": [], **audited["compatibility"]}
            if canonical_json(helper["migration"]) != canonical_json(
                expected_migration
            ):
                raise StandardLibraryRegistryError(
                    "audit.migration.correspondence: migration differs from audit"
                )
            actual_variants = [
                {
                    "fixture_group": variant["fixture_group"],
                    "selector": variant["selector"],
                    "variant_id": variant["variant_id"],
                }
                for variant in helper["semantic_definition"]["variants"]
            ]
            expected_variants = [
                {
                    "fixture_group": variant["fixture_group"],
                    "selector": variant["selector"],
                    "variant_id": variant["variant_id"],
                }
                for variant in audited["variants"]
            ]
            if canonical_json(actual_variants) != canonical_json(expected_variants):
                raise StandardLibraryRegistryError(
                    "audit.variant.correspondence: registry variants differ from audit"
                )
            actual_cases = {
                item["case_id"]: {
                    key: value for key, value in item.items() if key != "fixture_group"
                }
                for field in (
                    "examples",
                    "counterexamples",
                    "target_dependent_examples",
                )
                for item in helper[field]
            }
            expected_cases = {
                item["case_id"]: item
                for variant in audited["variants"]
                for item in groups[variant["fixture_group"]]["cases"]
            }
            if canonical_json(actual_cases) != canonical_json(expected_cases):
                raise StandardLibraryRegistryError(
                    "audit.example.correspondence: registry examples differ from edge corpus"
                )

        audit_bindings = {item["binding_id"]: item for item in audit["bindings"]}
        registry_bindings = {
            item["binding_id"]: item for item in registry["host_bindings"]
        }
        if set(audit_bindings) != set(registry_bindings):
            raise StandardLibraryRegistryError(
                "audit.binding.complete: registry binding set must equal ratified audit"
            )
        for binding_id, binding in registry_bindings.items():
            audited = audit_bindings[binding_id]
            if (
                binding["implementation_references"]
                != audited["implementation_references"]
            ):
                raise StandardLibraryRegistryError(
                    "audit.binding.implementation: binding implementation evidence differs"
                )
            if binding["test_reference"] != audited["test_reference"]:
                raise StandardLibraryRegistryError(
                    "audit.binding.test: binding test evidence differs"
                )
            exposure_map = {
                exposure["helper_id"].removeprefix("stdlib."): exposure["public_names"]
                for exposure in binding["exposures"]
            }
            audited_names = {
                name: sorted(public_names)
                for name, public_names in audited["public_names"].items()
            }
            if canonical_json(exposure_map) != canonical_json(audited_names):
                raise StandardLibraryRegistryError(
                    "audit.binding.name: host-language spelling differs from audit"
                )

    def _validate_fingerprint(self, registry: Mapping[str, Any]) -> None:
        expected = registry_fingerprint(registry)
        if registry["fingerprint"]["value"] != expected:
            raise StandardLibraryRegistryError(
                "fingerprint.mismatch: registry fingerprint is stale"
            )

    def validate_registry(
        self,
        registry: Mapping[str, Any],
        *,
        reconcile_audit: bool = True,
    ) -> tuple[int, int, int, int]:
        """Validate one registry and return helper, variant, binding, case counts."""
        self._preflight_required_evidence(registry)
        self._schema_validate(registry)
        self._validate_helper_identity(registry)
        self._validate_target_catalog(registry)
        self._validate_derivations(registry)
        self._validate_host_bindings(registry)
        self._validate_examples(registry)
        self._validate_references(registry)
        if reconcile_audit:
            self._validate_audit_reconciliation(registry)
        self._validate_fingerprint(registry)
        helpers = registry["helpers"]
        return (
            len(helpers),
            sum(len(helper["semantic_definition"]["variants"]) for helper in helpers),
            len(registry["host_bindings"]),
            sum(
                len(helper[field])
                for helper in helpers
                for field in (
                    "examples",
                    "counterexamples",
                    "target_dependent_examples",
                )
            ),
        )

    def validate_canonical_file(self) -> tuple[int, int, int, int]:
        """Validate content plus canonical checked-in serialization."""
        registry = load_json(self.registry_path)
        counts = self.validate_registry(registry)
        expected = serialized_json(registry, sort_keys=True)
        if self.registry_path.read_text(encoding="utf-8") != expected:
            raise StandardLibraryRegistryError(
                "serialization.nondeterministic: canonical registry is not sorted deterministic JSON"
            )
        return counts

    def materialize_invalid_case(self, case: Mapping[str, Any]) -> dict[str, Any]:
        """Apply one controlled mutation without altering the base registry."""
        errors = sorted(
            self.invalid_validator.iter_errors(case), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise StandardLibraryRegistryError(
                f"fixture.schema.invalid: {_json_path(list(error.path))}: {error.message}"
            )
        registry = load_json(self.root / str(case["registry_reference"]))
        for operation in case["operations"]:
            op = operation["op"]
            path = str(operation["path"])
            if op == "replace":
                _set_pointer(registry, path, copy.deepcopy(operation["value"]))
            elif op == "remove":
                _remove_pointer(registry, path)
            else:
                copied = copy.deepcopy(
                    resolve_pointer(registry, str(operation["from"]))
                )
                _set_pointer(registry, path, copied)
        return registry

    def validate_negative_fixtures(self) -> int:
        """Prove every controlled invalid registry fails for its declared rule."""
        count = 0
        for path in sorted(self.invalid_root.glob("*.json")):
            case = load_json(path)
            first = self.materialize_invalid_case(case)
            second = self.materialize_invalid_case(case)
            if canonical_json(first) != canonical_json(second):
                raise StandardLibraryRegistryError(
                    "fixture.nondeterministic: controlled mutation changed between runs"
                )
            try:
                self.validate_registry(first)
            except StandardLibraryRegistryError as exc:
                expected_rule = str(case["expected_rule"])
                if not str(exc).startswith(expected_rule + ":"):
                    raise StandardLibraryRegistryError(
                        f"fixture.wrong-rule: {path.name} expected {expected_rule}, got {exc}"
                    ) from exc
                count += 1
                continue
            raise StandardLibraryRegistryError(
                f"fixture.unexpected-pass: controlled invalid case passed: {path.name}"
            )
        return count

    @staticmethod
    def _helper_map(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        return {str(helper["id"]): helper for helper in registry["helpers"]}

    def project_essential(self, registry: Mapping[str, Any]) -> dict[str, Any]:
        """Build the legacy Essential-5 compatibility shape."""
        projection = registry["compatibility_projections"]["essential_5"]
        helpers = self._helper_map(registry)
        patterns: dict[str, Any] = {}
        for helper_id in projection["helper_order"]:
            helper = helpers[helper_id]
            docs = helper["documentation"]
            variants = helper["semantic_definition"]["variants"]
            item: dict[str, Any] = {
                "name": helper["names"]["registry"],
                "summary": docs["compatibility_summary"],
                "rfc": docs["compatibility_reference_label"],
            }
            if len(variants) == 1:
                item["regex"] = variants[0]["regex"]
                if variants[0]["semantic_ir"] is not None:
                    item["ast"] = variants[0]["semantic_ir"]
            elif helper_id == "stdlib.uuid":
                by_id = {variant["variant_id"]: variant for variant in variants}
                item["regex_default"] = by_id["uuid.generic"]["regex"]
                item["regex_v4"] = by_id["uuid.v4"]["regex"]
            elif helper_id == "stdlib.ip":
                by_id = {variant["variant_id"]: variant for variant in variants}
                item["regex_v4"] = by_id["ip.v4"]["regex"]
                item["regex_v6"] = by_id["ip.v6_full"]["regex"]
                item["regex_default"] = by_id["ip.either"]["regex"]
            else:
                raise StandardLibraryRegistryError(
                    f"projection.essential.unsupported: no projection rule for {helper_id}"
                )
            item.update(copy.deepcopy(docs["compatibility_extras"]))
            item["fixtures"] = copy.deepcopy(
                helper["semantic_definition"]["compatibility_fixtures"]
            )
            patterns[helper["names"]["registry"]] = item
        return {
            "title": projection["title"],
            "description": projection["description"],
            "naming_conventions": copy.deepcopy(projection["naming_conventions"]),
            "patterns": patterns,
        }

    def project_lsp(self, registry: Mapping[str, Any]) -> dict[str, Any]:
        """Build the legacy flat editor-registry compatibility shape."""
        projection = registry["compatibility_projections"]["lsp_registry"]
        helpers = self._helper_map(registry)
        registry_helpers = registry["helpers"]
        helper_indices = {
            helper["id"]: index for index, helper in enumerate(registry_helpers)
        }
        patterns = []
        for helper_id in projection["helper_order"]:
            helper = helpers[helper_id]
            docs = helper["documentation"]
            variants = helper["semantic_definition"]["variants"]
            preferred = next(
                (
                    (index, variant)
                    for index, variant in enumerate(variants)
                    if variant["selector"] in {"default", "default_or_other"}
                ),
                (0, variants[0]),
            )
            variant_index, variant = preferred
            helper_index = helper_indices[helper_id]
            patterns.append(
                {
                    "name": helper["names"]["registry"],
                    "summary": docs["summary"],
                    "documentation": docs["description"],
                    "rfc": docs["reference_label"],
                    "rfc_url": docs["reference_url"],
                    "regex": variant["regex"],
                    "ast_ref": (
                        "spec/stdlib/registry/1.0/registry.json"
                        f"#/helpers/{helper_index}/semantic_definition/variants/{variant_index}"
                    ),
                    "snippet": docs["snippet"],
                    "trigger_keywords": docs["trigger_keywords"],
                }
            )
        return {
            "title": projection["title"],
            "description": projection["description"],
            "version": projection["version"],
            "patterns": patterns,
        }

    def projections(self, registry: Mapping[str, Any]) -> dict[Path, dict[str, Any]]:
        """Return every checked-in non-normative projection."""
        return {
            self.essential_output: self.project_essential(registry),
            self.lsp_output: self.project_lsp(registry),
        }

    def write_projections(self) -> tuple[int, int, int, int]:
        """Validate the canonical source and deterministically write projections."""
        registry = load_json(self.registry_path)
        counts = self.validate_registry(registry)
        for path, value in self.projections(registry).items():
            path.write_text(serialized_json(value), encoding="utf-8")
        return counts

    def check_projections(self) -> tuple[int, int, int, int]:
        """Validate the canonical source and reject any projection drift."""
        counts = self.validate_canonical_file()
        registry = load_json(self.registry_path)
        for path, value in self.projections(registry).items():
            expected = serialized_json(value)
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                raise StandardLibraryRegistryError(
                    f"projection.drift: regenerate {path.relative_to(self.root)}"
                )
        return counts

    def certify(self) -> dict[str, Any]:
        """Run the complete canonical contract, including controlled negatives."""
        schema_count = self.validate_suite_structure()
        helper_count, variant_count, binding_count, case_count = (
            self.validate_canonical_file()
        )
        negative_count = self.validate_negative_fixtures()
        self.check_projections()
        registry = load_json(self.registry_path)
        return {
            "binding_count": binding_count,
            "case_count": case_count,
            "fingerprint": registry["fingerprint"]["value"],
            "helper_count": helper_count,
            "negative_count": negative_count,
            "schema_count": schema_count,
            "variant_count": variant_count,
        }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate without writing")
    mode.add_argument(
        "--write", action="store_true", help="write compatibility projections"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run deterministic write or non-mutating check mode."""
    args = _parse_args(argv)
    suite = StandardLibraryRegistrySuite()
    try:
        if args.write:
            counts = suite.write_projections()
            mode = "write"
        else:
            counts = suite.check_projections()
            suite.validate_negative_fixtures()
            mode = "check"
    except StandardLibraryRegistryError as exc:
        print(f"STDLIB_REGISTRY status=failed error={exc}", file=sys.stderr)
        return 1
    helper_count, variant_count, binding_count, case_count = counts
    registry = load_json(suite.registry_path)
    print(
        "STDLIB_REGISTRY status=passed "
        f"mode={mode} helpers={helper_count} variants={variant_count} "
        f"bindings={binding_count} cases={case_count} "
        f"fingerprint={registry['fingerprint']['value']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
