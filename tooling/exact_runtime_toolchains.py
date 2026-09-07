#!/usr/bin/env python3
"""Validate reconstructible exact-runtime identities used by certification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling.contract_validation import canonical_json, load_json
from tooling.pcre2_feature_probe import Engine

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "governance" / "exact-runtime-toolchains.json"
PYTHON_CORPUS = ROOT / "tests" / "conformance" / "python-re-runtime-certification.json"
EXECUTION_CORPORA = (
    ROOT / "tests" / "conformance" / "ecmascript-runtime-certification.json",
    ROOT / "tests" / "conformance" / "pcre2-runtime-certification.json",
    PYTHON_CORPUS,
)
EQUIVALENCE_REGISTRY = (
    ROOT / "spec" / "portability" / "equivalence" / "1.0" / "registry.json"
)
LSP_ACTION_MANIFEST = (
    ROOT
    / "tooling"
    / "lsp-server"
    / "tests"
    / "fixtures"
    / "canonical-actions-islands"
    / "manifest.json"
)
EXPECTED_KEYS = (
    "cpython-3.11.15",
    "node-22.23.2",
    "pcre2-10.42",
    "pcre2-10.43",
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ExactRuntimeToolchainError(ValueError):
    """The governed runtime reconstruction contract is invalid."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != "1.0.0":
        raise ExactRuntimeToolchainError("unsupported exact-runtime schema version")
    platform_contract = value.get("platform")
    if not isinstance(platform_contract, Mapping):
        raise ExactRuntimeToolchainError("platform contract is missing")
    toolchains = value.get("toolchains")
    if not isinstance(toolchains, Mapping) or tuple(sorted(toolchains)) != tuple(
        sorted(EXPECTED_KEYS)
    ):
        raise ExactRuntimeToolchainError("exact-runtime toolchain set differs")
    for key in EXPECTED_KEYS:
        record = toolchains[key]
        if not isinstance(record, Mapping):
            raise ExactRuntimeToolchainError(f"{key} record is malformed")
        environment = record.get("environment")
        artifact = record.get("artifact")
        source = record.get("source")
        build = record.get("build")
        layout = record.get("layout")
        if not isinstance(environment, str) or not environment.startswith("STRLING_"):
            raise ExactRuntimeToolchainError(f"{key} environment is malformed")
        if not isinstance(artifact, Mapping) or not SHA256.fullmatch(
            str(artifact.get("sha256", ""))
        ):
            raise ExactRuntimeToolchainError(f"{key} artifact identity is malformed")
        if not isinstance(source, Mapping) or not isinstance(build, Mapping):
            raise ExactRuntimeToolchainError(f"{key} provenance is incomplete")
        if not isinstance(layout, Mapping) or not str(
            layout.get("absolute_path", "")
        ).startswith("/opt/"):
            raise ExactRuntimeToolchainError(f"{key} governed layout is incomplete")
    node = toolchains["node-22.23.2"]
    if node["source"].get("sha256") != (
        "d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307"
    ):
        raise ExactRuntimeToolchainError("Node source archive identity differs")
    if node.get("identity") != {
        "architecture": "x64",
        "node": "v22.23.2",
        "platform": "linux",
        "v8": "12.4.254.21-node.56",
    }:
        raise ExactRuntimeToolchainError("Node runtime identity differs")
    python = toolchains["cpython-3.11.15"]
    if python["source"].get("sha256") != (
        "272179ddd9a2e41a0fc8e42e33dfbdca0b3711aa5abf372d3f2d51543d09b625"
    ):
        raise ExactRuntimeToolchainError("CPython source archive identity differs")
    if python.get("reproducibility", {}).get("identical_clean_builds", 0) < 2:
        raise ExactRuntimeToolchainError("CPython reproducibility proof is incomplete")
    for version, commit in (
        ("10.42", "52c08847921a324c804cabf2814549f50bce1265"),
        ("10.43", "3864abdb713f78831dd12d898ab31bbb0fa630b6"),
    ):
        if toolchains[f"pcre2-{version}"]["source"].get("commit") != commit:
            raise ExactRuntimeToolchainError(f"PCRE2 {version} source identity differs")


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    value = load_json(path)
    validate_manifest(value)
    return value


