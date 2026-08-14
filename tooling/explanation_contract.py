#!/usr/bin/env python3
"""Validate the independently versioned semantic explanation contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "explanations" / "semantic" / "1.0"
SCHEMA_PATH = CONTRACT_ROOT / "explanation.schema.json"
CANONICAL_SCHEMA_ROOT = ROOT / "spec" / "contracts" / "1.0"


class ExplanationContractError(ValueError):
    """The explanation schema or one of its cross-object invariants failed."""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ExplanationContractError(f"{path}: root must be an object")
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


def _sorted_unique(values: list[Any], label: str) -> None:
    keys = [_canonical_json(value) for value in values]
    if keys != sorted(set(keys)):
        raise ExplanationContractError(f"{label} must be unique and canonical")


class ExplanationContractSuite:
    """Schema plus deterministic graph and evidence correspondence checks."""

    def __init__(self, contract_root: Path = CONTRACT_ROOT) -> None:
        self.contract_root = contract_root
        self.schema = _load_json(contract_root / "explanation.schema.json")
        Draft202012Validator.check_schema(self.schema)
        canonical_schemas = [
            _load_json(path)
            for path in sorted(CANONICAL_SCHEMA_ROOT.glob("*.schema.json"))
        ]
        schema_store = {
            schema["$id"]: schema for schema in [*canonical_schemas, self.schema]
        }
        self.validator = Draft202012Validator(
            self.schema,
            resolver=RefResolver.from_schema(self.schema, store=schema_store),
            format_checker=FormatChecker(),
        )

    def validate_suite_structure(self) -> int:
        if self.schema["$id"] != (
            "https://strling.dev/explanations/semantic/1.0/explanation.schema.json"
        ):
            raise ExplanationContractError("explanation schema ID is not canonical")
        if self.schema.get("additionalProperties") is not False:
            raise ExplanationContractError(
                "explanation root must reject unknown fields"
            )
        if self.schema["properties"]["model_version"] != {"const": "1.0.0"}:
            raise ExplanationContractError("model version must be independently pinned")
        schema_text = json.dumps(self.schema, sort_keys=True).lower()
        for forbidden in (
            "emitted_pattern",
            "raw_source",
            "regex_source",
            "subject_text",
            "match_trace",
            "why_no_match",
            "whyNoMatch".lower(),
            "markdown_layout",
            "html",
            "widget",
        ):
            if forbidden in schema_text:
                raise ExplanationContractError(
                    f"explanation schema crosses a forbidden boundary: {forbidden}"
                )
        return 1

    def validate(self, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise ExplanationContractError(
                f"explanation {_json_path(error.path)}: {error.message}"
            )
        self._validate_correspondence(value)

    def validate_positive_examples(self) -> int:
        count = 0
        for path in sorted((self.contract_root / "examples").glob("*.json")):
            self.validate(_load_json(path))
            count += 1
        if count == 0:
            raise ExplanationContractError("at least one positive example is required")
        return count

    def validate_negative_examples(self) -> int:
        count = 0
        for path in sorted((self.contract_root / "invalid").glob("*.json")):
            try:
                self.validate(_load_json(path))
            except ExplanationContractError:
                count += 1
                continue
            raise ExplanationContractError(
                f"controlled invalid explanation unexpectedly passed: {path}"
            )
        if count == 0:
            raise ExplanationContractError(
                "at least one controlled invalid example is required"
            )
        return count

    def certify(self) -> dict[str, Any]:
        schema_count = self.validate_suite_structure()
        positive_count = self.validate_positive_examples()
        negative_count = self.validate_negative_examples()
        inputs = [
            SCHEMA_PATH,
            *sorted((self.contract_root / "examples").glob("*.json")),
            *sorted((self.contract_root / "invalid").glob("*.json")),
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
            "fingerprint": f"sha256:{fingerprint.hexdigest()}",
        }

    def _validate_correspondence(self, document: Mapping[str, Any]) -> None:
        nodes = document["nodes"]
        node_ids = [node["node_id"] for node in nodes]
        if node_ids != sorted(set(node_ids)):
            raise ExplanationContractError("nodes must have unique sorted node IDs")
        reachable = set(node_ids)

        program = document["program"]
        concise = document["concise"]
        root_id = program["root_node_id"]
        if root_id not in reachable or concise["root_node_id"] != root_id:
            raise ExplanationContractError("program root must resolve consistently")
        root = next(node for node in nodes if node["node_id"] == root_id)
        if concise["root_facts"] != root["facts"]:
            raise ExplanationContractError(
                "concise root facts must equal detailed facts"
            )
        if concise["source_mode"] != program["source_mode"]:
            raise ExplanationContractError("source mode must agree across views")
        source_ids = program["source_ids"]
        if source_ids != sorted(set(source_ids)):
            raise ExplanationContractError(
                "program source IDs must be unique and sorted"
            )
        if (program["source_mode"] == "source_less") != (source_ids == []):
            raise ExplanationContractError(
                "source-less mode and declared source identities disagree"
            )

        captures = document["captures"]
        capture_ids = [capture["capture_id"] for capture in captures]
        if capture_ids != sorted(set(capture_ids)):
            raise ExplanationContractError(
                "captures must have unique sorted identities"
            )
        capture_set = set(capture_ids)

        backreference_count = 0
        for node in nodes:
            self._validate_source_link(node["source"], reachable)
            self._validate_node(node, reachable, capture_set)
            if node["semantic"]["kind"] == "backreference":
                backreference_count += 1

        for capture in captures:
            for key in ("definition_node_id", "body_node_id"):
                self._require_node(capture[key], reachable, f"capture {key}")
            references = capture["reference_node_ids"]
            if references != sorted(set(references)):
                raise ExplanationContractError(
                    "capture reference node identities must be unique and sorted"
                )
            for node_id in references:
                self._require_node(node_id, reachable, "capture reference")
                node = next(item for item in nodes if item["node_id"] == node_id)
                semantic = node["semantic"]
                if (
                    semantic["kind"] != "backreference"
                    or semantic["capture_id"] != capture["capture_id"]
                ):
                    raise ExplanationContractError(
                        "capture references must resolve to matching backreferences"
                    )
            self._validate_source_link(capture["source"], reachable)

        safety = document["safety_findings"]
        safety_keys = [
            (item["code"], item["primary_node_id"], item["contributing_node_ids"])
            for item in safety
        ]
        if safety_keys != sorted(safety_keys) or len(safety_keys) != len(
            set(json.dumps(key) for key in safety_keys)
        ):
            raise ExplanationContractError("safety findings must be canonical")
        for item in safety:
            self._validate_evidence_nodes(item, reachable)

        uncertainties = document["uncertainties"]
        uncertainty_keys = [
            (item["code"], item["primary_node_id"], item["contributing_node_ids"])
            for item in uncertainties
        ]
        if uncertainty_keys != sorted(uncertainty_keys) or len(uncertainty_keys) != len(
            set(json.dumps(key) for key in uncertainty_keys)
        ):
            raise ExplanationContractError("uncertainties must be canonical")
        for item in uncertainties:
            self._validate_evidence_nodes(item, reachable)

        diagnostics = document["diagnostics"]
        self._validate_diagnostics(diagnostics, reachable)

        expected_counts = {
            "node_count": len(nodes),
            "capture_count": len(captures),
            "backreference_count": backreference_count,
            "safety_finding_count": len(safety),
            "uncertainty_count": len(uncertainties),
            "diagnostic_count": len(diagnostics),
        }
        for key, expected in expected_counts.items():
            if concise[key] != expected:
                raise ExplanationContractError(
                    f"concise {key} does not match detailed entities"
                )

        target = document.get("target")
        concise_target = concise.get("target")
        if (target is None) != (concise_target is None):
            raise ExplanationContractError(
                "concise and detailed target sections must appear together"
            )
        if target is not None and concise_target is not None:
            self._validate_target(target, concise_target, reachable)

    def _validate_node(
        self, node: Mapping[str, Any], reachable: set[str], captures: set[str]
    ) -> None:
        semantic = node["semantic"]
        kind = semantic["kind"]
        reference_fields: tuple[str, ...] = ()
        if kind == "sequence":
            reference_fields = ("items",)
        elif kind == "alternation":
            reference_fields = ("branches",)
        elif kind in {"repeat", "capture", "lookaround", "atomic"}:
            reference_fields = ("body_node_id",)
        for field in reference_fields:
            values = semantic[field]
            if isinstance(values, str):
                values = [values]
            for node_id in values:
                self._require_node(node_id, reachable, f"{kind} {field}")
        if (
            kind in {"capture", "backreference"}
            and semantic["capture_id"] not in captures
        ):
            raise ExplanationContractError(f"{kind} must resolve a capture identity")
        if kind == "backreference":
            self._require_node(
                semantic["definition_node_id"], reachable, "backreference definition"
            )

        structural = node["structural"]
        _sorted_unique(structural["leading_consumption"], "leading consumption")
        repetition = structural.get("repetition")
        if (kind == "repeat") != (repetition is not None):
            raise ExplanationContractError(
                "repetition structural facts must appear exactly on repeat nodes"
            )
        if repetition is not None:
            self._require_node(
                repetition["body_node_id"], reachable, "repetition structural body"
            )
        alternation = structural["alternation_branch_overlaps"]
        alternation_keys = [
            (
                item["left_branch_index"],
                item["left_node_id"],
                item["right_branch_index"],
                item["right_node_id"],
            )
            for item in alternation
        ]
        if alternation_keys != sorted(set(alternation_keys)):
            raise ExplanationContractError("alternation overlaps must be canonical")
        followers = structural["repetition_follower_overlaps"]
        follower_keys = [
            (
                item["repetition_index"],
                item["repetition_node_id"],
                item["following_index"],
                item["following_node_id"],
            )
            for item in followers
        ]
        if follower_keys != sorted(set(follower_keys)):
            raise ExplanationContractError(
                "repetition/follower overlaps must be canonical"
            )
        for item in [*alternation, *followers]:
            for key, value in item.items():
                if key.endswith("_node_id"):
                    self._require_node(value, reachable, f"structural {key}")

    def _validate_evidence_nodes(
        self, item: Mapping[str, Any], reachable: set[str]
    ) -> None:
        self._require_node(item["primary_node_id"], reachable, "primary evidence")
        contributing = item["contributing_node_ids"]
        if contributing != sorted(set(contributing)):
            raise ExplanationContractError(
                "contributing node identities must be unique and sorted"
            )
        for node_id in contributing:
            self._require_node(node_id, reachable, "contributing evidence")
        self._validate_source_link(item["source"], reachable)

    def _validate_diagnostics(
        self, diagnostics: list[Mapping[str, Any]], reachable: set[str]
    ) -> None:
        occurrences = [item["diagnostic"]["occurrence"] for item in diagnostics]
        if occurrences != list(range(len(diagnostics))):
            raise ExplanationContractError(
                "explanation diagnostics require local deterministic occurrences"
            )
        for item in diagnostics:
            self._validate_evidence_nodes(item, reachable)

    def _validate_target(
        self,
        target: Mapping[str, Any],
        concise: Mapping[str, Any],
        reachable: set[str],
    ) -> None:
        if target["target_profile"] != concise["target_profile"]:
            raise ExplanationContractError("target profile disagrees across views")
        if target["status"] != concise["status"]:
            raise ExplanationContractError("target status disagrees across views")
        decisions = target["decisions"]
        ordinals = [item["ordinal"] for item in decisions]
        if ordinals != list(range(len(decisions))):
            raise ExplanationContractError(
                "target decision ordinals must be contiguous"
            )
        unresolved = 0
        for decision in decisions:
            self._require_node(decision["node_id"], reachable, "target decision")
            self._validate_source_link(decision["source"], reachable)
            outcome = decision["outcome"]["kind"]
            if outcome == "unresolved":
                unresolved += 1
                if decision["evidence_class"] != "uncertainty":
                    raise ExplanationContractError(
                        "unresolved target decisions must remain uncertainty"
                    )
            elif decision["evidence_class"] != "target_plan":
                raise ExplanationContractError(
                    "resolved target decisions must be target-plan evidence"
                )
            constraint_ids = [
                item["constraint"]["constraint_id"] for item in decision["constraints"]
            ]
            if constraint_ids != sorted(set(constraint_ids)):
                raise ExplanationContractError(
                    "target constraints must have unique sorted identities"
                )
        expected_status = (
            "unresolved" if unresolved else self._planned_status(decisions)
        )
        if target["status"] != expected_status:
            raise ExplanationContractError(
                "target status must equal the completed plan evidence"
            )
        diagnostics = target["diagnostics"]
        self._validate_diagnostics(diagnostics, reachable)
        if concise["decision_count"] != len(decisions):
            raise ExplanationContractError("concise target decision count is stale")
        if concise["unresolved_count"] != unresolved:
            raise ExplanationContractError("concise target unresolved count is stale")
        if concise["diagnostic_count"] != len(diagnostics):
            raise ExplanationContractError("concise target diagnostic count is stale")

    @staticmethod
    def _planned_status(decisions: list[Mapping[str, Any]]) -> str:
        rank = {"native": 0, "equivalent_rewrite": 1, "unsupported": 2}
        return max(
            (decision["outcome"]["kind"] for decision in decisions),
            key=rank.__getitem__,
            default="native",
        )

    @staticmethod
    def _require_node(node_id: str, reachable: set[str], label: str) -> None:
        if node_id not in reachable:
            raise ExplanationContractError(f"{label} references missing {node_id}")

    @staticmethod
    def _validate_source_link(link: Mapping[str, Any], reachable: set[str]) -> None:
        spans = link["source_spans"]
        span_keys = [(item["source_id"], item["start"], item["end"]) for item in spans]
        if span_keys != sorted(set(span_keys)):
            raise ExplanationContractError("source spans must be unique and sorted")
        derived = link["derived_from_node_ids"]
        if derived != sorted(set(derived)):
            raise ExplanationContractError(
                "derived node identities must be unique and sorted"
            )
        for node_id in derived:
            if node_id not in reachable:
                raise ExplanationContractError(
                    f"source provenance references missing {node_id}"
                )


def main() -> int:
    result = ExplanationContractSuite().certify()
    print(
        "SEMANTIC_EXPLANATION_CONTRACT status=passed "
        f"schemas={result['schemas']} positive={result['positive']} "
        f"negative={result['negative']} fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
