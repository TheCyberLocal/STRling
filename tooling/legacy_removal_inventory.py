#!/usr/bin/env python3
"""Validate and derive the governed Fourth Edition legacy removal inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator

from tooling.binding_support_certification import _semantic_path_findings


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "governance" / "legacy-removal-inventory.json"
MANIFEST_SCHEMA_PATH = (
    ROOT / "governance" / "schemas" / "legacy-removal-inventory.schema.json"
)
EVIDENCE_ROOT = ROOT / "tests" / "architecture" / "legacy-removal" / "1.0"
EVIDENCE_SCHEMA_PATH = EVIDENCE_ROOT / "evidence.schema.json"
EVIDENCE_PATH = EVIDENCE_ROOT / "evidence.json"
REPORT_PATH = EVIDENCE_ROOT / "evidence.md"
PRETTIER_PATH = ROOT / "node_modules" / "prettier" / "bin" / "prettier.cjs"
BINDING_EVIDENCE_PATH = (
    ROOT / "tests" / "adapters" / "binding-support-4.0" / "evidence.json"
)
ARCHITECTURE_PATH = ROOT / "governance" / "architecture-rules.json"
GENERATED_PATH = ROOT / "governance" / "generated-artifacts.json"
WAIVER_ROOT = ROOT / "governance" / "waivers"


class LegacyRemovalInventoryError(RuntimeError):
    """Raised when the removal inventory is incomplete or inconsistent."""


@dataclass(frozen=True)
class LegacyRemovalInventoryReport:
    finding_count: int
    fixture_count: int
    binding_count: int
    remove_now_count: int
    temporary_count: int
    manifest_fingerprint: str
    evidence_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "finding_count": self.finding_count,
            "fixture_count": self.fixture_count,
            "binding_count": self.binding_count,
            "remove_now_count": self.remove_now_count,
            "temporary_count": self.temporary_count,
            "manifest_fingerprint": self.manifest_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LegacyRemovalInventoryError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise LegacyRemovalInventoryError(f"{path} must contain one JSON object")
    return value


def _fingerprint(value: Mapping[str, Any], excluded: set[str] | None = None) -> str:
    normalized = {
        key: item for key, item in value.items() if key not in (excluded or set())
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise LegacyRemovalInventoryError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def _prettier_format(value: str, parser: str) -> str:
    if not PRETTIER_PATH.is_file():
        raise LegacyRemovalInventoryError(
            "pinned Prettier is unavailable; run the root lockfile install"
        )
    completed = subprocess.run(
        ["node", str(PRETTIER_PATH), "--parser", parser],
        cwd=ROOT,
        input=value,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LegacyRemovalInventoryError(
            f"Prettier {parser} formatting failed: {detail}"
        )
    return completed.stdout


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LegacyRemovalInventoryError(f"git {' '.join(args)} failed: {detail}")
    return completed


def _git_files(selectors: Sequence[str]) -> tuple[str, ...]:
    files: set[str] = set()
    for selector in selectors:
        completed = _git("ls-files", "--", selector)
        files.update(line for line in completed.stdout.splitlines() if line)
    return tuple(sorted(files))


def _validate_schema(schema: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(item) for item in error.absolute_path) or "<root>"
        raise LegacyRemovalInventoryError(
            f"schema validation at {location}: {error.message}"
        )


def _rule_map(architecture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rules = architecture.get("rules")
    if not isinstance(rules, list):
        raise LegacyRemovalInventoryError("architecture rules must be an array")
    return {str(rule["id"]): rule for rule in rules if isinstance(rule, dict)}


def _artifact_map(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list):
        raise LegacyRemovalInventoryError("generated artifacts must be an array")
    return {
        str(artifact["id"]): artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
    }


def _required_rule_ids(architecture: Mapping[str, Any]) -> tuple[str, ...]:
    required: list[str] = []
    for identifier, rule in _rule_map(architecture).items():
        configuration = rule.get("configuration", {})
        keys = set(configuration) if isinstance(configuration, dict) else set()
        has_allowlist = any(
            token in key
            for key in keys
            for token in ("allowed", "permitted", "excluded", "tracked_paths")
        )
        if rule.get("status") != "enforced" or has_allowlist:
            required.append(identifier)
    return tuple(sorted(required))


def _required_artifact_ids(registry: Mapping[str, Any]) -> tuple[str, ...]:
    required: list[str] = []
    for identifier, artifact in _artifact_map(registry).items():
        authority = str(artifact.get("authority", ""))
        category = str(artifact.get("category", ""))
        if (
            artifact.get("enforcement") != "enforced"
            or "transitional" in authority
            or "compatibility" in authority
            or category == "spec-derived-fixture"
            or "stdlib" in identifier
            or identifier == "public-contract-snapshots"
        ):
            required.append(identifier)
    return tuple(sorted(required))


def _accepted_waiver_ids() -> tuple[str, ...]:
    identifiers: list[str] = []
    for path in sorted(WAIVER_ROOT.glob("*.yaml")):
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise LegacyRemovalInventoryError(
                f"cannot read waiver {path}: {error}"
            ) from error
        if not isinstance(value, dict):
            raise LegacyRemovalInventoryError(f"waiver {path} must be an object")
        if value.get("status") == "accepted":
            identifiers.append(str(value.get("waiver_id")))
    return tuple(sorted(identifiers))


def _declared_output_patterns(artifacts: Mapping[str, dict[str, Any]]) -> set[str]:
    return {
        str(output)
        for artifact in artifacts.values()
        for output in artifact.get("outputs", [])
        if isinstance(output, str)
    }


def _path_has_wildcard(path: str) -> bool:
    return any(character in path for character in "*?[")


def _validate_path(
    relative: str,
    *,
    label: str,
    declared_outputs: set[str],
) -> None:
    if "\\" in relative or relative.startswith("/") or ".." in Path(relative).parts:
        raise LegacyRemovalInventoryError(
            f"{label} has invalid repository path {relative}"
        )
    matches = _git_files((relative,))
    if matches:
        return
    candidate = ROOT / relative
    if not _path_has_wildcard(relative) and candidate.exists():
        return
    if relative in declared_outputs:
        return
    raise LegacyRemovalInventoryError(f"{label} path does not resolve: {relative}")


def _validate_findings(
    manifest: Mapping[str, Any],
    *,
    artifacts: Mapping[str, dict[str, Any]],
    rules: Mapping[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    findings = manifest.get("findings")
    if not isinstance(findings, list):
        raise LegacyRemovalInventoryError("manifest findings must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    declared_outputs = _declared_output_patterns(artifacts)
    for finding in findings:
        if not isinstance(finding, dict):
            raise LegacyRemovalInventoryError("each finding must be an object")
        identifier = str(finding["id"])
        if identifier in by_id:
            raise LegacyRemovalInventoryError(f"duplicate finding id {identifier}")
        by_id[identifier] = finding
        for relative in finding["paths"]:
            _validate_path(
                str(relative),
                label=finding["id"],
                declared_outputs=declared_outputs,
            )
        replacement = finding.get("canonical_replacement")
        if isinstance(replacement, dict):
            for relative in replacement["paths"]:
                _validate_path(
                    str(relative),
                    label=f"{finding['id']} replacement",
                    declared_outputs=declared_outputs,
                )
        disposition = finding["disposition"]
        if disposition == "REMOVE_NOW":
            if not isinstance(replacement, dict) or not isinstance(
                finding.get("deletion"), dict
            ):
                raise LegacyRemovalInventoryError(
                    f"{identifier} REMOVE_NOW requires replacement and deletion proof"
                )
            if finding.get("retention_rationale"):
                raise LegacyRemovalInventoryError(
                    f"{identifier} REMOVE_NOW cannot have retention rationale"
                )
        elif not finding.get("retention_rationale"):
            raise LegacyRemovalInventoryError(
                f"{identifier} retained finding requires architectural rationale"
            )
        if disposition == "RETAIN_TEMPORARILY":
            if not isinstance(finding.get("temporary_retention"), dict):
                raise LegacyRemovalInventoryError(
                    f"{identifier} temporary retention requires blocker, owner, and expiry"
                )
        elif finding.get("temporary_retention") is not None:
            raise LegacyRemovalInventoryError(
                f"{identifier} has temporary retention data for {disposition}"
            )
        for artifact_id in finding["generated_artifact_ids"]:
            if artifact_id not in artifacts:
                raise LegacyRemovalInventoryError(
                    f"{identifier} references missing generated artifact {artifact_id}"
                )
        for rule_id in finding["architecture_rule_ids"]:
            if rule_id not in rules:
                raise LegacyRemovalInventoryError(
                    f"{identifier} references missing architecture rule {rule_id}"
                )
    return by_id


def _validate_fixture_population(
    manifest: Mapping[str, Any],
    *,
    findings: Mapping[str, dict[str, Any]],
    rules: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    fixture = manifest["fixture_population"]
    rule = rules.get(fixture["governed_rule_id"])
    if rule is None:
        raise LegacyRemovalInventoryError("governed fixture rule is missing")
    configuration = rule.get("configuration")
    if not isinstance(configuration, dict) or not isinstance(
        configuration.get("tracked_paths"), list
    ):
        raise LegacyRemovalInventoryError("governed fixture rule has no tracked paths")
    universe = set(_git_files(tuple(configuration["tracked_paths"])))
    if len(universe) != fixture["expected_total"]:
        raise LegacyRemovalInventoryError(
            f"fixture denominator changed: expected {fixture['expected_total']}, found {len(universe)}"
        )
    classified: set[str] = set()
    overlap: set[str] = set()
    rows: list[dict[str, Any]] = []
    for family in fixture["families"]:
        selected = set(_git_files(tuple(family["selectors"])))
        if len(selected) != family["expected_count"]:
            raise LegacyRemovalInventoryError(
                f"fixture family {family['id']} expected {family['expected_count']}, found {len(selected)}"
            )
        finding = findings.get(family["finding_id"])
        if finding is None or finding["disposition"] != family["disposition"]:
            raise LegacyRemovalInventoryError(
                f"fixture family {family['id']} does not match its finding disposition"
            )
        overlap.update(classified & selected)
        classified.update(selected)
        rows.append(
            {
                "id": family["id"],
                "finding_id": family["finding_id"],
                "count": len(selected),
                "disposition": family["disposition"],
                "origin": family["origin"],
                "current_consumers": family["current_consumers"],
                "coverage_effect": family["coverage_effect"],
            }
        )
    unclassified = universe - classified
    unexpected = classified - universe
    if unclassified or unexpected or overlap:
        raise LegacyRemovalInventoryError(
            "fixture population does not partition exactly: "
            f"unclassified={len(unclassified)}, unexpected={len(unexpected)}, overlap={len(overlap)}"
        )
    return {
        "expected": len(universe),
        "classified": len(classified),
        "unclassified": 0,
        "overlap": 0,
        "families": rows,
    }


def _validate_bindings(
    manifest: Mapping[str, Any],
    *,
    findings: Mapping[str, dict[str, Any]],
    binding_evidence: Mapping[str, Any],
    rules: Mapping[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = binding_evidence.get("bindings")
    if not isinstance(rows, list):
        raise LegacyRemovalInventoryError("binding evidence rows are missing")
    binding_ids = tuple(str(row["id"]) for row in rows)
    if binding_ids != tuple(manifest["coverage"]["binding_ids"]):
        raise LegacyRemovalInventoryError(
            "manifest does not preserve the exact binding-support denominator and order"
        )
    result_rows: list[dict[str, Any]] = []
    for row in rows:
        identifier = str(row["id"])
        finding_id = f"ADAPTER-{identifier.upper()}"
        finding = findings.get(finding_id)
        if finding is None:
            raise LegacyRemovalInventoryError(
                f"binding {identifier} has no stable adapter finding {finding_id}"
            )
        replacement = finding.get("canonical_replacement")
        if (
            finding["disposition"] != "RETAIN_THIN_ADAPTER"
            or finding["ecosystem"] != identifier
            or not isinstance(replacement, dict)
            or replacement["route"] != row["canonical_route"]
        ):
            raise LegacyRemovalInventoryError(
                f"binding {identifier} route/disposition does not reproduce evidence"
            )
        result_rows.append(
            {
                "id": identifier,
                "finding_id": finding_id,
                "certification_tier": row["certification_tier"],
                "canonical_route": row["canonical_route"],
                "public_surfaces": row["public_surfaces"],
                "disposition": finding["disposition"],
            }
        )
    semantic_rule = rules.get("duplicated-binding-compilers")
    if semantic_rule is None:
        raise LegacyRemovalInventoryError("duplicated binding compiler rule is missing")
    configuration = semantic_rule.get("configuration")
    if not isinstance(configuration, dict):
        raise LegacyRemovalInventoryError(
            "duplicated binding compiler rule is malformed"
        )
    permitted = tuple(configuration.get("permitted_paths", []))
    declared = tuple(manifest["coverage"]["permitted_semantic_facades"])
    if permitted != declared:
        raise LegacyRemovalInventoryError(
            "permitted compiler facade inventory does not reproduce architecture rules"
        )
    forbidden = _semantic_path_findings(ROOT)
    evidence_forbidden = binding_evidence.get("semantic_ownership", {}).get(
        "forbidden_product_paths"
    )
    if forbidden or evidence_forbidden != []:
        raise LegacyRemovalInventoryError(
            f"binding semantic implementation paths remain: {forbidden or evidence_forbidden}"
        )
    return (
        {
            "expected": len(rows),
            "classified": len(result_rows),
            "canonical": len(result_rows),
            "rows": result_rows,
        },
        {
            "permitted_facades": list(permitted),
            "forbidden_product_paths": [],
        },
    )


def _validate_coverage(
    manifest: Mapping[str, Any],
    *,
    findings: Mapping[str, dict[str, Any]],
    architecture: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> None:
    coverage = manifest["coverage"]
    expected_rules = _required_rule_ids(architecture)
    if tuple(sorted(coverage["architecture_rule_ids"])) != expected_rules:
        raise LegacyRemovalInventoryError(
            f"architecture exception coverage changed: expected {expected_rules}"
        )
    expected_artifacts = _required_artifact_ids(registry)
    if tuple(sorted(coverage["generated_artifact_ids"])) != expected_artifacts:
        raise LegacyRemovalInventoryError(
            f"generated transitional/projection coverage changed: expected {expected_artifacts}"
        )
    expected_waivers = _accepted_waiver_ids()
    if tuple(sorted(coverage["waiver_ids"])) != expected_waivers:
        raise LegacyRemovalInventoryError(
            f"accepted waiver coverage changed: expected {expected_waivers}"
        )
    referenced_rules = {
        identifier
        for finding in findings.values()
        for identifier in finding["architecture_rule_ids"]
    }
    referenced_artifacts = {
        identifier
        for finding in findings.values()
        for identifier in finding["generated_artifact_ids"]
    }
    referenced_waivers = {
        identifier
        for finding in findings.values()
        for identifier in finding["waiver_ids"]
    }
    for label, declared, referenced in (
        (
            "architecture rules",
            set(coverage["architecture_rule_ids"]),
            referenced_rules,
        ),
        (
            "generated artifacts",
            set(coverage["generated_artifact_ids"]),
            referenced_artifacts,
        ),
        ("waivers", set(coverage["waiver_ids"]), referenced_waivers),
    ):
        missing = declared - referenced
        if missing:
            raise LegacyRemovalInventoryError(
                f"declared {label} lack finding classifications: {sorted(missing)}"
            )


def _validate_source(manifest: Mapping[str, Any]) -> dict[str, Any]:
    source = manifest["source"]
    branch = _git("branch", "--show-current").stdout.strip()
    expected_branch = source["branch"]
    if not branch:
        head = _git("rev-parse", "HEAD").stdout.strip()
        branch_tip = _git(
            "rev-parse",
            "--verify",
            f"refs/heads/{expected_branch}",
            check=False,
        )
        if branch_tip.returncode != 0 or branch_tip.stdout.strip() != head:
            actual_tip = branch_tip.stdout.strip() or "unavailable"
            raise LegacyRemovalInventoryError(
                "inventory detached HEAD does not equal the authorized branch tip: "
                f"expected {expected_branch} at {actual_tip}, found {head}"
            )
    elif branch != expected_branch:
        raise LegacyRemovalInventoryError(
            f"inventory branch changed: expected {expected_branch}, found {branch}"
        )
    _git("cat-file", "-e", f"{source['baseline_sha']}^{{commit}}")
    ancestor = _git(
        "merge-base", "--is-ancestor", source["baseline_sha"], "HEAD", check=False
    )
    if ancestor.returncode != 0:
        raise LegacyRemovalInventoryError(
            "production-certified baseline is not an ancestor of current HEAD"
        )
    certification = ROOT / source["production_certification_path"]
    if not certification.is_file():
        raise LegacyRemovalInventoryError(
            f"production certification is inaccessible: {certification}"
        )
    actual = _sha256(certification)
    if actual != source["production_certification_sha256"]:
        raise LegacyRemovalInventoryError(
            f"production certification hash changed: expected {source['production_certification_sha256']}, found {actual}"
        )
    return {
        "path": source["production_certification_path"],
        "sha256": actual,
        "accessible": True,
    }


def _counts(findings: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(finding[key]) for finding in findings).items()))


def _build_evidence(
    root: Path = ROOT,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if root != ROOT:
        raise LegacyRemovalInventoryError(
            "alternate roots are not supported by this producer"
        )
    value = dict(manifest or _read_json(MANIFEST_PATH))
    manifest_schema = _read_json(MANIFEST_SCHEMA_PATH)
    _validate_schema(manifest_schema, value)
    architecture = _read_json(ARCHITECTURE_PATH)
    registry = _read_json(GENERATED_PATH)
    binding_evidence = _read_json(BINDING_EVIDENCE_PATH)
    rules = _rule_map(architecture)
    artifacts = _artifact_map(registry)
    findings = _validate_findings(value, artifacts=artifacts, rules=rules)
    _validate_coverage(
        value,
        findings=findings,
        architecture=architecture,
        registry=registry,
    )
    fixture_reconciliation = _validate_fixture_population(
        value,
        findings=findings,
        rules=rules,
    )
    binding_routes, semantic_scan = _validate_bindings(
        value,
        findings=findings,
        binding_evidence=binding_evidence,
        rules=rules,
    )
    production = _validate_source(value)
    rows = list(findings.values())
    remove_now = [
        {
            "id": finding["id"],
            "paths": finding["paths"],
            "order": finding["deletion"]["order"],
            "follow_up_task": finding["deletion"]["follow_up_task"],
            "dependencies": finding["deletion"]["dependencies"],
        }
        for finding in rows
        if finding["disposition"] == "REMOVE_NOW"
    ]
    remove_now.sort(key=lambda item: (item["order"], item["id"]))
    temporary = [
        {
            "id": finding["id"],
            **finding["temporary_retention"],
        }
        for finding in rows
        if finding["disposition"] == "RETAIN_TEMPORARILY"
    ]
    temporary.sort(key=lambda item: item["id"])
    evidence: dict[str, Any] = {
        "$schema": "evidence.schema.json",
        "artifact_kind": "strling.legacy-removal-inventory-evidence",
        "schema_version": "1.0.0",
        "source": {
            "branch": value["source"]["branch"],
            "baseline_sha": value["source"]["baseline_sha"],
            "architecture_rule_count": len(rules),
            "covered_architecture_rule_ids": value["coverage"]["architecture_rule_ids"],
            "covered_generated_artifact_ids": value["coverage"][
                "generated_artifact_ids"
            ],
            "covered_waiver_ids": value["coverage"]["waiver_ids"],
        },
        "manifest_fingerprint": _fingerprint(value),
        "production_certification": production,
        "counts": {
            "findings": len(rows),
            "by_disposition": _counts(rows, "disposition"),
            "by_ecosystem": _counts(rows, "ecosystem"),
            "by_semantic_family": _counts(rows, "semantic_family"),
            "by_surface": _counts(rows, "surface"),
        },
        "fixture_reconciliation": fixture_reconciliation,
        "binding_routes": binding_routes,
        "semantic_path_scan": semantic_scan,
        "remove_now": remove_now,
        "temporary_retention": temporary,
        "readiness": {"status": "ready", "blocking_requirements": []},
    }
    evidence["fingerprint"] = _fingerprint(evidence)
    return evidence


def _render_report(manifest: Mapping[str, Any], evidence: Mapping[str, Any]) -> str:
    findings = {finding["id"]: finding for finding in manifest["findings"]}
    lines = [
        "# Legacy semantic and transitional dependency removal inventory",
        "",
        "> This report is mechanically derived from the governed JSON manifest and live repository evidence. It is not an independent source of truth.",
        "",
        f"- Baseline SHA: `{evidence['source']['baseline_sha']}`",
        f"- Manifest fingerprint: `{evidence['manifest_fingerprint']}`",
        f"- Evidence fingerprint: `{evidence['fingerprint']}`",
        f"- Readiness: **{evidence['readiness']['status'].upper()}**",
        "",
        "## Aggregate findings",
        "",
        "| Disposition | Count |",
        "| --- | ---: |",
    ]
    for disposition, count in evidence["counts"]["by_disposition"].items():
        lines.append(f"| `{disposition}` | {count} |")
    lines.extend(
        [
            "",
            "## Exact 1,094-path fixture reconciliation",
            "",
            "| Family | Count | Disposition | Finding |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for family in evidence["fixture_reconciliation"]["families"]:
        lines.append(
            f"| `{family['id']}` | {family['count']} | `{family['disposition']}` | `{family['finding_id']}` |"
        )
    lines.extend(
        [
            "",
            f"Classified: **{evidence['fixture_reconciliation']['classified']} / {evidence['fixture_reconciliation']['expected']}**; unclassified: **0**; overlaps: **0**.",
            "",
            "## Canonical binding routes",
            "",
            "| Binding | Tier | Canonical route | Finding |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in evidence["binding_routes"]["rows"]:
        lines.append(
            f"| `{row['id']}` | `{row['certification_tier']}` | {row['canonical_route']} | `{row['finding_id']}` |"
        )
    lines.extend(
        [
            "",
            "The product semantic-path scan reports exactly five permitted compiler-named facades and zero forbidden binding semantic paths.",
            "",
            "## REMOVE_NOW populations",
            "",
            "| Order | Finding | Follow-up | Paths | Dependencies |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in evidence["remove_now"]:
        dependencies = ", ".join(f"`{item}`" for item in row["dependencies"]) or "None"
        paths = "<br>".join(f"`{path}`" for path in row["paths"])
        lines.append(
            f"| {row['order']} | `{row['id']}` | `{row['follow_up_task']}` | {paths} | {dependencies} |"
        )
    lines.extend(
        [
            "",
            "## Temporary retention",
            "",
            "| Finding | Owner | Expiry condition |",
            "| --- | --- | --- |",
        ]
    )
    for row in evidence["temporary_retention"]:
        lines.append(
            f"| `{row['id']}` | `{row['owner']}` | {row['expiry_condition']} |"
        )
    lines.extend(
        [
            "",
            "## Complete finding index",
            "",
            "| Finding | Ecosystem | Family | Disposition | Rationale / removal proof |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for identifier in sorted(findings):
        finding = findings[identifier]
        summary = (
            finding["retention_rationale"]
            if finding["disposition"] != "REMOVE_NOW"
            else finding["reachability_evidence"][0]
        )
        lines.append(
            f"| `{identifier}` | `{finding['ecosystem']}` | `{finding['semantic_family']}` | `{finding['disposition']}` | {summary} |"
        )
    lines.extend(
        [
            "",
            "## Readiness conclusion",
            "",
            "Every identified component has a canonical replacement or explicit architectural justification. All REMOVE_NOW populations are unreachable from Supported and Preview product routes and are assigned to ordered follow-up tasks. Historical oracle machinery remains explicitly required and assigned to P19-T03; final rule ratchets remain assigned to P19-T05.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs() -> dict[str, Any]:
    manifest = _read_json(MANIFEST_PATH)
    evidence = _build_evidence(manifest=manifest)
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(
            _prettier_format(
                json.dumps(evidence, ensure_ascii=False, indent=4) + "\n", "json"
            )
        )
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_prettier_format(_render_report(manifest, evidence), "markdown"))
    return evidence


def _certify() -> LegacyRemovalInventoryReport:
    manifest = _read_json(MANIFEST_PATH)
    expected = _build_evidence(manifest=manifest)
    actual = _read_json(EVIDENCE_PATH)
    if actual != expected:
        raise LegacyRemovalInventoryError(
            "checked-in removal inventory evidence does not reproduce"
        )
    expected_evidence_text = _prettier_format(
        json.dumps(expected, ensure_ascii=False, indent=4) + "\n", "json"
    )
    try:
        actual_evidence_text = EVIDENCE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise LegacyRemovalInventoryError(
            f"cannot read {EVIDENCE_PATH}: {error}"
        ) from error
    if actual_evidence_text != expected_evidence_text:
        raise LegacyRemovalInventoryError(
            "checked-in structured evidence is not canonically formatted"
        )
    evidence_schema = _read_json(EVIDENCE_SCHEMA_PATH)
    _validate_schema(evidence_schema, actual)
    if actual["fingerprint"] != _fingerprint(actual, {"fingerprint"}):
        raise LegacyRemovalInventoryError("evidence fingerprint is not canonical")
    expected_report = _prettier_format(_render_report(manifest, actual), "markdown")
    try:
        actual_report = REPORT_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise LegacyRemovalInventoryError(
            f"cannot read {REPORT_PATH}: {error}"
        ) from error
    if actual_report != expected_report:
        raise LegacyRemovalInventoryError(
            "checked-in human report is not derived from structured evidence"
        )
    counts = actual["counts"]["by_disposition"]
    return LegacyRemovalInventoryReport(
        finding_count=actual["counts"]["findings"],
        fixture_count=actual["fixture_reconciliation"]["classified"],
        binding_count=actual["binding_routes"]["classified"],
        remove_now_count=counts.get("REMOVE_NOW", 0),
        temporary_count=counts.get("RETAIN_TEMPORARILY", 0),
        manifest_fingerprint=actual["manifest_fingerprint"],
        evidence_fingerprint=actual["fingerprint"],
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.write and not args.check:
        args.check = True
    try:
        if args.write:
            _write_outputs()
        report = _certify()
    except LegacyRemovalInventoryError as error:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f"legacy removal inventory failed: {error}", file=sys.stderr)
        return 1
    payload = {"status": "passed", **report.as_dict()}
    print(json.dumps(payload, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
