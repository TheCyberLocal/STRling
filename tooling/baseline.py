#!/usr/bin/env python3
"""Validate immutable certified migration baseline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

try:
    from governance import normalize_repository_path, path_matches
except ImportError:  # pragma: no cover - import path differs under tests
    from tooling.governance import normalize_repository_path, path_matches


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "governance/baselines/registry.json"
FINGERPRINT_ALGORITHM = (
    "sha256 of sorted UTF-8 records: repository path, NUL, lowercase SHA-256 "
    "of file bytes, LF; glob patterns expand against the selected source tree"
)
DISPOSITIONS = {"preserve", "port", "rewrite", "retire", "evidence", "discard"}
MATRIX_CATEGORIES = (
    "must_preserve",
    "evidence_only",
    "intentionally_replace",
    "known_defect_non_contractual",
)


class BaselineError(ValueError):
    """Raised when frozen baseline evidence cannot be trusted."""


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot read {path}: {exc}") from exc


def validate_instance(instance: object, schema: object, label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
    except (SchemaError, ValidationError) as exc:
        raise BaselineError(f"malformed {label}: {exc.message}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise BaselineError(f"cannot read {path}: {exc}") from exc


def git_output(root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise BaselineError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def git_paths(root: Path, commit: str) -> tuple[str, ...]:
    output = git_output(root, ["ls-tree", "-r", "--name-only", "-z", commit])
    return tuple(
        item.decode("utf-8", errors="surrogateescape")
        for item in output.split(b"\0")
        if item
    )


def git_file(root: Path, commit: str, path: str) -> bytes:
    normalize_repository_path(path)
    return git_output(root, ["show", f"{commit}:{path}"])


def resolve_record_path(root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise BaselineError(f"record path is not a string: {value!r}")
    path = normalize_repository_path(value)
    return root / path


def expand_certified_patterns(
    patterns: Sequence[object], available: Sequence[str]
) -> tuple[str, ...]:
    selected: set[str] = set()
    for value in patterns:
        if not isinstance(value, str):
            raise BaselineError(f"fingerprint pattern is not a string: {value!r}")
        pattern = normalize_repository_path(value, pattern=True)
        matches = {path for path in available if path_matches(path, pattern)}
        if not matches:
            raise BaselineError(
                f"certified fingerprint pattern matched nothing: {pattern}"
            )
        selected.update(matches)
    return tuple(sorted(selected))


def expand_frozen_patterns(root: Path, patterns: Sequence[object]) -> tuple[str, ...]:
    selected: set[str] = set()
    for value in patterns:
        if not isinstance(value, str):
            raise BaselineError(f"fingerprint pattern is not a string: {value!r}")
        pattern = normalize_repository_path(value, pattern=True)
        if any(character in pattern for character in "*?["):
            matches = {
                path.relative_to(root).as_posix()
                for path in root.glob(pattern)
                if path.is_file()
            }
        else:
            candidate = root / pattern
            matches = {pattern} if candidate.is_file() else set()
        if not matches:
            raise BaselineError(
                f"frozen fingerprint pattern matched nothing: {pattern}"
            )
        selected.update(matches)
    return tuple(sorted(selected))


def path_set_digest(paths: Sequence[str], reader: Callable[[str], bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        file_digest = sha256_bytes(reader(path))
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise BaselineError(f"{label} must be an object")
    return value


def require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise BaselineError(f"{label} must be an array")
    return value


def validate_git_identity(identity: Mapping[str, object], git_root: Path) -> None:
    names = ("certified_commit", "donor_commit", "main_commit")
    commits: dict[str, str] = {}
    for name in names:
        value = identity.get(name)
        if not isinstance(value, str):
            raise BaselineError(f"identity.{name} must be a commit SHA")
        git_output(git_root, ["cat-file", "-e", f"{value}^{{commit}}"])
        commits[name] = value

    pairs = {
        "certified_donor": ("certified_commit", "donor_commit"),
        "certified_main": ("certified_commit", "main_commit"),
        "donor_main": ("donor_commit", "main_commit"),
    }
    recorded = require_mapping(identity.get("merge_bases"), "identity.merge_bases")
    for label, (left, right) in pairs.items():
        actual = (
            git_output(git_root, ["merge-base", commits[left], commits[right]])
            .decode("ascii")
            .strip()
        )
        if recorded.get(label) != actual:
            raise BaselineError(
                f"identity.merge_bases.{label} is {recorded.get(label)!r}, "
                f"expected {actual}"
            )

    git_output(
        git_root,
        [
            "merge-base",
            "--is-ancestor",
            commits["donor_commit"],
            commits["certified_commit"],
        ],
    )
    git_output(
        git_root,
        [
            "merge-base",
            "--is-ancestor",
            commits["main_commit"],
            commits["donor_commit"],
        ],
    )


def validate_reference(
    root: Path,
    reference: object,
    schema_name: str,
    label: str,
) -> Mapping[str, object]:
    item = require_mapping(reference, label)
    path = resolve_record_path(root, item.get("path"))
    expected = item.get("sha256")
    actual = sha256_file(path)
    if expected != actual:
        raise BaselineError(
            f"{label} hash mismatch: expected {expected}, found {actual}"
        )
    record = load_json(path)
    schema = load_json(root / "governance/schemas" / schema_name)
    validate_instance(record, schema, label)
    return require_mapping(record, label)


def validate_cross_record_invariants(
    manifest: Mapping[str, object],
    certification: Mapping[str, object],
    inventory: Mapping[str, object],
    matrix: Mapping[str, object],
) -> None:
    identity = require_mapping(manifest.get("identity"), "manifest.identity")
    certified = identity.get("certified_commit")
    donor = identity.get("donor_commit")
    if certification.get("certified_commit") != certified:
        raise BaselineError("certification commit does not match manifest identity")
    result = require_mapping(certification.get("result_summary"), "result_summary")
    if result.get("status") != "passed" or result.get("failed") != 0:
        raise BaselineError("certification evidence is not a passing result")

    manifest_transitions = require_list(
        manifest.get("active_transitions"), "manifest.active_transitions"
    )
    evidence_transitions = require_list(
        certification.get("transitions"), "certification.transitions"
    )
    if sorted(manifest_transitions, key=lambda item: item["id"]) != sorted(
        evidence_transitions, key=lambda item: item["id"]
    ):
        raise BaselineError("manifest transitions differ from certification evidence")

    manifest_waivers = require_list(
        manifest.get("active_waivers"), "manifest.active_waivers"
    )
    evidence_waivers = require_list(certification.get("waivers"), "waivers")
    waiver_projection = [
        {"id": item["id"], "source": item["source"]} for item in evidence_waivers
    ]
    if sorted(manifest_waivers, key=lambda item: item["id"]) != sorted(
        waiver_projection, key=lambda item: item["id"]
    ):
        raise BaselineError("manifest waivers differ from certification evidence")

    comparison = require_mapping(inventory.get("comparison"), "inventory.comparison")
    if comparison.get("donor_commit") != donor:
        raise BaselineError("donor inventory commit does not match manifest identity")
    capabilities = require_list(inventory.get("capabilities"), "inventory.capabilities")
    capability_ids = [item["id"] for item in capabilities]
    if len(capability_ids) != len(set(capability_ids)):
        raise BaselineError("donor inventory capability IDs are not unique")
    counts = Counter(item["disposition"] for item in capabilities)
    if set(counts) != DISPOSITIONS:
        raise BaselineError("donor inventory does not cover every disposition")
    if dict(counts) != inventory.get("summary"):
        raise BaselineError("donor inventory summary does not match capabilities")

    if matrix.get("baseline_id") != manifest.get("baseline_id"):
        raise BaselineError("preservation matrix baseline ID does not match manifest")
    matrix_ids: list[str] = []
    for category in MATRIX_CATEGORIES:
        entries = require_list(matrix.get(category), f"matrix.{category}")
        matrix_ids.extend(item["id"] for item in entries)
    if len(matrix_ids) != len(set(matrix_ids)):
        raise BaselineError("preservation matrix IDs are not unique")


def validate_manifest(
    root: Path, manifest: Mapping[str, object], git_root: Path
) -> dict[str, int]:
    if manifest.get("fingerprint_algorithm") != FINGERPRINT_ALGORITHM:
        raise BaselineError("unsupported fingerprint algorithm")
    identity = require_mapping(manifest.get("identity"), "manifest.identity")
    validate_git_identity(identity, git_root)
    certified_commit = identity["certified_commit"]
    assert isinstance(certified_commit, str)
    available = git_paths(git_root, certified_commit)

    def certified_reader(path: str) -> bytes:
        return git_file(git_root, certified_commit, path)

    def frozen_reader(path: str) -> bytes:
        return (root / path).read_bytes()

    fingerprints = require_list(manifest.get("fingerprints"), "fingerprints")
    fingerprint_ids: list[str] = []
    for value in fingerprints:
        item = require_mapping(value, "fingerprint")
        identifier = item.get("id")
        if not isinstance(identifier, str):
            raise BaselineError("fingerprint ID must be a string")
        fingerprint_ids.append(identifier)
        patterns = require_list(item.get("paths"), f"fingerprint {identifier}.paths")
        if item.get("source") == "certified-commit":
            paths = expand_certified_patterns(patterns, available)
            reader = certified_reader
        else:
            paths = expand_frozen_patterns(root, patterns)
            reader = frozen_reader
        actual = path_set_digest(paths, reader)
        if actual != item.get("sha256"):
            raise BaselineError(
                f"fingerprint {identifier} mismatch: expected {item.get('sha256')}, "
                f"found {actual}"
            )
    if len(fingerprint_ids) != len(set(fingerprint_ids)):
        raise BaselineError("fingerprint IDs are not unique")

    certification = validate_reference(
        root,
        manifest.get("certification"),
        "certification-evidence.schema.json",
        "certification evidence",
    )
    inventory = validate_reference(
        root,
        manifest.get("donor_inventory"),
        "donor-inventory.schema.json",
        "donor inventory",
    )
    matrix = validate_reference(
        root,
        manifest.get("preservation_matrix"),
        "compatibility-preservation.schema.json",
        "preservation matrix",
    )
    validate_cross_record_invariants(manifest, certification, inventory, matrix)
    return {
        "fingerprints": len(fingerprints),
        "transitions": len(manifest["active_transitions"]),
        "waivers": len(manifest["active_waivers"]),
        "donor_capabilities": len(inventory["capabilities"]),
        "preservation_entries": sum(len(matrix[key]) for key in MATRIX_CATEGORIES),
    }


def validate_baselines(
    root: Path = ROOT,
    registry_path: Path | None = None,
    git_root: Path | None = None,
) -> dict[str, object]:
    registry_path = registry_path or root / "governance/baselines/registry.json"
    git_root = git_root or root
    registry = load_json(registry_path)
    registry_schema = load_json(
        root / "governance/schemas/frozen-baseline-registry.schema.json"
    )
    validate_instance(registry, registry_schema, "frozen baseline registry")
    registry_object = require_mapping(registry, "frozen baseline registry")
    entries = require_list(registry_object.get("baselines"), "registry.baselines")
    identifiers: list[str] = []
    totals = Counter()
    for value in entries:
        entry = require_mapping(value, "baseline registry entry")
        identifier = entry.get("id")
        assert isinstance(identifier, str)
        identifiers.append(identifier)
        manifest_path = resolve_record_path(root, entry.get("manifest"))
        actual_hash = sha256_file(manifest_path)
        if actual_hash != entry.get("sha256"):
            raise BaselineError(
                f"baseline {identifier} manifest hash mismatch: "
                f"expected {entry.get('sha256')}, found {actual_hash}"
            )
        manifest = load_json(manifest_path)
        manifest_schema = load_json(
            root / "governance/schemas/migration-baseline.schema.json"
        )
        validate_instance(manifest, manifest_schema, f"baseline {identifier}")
        manifest_object = require_mapping(manifest, f"baseline {identifier}")
        if manifest_object.get("baseline_id") != identifier:
            raise BaselineError(f"baseline registry ID mismatch for {identifier}")
        totals.update(validate_manifest(root, manifest_object, git_root))
    if len(identifiers) != len(set(identifiers)):
        raise BaselineError("baseline registry IDs are not unique")
    return {
        "status": "passed",
        "baselines": len(entries),
        **dict(totals),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without changes")
    parser.add_argument("--json", action="store_true", help="emit structured output")
    arguments = parser.parse_args(argv)
    try:
        summary = validate_baselines()
    except BaselineError as exc:
        if arguments.json:
            print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))
        else:
            print(f"[failed] frozen migration baseline: {exc}", file=sys.stderr)
        return 1
    if arguments.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(
            "[passed] frozen migration baseline: "
            f"{summary['baselines']} baseline, {summary['fingerprints']} fingerprints, "
            f"{summary['donor_capabilities']} donor capabilities"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
