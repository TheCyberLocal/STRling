#!/usr/bin/env python3
"""Freeze and validate the C#/F# .NET adapter migration evidence."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "dotnet-3.0"
BASE_COMMIT = "352d7c2547a58f692a709e464b458bf83103b09c"
CONTRACT_FILES = (
    "spec/contracts/1.0/compile-request.schema.json",
    "spec/contracts/1.0/compile-result.schema.json",
    "spec/contracts/1.0/diagnostic.schema.json",
    "spec/contracts/1.0/semantic-ir.schema.json",
    "spec/contracts/1.0/target-artifact.schema.json",
    "spec/contracts/1.0/target-profile.schema.json",
    "spec/frontends/simply/1.0/adapter-response.schema.json",
    "spec/frontends/simply/1.0/builder-request.schema.json",
    "spec/frontends/simply/1.0/protocol.json",
    "spec/frontends/simply/1.1/adapter-response.schema.json",
    "spec/frontends/simply/1.1/builder-request.schema.json",
    "spec/frontends/simply/1.1/protocol.json",
    "spec/interop/1.0/abi.json",
    "spec/interop/1.0/interop.schema.json",
    "spec/stdlib/registry/1.0/canonical-semantics.json",
    "spec/stdlib/registry/1.0/registry.json",
    "spec/targets/profiles/pcre2-10.43.json",
)
PRODUCT_PROJECTS = (
    "bindings/csharp/src/STRling/STRling.csproj",
    "bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj",
    "bindings/fsharp/src/STRling/STRling.fsproj",
)
SEMANTIC_PATHS = (
    "bindings/csharp/src/STRling/Core/Compiler.cs",
    "bindings/csharp/src/STRling/Core/HintEngine.cs",
    "bindings/csharp/src/STRling/Core/IR.cs",
    "bindings/csharp/src/STRling/Core/Nodes.cs",
    "bindings/csharp/src/STRling/Core/Parser.cs",
    "bindings/csharp/src/STRling/Emit/Pcre2Emitter.cs",
    "bindings/csharp/src/STRling/Essential.cs",
    "bindings/csharp/src/STRling/Pattern.cs",
    "bindings/csharp/src/STRling/Simply.cs",
    "bindings/csharp/src/STRling/Strling.cs",
    "bindings/fsharp/src/STRling/AST.fs",
    "bindings/fsharp/src/STRling/Compiler.fs",
    "bindings/fsharp/src/STRling/Core/Errors.fs",
    "bindings/fsharp/src/STRling/Core/Flags.fs",
    "bindings/fsharp/src/STRling/Core/Parser.fs",
    "bindings/fsharp/src/STRling/Emitters/Pcre2.fs",
    "bindings/fsharp/src/STRling/IR.fs",
    "bindings/fsharp/src/STRling/Simply.fs",
)
EXPECTED_FINGERPRINTS = {
    "tree": "sha256:3c24de77632d4cdbf1781cbfc1b2f48d9fa1c434deebec185a18c360632359da",
    "production": "sha256:06a6db43cd7e3c75215a36c3779023930e91d3779740eb97e0d1a4fc4eca8c24",
    "public": "sha256:abb278a6e9208005789488e5895534a580b53cb91a13f09c7a8ea207b6ac135f",
    "semantic": "sha256:19b47113cce1d9528e90921339575b87557498e283bcc317b0357035e00d9c5b",
}
EXPECTED_COUNTS = {
    "tree": 50,
    "production": 24,
    "tests": 12,
    "public": 26,
    "semantic": 18,
}
EXPECTED_FAMILIES = {
    "public_api": 6,
    "canonical_parity": 8,
    "compatibility_success": 5,
    "compatibility_refusal": 5,
    "marshaling_error": 8,
    "lifecycle_concurrency": 6,
    "unicode_resource": 6,
    "simply_stdlib": 8,
    "package_install": 5,
    "architecture_deletion": 6,
    "historical_preservation": 4,
    "runtime_tfm_rid": 5,
}
EXPECTED_BINDINGS = {"dotnet", "csharp", "fsharp"}
EXPECTED_OPERATIONS = {
    "compile",
    "describe",
    "simply.compile",
    "target_profile.inspect",
}
EXPECTED_RUNNERS = {
    "architecture",
    "cross-language",
    "csharp-adapter",
    "dotnet-substrate",
    "fsharp-adapter",
    "historical-reference",
    "manifest",
    "native-lifecycle",
    "package",
    "platform-ci",
    "public-contract",
}
EXPECTED_RUNTIMES = {"sdk-9.0.120", "sdk-9.0.200", "sdk-9.0.302"}
EXPECTED_OBSERVATIONS = (
    (
        "csharp",
        "sdk-9.0.120",
        "passed",
        625,
        "The unchanged net9.0 C# solution passes 625 tests with zero failures or skips.",
    ),
    (
        "fsharp",
        "sdk-9.0.120",
        "historical-passed-wrapper-debt",
        616,
        "The unchanged historical F# compiler passes 616 tests; the separate wrapper remains a zero-public-type incomplete project whose tests do not compile.",
    ),
    (
        "csharp",
        "sdk-9.0.200",
        "passed",
        625,
        "The unchanged net9.0 C# solution passes 625 tests with zero failures or skips.",
    ),
    (
        "fsharp",
        "sdk-9.0.200",
        "historical-passed-wrapper-debt",
        616,
        "The unchanged historical F# compiler passes 616 tests; the separate wrapper remains a zero-public-type incomplete project whose tests do not compile.",
    ),
    (
        "csharp",
        "sdk-9.0.302",
        "passed",
        625,
        "The unchanged net9.0 C# solution passes 625 tests with zero failures or skips.",
    ),
    (
        "fsharp",
        "sdk-9.0.302",
        "historical-passed-wrapper-debt",
        616,
        "The unchanged historical F# compiler passes 616 tests; the separate wrapper remains a zero-public-type incomplete project whose tests do not compile.",
    ),
)
REQUIRED_CASE_IDS = {
    "public-shared-native-client",
    "parity-target-artifact-exact",
    "refusal-no-local-semantic-fallback",
    "marshal-same-descriptor-release",
    "lifecycle-shared-client-reentrant",
    "simply-stdlib-lexical-not-semantic",
    "package-release-graph-one-substrate",
    "architecture-semantic-copy-denominator",
    "historical-source-bundle-replay",
    "runtime-sdk-9-0-120",
    "runtime-sdk-9-0-302",
}


class DotNetAdapterCertificationError(RuntimeError):
    """Raised when the .NET evidence denominator is invalid."""


@dataclass(frozen=True)
class DotNetAdapterCertificationReport:
    contract_fingerprint: str
    evidence_fingerprint: str
    baseline_fingerprint: str
    case_count: int
    family_counts: dict[str, int]
    tree_file_count: int
    public_input_count: int
    semantic_copy_count: int
    historical_source_count: int


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DotNetAdapterCertificationError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise DotNetAdapterCertificationError(f"{path} must contain one JSON object")
    return value


def _fingerprint_json(
    value: Mapping[str, Any], excluded: set[str] | None = None
) -> str:
    normalized = {
        key: item for key, item in value.items() if key not in (excluded or set())
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _files_fingerprint(root: Path, paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        content = (root / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def _git(
    root: Path, *arguments: str, text: bool = True
) -> subprocess.CompletedProcess[Any]:
    process = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=text, check=False
    )
    if process.returncode != 0:
        detail = (
            process.stderr.strip() if text else process.stderr.decode(errors="replace")
        )
        raise DotNetAdapterCertificationError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return process


def _path_sets(root: Path) -> dict[str, tuple[str, ...]]:
    tree = tuple(
        line
        for line in _git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            BASE_COMMIT,
            "--",
            "bindings/csharp",
            "bindings/fsharp",
        ).stdout.splitlines()
        if line
    )
    production = tuple(
        path for path in tree if "/src/" in path and path.endswith((".cs", ".fs"))
    )
    tests = tuple(
        path
        for path in tree
        if ("/test/" in path or "/tests/" in path) and path.endswith((".cs", ".fs"))
    )
    public = tuple(
        sorted(
            (
                *(path for path in production if "/STRling.Cli/" not in path),
                *PRODUCT_PROJECTS,
            )
        )
    )
    semantic = SEMANTIC_PATHS
    actual = {
        "tree": len(tree),
        "production": len(production),
        "tests": len(tests),
        "public": len(public),
        "semantic": len(semantic),
    }
    if actual != EXPECTED_COUNTS:
        raise DotNetAdapterCertificationError(
            f"task-start .NET path denominator changed: {actual!r}"
        )
    if any(path not in tree for path in public + semantic):
        raise DotNetAdapterCertificationError("task-start .NET path set is incomplete")
    return {
        "tree": tree,
        "production": production,
        "tests": tests,
        "public": public,
        "semantic": semantic,
    }


def _git_blob(root: Path, relative: str) -> bytes:
    return _git(root, "show", f"{BASE_COMMIT}:{relative}", text=False).stdout


def _git_fingerprint(root: Path, paths: Sequence[str]) -> str:
    listing = _git(root, "ls-tree", "-r", BASE_COMMIT, "--", *paths, text=False).stdout
    return f"sha256:{hashlib.sha256(listing).hexdigest()}"


def _blob(path: str, content: bytes, *, include_content: bool) -> dict[str, str]:
    result = {
        "path": path,
        "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }
    if include_content:
        result["content_base64"] = base64.b64encode(content).decode("ascii")
    return result


def _build_baseline(root: Path) -> dict[str, Any]:
    resolved = _git(root, "rev-parse", f"{BASE_COMMIT}^{{commit}}").stdout.strip()
    if resolved != BASE_COMMIT:
        raise DotNetAdapterCertificationError(
            ".NET task-start commit does not resolve exactly"
        )
    paths = _path_sets(root)
    fingerprints = {
        name: _git_fingerprint(root, paths[name])
        for name in ("tree", "production", "public", "semantic")
    }
    if fingerprints != EXPECTED_FINGERPRINTS:
        raise DotNetAdapterCertificationError(
            f"task-start .NET fingerprints changed: {fingerprints!r}"
        )
    cache = {path: _git_blob(root, path) for path in paths["tree"]}
    baseline: dict[str, Any] = {
        "$schema": "evidence.schema.json#/$defs/LegacyBaseline",
        "suite_id": "strling.dotnet-adapter-legacy-baseline",
        "suite_version": "3.0.0",
        "base_commit": BASE_COMMIT,
        "fingerprints": fingerprints,
        "public_files": [
            _blob(path, cache[path], include_content=False) for path in paths["public"]
        ],
        "semantic_copy_files": [
            _blob(path, cache[path], include_content=False)
            for path in paths["semantic"]
        ],
        "historical_source_files": [
            _blob(path, cache[path], include_content=True) for path in paths["tree"]
        ],
    }
    baseline["fingerprint"] = _fingerprint_json(baseline)
    return baseline


def _validate(schema: Mapping[str, Any], value: Mapping[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise DotNetAdapterCertificationError(
            f"{label} invalid at {location}: {error.message}"
        )


class DotNetAdapterCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.evidence_root = root / "tests" / "adapters" / "dotnet-3.0"

    def certify(self) -> DotNetAdapterCertificationReport:
        schema = _read_json(self.evidence_root / "evidence.schema.json")
        manifest = _read_json(self.evidence_root / "manifest.json")
        baseline = _read_json(self.evidence_root / "legacy-baseline.json")
        Draft202012Validator.check_schema(schema)
        return self.certify_documents(
            schema,
            manifest,
            baseline,
            expected_baseline=_build_baseline(self.root),
            contract_fingerprint=_files_fingerprint(self.root, CONTRACT_FILES),
        )

    def certify_documents(
        self,
        schema: Mapping[str, Any],
        manifest: Mapping[str, Any],
        baseline: Mapping[str, Any],
        *,
        expected_baseline: Mapping[str, Any],
        contract_fingerprint: str,
    ) -> DotNetAdapterCertificationReport:
        _validate(schema, manifest, ".NET adapter evidence manifest")
        baseline_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": "#/$defs/LegacyBaseline",
        }
        _validate(baseline_schema, baseline, ".NET legacy baseline")
        contract = manifest["contract"]
        legacy = manifest["legacy"]
        counts = manifest["counts"]
        cases = manifest["cases"]
        observations = manifest["task_start_observations"]
        if tuple(contract["files"]) != CONTRACT_FILES:
            raise DotNetAdapterCertificationError(
                ".NET contract file set or order changed"
            )
        if contract["fingerprint"] != contract_fingerprint:
            raise DotNetAdapterCertificationError(".NET contract fingerprint changed")
        expected_legacy = {
            "base_commit": BASE_COMMIT,
            "baseline_path": "tests/adapters/dotnet-3.0/legacy-baseline.json",
            "tree_file_count": EXPECTED_COUNTS["tree"],
            "production_source_count": EXPECTED_COUNTS["production"],
            "test_source_count": EXPECTED_COUNTS["tests"],
            "public_input_count": EXPECTED_COUNTS["public"],
            "semantic_copy_count": EXPECTED_COUNTS["semantic"],
            "tree_fingerprint": EXPECTED_FINGERPRINTS["tree"],
            "production_fingerprint": EXPECTED_FINGERPRINTS["production"],
            "public_fingerprint": EXPECTED_FINGERPRINTS["public"],
            "semantic_copy_fingerprint": EXPECTED_FINGERPRINTS["semantic"],
        }
        if legacy != expected_legacy:
            raise DotNetAdapterCertificationError(".NET legacy denominator changed")
        if baseline != expected_baseline:
            raise DotNetAdapterCertificationError(
                ".NET legacy baseline does not reproduce"
            )
        ids = [str(case["id"]) for case in cases]
        if len(ids) != len(set(ids)):
            raise DotNetAdapterCertificationError(
                ".NET evidence case ids must be unique"
            )
        families = dict(Counter(str(case["family"]) for case in cases))
        if families != EXPECTED_FAMILIES or counts["families"] != EXPECTED_FAMILIES:
            raise DotNetAdapterCertificationError(
                f".NET evidence family denominator changed: {families!r}"
            )
        if counts["total"] != 72 or len(cases) != 72:
            raise DotNetAdapterCertificationError(".NET evidence total changed")
        bindings = {str(item) for case in cases for item in case["bindings"]}
        runners = {str(case["runner"]) for case in cases}
        operations = {str(case["operation"]) for case in cases if "operation" in case}
        runtimes = {str(case["runtime"]) for case in cases if "runtime" in case}
        if bindings != EXPECTED_BINDINGS:
            raise DotNetAdapterCertificationError(".NET binding denominator changed")
        if runners != EXPECTED_RUNNERS:
            raise DotNetAdapterCertificationError(".NET runner denominator changed")
        if operations != EXPECTED_OPERATIONS:
            raise DotNetAdapterCertificationError(".NET operation denominator changed")
        if runtimes != EXPECTED_RUNTIMES:
            raise DotNetAdapterCertificationError(".NET runtime denominator changed")
        if not REQUIRED_CASE_IDS.issubset(ids):
            raise DotNetAdapterCertificationError(
                "required .NET evidence cases are missing"
            )
        actual_observations = tuple(
            (
                str(item["binding"]),
                str(item["runtime"]),
                str(item["status"]),
                item["tests"],
                str(item["detail"]),
            )
            for item in observations
        )
        if actual_observations != EXPECTED_OBSERVATIONS:
            raise DotNetAdapterCertificationError(
                "task-start .NET observations changed"
            )
        evidence_fingerprint = _fingerprint_json(manifest, {"fingerprint"})
        if manifest["fingerprint"] != evidence_fingerprint:
            raise DotNetAdapterCertificationError(".NET evidence fingerprint changed")
        return DotNetAdapterCertificationReport(
            contract_fingerprint=contract_fingerprint,
            evidence_fingerprint=evidence_fingerprint,
            baseline_fingerprint=str(baseline["fingerprint"]),
            case_count=72,
            family_counts=families,
            tree_file_count=EXPECTED_COUNTS["tree"],
            public_input_count=EXPECTED_COUNTS["public"],
            semantic_copy_count=EXPECTED_COUNTS["semantic"],
            historical_source_count=EXPECTED_COUNTS["tree"],
        )


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=4) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--write-manifest-fingerprint", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_baseline:
            _write_json(EVIDENCE_ROOT / "legacy-baseline.json", _build_baseline(ROOT))
        if arguments.write_manifest_fingerprint:
            manifest = _read_json(EVIDENCE_ROOT / "manifest.json")
            manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
            _write_json(EVIDENCE_ROOT / "manifest.json", manifest)
        report = DotNetAdapterCertificationSuite().certify()
        payload = {"status": "passed", **report.__dict__}
    except (DotNetAdapterCertificationError, OSError, ValueError) as error:
        if arguments.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f".NET adapter certification failed: {error}")
        return 1
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
