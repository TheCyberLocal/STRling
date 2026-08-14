#!/usr/bin/env python3
"""Validate the independently versioned bounded no-match contract."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "explanations" / "no-match" / "1.0"
SCHEMA_PATH = CONTRACT_ROOT / "no-match-explanation.schema.json"
TAXONOMY_PATH = CONTRACT_ROOT / "reason-taxonomy.json"
CORPUS_PATH = CONTRACT_ROOT / "verification-corpus.json"
CANONICAL_SCHEMA_ROOT = ROOT / "spec" / "contracts" / "1.0"
SEMANTIC_EXPLANATION_SCHEMA = (
    ROOT / "spec" / "explanations" / "semantic" / "1.0" / "explanation.schema.json"
)

POSITIVE_FIXTURES = (
    "likely-multiple-blockers.json",
    "matched-literal.json",
    "proven-literal-mismatch.json",
    "unavailable-target.json",
    "unknown-step-limit.json",
)
INVALID_FIXTURES = (
    "false-proven-after-limit.json",
    "mismatched-subject-span.json",
    "noncanonical-findings.json",
    "unavailable-without-target.json",
    "wrong-program-link.json",
)
EXAMPLE_CASES = {
    "likely-multiple-blockers.json": "input-start-multiple-blockers",
    "matched-literal.json": "matched-literal",
    "proven-literal-mismatch.json": "proven-literal-mismatch",
    "unavailable-target.json": "target-unsupported",
    "unknown-step-limit.json": "step-limit",
}
LIMIT_ORDER = (
    "subject_utf8_bytes",
    "subject_unicode_scalars",
    "steps",
    "depth",
    "branches",
    "findings",
    "elapsed",
)
LIMIT_REASON = {
    "subject_utf8_limit_reached": "subject_utf8_bytes",
    "subject_scalar_limit_reached": "subject_unicode_scalars",
    "step_limit_reached": "steps",
    "depth_limit_reached": "depth",
    "branch_limit_reached": "branches",
    "finding_limit_reached": "findings",
    "elapsed_limit_reached": "elapsed",
}
TARGET_REASON = {
    "target_unsupported": "unsupported",
    "target_unresolved": "unresolved",
}
REQUIRED_COVERAGE = {
    "alternation",
    "anchor",
    "backreference",
    "branch",
    "capture",
    "character_class",
    "depth",
    "elapsed",
    "finding",
    "likely",
    "literal",
    "lookaround",
    "matched",
    "multiple_blockers",
    "pathological",
    "proven",
    "repetition",
    "resource_limit",
    "search",
    "steps",
    "subject",
    "target",
    "target_dependent",
    "unavailable",
    "unicode",
    "unknown",
    "unsupported",
    "wildcard",
    "word_boundary",
    "zero_width",
}


class NoMatchExplanationContractError(ValueError):
    """The no-match schema or one of its cross-object invariants failed."""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise NoMatchExplanationContractError(f"{path}: root must be an object")
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


class NoMatchExplanationContractSuite:
    """Certify shape, taxonomy, corpus, status, provenance, and bounds."""

    def __init__(self, contract_root: Path = CONTRACT_ROOT) -> None:
        self.contract_root = contract_root
        self.schema = _load_json(contract_root / SCHEMA_PATH.name)
        self.taxonomy = _load_json(contract_root / TAXONOMY_PATH.name)
        self.corpus = _load_json(contract_root / CORPUS_PATH.name)
        Draft202012Validator.check_schema(self.schema)

        canonical_schemas = [
            _load_json(path)
            for path in sorted(CANONICAL_SCHEMA_ROOT.glob("*.schema.json"))
        ]
        semantic_explanation = _load_json(SEMANTIC_EXPLANATION_SCHEMA)
        store = {
            schema["$id"]: schema
            for schema in [*canonical_schemas, semantic_explanation, self.schema]
        }
        self.resolver = RefResolver.from_schema(self.schema, store=store)
        self.validator = Draft202012Validator(
            self.schema,
            resolver=self.resolver,
            format_checker=FormatChecker(),
        )
        semantic_schema = next(
            schema
            for schema in canonical_schemas
            if schema["$id"].endswith("/semantic-ir.schema.json")
        )
        self.semantic_validator = Draft202012Validator(
            semantic_schema,
            resolver=RefResolver.from_schema(semantic_schema, store=store),
            format_checker=FormatChecker(),
        )
        self.limit_validator = Draft202012Validator(
            {
                "$ref": (
                    "https://strling.dev/explanations/no-match/1.0/"
                    "no-match-explanation.schema.json#/$defs/Limits"
                )
            },
            resolver=self.resolver,
        )
        self.target_validator = Draft202012Validator(
            {
                "$ref": (
                    "https://strling.dev/explanations/no-match/1.0/"
                    "no-match-explanation.schema.json#/$defs/TargetContext"
                )
            },
            resolver=self.resolver,
        )
        self.reason_by_code = {
            reason["code"]: reason for reason in self.taxonomy.get("reasons", [])
        }

    def validate_suite_structure(self) -> int:
        if self.schema["$id"] != (
            "https://strling.dev/explanations/no-match/1.0/"
            "no-match-explanation.schema.json"
        ):
            raise NoMatchExplanationContractError(
                "no-match explanation schema ID is not canonical"
            )
        if self.schema.get("additionalProperties") is not False:
            raise NoMatchExplanationContractError(
                "no-match explanation root must reject unknown fields"
            )
        if self.schema["properties"]["model_version"] != {"const": "1.0.0"}:
            raise NoMatchExplanationContractError(
                "no-match model version must be independently pinned"
            )
        if self.schema["properties"]["execution_mode"] != {"const": "search"}:
            raise NoMatchExplanationContractError(
                "no-match 1.0 must expose only explicit search execution"
            )

        positive = tuple(
            path.name
            for path in sorted((self.contract_root / "examples").glob("*.json"))
        )
        invalid = tuple(
            path.name
            for path in sorted((self.contract_root / "invalid").glob("*.json"))
        )
        if positive != POSITIVE_FIXTURES:
            raise NoMatchExplanationContractError(
                "positive fixture inventory must equal the closed 1.0 corpus"
            )
        if invalid != INVALID_FIXTURES:
            raise NoMatchExplanationContractError(
                "invalid fixture inventory must equal the closed 1.0 corpus"
            )
        self._validate_taxonomy()
        self._validate_corpus()

        schema_text = json.dumps(self.schema, sort_keys=True).lower()
        for forbidden in (
            "subject_text",
            "raw_regex",
            "emitted_pattern",
            "backtracking_trace",
            "engine_trace",
            "markdown",
            "html",
            "widget",
            "lsp",
        ):
            if forbidden in schema_text:
                raise NoMatchExplanationContractError(
                    f"no-match schema crosses a forbidden boundary: {forbidden}"
                )
        return 1

    def validate(self, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise NoMatchExplanationContractError(
                f"no-match explanation {_json_path(error.path)}: {error.message}"
            )
        self._validate_correspondence(value)

    def validate_positive_examples(self) -> int:
        cases = {case["case_id"]: case for case in self.corpus["cases"]}
        programs = {
            program["program_id"]: program["program"]
            for program in self.corpus["programs"]
        }
        for name in POSITIVE_FIXTURES:
            document = _load_json(self.contract_root / "examples" / name)
            self.validate(document)
            case = cases[EXAMPLE_CASES[name]]
            program = programs[case["program_id"]]
            expected_limits = dict(self.corpus["default_limits"])
            expected_limits.update(case.get("limits", {}))
            if document["semantic_program"] != _sha256(program):
                raise NoMatchExplanationContractError(
                    f"{name}: semantic program digest does not match its corpus input"
                )
            subject = case["subject"]
            subject_identity = document["subject"]
            if subject_identity != {
                "sha256": hashlib.sha256(subject.encode("utf-8")).hexdigest(),
                "utf8_bytes": len(subject.encode("utf-8")),
                "unicode_scalars": len(subject),
            }:
                raise NoMatchExplanationContractError(
                    f"{name}: subject identity does not match its private corpus input"
                )
            if document["limits"] != expected_limits:
                raise NoMatchExplanationContractError(
                    f"{name}: limits do not match its corpus case"
                )
            expected = case["expected"]
            actual_reasons = [
                finding["reason_code"] for finding in document["findings"]
            ]
            if (
                document["outcome"] != expected["outcome"]
                or document["explanation_disposition"] != expected["disposition"]
                or set(actual_reasons) != set(expected["reason_codes"])
            ):
                raise NoMatchExplanationContractError(
                    f"{name}: result does not match its authored corpus expectation"
                )
            if document.get("target") != case.get("target"):
                raise NoMatchExplanationContractError(
                    f"{name}: target context does not match its corpus case"
                )
            self._validate_subject_boundaries(document, subject)
        return len(POSITIVE_FIXTURES)

    def validate_negative_examples(self) -> int:
        count = 0
        for name in INVALID_FIXTURES:
            path = self.contract_root / "invalid" / name
            try:
                self.validate(_load_json(path))
            except NoMatchExplanationContractError:
                count += 1
                continue
            raise NoMatchExplanationContractError(
                f"controlled invalid no-match explanation unexpectedly passed: {path}"
            )
        return count

    def certify(self) -> dict[str, Any]:
        schema_count = self.validate_suite_structure()
        positive_count = self.validate_positive_examples()
        negative_count = self.validate_negative_examples()
        dispositions = Counter(
            case["expected"]["disposition"] for case in self.corpus["cases"]
        )
        inputs = [
            SCHEMA_PATH,
            TAXONOMY_PATH,
            CORPUS_PATH,
            *[self.contract_root / "examples" / name for name in POSITIVE_FIXTURES],
            *[self.contract_root / "invalid" / name for name in INVALID_FIXTURES],
        ]
        fingerprint = hashlib.sha256()
        for path in inputs:
            fingerprint.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            fingerprint.update(b"\0")
            fingerprint.update(path.read_bytes())
            fingerprint.update(b"\0")
        return {
            "schemas": schema_count,
            "positive": positive_count,
            "negative": negative_count,
            "reasons": len(self.reason_by_code),
            "programs": len(self.corpus["programs"]),
            "cases": len(self.corpus["cases"]),
            "matched": dispositions["not_applicable"],
            "proven": dispositions["proven"],
            "likely": dispositions["likely"],
            "unknown": dispositions["unknown"],
            "unavailable": dispositions["unavailable"],
            "fingerprint": f"sha256:{fingerprint.hexdigest()}",
        }

    def _validate_taxonomy(self) -> None:
        if set(self.taxonomy) != {"model_version", "reasons"}:
            raise NoMatchExplanationContractError("reason taxonomy must be closed")
        if self.taxonomy["model_version"] != "1.0.0":
            raise NoMatchExplanationContractError("reason taxonomy version is stale")
        reasons = self.taxonomy["reasons"]
        codes = [reason.get("code") for reason in reasons]
        schema_codes = self.schema["$defs"]["ReasonCode"]["enum"]
        if codes != schema_codes or len(codes) != len(set(codes)):
            raise NoMatchExplanationContractError(
                "reason taxonomy must equal schema order without duplicates"
            )
        allowed_families = {
            "assertion_failure",
            "bounded_uncertainty",
            "consuming_mismatch",
            "position_failure",
            "state_failure",
            "structure_failure",
            "target_disposition",
        }
        for reason in reasons:
            if set(reason) != {
                "code",
                "family",
                "evidence_class",
                "node_required",
                "subject_location_required",
            }:
                raise NoMatchExplanationContractError(
                    f"{reason.get('code')}: taxonomy entry must be closed"
                )
            if reason["family"] not in allowed_families:
                raise NoMatchExplanationContractError(
                    f"{reason['code']}: taxonomy family is unknown"
                )
            if reason["evidence_class"] not in {
                "canonical_evaluation",
                "target_plan",
                "uncertainty",
            }:
                raise NoMatchExplanationContractError(
                    f"{reason['code']}: evidence class is unknown"
                )

    def _validate_corpus(self) -> None:
        if set(self.corpus) != {
            "model_version",
            "default_limits",
            "programs",
            "cases",
        }:
            raise NoMatchExplanationContractError("verification corpus must be closed")
        if self.corpus["model_version"] != "1.0.0":
            raise NoMatchExplanationContractError(
                "verification corpus version is stale"
            )
        self._validate_schema_value(
            self.limit_validator, self.corpus["default_limits"], "default limits"
        )

        program_ids: list[str] = []
        programs: dict[str, Mapping[str, Any]] = {}
        for entry in self.corpus["programs"]:
            if set(entry) != {"program_id", "program"}:
                raise NoMatchExplanationContractError(
                    "corpus program entry must be closed"
                )
            program_id = entry["program_id"]
            if not isinstance(program_id, str) or not program_id:
                raise NoMatchExplanationContractError("corpus program ID is invalid")
            self._validate_schema_value(
                self.semantic_validator,
                entry["program"],
                f"corpus program {program_id}",
            )
            program_ids.append(program_id)
            programs[program_id] = entry["program"]
        if program_ids != sorted(set(program_ids)):
            raise NoMatchExplanationContractError(
                "corpus programs must have unique sorted IDs"
            )

        case_ids: list[str] = []
        coverage: set[str] = set()
        for case in self.corpus["cases"]:
            required = {"case_id", "program_id", "subject", "expected", "coverage"}
            if not required.issubset(case) or not set(case).issubset(
                required | {"limits", "target"}
            ):
                raise NoMatchExplanationContractError(
                    "corpus case entry must be closed"
                )
            case_id = case["case_id"]
            if not isinstance(case_id, str) or not case_id:
                raise NoMatchExplanationContractError("corpus case ID is invalid")
            case_ids.append(case_id)
            if case["program_id"] not in programs:
                raise NoMatchExplanationContractError(
                    f"{case_id}: program reference does not resolve"
                )
            subject = case["subject"]
            if not isinstance(subject, str):
                raise NoMatchExplanationContractError(
                    f"{case_id}: subject must be text"
                )
            limits = dict(self.corpus["default_limits"])
            limits.update(case.get("limits", {}))
            self._validate_schema_value(
                self.limit_validator, limits, f"{case_id} limits"
            )
            if "target" in case:
                self._validate_schema_value(
                    self.target_validator, case["target"], f"{case_id} target"
                )
            expected = case["expected"]
            if set(expected) != {"outcome", "disposition", "reason_codes"}:
                raise NoMatchExplanationContractError(
                    f"{case_id}: expected result must be closed"
                )
            if expected["outcome"] not in {
                "matched",
                "no_match",
                "unknown",
                "unavailable",
            }:
                raise NoMatchExplanationContractError(f"{case_id}: outcome is unknown")
            reasons = expected["reason_codes"]
            if (
                not isinstance(reasons, list)
                or len(reasons) != len(set(reasons))
                or any(reason not in self.reason_by_code for reason in reasons)
            ):
                raise NoMatchExplanationContractError(
                    f"{case_id}: expected reasons are invalid"
                )
            if expected["outcome"] == "matched" and reasons:
                raise NoMatchExplanationContractError(
                    f"{case_id}: matched case cannot expect a finding"
                )
            case_coverage = case["coverage"]
            if (
                not isinstance(case_coverage, list)
                or not case_coverage
                or len(case_coverage) != len(set(case_coverage))
                or any(not isinstance(item, str) or not item for item in case_coverage)
            ):
                raise NoMatchExplanationContractError(
                    f"{case_id}: coverage must be unique nonempty labels"
                )
            coverage.update(case_coverage)
        if len(case_ids) != len(set(case_ids)):
            raise NoMatchExplanationContractError("corpus case IDs must be unique")
        if not REQUIRED_COVERAGE.issubset(coverage):
            missing = sorted(REQUIRED_COVERAGE - coverage)
            raise NoMatchExplanationContractError(
                f"verification corpus coverage is incomplete: {missing}"
            )
        expected_limits = set(LIMIT_REASON.values())
        actual_limits = {
            LIMIT_REASON[reason]
            for case in self.corpus["cases"]
            for reason in case["expected"]["reason_codes"]
            if reason in LIMIT_REASON
        }
        if actual_limits != expected_limits:
            raise NoMatchExplanationContractError(
                "verification corpus must isolate all seven resource limits"
            )

    def _validate_correspondence(self, document: Mapping[str, Any]) -> None:
        if (
            document["semantic_explanation"]["semantic_program"]
            != document["semantic_program"]
        ):
            raise NoMatchExplanationContractError(
                "semantic explanation program must equal the evaluated program"
            )
        findings = document["findings"]
        if [finding["ordinal"] for finding in findings] != list(range(len(findings))):
            raise NoMatchExplanationContractError(
                "finding ordinals must be contiguous canonical order"
            )
        limits = document["limits"]
        work = document["work"]
        if len(findings) > limits["max_findings"]:
            raise NoMatchExplanationContractError(
                "retained findings exceed the configured finding limit"
            )
        comparisons = (
            (work["steps"], limits["max_steps"], "steps"),
            (work["maximum_depth"], limits["max_depth"], "depth"),
            (
                work["branch_expansions"],
                limits["max_branch_expansions"],
                "branch expansions",
            ),
        )
        for actual, maximum, label in comparisons:
            if actual > maximum:
                raise NoMatchExplanationContractError(
                    f"work report {label} exceeds configured limit"
                )
        reached = work["reached_limits"]
        if reached != [kind for kind in LIMIT_ORDER if kind in reached]:
            raise NoMatchExplanationContractError(
                "reached limits must use canonical order"
            )

        outcome = document["outcome"]
        disposition = document["explanation_disposition"]
        for finding in findings:
            reason = self.reason_by_code[finding["reason_code"]]
            if finding["evidence_class"] != reason["evidence_class"]:
                raise NoMatchExplanationContractError(
                    f"{finding['reason_code']}: evidence class contradicts taxonomy"
                )
            has_node = "node_id" in finding
            has_source = "source" in finding
            has_location = "subject_location" in finding
            if has_node != has_source or has_node != reason["node_required"]:
                raise NoMatchExplanationContractError(
                    f"{finding['reason_code']}: node/source requirements are inconsistent"
                )
            if has_location != reason["subject_location_required"]:
                raise NoMatchExplanationContractError(
                    f"{finding['reason_code']}: subject location requirement is inconsistent"
                )
            if has_location != ("context" in finding):
                raise NoMatchExplanationContractError(
                    f"{finding['reason_code']}: subject location and context must correspond"
                )
            self._validate_location(document, finding)

        if outcome == "no_match":
            if any(
                finding["confidence"] != disposition
                or finding["evidence_class"] != "canonical_evaluation"
                for finding in findings
            ):
                raise NoMatchExplanationContractError(
                    "complete no-match findings must equal proven/likely disposition"
                )
        elif outcome == "unknown":
            if any(
                finding["confidence"] != "unknown"
                or finding["evidence_class"] != "uncertainty"
                for finding in findings
            ):
                raise NoMatchExplanationContractError(
                    "unknown result may contain only uncertainty findings"
                )
            reasons = {finding["reason_code"] for finding in findings}
            expected_reached = {
                LIMIT_REASON[reason] for reason in reasons if reason in LIMIT_REASON
            }
            if set(reached) != expected_reached:
                raise NoMatchExplanationContractError(
                    "unknown resource reasons and reached limits must correspond exactly"
                )
        elif outcome == "unavailable":
            target = document.get("target")
            if target is None:
                raise NoMatchExplanationContractError(
                    "unavailable result requires target context"
                )
            if any(
                finding["confidence"] != "unavailable"
                or finding["evidence_class"] != "target_plan"
                for finding in findings
            ):
                raise NoMatchExplanationContractError(
                    "unavailable result may contain only target-plan findings"
                )
            for finding in findings:
                expected_status = TARGET_REASON.get(finding["reason_code"])
                if expected_status != target["status"]:
                    raise NoMatchExplanationContractError(
                        "target reason and completed target status do not correspond"
                    )
        elif findings or disposition != "not_applicable":
            raise NoMatchExplanationContractError(
                "matched result cannot carry no-match evidence"
            )

        target = document.get("target")
        if target and target["status"] in {"unsupported", "unresolved"}:
            if outcome != "unavailable":
                raise NoMatchExplanationContractError(
                    "unsupported or unresolved target must be unavailable"
                )

    def _validate_location(
        self, document: Mapping[str, Any], finding: Mapping[str, Any]
    ) -> None:
        location = finding.get("subject_location")
        if location is None:
            return
        length = document["subject"]["utf8_bytes"]
        if location["kind"] == "position":
            if location["byte_offset"] > length:
                raise NoMatchExplanationContractError(
                    "finding subject position exceeds subject length"
                )
        elif location["start"] > location["end"] or location["end"] > length:
            raise NoMatchExplanationContractError(
                "finding subject span is reversed or exceeds subject length"
            )
        context = finding["context"]
        if context["candidate_start"] > length:
            raise NoMatchExplanationContractError(
                "finding candidate start exceeds subject length"
            )

    def _validate_subject_boundaries(
        self, document: Mapping[str, Any], subject: str
    ) -> None:
        boundaries = {0}
        offset = 0
        for character in subject:
            offset += len(character.encode("utf-8"))
            boundaries.add(offset)
        for finding in document["findings"]:
            location = finding.get("subject_location")
            if location is None:
                continue
            offsets = (
                [location["byte_offset"]]
                if location["kind"] == "position"
                else [location["start"], location["end"]]
            )
            if any(value not in boundaries for value in offsets):
                raise NoMatchExplanationContractError(
                    "finding subject location is not a UTF-8 scalar boundary"
                )

    @staticmethod
    def _validate_schema_value(
        validator: Draft202012Validator, value: Any, label: str
    ) -> None:
        errors = sorted(
            validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise NoMatchExplanationContractError(
                f"{label} {_json_path(error.path)}: {error.message}"
            )


def main() -> int:
    result = NoMatchExplanationContractSuite().certify()
    print(
        "NO_MATCH_EXPLANATION_CONTRACT status=passed "
        f"schemas={result['schemas']} positive={result['positive']} "
        f"negative={result['negative']} reasons={result['reasons']} "
        f"programs={result['programs']} cases={result['cases']} "
        f"matched={result['matched']} proven={result['proven']} "
        f"likely={result['likely']} unknown={result['unknown']} "
        f"unavailable={result['unavailable']} "
        f"fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
