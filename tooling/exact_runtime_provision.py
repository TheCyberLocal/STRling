#!/usr/bin/env python3
"""Provision the immutable Linux runtime set used by empirical certification.

Network access is confined to this setup command. Certification operations are
offline and consume only paths that this command has hash- and identity-checked.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling.exact_runtime_toolchains import (
    EXPECTED_KEYS,
    ExactRuntimeToolchainError,
    file_sha256,
    load_manifest,
    verify_configured_runtimes,
)

OWNED_ROOT = Path("/opt/strling-toolchains")


class ExactRuntimeProvisionError(ValueError):
    """The governed runtime set could not be reconstructed safely."""


def _run(command: Sequence[str], *, cwd: Path | None = None, env=None) -> None:
    try:
        subprocess.run(
            list(command),
            cwd=cwd,
            env=env,
            check=True,
            timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ExactRuntimeProvisionError(
            f"runtime provisioning command failed: {' '.join(command)}"
        ) from error


def _record_path(record: Mapping[str, Any]) -> Path:
    return Path(str(record["layout"]["absolute_path"]))


def runtime_environment(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Return the canonical environment handoff in stable key order."""

    return {
        str(manifest["toolchains"][key]["environment"]): str(
            manifest["toolchains"][key]["layout"]["absolute_path"]
        )
        for key in EXPECTED_KEYS
    }


def _download(source: Mapping[str, Any], downloads: Path) -> Path:
    archive = downloads / str(source["archive"])
    expected = str(source["sha256"])
    if archive.is_file() and file_sha256(archive) == expected:
        return archive
    downloads.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=downloads, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with urllib.request.urlopen(str(source["url"]), timeout=120) as response:
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
        if file_sha256(temporary) != expected:
            raise ExactRuntimeProvisionError(
                f"source archive SHA-256 differs: {source['archive']}"
            )
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
    return archive


def _extract(archive: Path, destination: Path) -> None:
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise ExactRuntimeProvisionError(
            f"partial governed source or runtime already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:*") as bundle:
        roots = {Path(member.name).parts[0] for member in bundle.getmembers()}
        if len(roots) != 1 or "" in roots or "." in roots or ".." in roots:
            raise ExactRuntimeProvisionError("source archive root is malformed")
        bundle.extractall(destination.parent, filter="data")
    extracted = destination.parent / next(iter(roots))
    if extracted != destination:
        extracted.rename(destination)


def _provision_node(record: Mapping[str, Any], downloads: Path) -> None:
    executable = _record_path(record)
    if executable.is_file():
        return
    archive = _download(record["source"], downloads)
    _extract(archive, executable.parents[1])


def _provision_python(record: Mapping[str, Any], downloads: Path) -> None:
    executable = _record_path(record)
    if executable.is_file():
        return
    archive = _download(record["source"], downloads)
    source = OWNED_ROOT / "sources" / "Python-3.11.15"
    build = OWNED_ROOT / "build" / "cpython-3.11.15"
    _extract(archive, source)
    if build.exists():
        raise ExactRuntimeProvisionError(f"partial governed build exists: {build}")
    build.mkdir(parents=True)
    environment = dict(os.environ)
    environment.update(
        {
            "CFLAGS": str(record["build"]["cflags"]),
            "SOURCE_DATE_EPOCH": str(record["build"]["source_date_epoch"]),
        }
    )
    _run(
        [str(source / "configure"), *record["build"]["configure"]],
        cwd=build,
        env=environment,
    )
    _run(["make", "-j2"], cwd=build, env=environment)
    _run(["make", "install"], cwd=build, env=environment)


def _provision_pcre2(
    key: str, record: Mapping[str, Any], sources: Path
) -> None:
    library = _record_path(record)
    if library.is_file():
        return
    source = sources / key
    build = library.parent
    if source.exists() or (build.exists() and any(build.iterdir())):
        raise ExactRuntimeProvisionError(
            f"partial governed PCRE2 source/build exists for {key}"
        )
    source.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", str(source)])
    _run(
        [
            "git",
            "-C",
            str(source),
            "fetch",
            "--depth=1",
            str(record["source"]["repository"]),
            str(record["source"]["tag"]),
        ]
    )
    _run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"])
    observed = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if observed != record["source"]["commit"]:
        raise ExactRuntimeProvisionError(f"{key} source commit differs")
    build.mkdir(parents=True, exist_ok=True)
    options = [
        f"-D{name}={value}" for name, value in record["build"]["options"].items()
    ]
    _run(["cmake", "-S", str(source), "-B", str(build), *options])
    _run(["cmake", "--build", str(build), "--parallel", "2"])


def provision(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if os.name != "posix" or Path("/opt").anchor != "/":
        raise ExactRuntimeProvisionError(
            "exact runtimes are governed for Ubuntu 24.04 x86_64"
        )
    OWNED_ROOT.mkdir(parents=True, exist_ok=True)
    downloads = OWNED_ROOT / "downloads"
    toolchains = manifest["toolchains"]
    for key in EXPECTED_KEYS:
        record = toolchains[key]
        path = _record_path(record)
        if path.is_file() and file_sha256(path) != record["artifact"]["sha256"]:
            raise ExactRuntimeProvisionError(
                f"cached {key} artifact SHA-256 differs; discard that cache entry"
            )
        if key.startswith("node-"):
            _provision_node(record, downloads)
        elif key.startswith("cpython-"):
            _provision_python(record, downloads)
        else:
            _provision_pcre2(key, record, OWNED_ROOT / "sources")
    environment = runtime_environment(manifest)
    os.environ.update(environment)
    return verify_configured_runtimes(manifest)


def write_environment(path: Path, environment: Mapping[str, str]) -> None:
    for name, value in environment.items():
        if "\n" in name or "\r" in name or "=" in name:
            raise ExactRuntimeProvisionError("runtime variable name is malformed")
        if "\n" in value or "\r" in value:
            raise ExactRuntimeProvisionError("runtime path contains a line ending")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        for name, value in sorted(environment.items()):
            stream.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--github-env", type=Path)
    parser.add_argument("--print-env", action="store_true")
    parser.add_argument(
        "--execute-adversarial",
        action="store_true",
        help="run the governed strict real-engine equivalence check after verification",
    )
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=Path("artifacts/adversarial-semantic-runtime/evidence.json"),
    )
    args = parser.parse_args()
    manifest = load_manifest()
    environment = runtime_environment(manifest)
    if args.provision:
        result = provision(manifest)
    else:
        os.environ.update(environment)
        try:
            result = verify_configured_runtimes(manifest)
        except ExactRuntimeToolchainError as error:
            raise ExactRuntimeProvisionError(str(error)) from error
    if args.github_env is not None:
        write_environment(args.github_env, environment)
    if args.execute_adversarial:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tooling.adversarial_semantic_audit",
                "--strict",
                "--json",
                "--output",
                str(args.evidence_output),
            ],
            check=False,
            env=os.environ,
        )
        return completed.returncode
    if args.print_env:
        for name, value in sorted(environment.items()):
            print(f"export {name}={value}")
    else:
        print(
            "Exact governed runtimes: PASSED "
            f"({len(result['toolchains'])}/{len(EXPECTED_KEYS)})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
