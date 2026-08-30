#!/usr/bin/env python3
"""Generate or verify registered repository artifacts."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "governance/generated-artifacts.json"
DEFAULT_SCHEMA = ROOT / "governance/schemas/generated-artifact-registry.schema.json"


class RegistryError(ValueError):
    """Raised when the artifact registry cannot be trusted."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ArtifactResult:
    artifact: str
    status: str
    command: list[str] | None
    exit_code: int | None
    reason: str | None
    stdout: str = ""
    stderr: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "command": self.command,
            "exit_code": self.exit_code,
            "reason": self.reason,
        }


Executor = Callable[[Sequence[str], Path], CommandResult]
Snapshotter = Callable[[Path], Mapping[str, str]]


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read {path}: {exc}") from exc


def validate_registry(registry: object, schema: object) -> dict[str, object]:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)
    except (SchemaError, ValidationError) as exc:
        raise RegistryError(f"malformed artifact registry: {exc.message}") from exc
    if not isinstance(registry, dict):
        raise RegistryError("artifact registry root must be an object")
    artifacts = registry["artifacts"]
    assert isinstance(artifacts, list)
    identifiers = [artifact["id"] for artifact in artifacts]
    if len(identifiers) != len(set(identifiers)):
        raise RegistryError("artifact identifiers must be unique")
    return registry


def load_registry(
    registry_path: Path = DEFAULT_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, object]:
    return validate_registry(load_json(registry_path), load_json(schema_path))


def expand_paths(root: Path, patterns: Sequence[str]) -> set[Path]:
    matches: set[Path] = set()
    for pattern in patterns:
        absolute_pattern = str(root / pattern)
        matches.update(
            Path(match).resolve()
            for match in glob.glob(absolute_pattern, recursive=True)
        )
    return matches


def missing_patterns(root: Path, patterns: Sequence[str]) -> list[str]:
    return [pattern for pattern in patterns if not expand_paths(root, [pattern])]


def validate_artifact_relationships(registry: Mapping[str, object], root: Path) -> None:
    artifacts = registry["artifacts"]
    assert isinstance(artifacts, list)
    toolchain: object | None = None
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        sources = artifact["authoritative_sources"]
        inputs = artifact["generator_inputs"]
        outputs = artifact["outputs"]
        assert isinstance(sources, list)
        assert isinstance(inputs, list)
        assert isinstance(outputs, list)
        source_files = expand_paths(root, [*sources, *inputs])
        output_files = expand_paths(root, outputs)
        overlap = sorted(
            str(path.relative_to(root)) for path in source_files & output_files
        )
        if overlap:
            raise RegistryError(
                f"{artifact['id']} uses generated output as its own input: "
                + ", ".join(overlap)
            )
        enforcement = artifact["enforcement"]
        profile_enforcement = artifact.get("profile_enforcement")
        if enforcement != "profile-enforced":
            if profile_enforcement is not None:
                raise RegistryError(
                    f"{artifact['id']} declares profile enforcement without "
                    "profile-enforced status"
                )
            continue
        assert isinstance(profile_enforcement, dict)
        if toolchain is None:
            toolchain = load_json(root / "toolchain.json")
        if not isinstance(toolchain, dict):
            raise RegistryError("toolchain.json root must be an object")
        policy = toolchain.get("policy")
        if not isinstance(policy, dict):
            raise RegistryError("toolchain.json is missing policy")
        operations = policy.get("operation_registry")
        profiles = policy.get("profiles")
        if not isinstance(operations, dict) or not isinstance(profiles, dict):
            raise RegistryError("toolchain operation/profile policy is malformed")
        operation_id = profile_enforcement["operation"]
        governed_profiles = profile_enforcement["profiles"]
        assert isinstance(operation_id, str)
        assert isinstance(governed_profiles, list)
        operation = operations.get(operation_id)
        if not isinstance(operation, dict):
            raise RegistryError(
                f"{artifact['id']} references unknown profile operation {operation_id}"
            )
        verification = artifact["verification"]
        assert isinstance(verification, dict)
        if operation.get("command") != verification["command"]:
            raise RegistryError(
                f"{artifact['id']} profile operation command differs from its "
                "registered verification command"
            )
        for profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                raise RegistryError(f"malformed profile {profile_name}")
            profile_operations = profile.get("operations")
            if not isinstance(profile_operations, list):
                raise RegistryError(f"profile {profile_name} has no operation list")
            count = sum(
                1
                for item in profile_operations
                if isinstance(item, dict) and item.get("operation") == operation_id
            )
            expected = 1 if profile_name in governed_profiles else 0
            if count != expected:
                raise RegistryError(
                    f"{artifact['id']} expects {operation_id} exactly {expected} "
                    f"time(s) in profile {profile_name}, found {count}"
                )


def host_command(command: Sequence[str], cwd: Path) -> list[str]:
    arguments = list(command)
    if os.name != "nt" or not arguments:
        return arguments
    if arguments[0] == "python3":
        arguments[0] = sys.executable
    elif arguments[:2] == ["./strling", "contracts"]:
        arguments = [
            sys.executable,
            str(cwd / "tooling/public_contracts.py"),
            *arguments[2:],
        ]
    return arguments


