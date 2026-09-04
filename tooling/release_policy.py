#!/usr/bin/env python3
"""Validate and project the authoritative STRling product release policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "governance/release-policy.json"
SCHEMA_PATH = ROOT / "governance/schemas/release-policy.schema.json"
DOCUMENT_PATH = ROOT / "docs/release-policy.md"
SUPPORT_MANIFEST_PATH = ROOT / "tests/adapters/binding-support-4.0/manifest.json"
SUPPLY_CHAIN_PATH = ROOT / "tests/certification/release-supply-chain/1.0/manifest.json"

SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ReleasePolicyError(ValueError):
    """Raised when policy or a governed projection violates the contract."""


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[str, ...]

    @property
    def status(self) -> str:
        return "passed" if not self.findings else "failed"

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": "release-policy",
            "status": self.status,
            "finding_count": len(self.findings),
            "findings": list(self.findings),
        }


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePolicyError(f"cannot read {path}: {exc}") from exc


def load_policy(
    policy_path: Path = POLICY_PATH, schema_path: Path = SCHEMA_PATH
) -> dict[str, object]:
    policy = _load_json(policy_path)
    schema = _load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ReleasePolicyError(
            f"malformed release-policy schema: {exc.message}"
        ) from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(policy),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ReleasePolicyError(f"malformed release policy: {rendered}")
    assert isinstance(policy, dict)
    return policy


def _unique_ids(records: object, label: str, findings: list[str]) -> set[str]:
    assert isinstance(records, list)
    ids = [str(record["id"]) for record in records]
    duplicates = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    if duplicates:
        findings.append(
            f"RP-ID-001 {label}: duplicate registrations {', '.join(duplicates)}"
        )
    return set(ids)


def _json_pointer(document: object, pointer: str) -> object:
    current = document
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise KeyError(pointer)
    return current


def _observed_surface_version(root: Path, surface: Mapping[str, object]) -> str | None:
    probe = surface["probe"]
    assert isinstance(probe, dict)
    kind = str(probe["kind"])
    path = root / str(surface["path"])
    if not path.is_file():
        raise ReleasePolicyError(
            f"RP-VERSION-002 {surface['id']}: registered version surface is missing: "
            f"{surface['path']}"
        )
    if kind == "tag":
        return None
    if kind == "json":
        document = _load_json(path)
        return str(_json_pointer(document, str(probe["pointer"])))
    if kind == "absent":
        document = _load_json(path)
        try:
            _json_pointer(document, str(probe["pointer"]))
        except (KeyError, IndexError):
            return None
        raise ReleasePolicyError(
            f"RP-VERSION-008 {surface['id']}: non-release manifest must not "
            f"declare {probe['pointer']} in {surface['path']}"
        )
    pattern = re.compile(str(probe["pattern"]))
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None or match.lastindex != 1:
        raise ReleasePolicyError(
            f"RP-VERSION-003 {surface['id']}: probe did not select exactly one version "
            f"from {surface['path']}"
        )
    return match.group(1)


def _validate_versions(
    root: Path, policy: Mapping[str, object], findings: list[str]
) -> None:
    product = policy["product"]
    assert isinstance(product, dict)
    product_version = str(product["version"])
    projection = product["repository_projection"]
    assert isinstance(projection, dict)
    projection_version = str(projection["version"])
    projection_status = str(projection["status"])
    if not SEMVER_RE.fullmatch(product_version):
        findings.append(f"RP-VERSION-001 product: invalid SemVer {product_version!r}")
    if projection_status == "active" and projection_version != product_version:
        findings.append(
            "RP-VERSION-004 product: active repository projection must equal the "
            f"product version {product_version}, observed {projection_version}"
        )

    surfaces = policy["version_surfaces"]
    assert isinstance(surfaces, list)
    _unique_ids(surfaces, "version surfaces", findings)
    for raw_surface in surfaces:
        assert isinstance(raw_surface, dict)
        surface: Mapping[str, object] = raw_surface
        try:
            observed = _observed_surface_version(root, surface)
        except (ReleasePolicyError, KeyError, IndexError, ValueError) as exc:
            findings.append(str(exc))
            continue
        declared = surface["current_version"]
        if observed != declared:
            findings.append(
                f"RP-VERSION-005 {surface['id']}: {surface['path']} declares "
                f"{observed!r}; inventory records {declared!r}"
            )
        probe = surface["probe"]
        assert isinstance(probe, dict)
        expected = str(probe["expected"])
        expected_value = (
            projection_version if expected == "repository_projection" else expected
        )
        if observed is not None and observed != expected_value:
            findings.append(
                f"RP-VERSION-006 {surface['id']}: expected {expected_value!r} from "
                f"{surface['authority']}; observed {observed!r} at {surface['path']}"
            )
        if surface["coordinates_with_product"] and surface["independently_versioned"]:
            findings.append(
                f"RP-VERSION-007 {surface['id']}: a product-coordinated surface "
                "cannot also be independently versioned"
            )


def _validate_support(
    root: Path, policy: Mapping[str, object], findings: list[str]
) -> None:
    tiers = policy["support_tiers"]
    assert isinstance(tiers, list)
    tier_ids = _unique_ids(tiers, "support tiers", findings)
    if tier_ids != {"Supported", "Preview", "Legacy"}:
        findings.append(
            "RP-SUPPORT-001 support tiers: expected exactly Supported, Preview, and "
            f"Legacy; observed {', '.join(sorted(tier_ids))}"
        )

    claims = policy["support_claims"]
    assert isinstance(claims, list)
    _unique_ids(claims, "support claims", findings)
    claim_by_id = {str(claim["id"]): claim for claim in claims}
    for claim in claims:
        assert isinstance(claim, dict)
        if (
            claim["tier"] == "Supported"
            and claim["certification_status"] != "certified"
        ):
            findings.append(
                f"RP-SUPPORT-002 {claim['id']}: Supported requires certified evidence; "
                f"observed {claim['certification_status']}"
            )
        for evidence in claim["evidence"]:
            evidence_text = str(evidence)
            if evidence_text.startswith(("tests/", "spec/", "governance/", "tooling/")):
                if not (root / evidence_text).exists():
                    findings.append(
                        f"RP-SUPPORT-003 {claim['id']}: evidence path does not exist: "
                        f"{evidence_text}"
                    )

    manifest = _load_json(root / SUPPORT_MANIFEST_PATH.relative_to(ROOT))
    assert isinstance(manifest, dict)
    bindings = manifest["bindings"]
    assert isinstance(bindings, list)
    allowed_tiers = {
        "supported_candidate": {"Supported", "Preview", "Legacy"},
        "preview_candidate": {"Preview", "Legacy"},
        "legacy_candidate": {"Legacy"},
    }
    manifest_ids = set()
    for binding in bindings:
        assert isinstance(binding, dict)
        binding_id = str(binding["id"])
        manifest_ids.add(binding_id)
        claim_id = f"binding:{binding_id}"
        claim = claim_by_id.get(claim_id)
        if claim is None:
            findings.append(
                f"RP-SUPPORT-004 {claim_id}: registered binding route has no public "
                "support classification"
            )
            continue
        candidate = str(binding["certification_tier"])
        if claim["tier"] not in allowed_tiers.get(candidate, set()):
            findings.append(
                f"RP-SUPPORT-005 {claim_id}: {candidate} evidence cannot ratify "
                f"{claim['tier']}; allowed={sorted(allowed_tiers.get(candidate, set()))}"
            )
    claim_binding_ids = {
        str(claim_id).split(":", 1)[1]
        for claim_id in claim_by_id
        if claim_id.startswith("binding:")
    }
    unregistered = sorted(claim_binding_ids - manifest_ids)
    if unregistered:
        findings.append(
            "RP-SUPPORT-006 bindings: support claims lack registered routes: "
            + ", ".join(unregistered)
        )

    target_profiles = sorted((root / "spec/targets/profiles").glob("*.json"))
    target_evidence = {
        str(evidence)
        for claim in claims
        if claim["dimension"] == "target-profile"
        for evidence in claim["evidence"]
        if str(evidence).startswith("spec/targets/profiles/")
    }
    registered_profiles = {
        path.relative_to(root).as_posix() for path in target_profiles
    }
    if target_evidence != registered_profiles:
        findings.append(
            "RP-SUPPORT-007 target profiles: every governed profile must have exactly "
            f"one support claim; missing={sorted(registered_profiles - target_evidence)}, "
            f"unknown={sorted(target_evidence - registered_profiles)}"
        )


def _validate_lifecycle(policy: Mapping[str, object], findings: list[str]) -> None:
    channels = policy["release_channels"]
    assert isinstance(channels, list)
    channel_ids = _unique_ids(channels, "release channels", findings)
    if channel_ids != {"development", "release-candidate", "stable"}:
        findings.append(
            "RP-LIFECYCLE-004 release channels: retained channels must be exactly "
            f"development, release-candidate, and stable; observed={sorted(channel_ids)}"
        )
    excluded = policy["excluded_release_channels"]
    assert isinstance(excluded, list)
    excluded_ids = _unique_ids(excluded, "excluded release channels", findings)
    if excluded_ids != {"alpha", "beta"}:
        findings.append(
            "RP-LIFECYCLE-003 release channels: alpha and beta must be explicitly "
            f"retained or excluded; excluded={sorted(excluded_ids)}"
        )
    lifecycle = policy["release_lifecycle"]
    assert isinstance(lifecycle, dict)
    states = lifecycle["states"]
    assert isinstance(states, list)
    state_ids = _unique_ids(states, "release states", findings)
    expected_states = {
        "source-candidate",
        "deterministic-verified",
        "certified",
        "publishable",
        "published",
        "verified",
    }
    if state_ids != expected_states:
        findings.append(
            "RP-LIFECYCLE-001 release states: expected canonical six-state model; "
            f"observed {', '.join(sorted(state_ids))}"
        )
    transitions = lifecycle["transitions"]
    assert isinstance(transitions, list)
    observed = {(str(item["from"]), str(item["to"])) for item in transitions}
    expected = {
        ("source-candidate", "deterministic-verified"),
        ("deterministic-verified", "certified"),
        ("certified", "publishable"),
        ("publishable", "published"),
        ("published", "verified"),
    }
    if observed != expected:
        findings.append(
            "RP-LIFECYCLE-002 transitions: only the ordered candidate-to-verified "
            f"chain is allowed; observed {sorted(observed)}"
        )
    publication = policy["publication"]
    assert isinstance(publication, dict)
    if publication["certification_authorizes_publication"] is not False:
        findings.append(
            "RP-PUBLISH-001 publication: certification must never authorize publication"
        )
    if publication["owner_authorization_required"] is not True:
        findings.append(
            "RP-PUBLISH-002 publication: explicit owner authorization is required"
        )
    rc = lifecycle["release_candidate"]
    assert isinstance(rc, dict)
    if rc["replaceable"] is not False:
        findings.append(
            "RP-PUBLISH-003 release candidate: published coordinates are immutable"
        )


def _validate_supply_chain(
    root: Path, policy: Mapping[str, object], findings: list[str]
) -> None:
    manifest = _load_json(root / SUPPLY_CHAIN_PATH.relative_to(ROOT))
    assert isinstance(manifest, dict)
    source_policy = manifest["source_policy"]
    assert isinstance(source_policy, dict)
    if source_policy.get("publication_authorized") is not False:
        findings.append(
            "RP-PUBLISH-004 release supply chain: certification source policy must "
            "set publication_authorized=false"
        )
    profile_policy = manifest["profile_policy"]
    assert isinstance(profile_policy, dict)
    publishing_profiles = sorted(
        profile
        for profile, raw in profile_policy.items()
        if isinstance(raw, dict) and raw.get("publication") is not False
    )
    if publishing_profiles:
        findings.append(
            "RP-PUBLISH-005 release supply chain: certification profiles may not "
            "publish; offenders=" + ", ".join(publishing_profiles)
        )
    workflow_policy = manifest["workflow_policy"]
    assert isinstance(workflow_policy, dict)
    if workflow_policy.get("manual_authorization_default") is not True:
        findings.append(
            "RP-PUBLISH-006 workflow: dry-run/manual authorization must default safe"
        )

    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    artifact_ids = {
        str(item["id"])[len("release:") :]
        if str(item["id"]).startswith("release:")
        else str(item["id"])
        for item in artifacts
    }
    claims = policy["support_claims"]
    assert isinstance(claims, list)
    binding_ids = {
        str(claim["id"])[len("binding:") :]
        for claim in claims
        if claim["dimension"] == "binding"
    }
    if artifact_ids != binding_ids:
        findings.append(
            "RP-PUBLISH-007 release artifacts: every binding support claim must map "
            f"to one release artifact; missing={sorted(binding_ids - artifact_ids)}, "
            f"unknown={sorted(artifact_ids - binding_ids)}"
        )


def _validate_waivers(
    root: Path, policy: Mapping[str, object], findings: list[str]
) -> None:
    waivers = policy["waivers"]
    assert isinstance(waivers, dict)
    declared = set(str(item) for item in waivers["active"])
    accepted: set[str] = set()
    for path in (root / "governance/waivers").glob("*.yaml"):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(record, dict) and record.get("status") == "accepted":
            accepted.add(str(record["waiver_id"]))
    if declared != accepted:
        findings.append(
            "RP-WAIVER-001 waivers: policy must account for every accepted waiver "
            f"exactly; missing={sorted(accepted - declared)}, stale={sorted(declared - accepted)}"
        )


def validate_policy(
    root: Path = ROOT, policy: Mapping[str, object] | None = None
) -> ValidationResult:
    if policy is None:
        policy = load_policy(
            root / POLICY_PATH.relative_to(ROOT), root / SCHEMA_PATH.relative_to(ROOT)
        )
    findings: list[str] = []
    version_kinds = policy["version_kinds"]
    kind_ids = _unique_ids(version_kinds, "version kinds", findings)
    if "product" not in kind_ids:
        findings.append(
            "RP-VERSION-009 version kinds: product identity is unregistered"
        )
    else:
        product_kind = next(item for item in version_kinds if item["id"] == "product")
        product = policy["product"]
        if product_kind["authority"] != product["version_authority"]:
            findings.append(
                "RP-VERSION-010 product: version-kind authority contradicts the "
                "canonical product-version authority"
            )
    _validate_versions(root, policy, findings)
    _validate_support(root, policy, findings)
    _validate_lifecycle(policy, findings)
    _validate_supply_chain(root, policy, findings)
    _validate_waivers(root, policy, findings)
    return ValidationResult(tuple(findings))


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    rendered_rows = [
        [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        for row in rows
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rendered_rows))
        for index, header in enumerate(headers)
    ]
    lines = [
        "| "
        + " | ".join(
            header.ljust(widths[index]) for index, header in enumerate(headers)
        )
        + " |",
        "| " + " | ".join("-" * width for width in widths) + " |",
    ]
    for row in rendered_rows:
        lines.append(
            "| "
            + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
            + " |"
        )
    return lines


def render_document(policy: Mapping[str, object]) -> str:
    product = policy["product"]
    assert isinstance(product, dict)
    projection = product["repository_projection"]
    assert isinstance(projection, dict)
    lines = [
        "<!-- Generated by tooling/release_policy.py from governance/release-policy.json. -->",
        "",
        "# STRling release policy",
        "",
        f"Policy version: `{policy['policy_version']}`. Product version: **STRling {product['version']}**.",
        "",
        "This document is a human-readable projection. The machine authority is",
        "[`governance/release-policy.json`](../governance/release-policy.json).",
        "Certification never authorizes publication; explicit owner authorization is required.",
        "",
        "## Version identity",
        "",
        f"The sole product-version authority is `{product['version_authority']}`. The current",
        f"checked-in package projection remains `{projection['version']}` in `{projection['status']}`",
        f"state. {projection['activation_rule']}",
        "",
        "Product SemVer classifications:",
        "",
    ]
    for identifier, rule in product["semver_rules"].items():
        lines.append(f"-   `{identifier.replace('_', '-')}` — {rule}")
    lines.extend(["", "Independent version kinds:", ""])
    kinds = policy["version_kinds"]
    assert isinstance(kinds, list)
    lines.extend(
        _table(
            ("Identity", "Authority", "Meaning", "Product effect"),
            [
                (
                    item["id"],
                    item["authority"],
                    item["semantics"],
                    item["product_version_effect"],
                )
                for item in kinds
            ],
        )
    )
    lines.extend(["", "## Version-bearing surfaces", ""])
    surfaces = policy["version_surfaces"]
    assert isinstance(surfaces, list)
    lines.extend(
        _table(
            ("Surface", "Current", "Coordination", "Destination", "Disposition"),
            [
                (
                    item["surface"],
                    item["current_version"]
                    if item["current_version"] is not None
                    else "tag-derived",
                    "product" if item["coordinates_with_product"] else "independent",
                    item["publication_destination"],
                    item["disposition"],
                )
                for item in surfaces
            ],
        )
    )
    lines.extend(["", "## Support tiers", ""])
    tiers = policy["support_tiers"]
    assert isinstance(tiers, list)
    for tier in tiers:
        lines.extend([f"### {tier['id']}", "", str(tier["definition"]), ""])
        for requirement in tier["requirements"]:
            lines.append(f"-   {requirement}")
        lines.extend(["", f"Change rule: {tier['change_rule']}", ""])
    lines.extend(["## Ratified support claims", ""])
    claims = policy["support_claims"]
    assert isinstance(claims, list)
    lines.extend(
        _table(
            ("Claim", "Tier", "Evidence state", "Exact scope", "Limitations"),
            [
                (
                    item["subject"],
                    item["tier"],
                    item["certification_status"],
                    item["scope"],
                    "; ".join(item["limitations"]) or "None",
                )
                for item in claims
            ],
        )
    )
    lines.extend(
        [
            "",
            "A claim covers only its exact registered versions, profiles, runtimes, platforms,",
            "and architectures. Newer upstream versions are unknown and unsupported until a new",
            "or revised profile and governed evidence are registered. EOL versions may be moved to",
            "Legacy or removed only through policy and deprecation. Nightly/prerelease engines are",
            "Preview at most and require their own exact evidence. Uncertainty remains explicit.",
            "",
            "### Target/profile version policy",
            "",
        ]
    )
    for name, rule in policy["target_profile_policy"].items():
        lines.append(f"-   **{name.replace('_', ' ')}** — {rule}")
    lines.extend(["", "### Runtime and platform policy", ""])
    for name, rule in policy["runtime_platform_policy"].items():
        lines.append(f"-   **{name.replace('_', ' ')}** — {rule}")
    lines.extend(
        [
            "",
            "## Release channels",
            "",
        ]
    )
    for channel in policy["release_channels"]:
        lines.extend(
            [
                f"### {channel['id']}",
                "",
                f"Public: `{str(channel['public']).lower()}`. Notation: {channel['version_notation']}",
                "",
                str(channel["semantics"]),
                "",
                f"Immutability: {channel['immutability']}",
                "",
            ]
        )
    lines.extend(["Excluded channels:", ""])
    for channel in policy["excluded_release_channels"]:
        lines.append(f"-   **{channel['id']}** — {channel['reason']}")
    lines.append("")
    lifecycle = policy["release_lifecycle"]
    assert isinstance(lifecycle, dict)
    lines.extend(["## Release state model", ""])
    for state in lifecycle["states"]:
        lines.append(f"-   **{state['id']}** — {state['meaning']}")
    lines.extend(["", "Allowed transitions:", ""])
    for transition in lifecycle["transitions"]:
        lines.append(
            f"-   `{transition['from']} → {transition['to']}` — "
            + "; ".join(transition["requirements"])
        )
    rc = lifecycle["release_candidate"]
    lines.extend(
        [
            "",
            "## Release candidates",
            "",
            f"Notation: `{rc['notation']}`. Public coordinates are permitted only after explicit",
            f"authorization and are never replaceable. {rc['promotion']}",
            "",
            rc["change_rule"],
            "",
            f"Evidence binding: {rc['evidence_binding']}",
            "",
            "## Stable release evidence",
            "",
        ]
    )
    for evidence in lifecycle["stable_evidence"]:
        lines.append(f"-   {evidence}")
    compatibility = policy["compatibility"]
    assert isinstance(compatibility, dict)
    lines.extend(["", "## Compatibility and deprecation", ""])
    for name, meaning in compatibility["dimensions"].items():
        lines.append(f"-   **{name} compatibility** — {meaning}")
    lines.append("")
    for surface in compatibility["surfaces"]:
        lines.append(f"-   **{surface['id']}** — " + " ".join(surface["guarantees"]))
    deprecation = compatibility["deprecation"]
    lines.extend(
        [
            "",
            f"Deprecation notice: {deprecation['notice']}",
            "",
            f"Minimum window: {deprecation['minimum_window']}",
            "",
            f"Replacement: {deprecation['replacement']}",
            "",
            f"Removal: {deprecation['removal']}",
            "",
            f"Emergency exception: {deprecation['emergency']}",
            "",
            "## Publication authorization",
            "",
            str(policy["publication"]["tooling_guard"]),
            "",
            "Covered public actions:",
            "",
        ]
    )
    for action in policy["publication"]["covered_actions"]:
        lines.append(f"-   {action}")
    verification = policy["post_publication_verification"]
    lines.extend(["", "## Post-publication verification", ""])
    for check in verification["checks"]:
        lines.append(f"-   {check}")
    lines.extend(["", "If verification fails:", ""])
    for handling in verification["failure_handling"]:
        lines.append(f"-   {handling}")
    waivers = policy["waivers"]
    lines.extend(["", "## Waivers and stable blockers", ""])
    lines.append(
        "Active governed waiver: "
        + ", ".join(f"`{identifier}`" for identifier in waivers["active"])
        + "."
    )
    lines.extend(["", "Waiver rules:", ""])
    for requirement in waivers["requirements"]:
        lines.append(f"-   {requirement}")
    lines.extend(["", "Stable-release blockers:", ""])
    for blocker in waivers["stable_release_blockers"]:
        lines.append(f"-   {blocker}")
    lines.append("")
    return "\n".join(lines)


def check_document(root: Path, policy: Mapping[str, object]) -> str | None:
    expected = render_document(policy)
    path = root / DOCUMENT_PATH.relative_to(ROOT)
    if not path.is_file():
        return (
            f"RP-DOC-001 documentation projection is missing: {path.relative_to(root)}"
        )
    observed = path.read_text(encoding="utf-8")
    if observed != expected:
        return (
            "RP-DOC-002 docs/release-policy.md does not match the machine-readable "
            "release policy; run python tooling/release_policy.py --write"
        )
    return None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy = load_policy()
        result = validate_policy(policy=policy)
        findings = list(result.findings)
        if args.write and not findings:
            with DOCUMENT_PATH.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(render_document(policy))
        if args.check or not args.write:
            documentation = check_document(ROOT, policy)
            if documentation is not None:
                findings.append(documentation)
        result = ValidationResult(tuple(findings))
    except ReleasePolicyError as exc:
        result = ValidationResult((str(exc),))
    if args.json_output:
        print(json.dumps(result.as_dict(), sort_keys=True))
    else:
        print(f"[{result.status}] release policy ({len(result.findings)} finding(s))")
        for finding in result.findings:
            print(f"  - {finding}")
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
