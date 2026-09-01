#!/usr/bin/env python3
"""Run the clean, no-reuse STRling production-certification aggregate."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
PROFILE_ARTIFACT_NAME = "profile-release.json"
PRODUCT_ARTIFACT_NAME = "product-certification-release.json"
PRODUCT_REPORT_NAME = "product-certification-release.md"
PRODUCTION_ARTIFACT_NAME = "production-candidate-certification.json"
PRODUCTION_REPORT_NAME = "production-candidate-certification.md"
CAPACITY_CONTRACT_PATH = ROOT / "governance/production-certification-capacity.json"
GIB = 1024**3


class ProductionCertificationError(RuntimeError):
    """Fail one production attempt without disguising its blocking cause."""


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def load_capacity_contract(
    path: Path = CAPACITY_CONTRACT_PATH,
) -> dict[str, Any]:
    """Load and fail closed on an inconsistent production-capacity contract."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductionCertificationError(
            f"production-capacity contract is unavailable: {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise ProductionCertificationError(
            "production-capacity contract must be a JSON object"
        )
    if value.get("schema_version") != "1.0.0" or value.get("contract_kind") != (
        "strling-production-certification-capacity"
    ):
        raise ProductionCertificationError(
            "production-capacity contract identity is invalid"
        )
    measurement = value.get("measurement_basis")
    if not isinstance(measurement, dict):
        raise ProductionCertificationError(
            "production-capacity contract lacks measurement_basis"
        )
    numeric_fields = (
        "rounded_workspace_envelope_bytes",
        "simultaneous_workspace_envelopes",
        "maximum_expected_transient_bytes",
        "safety_margin_bytes",
        "required_free_bytes",
    )
    for name in numeric_fields:
        if not isinstance(value.get(name), int) or value[name] <= 0:
            raise ProductionCertificationError(
                f"production-capacity contract {name} must be a positive integer"
            )
    observed = measurement.get("observed_transient_bytes")
    if not isinstance(observed, int) or observed <= 0:
        raise ProductionCertificationError(
            "production-capacity contract observed_transient_bytes must be positive"
        )
    envelope = value["rounded_workspace_envelope_bytes"]
    simultaneous = value["simultaneous_workspace_envelopes"]
    maximum = value["maximum_expected_transient_bytes"]
    margin = value["safety_margin_bytes"]
    required = value["required_free_bytes"]
    if observed > envelope:
        raise ProductionCertificationError(
            "production-capacity observation exceeds its workspace envelope"
        )
    if maximum != envelope * simultaneous:
        raise ProductionCertificationError(
            "production-capacity transient bytes must equal the workspace envelope multiplicity"
        )
    if required != maximum + margin:
        raise ProductionCertificationError(
            "production-capacity required_free_bytes must equal transient bytes plus safety margin"
        )
    return value