def execute_command(command: Sequence[str], cwd: Path) -> CommandResult:
    arguments = host_command(command, cwd)
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return CommandResult(127, stderr=str(exc))
    return CommandResult(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def snapshot_repository(root: Path) -> Mapping[str, str]:
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RegistryError(
            "cannot snapshot repository state: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    snapshot: dict[str, str] = {}
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        path = root / relative
        if path.is_symlink():
            payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
        elif path.is_file():
            payload = path.read_bytes()
        else:
            payload = b"<missing>"
        mode = stat.S_IMODE(path.lstat().st_mode) if path.exists() else 0
        digest = hashlib.sha256(str(mode).encode("ascii") + b"\0" + payload).hexdigest()
        snapshot[relative] = digest
    return snapshot


def run_registry(
    registry: Mapping[str, object],
    root: Path,
    *,
    check: bool,
    selected: str | None = None,
    executor: Executor = execute_command,
    snapshotter: Snapshotter = snapshot_repository,
) -> list[ArtifactResult]:
    validate_artifact_relationships(registry, root)
    initial_state = snapshotter(root) if check else {}
    artifacts = registry["artifacts"]
    assert isinstance(artifacts, list)
    known_ids = {artifact["id"] for artifact in artifacts}
    if selected is not None and selected not in known_ids:
        raise RegistryError(f"unknown artifact '{selected}'")

    results: list[ArtifactResult] = []
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        artifact_id = str(artifact["id"])
        if selected is not None and artifact_id != selected:
            continue
        enforcement = artifact["enforcement"]
        if enforcement == "profile-enforced":
            profile_enforcement = artifact["profile_enforcement"]
            assert isinstance(profile_enforcement, dict)
            profiles = profile_enforcement["profiles"]
            assert isinstance(profiles, list)
            results.append(
                ArtifactResult(
                    artifact_id,
                    "profile-enforced",
                    None,
                    None,
                    "verification is delegated exactly to profiles: "
                    + ", ".join(str(profile) for profile in profiles),
                )
            )
            continue
        if enforcement != "enforced":
            transition = artifact.get("transition")
            assert isinstance(transition, dict)
            results.append(
                ArtifactResult(
                    artifact_id,
                    str(enforcement),
                    None,
                    None,
                    str(transition["rationale"]),
                )
            )
            continue

        generator = artifact["generator"]
        verification = artifact["verification"]
        assert isinstance(generator, dict)
        assert isinstance(verification, dict)
        sources = artifact["authoritative_sources"]
        inputs = artifact["generator_inputs"]
        outputs = artifact["outputs"]
        implementations = generator["implementation_paths"]
        assert isinstance(sources, list)
        assert isinstance(inputs, list)
        assert isinstance(outputs, list)
        assert isinstance(implementations, list)

        missing_sources = missing_patterns(root, [*sources, *inputs, *implementations])
        if missing_sources:
            results.append(
                ArtifactResult(
                    artifact_id,
                    "failed",
                    None,
                    None,
                    "missing authoritative source or generator input: "
                    + ", ".join(missing_sources),
                )
            )
            continue
        missing_outputs = missing_patterns(root, outputs)
        if check and missing_outputs:
            results.append(
                ArtifactResult(
                    artifact_id,
                    "failed",
                    None,
                    None,
                    "missing expected output: " + ", ".join(missing_outputs),
                )
            )
            continue

        command_value = verification["command"] if check else generator["command"]
        assert isinstance(command_value, list)
        command = [str(part) for part in command_value]
        working_directory = root / str(generator["working_directory"])
        if not working_directory.is_dir():
            results.append(
                ArtifactResult(
                    artifact_id,
                    "failed",
                    command,
                    None,
                    f"missing working directory: {generator['working_directory']}",
                )
            )
            continue

        execution = executor(command, working_directory)
        reason = None
        status = "passed"
        if execution.returncode != 0:
            status = "failed"
            action = "verification" if check else "generation"
            reason = f"{action} command exited with status {execution.returncode}"
        elif missing_patterns(root, outputs):
            status = "failed"
            reason = "generator completed without producing every expected output"
        results.append(
            ArtifactResult(
                artifact_id,
                status,
                command,
                execution.returncode,
                reason,
                execution.stdout,
                execution.stderr,
            )
        )

    if check:
        final_state = snapshotter(root)
        if final_state != initial_state:
            changed = sorted(
                path
                for path in set(initial_state) | set(final_state)
                if initial_state.get(path) != final_state.get(path)
            )
            results.append(
                ArtifactResult(
                    "repository-state",
                    "failed",
                    None,
                    None,
                    "check mode modified repository files: " + ", ".join(changed),
                )
            )
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify registered artifacts."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--artifact")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    return parser.parse_args(argv)


def render_human(results: Sequence[ArtifactResult]) -> None:
    for result in results:
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(
                result.stderr,
                end="" if result.stderr.endswith("\n") else "\n",
                file=sys.stderr,
            )
        suffix = f" ({result.reason})" if result.reason else ""
        print(f"[{result.status}] {result.artifact}{suffix}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        registry = load_registry(args.registry.resolve(), args.schema.resolve())
        results = run_registry(
            registry,
            ROOT,
            check=args.check,
            selected=args.artifact,
        )
    except RegistryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    failed = any(result.status == "failed" for result in results)
    exit_code = 1 if failed else 0
    operation = "check" if args.check else "write"
    if args.json_output:
        print(
            json.dumps(
                {
                    "operation": "generate",
                    "mode": operation,
                    "status": "failed" if failed else "passed",
                    "exit_code": exit_code,
                    "results": [result.as_dict() for result in results],
                },
                sort_keys=True,
            )
        )
    else:
        render_human(results)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
