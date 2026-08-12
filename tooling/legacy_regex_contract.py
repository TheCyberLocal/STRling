#!/usr/bin/env python3
"""Certify the versioned regex-compatible source-dialect contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
DIALECT_ROOT = ROOT / "spec" / "frontends" / "legacy-regex" / "1.0"

EXPECTED_FILES = (
    "case.schema.json",
    "dialect.json",
    "dialect.schema.json",
    "fixtures/negative.json",
    "fixtures/positive.json",
    "grammar.ebnf",
)


class LegacyRegexContractError(ValueError):
    """The regex-compatible frontend contract is malformed or incomplete."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LegacyRegexContractError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise LegacyRegexContractError(f"{path}: root must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def utf8_boundaries(text: str) -> set[int]:
    boundaries = {0}
    current = 0
    for scalar in text:
        current += len(scalar.encode("utf-8"))
        boundaries.add(current)
    return boundaries


class LegacyRegexContractSuite:
    """Load and certify one complete frontend contract directory."""

    def __init__(self, dialect_root: Path = DIALECT_ROOT) -> None:
        self.dialect_root = dialect_root
        self.schemas = {
            name: load_json(dialect_root / name)
            for name in ("dialect.schema.json", "case.schema.json")
        }
        for schema in self.schemas.values():
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as error:
                raise LegacyRegexContractError(
                    f"invalid JSON Schema {schema.get('$id', '<unknown>')}: {error}"
                ) from error
        store = {schema["$id"]: schema for schema in self.schemas.values()}
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }
        self.dialect = load_json(dialect_root / "dialect.json")
        self.positive = load_json(dialect_root / "fixtures" / "positive.json")
        self.negative = load_json(dialect_root / "fixtures" / "negative.json")
        self.manifest = load_json(dialect_root / "fixtures" / "manifest.json")
        try:
            self.grammar = (dialect_root / "grammar.ebnf").read_text(encoding="utf-8")
        except OSError as error:
            raise LegacyRegexContractError(
                f"cannot read {dialect_root / 'grammar.ebnf'}: {error}"
            ) from error

    def _validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators[schema_name].iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            error = errors[0]
            raise LegacyRegexContractError(
                f"{schema_name} {_json_path(error.absolute_path)}: {error.message}"
            )

    @staticmethod
    def _require_sorted_unique(values: list[str], location: str) -> None:
        if values != sorted(values) or len(values) != len(set(values)):
            raise LegacyRegexContractError(
                f"{location} must be sorted and contain unique identities"
            )

    def _validate_contract(self) -> tuple[dict[str, dict[str, Any]], set[str]]:
        self._validate("dialect.schema.json", self.dialect)
        if self.dialect["authority"] != {
            "syntax_authority": True,
            "semantic_authority": False,
            "target_authority": False,
            "lowering_destination": "semantic-ir",
        }:
            raise LegacyRegexContractError(
                "frontend authority must remain syntax-only and lower to Semantic IR"
            )
        if self.dialect["source_model"]["target_assumption"] != "none":
            raise LegacyRegexContractError(
                "the source dialect cannot infer or select a target"
            )

        feature_ids = [entry["id"] for entry in self.dialect["features"]]
        diagnostic_ids = [entry["id"] for entry in self.dialect["diagnostics"]]
        self._require_sorted_unique(feature_ids, "dialect.features")
        self._require_sorted_unique(diagnostic_ids, "dialect.diagnostics")
        features = {entry["id"]: entry for entry in self.dialect["features"]}
        diagnostics = {entry["id"] for entry in self.dialect["diagnostics"]}
        for feature in features.values():
            if feature["status"] == "rejected":
                if feature["diagnostic_id"] not in diagnostics:
                    raise LegacyRegexContractError(
                        f"{feature['id']}: rejected feature has unknown diagnostic"
                    )
            elif "diagnostic_id" in feature:
                raise LegacyRegexContractError(
                    f"{feature['id']}: accepted feature cannot declare rejection"
                )

        grammar_rules = set(
            re.findall(r"^([A-Z][A-Za-z0-9]*)\s*=", self.grammar, re.MULTILINE)
        )
        if not grammar_rules:
            raise LegacyRegexContractError("grammar.ebnf contains no grammar rules")
        for feature in features.values():
            rule = feature.get("grammar_rule")
            if rule is not None and rule not in grammar_rules:
                raise LegacyRegexContractError(
                    f"{feature['id']}: missing grammar rule {rule}"
                )
        return features, diagnostics

    def _validate_fixtures(
        self,
        features: Mapping[str, Mapping[str, Any]],
        diagnostics: set[str],
    ) -> tuple[int, int]:
        self._validate("case.schema.json", self.positive)
        self._validate("case.schema.json", self.negative)
        if self.positive["kind"] != "positive" or self.negative["kind"] != "negative":
            raise LegacyRegexContractError("fixture documents have swapped kinds")

        all_case_ids: list[str] = []
        positive_coverage: set[str] = set()
        negative_feature_coverage: set[str] = set()
        negative_diagnostic_coverage: set[str] = set()
        flag_order = {
            flag: index for index, flag in enumerate(("i", "m", "s", "u", "x"))
        }

        for document in (self.positive, self.negative):
            case_ids = [case["id"] for case in document["cases"]]
            self._require_sorted_unique(case_ids, f"fixtures.{document['kind']}.cases")
            all_case_ids.extend(case_ids)
            for case in document["cases"]:
                feature_ids = case["feature_ids"]
                self._require_sorted_unique(feature_ids, f"{case['id']}.feature_ids")
                unknown = sorted(set(feature_ids) - set(features))
                if unknown:
                    raise LegacyRegexContractError(
                        f"{case['id']}: unknown feature identities {unknown}"
                    )
                expected = case["expected"]
                if document["kind"] == "positive":
                    rejected = [
                        identifier
                        for identifier in feature_ids
                        if features[identifier]["status"] == "rejected"
                    ]
                    if rejected:
                        raise LegacyRegexContractError(
                            f"{case['id']}: positive case covers rejected features {rejected}"
                        )
                    positive_coverage.update(feature_ids)
                    flags = expected.get("active_flags", [])
                    if flags != sorted(flags, key=flag_order.__getitem__):
                        raise LegacyRegexContractError(
                            f"{case['id']}: active flags are not in canonical order"
                        )
                else:
                    diagnostic = expected["diagnostic_id"]
                    if diagnostic not in diagnostics:
                        raise LegacyRegexContractError(
                            f"{case['id']}: unknown diagnostic {diagnostic}"
                        )
                    offset = expected["byte_offset"]
                    if offset not in utf8_boundaries(case["source"]):
                        raise LegacyRegexContractError(
                            f"{case['id']}: byte offset {offset} is not a UTF-8 boundary"
                        )
                    negative_feature_coverage.update(feature_ids)
                    negative_diagnostic_coverage.add(diagnostic)

        if len(all_case_ids) != len(set(all_case_ids)):
            raise LegacyRegexContractError(
                "fixture case identities must be global unique"
            )

        accepted_features = {
            identifier
            for identifier, feature in features.items()
            if feature["status"] != "rejected"
        }
        missing_positive = sorted(accepted_features - positive_coverage)
        if missing_positive:
            raise LegacyRegexContractError(
                f"accepted features lack positive fixtures: {missing_positive}"
            )
        rejected_features = {
            identifier
            for identifier, feature in features.items()
            if feature["status"] == "rejected"
        }
        missing_negative_features = sorted(
            rejected_features - negative_feature_coverage
        )
        if missing_negative_features:
            raise LegacyRegexContractError(
                f"rejected features lack negative fixtures: {missing_negative_features}"
            )
        required_diagnostics = {
            entry["id"]
            for entry in self.dialect["diagnostics"]
            if entry["fixture_required"]
        }
        missing_diagnostics = sorted(
            required_diagnostics - negative_diagnostic_coverage
        )
        if missing_diagnostics:
            raise LegacyRegexContractError(
                f"fixture-required diagnostics lack cases: {missing_diagnostics}"
            )
        return len(self.positive["cases"]), len(self.negative["cases"])

    def _validate_manifest(self, positive_count: int, negative_count: int) -> str:
        expected_keys = {
            "manifest_kind",
            "manifest_version",
            "contract_version",
            "authorship",
            "files",
            "case_counts",
        }
        if set(self.manifest) != expected_keys:
            raise LegacyRegexContractError("fixture manifest keys are invalid")
        if self.manifest["manifest_kind"] != "strling.regex-compatible-fixtures":
            raise LegacyRegexContractError("fixture manifest kind is invalid")
        for key in ("manifest_version", "contract_version"):
            if self.manifest[key] != "1.0.0":
                raise LegacyRegexContractError(f"fixture manifest {key} is invalid")
        if self.manifest["authorship"] != "specification-authored":
            raise LegacyRegexContractError(
                "fixture authorship must be specification-owned"
            )
        if self.manifest["case_counts"] != {
            "negative": negative_count,
            "positive": positive_count,
        }:
            raise LegacyRegexContractError("fixture manifest case counts are stale")

        entries = self.manifest["files"]
        if not isinstance(entries, list):
            raise LegacyRegexContractError("fixture manifest files must be an array")
        paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
        if paths != list(EXPECTED_FILES):
            raise LegacyRegexContractError(
                "fixture manifest paths must exactly cover governed contract inputs"
            )
        for entry in entries:
            if set(entry) != {"path", "sha256"}:
                raise LegacyRegexContractError(
                    f"manifest entry for {entry.get('path')} has invalid keys"
                )
            path = self.dialect_root / entry["path"]
            try:
                actual = sha256_bytes(path.read_bytes())
            except OSError as error:
                raise LegacyRegexContractError(
                    f"cannot fingerprint {entry['path']}: {error}"
                ) from error
            if entry["sha256"] != actual:
                raise LegacyRegexContractError(
                    f"fixture manifest fingerprint is stale for {entry['path']}"
                )
        certification = {
            "contract_version": self.dialect["contract_version"],
            "files": entries,
            "manifest": self.manifest,
        }
        return sha256_bytes(canonical_json(certification))

    def certify(self) -> dict[str, Any]:
        features, diagnostics = self._validate_contract()
        positive_count, negative_count = self._validate_fixtures(features, diagnostics)
        fingerprint = self._validate_manifest(positive_count, negative_count)
        statuses = {
            status: sum(feature["status"] == status for feature in features.values())
            for status in ("accepted", "compatibility-only", "rejected")
        }
        return {
            "contract_version": self.dialect["contract_version"],
            "schemas": len(self.schemas),
            "features": len(features),
            "feature_statuses": statuses,
            "diagnostics": len(diagnostics),
            "positive": positive_count,
            "negative": negative_count,
            "fingerprint": fingerprint,
        }


def main() -> int:
    try:
        result = LegacyRegexContractSuite().certify()
    except LegacyRegexContractError as error:
        print(f"LEGACY_REGEX_CONTRACT status=failed error={error}")
        return 1
    statuses = result["feature_statuses"]
    print(
        "LEGACY_REGEX_CONTRACT status=passed "
        f"version={result['contract_version']} schemas={result['schemas']} "
        f"features={result['features']} accepted={statuses['accepted']} "
        f"compatibility_only={statuses['compatibility-only']} "
        f"rejected={statuses['rejected']} diagnostics={result['diagnostics']} "
        f"positive={result['positive']} negative={result['negative']} "
        f"fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
