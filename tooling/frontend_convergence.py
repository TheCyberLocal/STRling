#!/usr/bin/env python3
"""Certify the authored frontend-convergence denominator and classifications."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__:
    from tooling.contract_validation import canonical_json
    from tooling.simply_contract import SimplyContractError, SimplyContractSuite
else:
    from contract_validation import canonical_json
    from simply_contract import SimplyContractError, SimplyContractSuite

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "tests" / "convergence" / "frontend-convergence.json"
SCHEMA_PATH = ROOT / "tests" / "convergence" / "frontend-convergence.schema.json"
SIMPLY_PROTOCOL = ROOT / "spec" / "frontends" / "simply" / "1.0" / "protocol.json"
SEMANTIC_MAPPING = ROOT / "spec" / "frontends" / "semantic" / "1.0" / "mapping.json"
LEGACY_DIALECT = ROOT / "spec" / "frontends" / "legacy-regex" / "1.0" / "dialect.json"

DOCUMENTATION_PATHS = (
    "README.md",
    "docs/architecture.md",
    "docs/index.md",
    "docs/spec_links.md",
    "docs/testing_design.md",
    "docs/testing_workflow.md",
    "docs/tutorial/first_contribution.md",
    "spec/README.md",
    "spec/frontends/README.md",
    "spec/frontends/semantic/1.0/README.md",
    "bindings/fsharp/README.md",
    "bindings/java/README.md",
    "bindings/kotlin/README.md",
    "bindings/lua/README.md",
)
DOCUMENTATION_REQUIRED = {
    "README.md": (
        "**Semantic STRling** is the flagship textual language.",
        "Use Simply when intent originates in program code.",
        "Use regex-compatible source",
        "only when importing or preserving regex-shaped input.",
        "docs/tutorial/first_contribution.md",
    ),
    "docs/architecture.md": (
        "**Semantic STRling DSL:**",
        "flagship textual semantic language",
        "**Simply APIs:**",
        "**Regex-compatible import frontend:**",
        "migration/frontend-convergence.md",
    ),
    "docs/index.md": (
        "Your First Semantic STRling Contribution",
        "for textual",
        "for programmatic",
        "for import and compatibility work",
    ),
    "docs/spec_links.md": (
        "Semantic STRling frontend 1.0",
        "Regex-compatible frontend 1.0",
        "Simply builder protocol 1.0",
    ),
    "docs/testing_design.md": (
        "**Semantic STRling** is the flagship textual language.",
        "**Simply** is the programmatic semantic-construction surface.",
        "**Regex-compatible source** is an explicit import and migration surface.",
        "python3 tooling/frontend_convergence.py --check",
    ),
    "docs/testing_workflow.md": (
        "**Semantic STRling** for flagship textual intent",
        "**Simply** for programmatic semantic construction",
        "**regex-compatible source** only for explicit import or migration evidence",
        "implementation, generated fixture, target regex spelling, or runtime wrapper",
    ),
    "docs/tutorial/first_contribution.md": (
        "# Your First Semantic STRling Contribution",
        "semantic strling 1.0;",
        '"id": "strling.semantic"',
        "./strling compile < zip-request.json",
    ),
    "spec/README.md": (
        "**Semantic STRling** is the flagship textual authoring language.",
        "**Simply** is the semantic construction frontend",
        "**regex frontend** or **regex-compatible source dialect**",
    ),
    "spec/frontends/README.md": (
        "flagship Semantic STRling",
        "language and deterministic Semantic IR mapping",
        "regex-compatible import dialect",
        "host-neutral semantic builder construction",
    ),
    "spec/frontends/semantic/1.0/README.md": (
        "# Semantic STRling textual frontend 1.0",
        "certified consumers of this contract",
        "python3 tooling/semantic_strling_contract.py",
    ),
}
DOCUMENTATION_FORBIDDEN = (
    "Parser and formatter implementation is still pending.",
    "The exact source model, parser boundary, formatter contract, diagnostics, and production grammar are the next architecture task.",
    "Implement and test in TypeScript first.",
    "while the canonical compiler is not yet available",
    "Parse a DSL pattern string",
    "DSL String Parsing",
    "compile_pattern(\"digit(3) '-' digit(4)\")",
    'parse("digit(',
    "compile(\"capture('foo', digit(3))",
    "start capture(digit(3))",
    "pattern = digit(5)",
    "remain later implementation work",
    "All bindings (Python, Java, C, etc.) read these JSON files and assert that their parser produces the identical AST.",
    "Tests in both Python and JavaScript",
)
DOCUMENTATION_BINDINGS = (
    "bindings/fsharp/README.md",
    "bindings/java/README.md",
    "bindings/kotlin/README.md",
    "bindings/lua/README.md",
)

EXPECTED_CASES = 11
EXPECTED_LEGACY_CASES = 9
EXPECTED_HOST_ROUTES = (
    "rust-native",
    "typescript-preview",
    "python-preview",
)
EXPECTED_REPRESENTATION_EXCLUSIONS = (
    "node_id spelling",
    "capture_id spelling",
    "source documents",
    "node origins",
    "source locations",
)
SUPPORTED_LEGACY_STATUSES = {"accepted", "compatibility-only"}
ALLOWED_CLASSIFICATIONS = {
    "preserved_behavior",
    "intentional_specification_correction",
    "unsupported_legacy_behavior",
    "unresolved_discrepancy",
}


class FrontendConvergenceError(ValueError):
    """The convergence evidence is incomplete, stale, or over-normalized."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FrontendConvergenceError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise FrontendConvergenceError(f"{path}: root must be an object")
    return value


