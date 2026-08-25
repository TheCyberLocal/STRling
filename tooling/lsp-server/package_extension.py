#!/usr/bin/env python3
"""Build and certify the platform-targeted STRling VS Code package."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


LSP_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = LSP_ROOT.parents[1]
CONTRACT_PATH = LSP_ROOT / "package_contract.json"
DEFAULT_OUTPUT = LSP_ROOT / "dist"
WORK_ROOT = LSP_ROOT / "build" / "package"
NORMALIZED_TIMESTAMP = 315_619_200
MANIFEST_NAME = "strling-package-manifest.json"


class PackageError(RuntimeError):
    """A deterministic package-contract failure."""


@contextmanager
def _owned_temporary(prefix: str):
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    path = (WORK_ROOT / f"{prefix}{uuid.uuid4().hex}").resolve()
    if path.parent != WORK_ROOT.resolve():
        raise PackageError("package work directory escaped its owned root")
    path.mkdir()
    try:
        yield path
    finally:
        if path.exists():
            if path.parent != WORK_ROOT.resolve():
                raise PackageError("package cleanup target escaped its owned root")
            shutil.rmtree(path)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _new_artifact_path(path: Path, *, suffix: str) -> Path:
    resolved = path.resolve()
    if resolved.suffix.lower() != suffix:
        raise PackageError(f"artifact output must end in {suffix}: {resolved}")
    if resolved.exists():
        raise PackageError(f"artifact output already exists: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PackageError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise PackageError(f"{path} must contain a JSON object")
    return value


def load_contract() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    recorded = contract.get("contract_fingerprint")
    material = dict(contract)
    material.pop("contract_fingerprint", None)
    actual = _fingerprint(material)
    if recorded != actual:
        raise PackageError(
            f"package contract fingerprint mismatch: expected {recorded}, got {actual}"
        )
    return contract


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path = REPOSITORY_ROOT,
    env: Mapping[str, str] | None = None,
    input_bytes: bytes | None = None,
    timeout: float = 300.0,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=cwd,
            env=None if env is None else dict(env),
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PackageError(f"cannot execute {arguments[0]}: {error}") from error
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise PackageError(
            f"command failed ({completed.returncode}): {' '.join(arguments)}"
            + (f"\n{stderr}" if stderr else "")
        )
    return completed


def _tool(name: str, environment_name: str) -> Path:
    configured = os.environ.get(environment_name)
    if configured:
        path = Path(configured).expanduser().absolute()
        if path.is_file():
            return path
        raise PackageError(f"{environment_name} does not name a file: {path}")
    located = shutil.which(name)
    if located:
        # Preserve the invoked symlink name. Multi-call executables such as
        # rustup select rustc/cargo behavior from argv[0].
        return Path(located).absolute()
    if os.name == "nt":
        candidate = Path.home() / ".cargo" / "bin" / f"{name}.exe"
        if candidate.is_file():
            return candidate.absolute()
    raise PackageError(f"required build tool is unavailable: {name}")


def _node_entry(package_name: str, bin_name: str) -> tuple[Path, Path]:
    node = _tool("node", "NODE")
    package_root = LSP_ROOT / "node_modules" / package_name
    metadata = _load_json(package_root / "package.json")
    declared = metadata.get("bin")
    if isinstance(declared, str):
        relative = declared
    elif isinstance(declared, dict) and isinstance(declared.get(bin_name), str):
        relative = declared[bin_name]
    else:
        raise PackageError(f"{package_name} does not declare the {bin_name} binary")
    entry = (package_root / relative).resolve()
    if not entry.is_file():
        raise PackageError(f"locked Node binary is unavailable: {entry}")
    return node, entry


def _node_or_native_command(node: Path, entry: Path) -> list[str]:
    header = entry.read_bytes()[:4]
    if header == b"\x7fELF" or header[:2] == b"MZ":
        return [str(entry)]
    return [str(node), str(entry)]


def _git(arguments: Sequence[str]) -> str:
    git = _tool("git", "GIT")
    return (
        _run([str(git), *arguments], timeout=30.0)
        .stdout.decode("utf-8", errors="strict")
        .strip()
    )


def _host_identity() -> tuple[str, str]:
    node_platform = {
        "darwin": "darwin",
        "linux": "linux",
        "win32": "win32",
    }.get(sys.platform)
    if node_platform is None:
        raise PackageError(f"unsupported package host platform: {sys.platform}")
    machine = platform.machine().lower()
    node_arch = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine)
    if node_arch is None:
        raise PackageError(f"unsupported package host architecture: {machine}")
    return node_platform, node_arch


def _rust_host() -> str:
    rustc = _tool("rustc", "RUSTC")
    output = _run([str(rustc), "-vV"], timeout=30.0).stdout.decode("utf-8")
    for line in output.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise PackageError("rustc -vV did not report a host triple")


def resolve_target(contract: Mapping[str, Any], requested: str) -> dict[str, Any]:
    node_platform, node_arch = _host_identity()
    rust_host = _rust_host()
    targets = contract["targets"]
    assert isinstance(targets, list)
    if requested == "auto":
        matching = [
            target
            for target in targets
            if target["node_platform"] == node_platform
            and target["node_arch"] == node_arch
            and target["rust_host"] == rust_host
        ]
    else:
        matching = [target for target in targets if target["id"] == requested]
        if matching and (
            matching[0]["node_platform"] != node_platform
            or matching[0]["node_arch"] != node_arch
            or matching[0]["rust_host"] != rust_host
        ):
            raise PackageError(
                f"target {requested} does not match host "
                f"{node_platform}-{node_arch}/{rust_host}"
            )
    if len(matching) != 1:
        raise PackageError(
            f"no declared package target matches {node_platform}-{node_arch}/{rust_host}"
        )
    return dict(matching[0])


def _safe_repository_source(relative: str) -> Path:
    if "\\" in relative:
        raise PackageError(f"repository input uses a backslash: {relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise PackageError(f"repository input escapes the root: {relative}")
    source = (REPOSITORY_ROOT / pure).resolve()
    try:
        source.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as error:
        raise PackageError(f"repository input escapes the root: {relative}") from error
    if not source.is_file() or source.is_symlink():
        raise PackageError(f"repository input is not a regular file: {relative}")
    return source


def _payload_path(root: Path, relative: str) -> Path:
    if "\\" in relative:
        raise PackageError(f"payload path uses a backslash: {relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise PackageError(f"payload path escapes its root: {relative}")
    path = (root / pure).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise PackageError(f"payload path escapes its root: {relative}") from error
    return path


def _copy_file(source: Path, destination: Path, mode: int = 0o644) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode)
    os.utime(destination, (NORMALIZED_TIMESTAMP, NORMALIZED_TIMESTAMP))


def _build_binaries(stage: Path, target: Mapping[str, Any], build_root: Path) -> None:
    cargo = _tool("cargo", "CARGO")
    commit_timestamp = _git(["show", "-s", "--format=%ct", "HEAD"])
    environment = dict(os.environ)
    environment.update(
        {
            "CARGO_INCREMENTAL": "0",
            "CARGO_PROFILE_RELEASE_DEBUG": "0",
            "CARGO_PROFILE_RELEASE_STRIP": "symbols",
            "SOURCE_DATE_EPOCH": commit_timestamp,
        }
    )
    if target["node_platform"] == "win32":
        rustflags = environment.get("RUSTFLAGS", "").strip()
        environment["RUSTFLAGS"] = f"{rustflags} -C link-arg=/Brepro".strip()
    target_dir = build_root / "cargo"
    _run(
        [
            str(cargo),
            "build",
            "--manifest-path",
            str(REPOSITORY_ROOT / "core" / "internal" / "Cargo.toml"),
            "--locked",
            "--release",
            "--target",
            str(target["rust_host"]),
            "--target-dir",
            str(target_dir),
            "--bin",
            "strling-kernel",
            "--bin",
            "strling-editor-core",
        ],
        env=environment,
        timeout=900.0,
    )
    suffix = str(target["executable_suffix"])
    release = target_dir / str(target["rust_host"]) / "release"
    for name in ("strling-kernel", "strling-editor-core"):
        source = release / f"{name}{suffix}"
        if not source.is_file():
            raise PackageError(f"cargo did not produce {source}")
        _copy_file(source, stage / "server" / "bin" / source.name, 0o755)


def _bundle_client(stage: Path) -> None:
    node, esbuild = _node_entry("esbuild", "esbuild")
    output = stage / "out" / "extension.js"
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            *_node_or_native_command(node, esbuild),
            str(LSP_ROOT / "client" / "extension.ts"),
            "--bundle",
            f"--outfile={output}",
            "--external:vscode",
            "--platform=node",
            "--format=cjs",
            "--target=node18",
            "--legal-comments=none",
            "--log-level=warning",
        ],
        cwd=LSP_ROOT,
        timeout=120.0,
    )
    output.chmod(0o644)
    os.utime(output, (NORMALIZED_TIMESTAMP, NORMALIZED_TIMESTAMP))


def _expanded_paths(contract: Mapping[str, Any], target: Mapping[str, Any]) -> set[str]:
    suffix = str(target["executable_suffix"])
    return {
        str(path).replace("{executable_suffix}", suffix)
        for path in contract["payload"]["required_paths"]
    }


def _entry(path: Path, root: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    mode = "0755" if relative.startswith("server/bin/") else "0644"
    return {
        "path": relative,
        "size": path.stat().st_size,
        "mode": mode,
        "sha256": _file_fingerprint(path),
    }


def _input_fingerprints() -> dict[str, str]:
    inputs = {
        "package_contract": CONTRACT_PATH,
        "package_lock": LSP_ROOT / "package-lock.json",
        "cargo_lock": REPOSITORY_ROOT / "core" / "internal" / "Cargo.lock",
        "simply_protocol": REPOSITORY_ROOT
        / "spec"
        / "frontends"
        / "simply"
        / "1.1"
        / "protocol.json",
        "stdlib_registry": REPOSITORY_ROOT
        / "spec"
        / "stdlib"
        / "registry"
        / "1.0"
        / "registry.json",
        "island_registry": REPOSITORY_ROOT
        / "spec"
        / "tooling"
        / "island_boundaries.json",
    }
    return {name: _file_fingerprint(path) for name, path in inputs.items()}


def _write_manifest(
    stage: Path, contract: Mapping[str, Any], target: Mapping[str, Any]
) -> dict[str, Any]:
    package = _load_json(LSP_ROOT / "package.json")
    entries = sorted(
        (
            _entry(path, stage)
            for path in stage.rglob("*")
            if path.is_file() and path.name != MANIFEST_NAME
        ),
        key=lambda item: item["path"],
    )
    payload_material = {
        "contract_fingerprint": contract["contract_fingerprint"],
        "extension_version": package["version"],
        "target": target["id"],
        "rust_host": target["rust_host"],
        "inputs": _input_fingerprints(),
        "entries": entries,
    }
    manifest: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "contract_version": contract["contract_version"],
        **payload_material,
        "source_commit": _git(["rev-parse", "HEAD"]),
        "source_commit_timestamp": int(_git(["show", "-s", "--format=%ct", "HEAD"])),
        "payload_fingerprint": _fingerprint(payload_material),
    }
    manifest["manifest_fingerprint"] = _fingerprint(manifest)
    destination = stage / MANIFEST_NAME
    destination.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    destination.chmod(0o644)
    os.utime(destination, (NORMALIZED_TIMESTAMP, NORMALIZED_TIMESTAMP))
    return manifest


def _matches_forbidden(path: str, patterns: Sequence[str]) -> bool:
    return any(
        fnmatch.fnmatchcase(path, pattern) or PurePosixPath(path).match(pattern)
        for pattern in patterns
    )


def validate_payload(
    root: Path, contract: Mapping[str, Any], target: Mapping[str, Any]
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise PackageError(f"payload directory is missing: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    relative = {path.relative_to(root).as_posix() for path in files}
    required = _expanded_paths(contract, target)
    if relative != required:
        missing = sorted(required - relative)
        unexpected = sorted(relative - required)
        raise PackageError(
            f"payload contents differ from contract; missing={missing}, unexpected={unexpected}"
        )
    forbidden = contract["payload"]["forbidden_path_patterns"]
    bad = sorted(path for path in relative if _matches_forbidden(path, forbidden))
    if bad:
        raise PackageError(f"payload contains forbidden paths: {bad}")
    limits = contract["limits"]
    if len(files) > limits["max_payload_files"]:
        raise PackageError("payload file count exceeds contract limit")
    if sum(path.stat().st_size for path in files) > limits["max_payload_bytes"]:
        raise PackageError("payload size exceeds contract limit")
    if any(
        len(path.relative_to(root).as_posix().encode("utf-8"))
        > limits["max_path_bytes"]
        for path in files
    ):
        raise PackageError("payload path length exceeds contract limit")

    manifest = _load_json(root / MANIFEST_NAME)
    if manifest.get("target") != target["id"]:
        raise PackageError("payload manifest target is incorrect")
    if manifest.get("contract_fingerprint") != contract["contract_fingerprint"]:
        raise PackageError("payload manifest contract fingerprint is incorrect")
    recorded_manifest_fingerprint = manifest.get("manifest_fingerprint")
    manifest_material = dict(manifest)
    manifest_material.pop("manifest_fingerprint", None)
    if recorded_manifest_fingerprint != _fingerprint(manifest_material):
        raise PackageError("payload manifest fingerprint is incorrect")
    entries = sorted(
        (
            _entry(path, root)
            for path in files
            if path.relative_to(root).as_posix() != MANIFEST_NAME
        ),
        key=lambda item: item["path"],
    )
    if manifest.get("entries") != entries:
        raise PackageError("payload entry hashes differ from the manifest")
    payload_material = {
        "contract_fingerprint": manifest["contract_fingerprint"],
        "extension_version": manifest["extension_version"],
        "target": manifest["target"],
        "rust_host": manifest["rust_host"],
        "inputs": manifest["inputs"],
        "entries": manifest["entries"],
    }
    if manifest.get("payload_fingerprint") != _fingerprint(payload_material):
        raise PackageError("payload fingerprint is incorrect")
    return manifest


def _safe_output(output: Path) -> Path:
    resolved = output.resolve()
    default = DEFAULT_OUTPUT.resolve()
    if resolved == default:
        return resolved
    if resolved.exists():
        raise PackageError(f"non-default output already exists: {resolved}")
    return resolved


def assemble(output: Path, requested_target: str) -> dict[str, Any]:
    contract = load_contract()
    target = resolve_target(contract, requested_target)
    output = _safe_output(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with _owned_temporary("build-") as temporary_root:
        stage = temporary_root / "payload"
        stage.mkdir()
        copies = contract["payload"]["copies"]
        for item in copies:
            _copy_file(
                _safe_repository_source(str(item["source"])),
                _payload_path(stage, str(item["destination"])),
            )
        _build_binaries(stage, target, temporary_root)
        _bundle_client(stage)
        _write_manifest(stage, contract, target)
        validate_payload(stage, contract, target)
        if output == DEFAULT_OUTPUT.resolve() and output.exists():
            # The generator owns only this exact disposable directory.
            shutil.rmtree(output)
        shutil.copytree(stage, output)
    manifest = validate_payload(output, contract, target)
    return {"output": str(output), "target": target, "manifest": manifest}


def _package_vsix(payload: Path, target: Mapping[str, Any], output: Path) -> Path:
    node, vsce = _node_entry("@vscode/vsce", "vsce")
    output = output.resolve()
    if output.exists():
        raise PackageError(f"VSIX output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(node),
            str(vsce),
            "package",
            "--target",
            str(target["id"]),
            "--out",
            str(output),
            "--no-dependencies",
        ],
        cwd=payload,
        timeout=300.0,
    )
    if not output.is_file():
        raise PackageError(f"VSCE did not produce {output}")
    return output


def _zip_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        names: set[str] = set()
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            pure = PurePosixPath(name)
            if (
                name in names
                or pure.is_absolute()
                or ".." in pure.parts
                or "\\" in name
            ):
                raise PackageError(f"unsafe or duplicate VSIX entry: {name}")
            names.add(name)
            data = archive.read(info)
            entries.append(
                {
                    "path": name,
                    "size": len(data),
                    "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                }
            )
    return sorted(entries, key=lambda entry: entry["path"])


def _directory_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _runtime_environment(payload: Path, target: Mapping[str, Any]) -> dict[str, str]:
    suffix = str(target["executable_suffix"])
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": str(payload / "server" / "libs"),
            "STRLING_KERNEL": str(
                payload / "server" / "bin" / f"strling-kernel{suffix}"
            ),
            "STRLING_EDITOR_CORE": str(
                payload / "server" / "bin" / f"strling-editor-core{suffix}"
            ),
            "STRLING_SIMPLY_PROTOCOL_PATH": str(
                payload / "server" / "resources" / "simply-protocol.json"
            ),
            "STRLING_STDLIB_REGISTRY_PATH": str(
                payload / "server" / "resources" / "stdlib-registry.json"
            ),
            "STRLING_ISLAND_BOUNDARIES_PATH": str(
                payload / "server" / "resources" / "island-boundaries.json"
            ),
        }
    )
    return environment


def _runtime_smoke(payload: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    environment = _runtime_environment(payload, target)
    kernel = environment["STRLING_KERNEL"]
    kernel_result = _run(
        [
            kernel,
            "import",
            "--input",
            "-",
            "--output",
            "semantic",
            "--output",
            "analysis",
            "--partial-semantics",
            "allow_for_diagnostics",
            "--max-diagnostics",
            "256",
            "--format",
            "json",
        ],
        cwd=payload,
        env=environment,
        input_bytes=b"a+",
        timeout=30.0,
    )
    compile_result = json.loads(kernel_result.stdout.decode("utf-8"))
    if compile_result.get("contract_version") != "1.0.0":
        raise PackageError("packaged kernel returned the wrong contract")

    source = "a+"
    source_id = "src:cli." + hashlib.sha256(source.encode("utf-8")).hexdigest()
    request = {
        "contract_version": "1.0.0",
        "source_id": source_id,
        "frontend": "regex",
        "source": source,
        "cursor_byte": 1,
    }
    editor_result = _run(
        [environment["STRLING_EDITOR_CORE"]],
        cwd=payload,
        env=environment,
        input_bytes=_canonical_bytes(request),
        timeout=30.0,
    )
    editor_evidence = json.loads(editor_result.stdout.decode("utf-8"))
    if editor_evidence.get("contract_version") != "1.0.0":
        raise PackageError("packaged editor core returned the wrong contract")
    return {
        "kernel_outcome": compile_result.get("outcome"),
        "kernel_result_fingerprint": _fingerprint(compile_result),
        "editor_result_fingerprint": _fingerprint(editor_evidence),
    }


def _lsp_runtime_evidence(payload: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    completed = _run(
        [
            sys.executable,
            str(LSP_ROOT / "tests" / "packaged_runtime_evidence.py"),
            "--payload",
            str(payload),
            "--target",
            str(target["id"]),
        ],
        cwd=REPOSITORY_ROOT,
        timeout=180.0,
    )
    try:
        evidence = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageError("packaged LSP evidence returned malformed JSON") from error
    if not isinstance(evidence, dict) or evidence.get("status") != "passed":
        raise PackageError("packaged LSP evidence did not pass")
    return evidence


def _extract_extension(vsix: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(vsix) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith("extension/"):
                continue
            relative = info.filename.removeprefix("extension/")
            if not relative:
                continue
            output = _payload_path(destination, relative)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(archive.read(info))
    return destination


def _lifecycle_smoke(
    vsix: Path, contract: Mapping[str, Any], target: Mapping[str, Any], root: Path
) -> dict[str, bool]:
    extensions = root / "extensions"
    extensions.mkdir(parents=True)
    install = extensions / "strling-lang.vscode-strling-1.0.0"
    _extract_extension(vsix, install)
    validate_payload(install, contract, target)
    marker = install / "stale-upgrade-marker"
    marker.write_text("stale", encoding="utf-8")
    resolved_install = install.resolve()
    resolved_extensions = extensions.resolve()
    if resolved_install.parent != resolved_extensions:
        raise PackageError("isolated upgrade target escaped its extension root")
    shutil.rmtree(resolved_install)
    _extract_extension(vsix, install)
    validate_payload(install, contract, target)
    if marker.exists():
        raise PackageError("isolated upgrade retained stale content")
    shutil.rmtree(resolved_install)
    return {
        "install": True,
        "upgrade": True,
        "uninstall": not install.exists(),
    }


def certify(
    requested_target: str, artifact_output: Path | None = None
) -> dict[str, Any]:
    if _git(["status", "--porcelain", "--untracked-files=all"]):
        raise PackageError("clean-checkout certification requires a clean Git tree")
    contract = load_contract()
    target = resolve_target(contract, requested_target)
    with _owned_temporary("certify-") as root:
        payload_a = root / "run-a" / "dist"
        payload_b = root / "run-b" / "dist"
        result_a = assemble(payload_a, str(target["id"]))
        result_b = assemble(payload_b, str(target["id"]))
        if _directory_bytes(payload_a) != _directory_bytes(payload_b):
            raise PackageError("independent payload builds are not byte-for-byte equal")
        vsix_a = (
            root
            / "run-a"
            / (
                f"vscode-strling-{result_a['manifest']['extension_version']}-{target['id']}.vsix"
            )
        )
        vsix_b = (
            root
            / "run-b"
            / (
                f"vscode-strling-{result_b['manifest']['extension_version']}-{target['id']}.vsix"
            )
        )
        _package_vsix(payload_a, target, vsix_a)
        _package_vsix(payload_b, target, vsix_b)
        zip_entries_a = _zip_entries(vsix_a)
        zip_entries_b = _zip_entries(vsix_b)
        if zip_entries_a != zip_entries_b:
            raise PackageError("independent VSIX entry manifests differ")
        runtime = _runtime_smoke(payload_a, target)
        lsp = _lsp_runtime_evidence(payload_a, target)
        lifecycle = _lifecycle_smoke(vsix_a, contract, target, root / "lifecycle")
        result: dict[str, Any] = {
            "status": "passed",
            "target": target["id"],
            "rust_host": target["rust_host"],
            "source_commit": result_a["manifest"]["source_commit"],
            "contract_fingerprint": contract["contract_fingerprint"],
            "payload_fingerprint": result_a["manifest"]["payload_fingerprint"],
            "payload_files": len(result_a["manifest"]["entries"]) + 1,
            "vsix_sha256": _file_fingerprint(vsix_a),
            "vsix_entry_fingerprint": _fingerprint(zip_entries_a),
            "vsix_entries": len(zip_entries_a),
            "payload_reproducible": True,
            "vsix_entries_reproducible": True,
            "runtime": runtime,
            "lsp": lsp,
            "lifecycle": lifecycle,
        }
        if artifact_output is not None:
            retained = _new_artifact_path(artifact_output, suffix=".vsix")
            shutil.copyfile(vsix_a, retained)
            if _file_fingerprint(retained) != result["vsix_sha256"]:
                raise PackageError("retained VSIX differs from the certified artifact")
            result["retained_vsix"] = str(retained)
        return result


def _default_vsix(target: Mapping[str, Any]) -> Path:
    version = _load_json(LSP_ROOT / "package.json")["version"]
    return LSP_ROOT / f"vscode-strling-{version}-{target['id']}.vsix"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("assemble", "package", "certify"):
        command = subparsers.add_parser(name)
        command.add_argument("--target", default="auto")
    subparsers.choices["assemble"].add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT
    )
    subparsers.choices["package"].add_argument("--output", type=Path, default=None)
    subparsers.choices["certify"].add_argument("--output", type=Path, default=None)
    subparsers.choices["certify"].add_argument("--evidence", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "assemble":
            result = assemble(args.output, args.target)
        elif args.command == "package":
            result = assemble(DEFAULT_OUTPUT, args.target)
            target = result["target"]
            output = args.output or _default_vsix(target)
            result = {
                **result,
                "vsix": str(_package_vsix(DEFAULT_OUTPUT, target, output)),
            }
        else:
            result = certify(args.target, args.output)
    except PackageError as error:
        print(f"STRling package error: {error}", file=sys.stderr)
        return 2
    evidence = getattr(args, "evidence", None)
    if evidence is not None:
        evidence_path = _new_artifact_path(evidence, suffix=".json")
        evidence_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=4, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
