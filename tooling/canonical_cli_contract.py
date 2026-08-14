#!/usr/bin/env python3
"""Validate the versioned canonical CLI response and verification corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = ROOT / "spec" / "cli" / "1.0"
RESPONSE_SCHEMA_PATH = CLI_ROOT / "cli-response.schema.json"
MANIFEST_ROOT = ROOT / "tests" / "cli" / "1.0"
MANIFEST_SCHEMA_PATH = MANIFEST_ROOT / "manifest.schema.json"
MANIFEST_PATH = MANIFEST_ROOT / "manifest.json"

EXPECTED_COMMANDS = {
    "check",
    "compile",
    "explain",
    "import",
    "migrate",
    "simply",
    "target_inspect",
    "target_list",
}
EXPECTED_EXITS = {0, 2, 64, 69, 70, 74}
EXPECTED_COMPATIBILITY = {
    "compile_raw_request": "retained",
    "parse_strl_emit_pcre2": "retired",
    "parse_strl_positional_input": "mapped",
    "parse_strl_schema": "retired",
    "quality_check_alias": "retained",
    "simply_adapter": "retained",
}
EXPECTED_PROFILE_PATHS = {
    "spec/targets/profiles/ecmascript-2024.json",
    "spec/targets/profiles/pcre2-10.42.json",
    "spec/targets/profiles/pcre2-10.43.json",
    "spec/targets/profiles/python-re-3.11-bytes.json",
    "spec/targets/profiles/python-re-3.11.json",
}


class CanonicalCliContractError(ValueError):
    """The CLI schema or verification design is incomplete or inconsistent."""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise CanonicalCliContractError(f"{path}: root must be an object")
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _require_sorted_unique(values: Sequence[Any], label: str) -> None:
    keys = [_canonical_json(value) for value in values]
    if keys != sorted(set(keys)):
        raise CanonicalCliContractError(f"{label} must be unique and sorted")


def _schema_store() -> dict[str, dict[str, Any]]:
    paths = [
        *sorted((ROOT / "spec" / "contracts" / "1.0").glob("*.schema.json")),
        ROOT / "spec" / "explanations" / "semantic" / "1.0" / "explanation.schema.json",
        ROOT
        / "spec"
        / "explanations"
        / "no-match"
        / "1.0"
        / "no-match-explanation.schema.json",
        ROOT
        / "spec"
        / "conversions"
        / "semantic"
        / "1.0"
        / "conversion-result.schema.json",
        RESPONSE_SCHEMA_PATH,
    ]
    schemas = [_load_json(path) for path in paths]
    return {schema["$id"]: schema for schema in schemas}


class CanonicalCliContractSuite:
    """Closed schema, profile, command, mutation, and coverage validation."""

    def __init__(self) -> None:
        self.response_schema = _load_json(RESPONSE_SCHEMA_PATH)
        self.manifest_schema = _load_json(MANIFEST_SCHEMA_PATH)
        self.manifest = _load_json(MANIFEST_PATH)
        Draft202012Validator.check_schema(self.response_schema)
        Draft202012Validator.check_schema(self.manifest_schema)
        store = _schema_store()
        self.response_validator = Draft202012Validator(
            self.response_schema,
            resolver=RefResolver.from_schema(self.response_schema, store=store),
            format_checker=FormatChecker(),
        )
        self.manifest_validator = Draft202012Validator(
            self.manifest_schema,
            format_checker=FormatChecker(),
        )

    def validate_response(self, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.response_validator.iter_errors(value),
            key=lambda error: list(error.path),
        )
        if errors:
            raise CanonicalCliContractError(
                f"CLI response rejected: {errors[0].message}"
            )

    def validate_manifest(self, manifest: Mapping[str, Any]) -> None:
        errors = sorted(
            self.manifest_validator.iter_errors(manifest),
            key=lambda error: list(error.path),
        )
        if errors:
            raise CanonicalCliContractError(
                f"CLI manifest rejected: {errors[0].message}"
            )

        commands = manifest["commands"]
        command_ids = [entry["id"] for entry in commands]
        _require_sorted_unique(command_ids, "command identities")
        if set(command_ids) != EXPECTED_COMMANDS:
            raise CanonicalCliContractError("command tree is incomplete or expanded")

        exits = manifest["exit_codes"]
        exit_codes = [entry["code"] for entry in exits]
        if exit_codes != sorted(EXPECTED_EXITS):
            raise CanonicalCliContractError("exit taxonomy changed")

        compatibility = manifest["compatibility"]
        compatibility_ids = [entry["id"] for entry in compatibility]
        _require_sorted_unique(compatibility_ids, "compatibility identities")
        observed_compatibility = {
            entry["id"]: entry["disposition"] for entry in compatibility
        }
        if observed_compatibility != EXPECTED_COMPATIBILITY:
            raise CanonicalCliContractError("compatibility dispositions changed")

        requirements = manifest["coverage_requirements"]
        _require_sorted_unique(requirements, "coverage requirements")
        cases = manifest["cases"]
        case_ids = [entry["id"] for entry in cases]
        _require_sorted_unique(case_ids, "case identities")
        observed_coverage = {
            coverage for case in cases for coverage in case["coverage"]
        }
        missing_coverage = set(requirements) - observed_coverage
        if missing_coverage:
            raise CanonicalCliContractError(
                "cases omit coverage: " + ", ".join(sorted(missing_coverage))
            )
        observed_commands = {case["command"] for case in cases}
        if observed_commands != EXPECTED_COMMANDS:
            raise CanonicalCliContractError("cases do not cover every command")
        for case in cases:
            _require_sorted_unique(case["coverage"], f"{case['id']} coverage")
            if case["expected_exit"] not in EXPECTED_EXITS:
                raise CanonicalCliContractError(
                    f"{case['id']} uses an unknown exit code"
                )

        for key in (
            "positive_response_variants",
            "negative_mutations",
            "authority_paths",
        ):
            _require_sorted_unique(manifest[key], key)
        for relative in manifest["authority_paths"]:
            if not (ROOT / relative).is_file():
                raise CanonicalCliContractError(
                    f"authority path does not exist: {relative}"
                )

        self._validate_profiles(manifest["profiles"])
        self._validate_required_cases(case_ids)

    def _validate_profiles(self, profiles: Sequence[Mapping[str, Any]]) -> None:
        aliases = [entry["alias"] for entry in profiles]
        paths = [entry["path"] for entry in profiles]
        _require_sorted_unique(aliases, "profile aliases")
        if set(paths) != EXPECTED_PROFILE_PATHS:
            raise CanonicalCliContractError(
                "profile registry is incomplete or expanded"
            )
        target_schema = _load_json(
            ROOT / "spec" / "contracts" / "1.0" / "target-profile.schema.json"
        )
        store = _schema_store()
        validator = Draft202012Validator(
            target_schema,
            resolver=RefResolver.from_schema(target_schema, store=store),
            format_checker=FormatChecker(),
        )
        for entry in profiles:
            profile = _load_json(ROOT / entry["path"])
            errors = sorted(
                validator.iter_errors(profile), key=lambda error: list(error.path)
            )
            if errors:
                raise CanonicalCliContractError(
                    f"{entry['path']} is not a valid target profile: {errors[0].message}"
                )
            digest = hashlib.sha256(_canonical_json(profile)).hexdigest()
            if digest != entry["sha256"]:
                raise CanonicalCliContractError(
                    f"{entry['path']} canonical fingerprint changed"
                )
            if profile["profile_id"] != entry["profile_id"]:
                raise CanonicalCliContractError(
                    f"{entry['path']} profile identity changed"
                )
            if profile["profile_version"] != entry["profile_version"]:
                raise CanonicalCliContractError(
                    f"{entry['path']} profile version changed"
                )

    @staticmethod
    def _validate_required_cases(case_ids: Sequence[str]) -> None:
        required = {
            "case.broken_pipe",
            "case.compile_raw_request",
            "case.compile_target_artifact",
            "case.deterministic_repeat",
            "case.explain_no_match",
            "case.library_parity_semantic",
            "case.library_parity_target_artifact",
            "case.output_existing",
            "case.output_failure_no_file",
            "case.wrapper_parity",
        }
        missing = required - set(case_ids)
        if missing:
            raise CanonicalCliContractError(
                "required cases are missing: " + ", ".join(sorted(missing))
            )

    def positive_responses(self) -> dict[str, dict[str, Any]]:
        request = _load_json(
            ROOT
            / "spec"
            / "contracts"
            / "1.0"
            / "examples"
            / "compile-request"
            / "semantic-input.json"
        )
        result = _load_json(
            ROOT
            / "spec"
            / "contracts"
            / "1.0"
            / "examples"
            / "compile-result"
            / "success.json"
        )
        failed_request = _load_json(
            ROOT
            / "spec"
            / "contracts"
            / "1.0"
            / "examples"
            / "compile-request"
            / "unsupported-frontend.json"
        )
        failed_result = _load_json(
            ROOT
            / "spec"
            / "contracts"
            / "1.0"
            / "examples"
            / "compile-result"
            / "unsupported-frontend.json"
        )
        explanation = _load_json(
            ROOT
            / "spec"
            / "explanations"
            / "semantic"
            / "1.0"
            / "examples"
            / "source-less-literal.json"
        )
        no_match = _load_json(
            ROOT
            / "spec"
            / "explanations"
            / "no-match"
            / "1.0"
            / "examples"
            / "proven-literal-mismatch.json"
        )
        conversion = _load_json(
            ROOT
            / "spec"
            / "conversions"
            / "semantic"
            / "1.0"
            / "examples"
            / "exact-semantic-dsl.json"
        )
        profiles = [
            (_load_json(ROOT / entry["path"]), entry)
            for entry in self.manifest["profiles"]
        ]
        references = [
            {
                "profile_id": entry["profile_id"],
                "profile_version": entry["profile_version"],
                "sha256": entry["sha256"],
            }
            for _, entry in profiles
        ]
        return {
            "explain_compile_failed": {
                "cli_contract_version": "1.0.0",
                "command": "explain",
                "status": "compile_failed",
                "compile_request": failed_request,
                "compile_result": failed_result,
            },
            "explain_completed": {
                "cli_contract_version": "1.0.0",
                "command": "explain",
                "status": "completed",
                "compile_request": request,
                "compile_result": result,
                "explanation": explanation,
                "no_match": no_match,
            },
            "migrate_compile_failed": {
                "cli_contract_version": "1.0.0",
                "command": "migrate",
                "status": "compile_failed",
                "compile_request": failed_request,
                "compile_result": failed_result,
            },
            "migrate_completed": {
                "cli_contract_version": "1.0.0",
                "command": "migrate",
                "status": "completed",
                "compile_request": request,
                "compile_result": result,
                "conversion": conversion,
            },
            "target_inspect": {
                "cli_contract_version": "1.0.0",
                "command": "target.inspect",
                "profile_reference": references[0],
                "profile": profiles[0][0],
            },
            "target_list": {
                "cli_contract_version": "1.0.0",
                "command": "target.list",
                "profiles": references,
            },
        }

    def validate_positive_responses(self) -> int:
        responses = self.positive_responses()
        expected = self.manifest["positive_response_variants"]
        if sorted(responses) != expected:
            raise CanonicalCliContractError("positive response inventory changed")
        for response in responses.values():
            self.validate_response(response)
        return len(responses)

    def validate_negative_mutations(self) -> int:
        positives = self.positive_responses()
        mutations: dict[str, dict[str, Any]] = {}

        value = copy.deepcopy(positives["explain_compile_failed"])
        value["explanation"] = positives["explain_completed"]["explanation"]
        mutations["compile_failed_with_explanation"] = value

        value = copy.deepcopy(positives["explain_completed"])
        del value["explanation"]
        mutations["explain_missing_explanation"] = value

        value = copy.deepcopy(positives["migrate_completed"])
        del value["conversion"]
        mutations["migrate_missing_conversion"] = value

        value = copy.deepcopy(positives["target_list"])
        value["unexpected"] = True
        mutations["unknown_root_field"] = value

        value = copy.deepcopy(positives["target_inspect"])
        value["command"] = "target.list"
        mutations["wrong_command_tag"] = value

        value = copy.deepcopy(positives["migrate_completed"])
        value["cli_contract_version"] = "2.0.0"
        mutations["wrong_contract_version"] = value

        expected = self.manifest["negative_mutations"]
        if sorted(mutations) != expected:
            raise CanonicalCliContractError("negative mutation inventory changed")
        for name, mutation in mutations.items():
            try:
                self.validate_response(mutation)
            except CanonicalCliContractError:
                continue
            raise CanonicalCliContractError(
                f"controlled invalid response unexpectedly passed: {name}"
            )
        return len(mutations)

    def validate_schema_boundary(self) -> None:
        if self.response_schema["$id"] != (
            "https://strling.dev/cli/1.0/cli-response.schema.json"
        ):
            raise CanonicalCliContractError("CLI schema ID changed")
        text = json.dumps(self.response_schema, sort_keys=True).lower()
        for forbidden in (
            "subject_text",
            "raw_subject",
            "regex_parser",
            "portability_heuristic",
            "target_probe",
            "installed_engine",
        ):
            if forbidden in text:
                raise CanonicalCliContractError(
                    f"CLI schema crosses a forbidden boundary: {forbidden}"
                )

    def certify(self) -> dict[str, Any]:
        self.validate_schema_boundary()
        self.validate_manifest(self.manifest)
        positive = self.validate_positive_responses()
        negative = self.validate_negative_mutations()
        inputs = [
            CLI_ROOT / "README.md",
            RESPONSE_SCHEMA_PATH,
            MANIFEST_SCHEMA_PATH,
            MANIFEST_PATH,
        ]
        fingerprint = hashlib.sha256()
        for path in inputs:
            fingerprint.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            fingerprint.update(b"\0")
            fingerprint.update(path.read_bytes())
            fingerprint.update(b"\0")
        return {
            "commands": len(self.manifest["commands"]),
            "cases": len(self.manifest["cases"]),
            "coverage_requirements": len(self.manifest["coverage_requirements"]),
            "profiles": len(self.manifest["profiles"]),
            "positive_responses": positive,
            "negative_mutations": negative,
            "fingerprint": f"sha256:{fingerprint.hexdigest()}",
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the canonical STRling CLI contract and corpus."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate without writing (the only supported mode)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        result = CanonicalCliContractSuite().certify()
    except (CanonicalCliContractError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