def artifact_sha256(key: str) -> str:
    manifest = load_manifest()
    try:
        return str(manifest["toolchains"][key]["artifact"]["sha256"])
    except KeyError as error:
        raise ExactRuntimeToolchainError(f"unknown exact runtime {key}") from error


def _capture(command: Sequence[str]) -> str:
    completed = subprocess.run(
        list(command),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ExactRuntimeToolchainError(
            f"runtime identity command failed: {' '.join(command)}"
        )
    return completed.stdout.strip()


def verify_configured_runtimes(
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    governed = dict(manifest or load_manifest())
    platform_contract = governed["platform"]
    if platform.system() != platform_contract["system"] or (
        platform.machine() != platform_contract["machine"]
    ):
        raise ExactRuntimeToolchainError("host platform differs from runtime contract")
    checked: dict[str, Any] = {}
    for key in EXPECTED_KEYS:
        record = governed["toolchains"][key]
        env_name = record["environment"]
        value = os.environ.get(env_name)
        if not value:
            raise ExactRuntimeToolchainError(f"{env_name} is not configured")
        path = Path(value)
        if not path.is_file():
            raise ExactRuntimeToolchainError(f"{env_name} is not a file")
        observed = file_sha256(path)
        if observed != record["artifact"]["sha256"]:
            raise ExactRuntimeToolchainError(f"{key} artifact SHA-256 differs")
        checked[key] = {"path": str(path), "sha256": observed}
    python_path = checked["cpython-3.11.15"]["path"]
    python_identity = json.loads(
        _capture(
            [
                python_path,
                "-I",
                "-S",
                "-B",
                "-c",
                (
                    "import json,platform,sys,sysconfig;"
                    "print(json.dumps({'version':platform.python_version(),"
                    "'implementation':platform.python_implementation().lower(),"
                    "'platform':sys.platform,'machine':platform.machine(),"
                    "'soabi':sysconfig.get_config_var('SOABI'),"
                    "'sysconfig_platform':sysconfig.get_platform()},sort_keys=True))"
                ),
            ]
        )
    )
    expected_python = {
        "implementation": "cpython",
        "machine": "x86_64",
        "platform": "linux",
        "soabi": "cpython-311-x86_64-linux-gnu",
        "sysconfig_platform": "linux-x86_64",
        "version": "3.11.15",
    }
    if python_identity != expected_python:
        raise ExactRuntimeToolchainError("CPython runtime identity differs")
    checked["cpython-3.11.15"]["identity"] = python_identity
    node_path = checked["node-22.23.2"]["path"]
    node_identity = json.loads(
        _capture(
            [
                node_path,
                "-e",
                (
                    "console.log(JSON.stringify({architecture:process.arch,"
                    "node:process.version,platform:process.platform,"
                    "v8:process.versions.v8}))"
                ),
            ]
        )
    )
    if node_identity != governed["toolchains"]["node-22.23.2"]["identity"]:
        raise ExactRuntimeToolchainError("Node runtime identity differs")
    checked["node-22.23.2"]["identity"] = node_identity
    for version in ("10.42", "10.43"):
        key = f"pcre2-{version}"
        observed_version = Engine(Path(checked[key]["path"])).version()
        if observed_version.split()[0] != version:
            raise ExactRuntimeToolchainError(
                f"PCRE2 {version} runtime identity differs"
            )
        checked[key]["identity"] = {"engine_version": observed_version}
    return {
        "schema_version": governed["schema_version"],
        "status": "passed",
        "toolchains": checked,
        "manifest_sha256": hashlib.sha256(canonical_json(governed)).hexdigest(),
    }


def write_python_corpus_identity() -> None:
    text = PYTHON_CORPUS.read_text(encoding="utf-8")
    pattern = re.compile(r'("executable_sha256": ")[0-9a-f]{64}("[,])')
    updated, replacements = pattern.subn(
        rf"\g<1>{artifact_sha256('cpython-3.11.15')}\g<2>", text
    )
    if replacements != 1:
        raise ExactRuntimeToolchainError(
            "Python corpus must contain exactly one executable identity"
        )
    PYTHON_CORPUS.write_text(updated, encoding="utf-8", newline="\n")


def write_equivalence_registry_identity() -> None:
    text = EQUIVALENCE_REGISTRY.read_text(encoding="utf-8")
    for corpus in EXECUTION_CORPORA:
        relative = corpus.relative_to(ROOT).as_posix()
        pattern = re.compile(
            rf'("path": "{re.escape(relative)}",\s*"sha256": ")'
            r"[0-9a-f]{64}(\")"
        )
        text, replacements = pattern.subn(rf"\g<1>{file_sha256(corpus)}\g<2>", text)
        if replacements != 2:
            raise ExactRuntimeToolchainError(
                f"equivalence registry must contain two {relative} execution identities"
            )
    EQUIVALENCE_REGISTRY.write_text(text, encoding="utf-8", newline="\n")


def strategy_fingerprints() -> dict[str, str]:
    registry = load_json(EQUIVALENCE_REGISTRY)
    strategies = registry.get("strategies")
    if not isinstance(strategies, list) or len(strategies) != 2:
        raise ExactRuntimeToolchainError(
            "equivalence registry strategy set is malformed"
        )
    fingerprints: dict[str, str] = {}
    for strategy in strategies:
        if not isinstance(strategy, Mapping) or not isinstance(
            strategy.get("strategy_id"), str
        ):
            raise ExactRuntimeToolchainError(
                "equivalence registry strategy is malformed"
            )
        fingerprints[strategy["strategy_id"]] = hashlib.sha256(
            canonical_json(strategy)
        ).hexdigest()
    return fingerprints


def _replace_identity(text: str, pattern: str, identity: str, *, path: Path) -> str:
    updated, replacements = re.subn(
        pattern,
        rf"\g<1>{identity}\g<2>",
        text,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise ExactRuntimeToolchainError(
            f"{path.relative_to(ROOT).as_posix()} identity boundary differs"
        )
    return updated


def _rewrite_strategy_references() -> dict[Path, str]:
    fingerprints = strategy_fingerprints()
    atomic = fingerprints["rewrite.atomic_literal.elide.v1"]
    exact_once = fingerprints["rewrite.repeat_exactly_once.elide.v1"]
    rewrites = {
        ROOT / "core/tests/rewrite_equivalence_registry.rs": (
            (
                r'(direct\.strategies\[0\]\.strategy_fingerprint\.as_str\(\),\s*")'
                r"[0-9a-f]{64}(\")",
                atomic,
            ),
            (
                r'(direct\.strategies\[1\]\.strategy_fingerprint\.as_str\(\),\s*")'
                r"[0-9a-f]{64}(\")",
                exact_once,
            ),
        ),
        ROOT / "core/tests/portability_diagnostics.rs": (
            (
                r'(assert!\(advice\.contains\("rewrite\.atomic_literal\.elide\.v1"\)\);\s*'
                r'assert!\(\s*advice\.contains\("sha256:)'
                r"[0-9a-f]{64}(\")",
                atomic,
            ),
        ),
        ROOT / "core/tests/semantic_rewrite.rs": (
            (
                r'(first\.certification\.strategy_fingerprint\.as_str\(\),\s*")'
                r"[0-9a-f]{64}(\")",
                exact_once,
            ),
        ),
        ROOT / "core/tests/editor_intelligence.rs": (
            (
                r'(action\.strategy_fingerprint,\s*")'
                r"[0-9a-f]{64}(\")",
                exact_once,
            ),
        ),
        ROOT / "docs/portability-planning.md": (
            (
                r"(The current `rewrite\.atomic_literal\.elide\.v1` definition has canonical strategy\s*"
                r"fingerprint\s*`)[0-9a-f]{64}(`)",
                atomic,
            ),
            (
                r"(`rewrite\.repeat_exactly_once\.elide\.v1` definition with canonical strategy\s*"
                r"fingerprint\s*`)[0-9a-f]{64}(`)",
                exact_once,
            ),
        ),
        ROOT
        / "spec/contracts/1.0/examples/compile-result/equivalence-explanation.json": (
            (
                r"(strategy rewrite\.atomic_literal\.elide\.v1 sha256:)"
                r"[0-9a-f]{64}(;)",
                atomic,
            ),
        ),
        ROOT / "tooling/lsp-server/tests/test_canonical_actions_islands_evidence.py": (
            (
                r'(strategy_fingerprint"\] == \(\s*"sha256:)'
                r"[0-9a-f]{64}(\")",
                exact_once,
            ),
        ),
        LSP_ACTION_MANIFEST: (
            (
                r'("strategy_fingerprint": "sha256:)'
                r"[0-9a-f]{64}(\")",
                exact_once,
            ),
            (
                r'("rewrite_registry": "sha256:)'
                r"[0-9a-f]{64}(\")",
                file_sha256(EQUIVALENCE_REGISTRY),
            ),
        ),
    }
    rendered: dict[Path, str] = {}
    for path, replacements in rewrites.items():
        text = path.read_text(encoding="utf-8")
        for pattern, identity in replacements:
            text = _replace_identity(text, pattern, identity, path=path)
        if path == LSP_ACTION_MANIFEST:
            manifest = json.loads(text)
            material = dict(manifest)
            material.pop("fingerprint", None)
            manifest_identity = hashlib.sha256(canonical_json(material)).hexdigest()
            text = _replace_identity(
                text,
                r'(^    "fingerprint": "sha256:)[0-9a-f]{64}("$)',
                manifest_identity,
                path=path,
            )
        rendered[path] = text
    return rendered


def write_strategy_references() -> None:
    for path, text in _rewrite_strategy_references().items():
        path.write_text(text, encoding="utf-8", newline="\n")


def verify_strategy_references() -> None:
    for path, expected in _rewrite_strategy_references().items():
        if path.read_text(encoding="utf-8") != expected:
            raise ExactRuntimeToolchainError(
                f"{path.relative_to(ROOT).as_posix()} strategy identity is stale"
            )


def verify_dependent_identities() -> None:
    python_text = PYTHON_CORPUS.read_text(encoding="utf-8")
    expected_python, replacements = re.subn(
        r'("executable_sha256": ")[0-9a-f]{64}("[,])',
        rf"\g<1>{artifact_sha256('cpython-3.11.15')}\g<2>",
        python_text,
    )
    if replacements != 1 or expected_python != python_text:
        raise ExactRuntimeToolchainError("Python corpus runtime identity is stale")
    registry_text = EQUIVALENCE_REGISTRY.read_text(encoding="utf-8")
    expected_registry = registry_text
    for corpus in EXECUTION_CORPORA:
        relative = corpus.relative_to(ROOT).as_posix()
        expected_registry, replacements = re.subn(
            rf'("path": "{re.escape(relative)}",\s*"sha256": ")'
            r"[0-9a-f]{64}(\")",
            rf"\g<1>{file_sha256(corpus)}\g<2>",
            expected_registry,
        )
        if replacements != 2:
            raise ExactRuntimeToolchainError(
                f"equivalence registry {relative} identity boundary differs"
            )
    if expected_registry != registry_text:
        raise ExactRuntimeToolchainError(
            "equivalence registry runtime identity is stale"
        )
    verify_strategy_references()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-python-corpus", action="store_true")
    parser.add_argument("--write-dependent-identities", action="store_true")
    parser.add_argument("--write-strategy-references", action="store_true")
    parser.add_argument("--check-strategy-references", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.write_python_corpus:
        write_python_corpus_identity()
    if args.write_dependent_identities:
        write_python_corpus_identity()
        write_equivalence_registry_identity()
        write_strategy_references()
    if args.write_strategy_references:
        write_strategy_references()
    if args.check_strategy_references:
        verify_strategy_references()
    if args.check:
        verify_dependent_identities()
    result = verify_configured_runtimes() if args.check else {"status": "passed"}
    if args.json:
        print(
            json.dumps(
                result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
    else:
        print(f"Exact runtime toolchains: {result['status'].upper()}")


if __name__ == "__main__":
    main()