def storage_capacity_evidence(
    *, free_bytes: int, contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate available capacity without using unrelated caches as a proxy."""

    required = int(contract["required_free_bytes"])
    return {
        "status": "passed" if free_bytes >= required else "failed",
        "free_bytes": free_bytes,
        "required_free_bytes": required,
        "maximum_expected_transient_bytes": int(
            contract["maximum_expected_transient_bytes"]
        ),
        "rounded_workspace_envelope_bytes": int(
            contract["rounded_workspace_envelope_bytes"]
        ),
        "simultaneous_workspace_envelopes": int(
            contract["simultaneous_workspace_envelopes"]
        ),
        "safety_margin_bytes": int(contract["safety_margin_bytes"]),
        "contract_path": str(CAPACITY_CONTRACT_PATH.relative_to(ROOT)),
        "contract_fingerprint": fingerprint(contract),
    }


def require_runtime_capacity_reserve(
    *, contract: Mapping[str, Any], root: Path
) -> None:
    """Keep the separate emergency reserve intact at production stage boundaries."""

    free_bytes = shutil.disk_usage(root).free
    reserve = int(contract["safety_margin_bytes"])
    if free_bytes < reserve:
        raise ProductionCertificationError(
            "production certification exhausted its capacity reserve: "
            f"requires {reserve / GIB:.0f} GiB at stage boundaries, "
            f"found {free_bytes / GIB:.2f} GiB"
        )


def run_capacity_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    contract: Mapping[str, Any],
    env: Mapping[str, str] | None = None,
) -> None:
    """Run one outer production stage with fail-closed reserve checks."""

    require_runtime_capacity_reserve(contract=contract, root=cwd)
    run_live(command, cwd=cwd, env=env)
    require_runtime_capacity_reserve(contract=contract, root=cwd)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["release"], required=True)
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument("--no-reuse", action="store_true", required=True)
    parser.add_argument("--plain", action="store_true", required=True)
    return parser.parse_args(argv)


def capture(
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as error:
        return subprocess.CompletedProcess(
            list(command), 127, stdout="", stderr=str(error)
        )


def require_capture(
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: Mapping[str, str] | None = None,
) -> str:
    completed = capture(command, cwd=cwd, env=env)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ProductionCertificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}: {detail}"
        )
    return completed.stdout.strip()


def run_live(
    command: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None
) -> None:
    print(f">> {' '.join(command)}", flush=True)
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        check=False,
    )
    if completed.returncode != 0:
        raise ProductionCertificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}"
        )


def release_profile_command(profile_artifact: Path) -> list[str]:
    """Select the complete governed Release profile membership.

    The production CLI's required ``--all`` flag selects every production
    certification stage. It is distinct from the quality runner's optional
    ``all`` component selector, which expands component operations beyond
    their profile-declared target sets.
    """

    return [
        "./strling",
        "profile",
        "release",
        "--artifact",
        str(profile_artifact),
    ]


def repository_identity(root: Path) -> dict[str, Any]:
    return {
        "branch": require_capture(["git", "branch", "--show-current"], cwd=root),
        "sha": require_capture(["git", "rev-parse", "HEAD"], cwd=root),
        "status_porcelain": require_capture(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root
        ),
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_certification_environment() -> dict[str, str]:
    environment = dict(os.environ)
    defaults = {
        "JAVA_HOME": "/opt/temurin-11.0.32+9",
        "STRLING_MAVEN_REPOSITORY": "/root/.m2/repository",
        "STRLING_CPYTHON_311_BINARY": (
            "/opt/strling-toolchains/install/cpython-3.11.15/bin/python3.11"
        ),
        "STRLING_NODE_22_BINARY": "/usr/local/bin/node",
        "STRLING_PCRE2_1042_LIBRARY": (
            "/opt/pcre2-10.42-build-default/libpcre2-8.so.0.11.2"
        ),
        "STRLING_PCRE2_1043_LIBRARY": (
            "/opt/pcre2-10.43-build-default/libpcre2-8.so.0.12.0"
        ),
        "STRLING_PCRE2_1042_BUILD_ID": (
            "pcre2-10.42@52c08847921a324c804cabf2814549f50bce1265"
        ),
        "STRLING_PCRE2_1043_BUILD_ID": (
            "pcre2-10.43@3864abdb713f78831dd12d898ab31bbb0fa630b6"
        ),
    }
    for name, value in defaults.items():
        environment.setdefault(name, value)
    environment["PATH"] = (
        f"{environment['JAVA_HOME']}/bin:/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
    )
    environment.update(
        {
            "COMPOSER_ALLOW_SUPERUSER": "1",
            "COMPOSER_NO_INTERACTION": "1",
            "STRLING_OSV_SCANNER": shutil.which("osv-scanner", path=environment["PATH"])
            or "",
            "STRLING_PRODUCTION_CERTIFICATION": "1",
            "STRLING_CERTIFICATION_NO_REUSE": "1",
        }
    )
    return environment


def environment_fingerprints(environment: Mapping[str, str]) -> dict[str, Any]:
    probes = {
        "bash": ["bash", "--version"],
        "python": [sys.executable, "--version"],
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
        "ruff": ["ruff", "--version"],
        "cargo": ["cargo", "--version"],
        "rustc": ["rustc", "--version"],
        "clippy": ["cargo", "+1.75.0", "clippy", "--version"],
        "rustfmt": ["rustfmt", "+1.75.0", "--version"],
        "rust_nightly": ["rustc", "+nightly-2026-08-01", "-vV"],
        "cargo_fuzz": ["cargo", "+nightly-2026-08-01", "fuzz", "--version"],
        "cargo_audit": ["cargo-audit", "--version"],
        "cmake": ["cmake", "--version"],
        "gcc": ["gcc", "--version"],
        "dotnet": ["dotnet", "--version"],
        "dart": ["dart", "--version"],
        "go": ["go", "version"],
        "java": ["java", "-version"],
        "maven": ["mvn", "--version"],
        "lua": ["lua", "-v"],
        "luarocks": ["luarocks", "--version"],
        "perl": ["perl", "-e", "print $^V"],
        "cpanm": ["cpanm", "--version"],
        "php": ["php", "--version"],
        "composer": ["composer", "--version"],
        "r": ["R", "--version"],
        "ruby": ["ruby", "--version"],
        "bundler": ["bundle", "--version"],
        "swift": ["swift", "--version"],
        "conan": ["conan", "--version"],
        "osv_scanner": ["osv-scanner", "--version"],
        "docker": ["docker", "version", "--format", "{{json .}}"],
    }
    results: dict[str, Any] = {}
    for name, command in probes.items():
        completed = capture(command, env=environment)
        results[name] = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    disk = shutil.disk_usage(ROOT)
    configured_artifacts: dict[str, Any] = {}
    for name in (
        "STRLING_OSV_SCANNER",
        "STRLING_NODE_22_BINARY",
        "STRLING_CPYTHON_311_BINARY",
        "STRLING_PCRE2_1042_LIBRARY",
        "STRLING_PCRE2_1043_LIBRARY",
    ):
        path = Path(environment.get(name, ""))
        configured_artifacts[name] = {
            "path": str(path),
            "sha256": _file_sha256(path) if path.is_file() else None,
        }
    return {
        "platform": platform.platform(),
        "python_implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "disk_free_bytes": disk.free,
        "java_home": environment.get("JAVA_HOME"),
        "configured_artifacts": configured_artifacts,
        "probes": results,
    }


def create_worktree(*, source_sha: str, path: Path) -> None:
    if path.exists():
        raise ProductionCertificationError(f"no-reuse worktree already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    run_live(["git", "worktree", "add", "--detach", str(path), source_sha], cwd=ROOT)
    identity = repository_identity(path)
    if identity["sha"] != source_sha or identity["status_porcelain"]:
        raise ProductionCertificationError(
            "created worktree does not prove the requested clean source identity"
        )


def materialize_governed_production_inputs(
    *, authority_root: Path, worktree: Path
) -> list[dict[str, Any]]:
    """Copy exact ignored historical evidence required by tracked generators."""

    inventory_path = worktree / "governance/legacy-removal-inventory.json"
    inventory = load_json(inventory_path)
    source = inventory.get("source")
    if not isinstance(source, Mapping):
        raise ProductionCertificationError(
            "legacy-removal inventory lacks its governed source object"
        )
    raw_path = source.get("production_certification_path")
    expected_sha256 = source.get("production_certification_sha256")
    if not isinstance(raw_path, str) or not isinstance(expected_sha256, str):
        raise ProductionCertificationError(
            "legacy-removal inventory lacks production-certification identity"
        )
    relative_path = Path(raw_path)
    required_prefix = ("artifacts", "production-certification")
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.parts[:2] != required_prefix
    ):
        raise ProductionCertificationError(
            f"governed production input has an unsafe path: {raw_path}"
        )
    try:
        authority = (authority_root / relative_path).resolve(strict=True)
    except OSError as error:
        raise ProductionCertificationError(
            f"governed production input is unavailable: {raw_path}"
        ) from error
    authority_boundary = authority_root.resolve()
    if not authority.is_relative_to(authority_boundary):
        raise ProductionCertificationError(
            f"governed production input escapes the authority root: {raw_path}"
        )
    actual_sha256 = _file_sha256(authority)
    if actual_sha256 != expected_sha256:
        raise ProductionCertificationError(
            "governed production input hash changed: "
            f"expected {expected_sha256}, found {actual_sha256}"
        )
    target = worktree / relative_path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(authority, target)
    except OSError as error:
        raise ProductionCertificationError(
            f"could not materialize governed production input: {raw_path}"
        ) from error
    copied_sha256 = _file_sha256(target)
    if copied_sha256 != expected_sha256:
        raise ProductionCertificationError(
            "materialized governed production input failed exact verification"
        )
    return [
        {
            "path": relative_path.as_posix(),
            "sha256": copied_sha256,
            "size_bytes": target.stat().st_size,
            "authority": "hash-bound historical certification evidence",
        }
    ]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProductionCertificationError(f"expected a JSON object: {path}")
    return value


def render_report(artifact: Mapping[str, Any]) -> str:
    evidence = artifact["deterministic_evidence"]
    aggregate = evidence.get("aggregate", {})
    paths = evidence.get("artifacts", {})
    certification = evidence.get("certification", {})
    areas = certification.get("evidence_areas", {})
    waivers = certification.get("waiver_references", [])
    lines = [
        "# STRling production-candidate certification",
        "",
        f"- Status: **{evidence['status']}**",
        f"- Source SHA: `{evidence['source']['sha']}`",
        f"- Command: `{evidence['command']}`",
        f"- No reuse: `{str(evidence['no_reuse']['honored']).lower()}`",
        f"- Profile result: `{aggregate.get('status', 'not-run')}`",
        f"- Passed operations: `{aggregate.get('passed', 0)}`",
        f"- Failed operations: `{aggregate.get('failed', 0)}`",
        f"- Unavailable operations: `{aggregate.get('unavailable', 0)}`",
        f"- Incomplete operations: `{aggregate.get('incomplete', 0)}`",
        f"- Profile definition: `{certification.get('profile_definition_version', 'not-run')}`",
        f"- Profile fingerprint: `{certification.get('profile_definition_fingerprint', 'not-run')}`",
        f"- Product evidence fingerprint: `{certification.get('product_evidence_fingerprint', 'not-run')}`",
        f"- Governed waivers: `{', '.join(waivers) if waivers else 'none'}`",
        "",
        "## Evidence areas",
        "",
        "",
    ]
    for name, counts in sorted(areas.items()):
        rendered = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        lines.append(f"- {name}: `{rendered}`")
    lines.extend(["", "## Artifacts", ""])
    for name, path in sorted(paths.items()):
        identity = evidence.get("artifact_identities", {}).get(name, {})
        lines.append(
            f"- {name}: `{path}` (sha256 `{identity.get('sha256', 'not-generated')}`)"
        )
    lines.extend(
        [
            "",
            "This report is rendered from `production-candidate-certification.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def profile_summary(profile: Mapping[str, Any]) -> dict[str, Any]:
    deterministic = profile.get("deterministic_evidence")
    if not isinstance(deterministic, Mapping):
        raise ProductionCertificationError(
            "profile artifact lacks deterministic certification evidence"
        )
    aggregate = deterministic.get("aggregate")
    if not isinstance(aggregate, Mapping):
        raise ProductionCertificationError("profile artifact lacks aggregate counts")
    counts = aggregate.get("counts")
    if not isinstance(counts, Mapping):
        raise ProductionCertificationError("profile artifact lacks status counts")
    return {
        "status": aggregate.get("status"),
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "unavailable": counts.get("unavailable", 0),
        "incomplete": counts.get("incomplete", 0),
        "waived": counts.get("waived", 0),
        "total": aggregate.get("operation_count", 0),
    }


def product_summary(product: Mapping[str, Any]) -> dict[str, Any]:
    deterministic = product.get("deterministic_evidence")
    if not isinstance(deterministic, Mapping):
        raise ProductionCertificationError(
            "product artifact lacks deterministic certification evidence"
        )
    authority = deterministic.get("authority")
    results = deterministic.get("results")
    if not isinstance(authority, Mapping) or not isinstance(results, list):
        raise ProductionCertificationError(
            "product artifact lacks authority or result evidence"
        )
    source_profile = authority.get("source_profile")
    if not isinstance(source_profile, Mapping):
        raise ProductionCertificationError("product artifact lacks profile authority")
    areas: dict[str, dict[str, int]] = {}
    waiver_references: set[str] = set()
    for result in results:
        if not isinstance(result, Mapping):
            raise ProductionCertificationError("product result is malformed")
        area = str(result.get("evidence_area", "unclassified"))
        status = str(result.get("status", "unknown"))
        counts = areas.setdefault(area, {})
        counts[status] = counts.get(status, 0) + 1
        references = result.get("waiver_references", [])
        if isinstance(references, list):
            waiver_references.update(str(item) for item in references)
    source_evidence = deterministic.get("source_profile_evidence", {})
    profile = (
        source_evidence.get("profile", {})
        if isinstance(source_evidence, Mapping)
        else {}
    )
    return {
        "product_schema_version": product.get("schema_version"),
        "product_evidence_fingerprint": product.get("evidence_fingerprint"),
        "profile_artifact_schema_version": source_profile.get(
            "artifact_schema_version"
        ),
        "profile_definition_version": profile.get("definition_version"),
        "profile_definition_fingerprint": source_profile.get("definition_fingerprint"),
        "evidence_areas": areas,
        "waiver_references": sorted(waiver_references),
        "claim_summary": deterministic.get("aggregate", {}),
    }


def artifact_identity(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"sha256": None, "size_bytes": None}
    return {"sha256": _file_sha256(path), "size_bytes": path.stat().st_size}


def write_artifact(
    *,
    output_dir: Path,
    source: Mapping[str, Any],
    environment: Mapping[str, Any],
    worktree: Path,
    status: str,
    profile_artifact: Path | None,
    product_artifact: Path | None,
    product_report: Path | None,
    worktree_created: bool,
    final_source_status: str | None,
    final_root_status: str | None,
    generated_artifacts_recreated: bool,
    failure: str | None,
) -> Path:
    aggregate: dict[str, Any] = {}
    if profile_artifact is not None and profile_artifact.is_file():
        aggregate = profile_summary(load_json(profile_artifact))
    artifacts = {
        "profile": str(profile_artifact) if profile_artifact else "",
        "product": str(product_artifact) if product_artifact else "",
        "product_report": str(product_report) if product_report else "",
    }
    artifact_identities = {
        "profile": artifact_identity(profile_artifact),
        "product": artifact_identity(product_artifact),
        "product_report": artifact_identity(product_report),
    }
    certification: dict[str, Any] = {}
    if product_artifact is not None and product_artifact.is_file():
        certification = product_summary(load_json(product_artifact))
    deterministic: dict[str, Any] = {
        "status": status,
        "source": dict(source),
        "command": "npm run test:all -- --profile release --all --no-reuse --plain",
        "profile": "release",
        "no_reuse": {
            "honored": worktree_created,
            "clean_detached_worktree": str(worktree),
            "initial_source_status": "clean",
            "final_source_status": final_source_status,
            "final_root_status": final_root_status,
            "generated_artifacts_recreated": generated_artifacts_recreated,
        },
        "environment": dict(environment),
        "aggregate": aggregate,
        "certification": certification,
        "artifacts": artifacts,
        "artifact_identities": artifact_identities,
        "failure": failure,
        "publication_authorized": False,
    }
    artifact = {
        "schema_version": "1.0.0",
        "artifact_kind": "strling-production-candidate-certification",
        "deterministic_evidence": deterministic,
        "evidence_fingerprint": fingerprint(deterministic),
        "execution_metadata": {
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        },
    }
    artifact_path = output_dir / PRODUCTION_ARTIFACT_NAME
    artifact_path.write_text(
        json.dumps(artifact, indent=4, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / PRODUCTION_REPORT_NAME).write_text(
        render_report(artifact), encoding="utf-8"
    )
    return artifact_path


def main(argv: Sequence[str] | None = None) -> int:
    parse_args(argv)
    source = repository_identity(ROOT)
    if source["status_porcelain"]:
        print(
            "Error: production certification requires a clean source tree",
            file=sys.stderr,
        )
        return 2
    certification_environment = build_certification_environment()
    environment = environment_fingerprints(certification_environment)
    try:
        capacity_contract = load_capacity_contract()
    except ProductionCertificationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    capacity = storage_capacity_evidence(
        free_bytes=environment["disk_free_bytes"], contract=capacity_contract
    )
    environment["storage_capacity"] = capacity
    if capacity["status"] != "passed":
        print(
            "Error: production certification requires "
            f"{capacity['required_free_bytes'] / GIB:.0f} GiB free "
            f"({capacity['maximum_expected_transient_bytes'] / GIB:.0f} GiB "
            "maximum expected transient output plus "
            f"{capacity['safety_margin_bytes'] / GIB:.0f} GiB safety margin); "
            f"found {capacity['free_bytes'] / GIB:.2f} GiB",
            file=sys.stderr,
        )
        return 2

    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{source['sha'][:12]}-{timestamp}"
    worktree = ROOT / ".cert" / "production-certification" / run_id / "source"
    output_dir = (
        ROOT / "artifacts" / "production-certification" / source["sha"] / run_id
    )
    if output_dir.exists():
        print(f"Error: no-reuse output already exists: {output_dir}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True)
    profile_artifact = output_dir / PROFILE_ARTIFACT_NAME
    product_artifact = output_dir / PRODUCT_ARTIFACT_NAME
    product_report = output_dir / PRODUCT_REPORT_NAME
    failure: str | None = None
    worktree_created = False
    generated_artifacts_recreated = False
    final_source_status: str | None = None
    final_root_status: str | None = None
    try:
        create_worktree(source_sha=source["sha"], path=worktree)
        worktree_created = True
        environment["materialized_governed_inputs"] = (
            materialize_governed_production_inputs(
                authority_root=ROOT, worktree=worktree
            )
        )
        exact_runtime_result = require_capture(
            [
                "python3",
                "-m",
                "tooling.exact_runtime_toolchains",
                "--check",
                "--json",
            ],
            cwd=worktree,
            env=certification_environment,
        )
        environment["exact_runtime_toolchains"] = json.loads(exact_runtime_result)
        run_capacity_checked(
            ["npm", "ci", "--no-audit", "--no-fund"],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            ["npm", "ci", "--no-audit", "--no-fund"],
            cwd=worktree / "tooling/lsp-server",
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            ["./strling", "setup", "all"],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            [
                "cargo",
                "+1.75.0",
                "build",
                "--manifest-path",
                "bindings/interop/Cargo.toml",
                "--locked",
            ],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            ["./strling", "generate"],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            ["./strling", "generate", "--check", "--json"],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        if repository_identity(worktree)["status_porcelain"]:
            raise ProductionCertificationError(
                "generated-artifact reconstruction changed the clean source tree"
            )
        generated_artifacts_recreated = True
        run_capacity_checked(
            release_profile_command(profile_artifact),
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        run_capacity_checked(
            [
                "python3",
                "-m",
                "tooling.product_certification",
                "--profile-artifact",
                str(profile_artifact),
                "--artifact",
                str(product_artifact),
                "--report",
                str(product_report),
            ],
            cwd=worktree,
            contract=capacity_contract,
            env=certification_environment,
        )
        final_source = repository_identity(worktree)
        final_source_status = final_source["status_porcelain"]
        if final_source["sha"] != source["sha"] or final_source["status_porcelain"]:
            raise ProductionCertificationError(
                "final certification worktree is not clean"
            )
        summary = profile_summary(load_json(profile_artifact))
        if any(
            summary.get(name, 0) for name in ("failed", "unavailable", "incomplete")
        ):
            raise ProductionCertificationError(
                "Release aggregate contains a required non-passing operation"
            )
        write_artifact(
            output_dir=output_dir,
            source=source,
            environment=environment,
            worktree=worktree,
            status="passed",
            profile_artifact=profile_artifact,
            product_artifact=product_artifact,
            product_report=product_report,
            worktree_created=worktree_created,
            final_source_status=final_source_status,
            final_root_status=repository_identity(ROOT)["status_porcelain"],
            generated_artifacts_recreated=generated_artifacts_recreated,
            failure=None,
        )
        run_live(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT)
        final_root_status = repository_identity(ROOT)["status_porcelain"]
        if final_root_status:
            raise ProductionCertificationError(
                "production certification changed the canonical source tree"
            )
        print(f"Production candidate artifact: {output_dir / PRODUCTION_ARTIFACT_NAME}")
        return 0
    except ProductionCertificationError as error:
        failure = str(error)
        artifact_path = write_artifact(
            output_dir=output_dir,
            source=source,
            environment=environment,
            worktree=worktree,
            status="failed",
            profile_artifact=profile_artifact if profile_artifact.is_file() else None,
            product_artifact=product_artifact if product_artifact.is_file() else None,
            product_report=product_report if product_report.is_file() else None,
            worktree_created=worktree_created,
            final_source_status=final_source_status,
            final_root_status=final_root_status,
            generated_artifacts_recreated=generated_artifacts_recreated,
            failure=failure,
        )
        print(f"Error: {failure}", file=sys.stderr)
        print(f"Failure artifact: {artifact_path}", file=sys.stderr)
        print(f"Retained diagnostic worktree: {worktree}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