def _load_documentation(root: Path) -> dict[str, str]:
    documents: dict[str, str] = {}
    for relative_path in DOCUMENTATION_PATHS:
        path = root / relative_path
        try:
            documents[relative_path] = path.read_text(encoding="utf-8")
        except OSError as error:
            raise FrontendConvergenceError(f"cannot read {path}: {error}") from error
    return documents


def validate_documentation(documents: Mapping[str, str]) -> int:
    actual_paths = set(documents)
    expected_paths = set(DOCUMENTATION_PATHS)
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        raise FrontendConvergenceError(
            f"documentation denominator changed; missing={missing} extra={extra}"
        )

    for relative_path, required_snippets in DOCUMENTATION_REQUIRED.items():
        content = documents[relative_path]
        for snippet in required_snippets:
            if snippet not in content:
                raise FrontendConvergenceError(
                    f"{relative_path}: missing canonical documentation marker {snippet!r}"
                )

    for relative_path, content in documents.items():
        for snippet in DOCUMENTATION_FORBIDDEN:
            if snippet in content:
                raise FrontendConvergenceError(
                    f"{relative_path}: stale documentation marker {snippet!r}"
                )

    for relative_path in DOCUMENTATION_BINDINGS:
        content = documents[relative_path]
        for snippet in (
            "Migration status:",
            "compatibility evidence",
            "compiler boundary.",
            "Semantic STRling is the flagship textual language.",
            "Regex-compatible text is",
            "import/compatibility surface, not Semantic STRling.",
            "STRling 4.0 uses one canonical pipeline",
        ):
            if snippet not in content:
                raise FrontendConvergenceError(
                    f"{relative_path}: binding hierarchy marker {snippet!r} is absent"
                )

    tutorial = documents["docs/tutorial/first_contribution.md"]
    hierarchy = (
        "Semantic STRling for flagship textual intent",
        "Simply when the same intent is built programmatically",
        "regex-compatible source only for an explicit import obligation",
    )
    positions = [tutorial.find(marker) for marker in hierarchy]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise FrontendConvergenceError("tutorial authoring hierarchy changed")

    return len(documents)


def _mapping_ids(mapping: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for field in ("program_mappings", "node_mappings", "member_mappings"):
        entries = mapping.get(field)
        if not isinstance(entries, list):
            raise FrontendConvergenceError(f"semantic mapping {field} is invalid")
        for entry in entries:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("id"), str):
                raise FrontendConvergenceError(
                    f"semantic mapping {field} has invalid entry"
                )
            result.add(entry["id"])
    return result


def corpus_fingerprint(corpus: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(corpus))
    body.pop("corpus_fingerprint", None)
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


def build_builder_request(
    corpus: Mapping[str, Any],
    case: Mapping[str, Any],
    profile_reference: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "protocol_version": "1.0.0",
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "identity_namespace": case["identity_namespace"],
        "semantic_options": copy.deepcopy(case["semantic_options"]),
        "steps": copy.deepcopy(case["steps"]),
        "root_step_id": case["root_step_id"],
        "compile": {
            "target_profile": copy.deepcopy(profile_reference),
            "requested_outputs": copy.deepcopy(corpus["comparison_outputs"]),
            "compiler_options": copy.deepcopy(corpus["compiler_options"]),
        },
    }


def _profile_fingerprint(profile: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(profile)).hexdigest()


class FrontendConvergenceSuite:
    def __init__(
        self,
        root: Path = ROOT,
        corpus: Mapping[str, Any] | None = None,
        documents: Mapping[str, str] | None = None,
    ) -> None:
        self.root = root
        self.corpus = (
            copy.deepcopy(dict(corpus))
            if corpus is not None
            else _load_json(
                root / "tests" / "convergence" / "frontend-convergence.json"
            )
        )
        self.schema = _load_json(
            root / "tests" / "convergence" / "frontend-convergence.schema.json"
        )
        self.simply = _load_json(
            root / "spec" / "frontends" / "simply" / "1.0" / "protocol.json"
        )
        self.semantic = _load_json(
            root / "spec" / "frontends" / "semantic" / "1.0" / "mapping.json"
        )
        self.legacy = _load_json(
            root / "spec" / "frontends" / "legacy-regex" / "1.0" / "dialect.json"
        )
        self.documents = (
            copy.deepcopy(dict(documents))
            if documents is not None
            else _load_documentation(root)
        )

    def _validate_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.corpus),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            first = errors[0]
            path = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in first.absolute_path
            )
            raise FrontendConvergenceError(f"{path}: {first.message}")

    def _validate_profiles(self) -> None:
        seen: set[str] = set()
        for entry in self.corpus["target_profiles"]:
            path = self.root / entry["path"]
            profile = _load_json(path)
            reference = entry["reference"]
            profile_id = reference["profile_id"]
            if profile_id in seen:
                raise FrontendConvergenceError(f"duplicate target profile {profile_id}")
            seen.add(profile_id)
            if profile.get("profile_id") != profile_id:
                raise FrontendConvergenceError(
                    f"{profile_id}: profile identity mismatch"
                )
            if profile.get("profile_version") != reference["profile_version"]:
                raise FrontendConvergenceError(
                    f"{profile_id}: profile version mismatch"
                )
            if _profile_fingerprint(profile) != reference["sha256"]:
                raise FrontendConvergenceError(
                    f"{profile_id}: profile fingerprint mismatch"
                )

    def _validate_denominator(self) -> dict[str, Any]:
        if tuple(self.corpus["host_routes"]) != EXPECTED_HOST_ROUTES:
            raise FrontendConvergenceError("host route denominator changed")
        if (
            tuple(self.corpus["representation_exclusions"])
            != EXPECTED_REPRESENTATION_EXCLUSIONS
        ):
            raise FrontendConvergenceError("representation exclusions changed")
        cases = self.corpus["cases"]
        if len(cases) != EXPECTED_CASES:
            raise FrontendConvergenceError(
                f"expected {EXPECTED_CASES} convergence cases, found {len(cases)}"
            )
        case_ids = [case["id"] for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise FrontendConvergenceError("convergence case identities must be unique")
        semantic_sources = [case["semantic_source"] for case in cases]
        if len(semantic_sources) != len(set(semantic_sources)):
            raise FrontendConvergenceError("Semantic source cases must be unique")

        expected_operations = {entry["id"] for entry in self.simply["operations"]}
        expected_mappings = _mapping_ids(self.semantic)
        features = {entry["id"]: entry for entry in self.legacy["features"]}
        expected_supported = {
            feature_id
            for feature_id, entry in features.items()
            if entry["status"] in SUPPORTED_LEGACY_STATUSES
        }
        expected_rejected = {
            feature_id
            for feature_id, entry in features.items()
            if entry["status"] == "rejected"
        }
        expected_families = {
            entry["family"]
            for entry in features.values()
            if entry["status"] in SUPPORTED_LEGACY_STATUSES
        }

        actual_operations: set[str] = set()
        actual_mappings: set[str] = set()
        actual_supported: set[str] = set()
        actual_families: set[str] = set()
        legacy_cases = 0
        simply_suite = SimplyContractSuite()
        for case in cases:
            actual_operations.update(step["operation"] for step in case["steps"])
            actual_mappings.update(case["semantic_mapping_ids"])
            if not set(case["semantic_mapping_ids"]).issubset(expected_mappings):
                raise FrontendConvergenceError(
                    f"{case['id']}: unknown semantic mapping"
                )
            if case["root_step_id"] not in {step["step_id"] for step in case["steps"]}:
                raise FrontendConvergenceError(f"{case['id']}: root step is absent")
            for profile in self.corpus["target_profiles"]:
                request = build_builder_request(self.corpus, case, profile["reference"])
                try:
                    simply_suite.project_request(request)
                except SimplyContractError as error:
                    raise FrontendConvergenceError(
                        f"{case['id']}: invalid Simply request: {error}"
                    ) from error
            legacy = case.get("legacy")
            if legacy is not None:
                legacy_cases += 1
                if legacy["disposition"] not in ALLOWED_CLASSIFICATIONS:
                    raise FrontendConvergenceError(
                        f"{case['id']}: unknown legacy disposition"
                    )
                if legacy["disposition"] == "unresolved_discrepancy":
                    raise FrontendConvergenceError(
                        f"{case['id']}: unresolved legacy discrepancy blocks"
                    )
                for feature_id in legacy["feature_ids"]:
                    entry = features.get(feature_id)
                    if (
                        entry is None
                        or entry["status"] not in SUPPORTED_LEGACY_STATUSES
                    ):
                        raise FrontendConvergenceError(
                            f"{case['id']}: legacy feature {feature_id} is not supported"
                        )
                    actual_supported.add(feature_id)
                    actual_families.add(entry["family"])

        if legacy_cases != EXPECTED_LEGACY_CASES:
            raise FrontendConvergenceError(
                f"expected {EXPECTED_LEGACY_CASES} legacy convergence cases, found {legacy_cases}"
            )
        if actual_operations != expected_operations:
            missing = sorted(expected_operations - actual_operations)
            extra = sorted(actual_operations - expected_operations)
            raise FrontendConvergenceError(
                f"Simply operation coverage changed; missing={missing} extra={extra}"
            )
        if actual_mappings != expected_mappings:
            missing = sorted(expected_mappings - actual_mappings)
            extra = sorted(actual_mappings - expected_mappings)
            raise FrontendConvergenceError(
                f"Semantic mapping coverage changed; missing={missing} extra={extra}"
            )
        if actual_supported != expected_supported:
            missing = sorted(expected_supported - actual_supported)
            extra = sorted(actual_supported - expected_supported)
            raise FrontendConvergenceError(
                f"legacy supported-feature coverage changed; missing={missing} extra={extra}"
            )
        if actual_families != expected_families:
            raise FrontendConvergenceError("legacy family coverage changed")

        rejected = self.corpus["rejected_legacy_features"]
        actual_rejected = {entry["feature_id"] for entry in rejected}
        if len(actual_rejected) != len(rejected):
            raise FrontendConvergenceError(
                "rejected legacy classifications are duplicated"
            )
        if actual_rejected != expected_rejected:
            missing = sorted(expected_rejected - actual_rejected)
            extra = sorted(actual_rejected - expected_rejected)
            raise FrontendConvergenceError(
                f"rejected legacy classification coverage changed; missing={missing} extra={extra}"
            )
        for entry in rejected:
            if entry["disposition"] == "unresolved_discrepancy":
                raise FrontendConvergenceError(
                    f"{entry['feature_id']}: unresolved legacy discrepancy blocks"
                )
            if entry["disposition"] != "unsupported_legacy_behavior":
                raise FrontendConvergenceError(
                    f"{entry['feature_id']}: rejected legacy disposition changed"
                )

        return {
            "cases": len(cases),
            "host_routes": len(EXPECTED_HOST_ROUTES),
            "operations": len(expected_operations),
            "mappings": len(expected_mappings),
            "legacy_cases": legacy_cases,
            "legacy_features": len(expected_supported),
            "legacy_families": len(expected_families),
            "rejected": len(expected_rejected),
            "profiles": len(self.corpus["target_profiles"]),
        }

    def certify(self) -> dict[str, Any]:
        self._validate_schema()
        self._validate_profiles()
        result = self._validate_denominator()
        documents = validate_documentation(self.documents)
        expected = corpus_fingerprint(self.corpus)
        if self.corpus["corpus_fingerprint"] != expected:
            raise FrontendConvergenceError(
                "frontend convergence corpus fingerprint is stale"
            )
        return {**result, "documents": documents, "fingerprint": expected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate checked evidence"
    )
    parser.parse_args()
    try:
        result = FrontendConvergenceSuite().certify()
    except (FrontendConvergenceError, OSError, json.JSONDecodeError) as error:
        print(f"FRONTEND_CONVERGENCE status=failed error={error}")
        return 1
    print(
        "FRONTEND_CONVERGENCE status=passed "
        + " ".join(f"{key}={value}" for key, value in result.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
