#!/usr/bin/env python3
"""Freeze and validate the Go, Dart, and Swift adapter migration evidence."""

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
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "go-dart-swift-3.0"
BASE_COMMIT = "b6cefe0add189d687f7c2940f4a505621c60c8e4"
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
PUBLIC_METADATA = (
    "bindings/dart/pubspec.lock",
    "bindings/dart/pubspec.yaml",
    "bindings/go/go.mod",
    "bindings/swift/Package.swift",
)
SEMANTIC_PATHS = (
    "bindings/go/ast.go",
    "bindings/go/core/compiler.go",
    "bindings/go/core/diagnostics.go",
    "bindings/go/core/errors.go",
    "bindings/go/core/hint_engine.go",
    "bindings/go/core/ir.go",
    "bindings/go/core/nodes.go",
    "bindings/go/core/parser.go",
    "bindings/go/core/validator.go",
    "bindings/go/emitters/pcre2.go",
    "bindings/go/simply/essential.go",
    "bindings/go/simply/simply.go",
    "bindings/dart/lib/essential.dart",
    "bindings/dart/lib/simply.dart",
    "bindings/dart/lib/src/core/diagnostics.dart",
    "bindings/dart/lib/src/core/hint_engine.dart",
    "bindings/dart/lib/src/core/parser.dart",
    "bindings/dart/lib/src/emitters/pcre2.dart",
    "bindings/dart/lib/src/nodes.dart",
    "bindings/swift/Sources/STRling/Core/Compiler.swift",
    "bindings/swift/Sources/STRling/Core/Diagnostics.swift",
    "bindings/swift/Sources/STRling/Core/Errors.swift",
    "bindings/swift/Sources/STRling/Core/HintEngine.swift",
    "bindings/swift/Sources/STRling/Core/IR.swift",
    "bindings/swift/Sources/STRling/Core/Nodes.swift",
    "bindings/swift/Sources/STRling/Core/Parser.swift",
    "bindings/swift/Sources/STRling/Emitters/PCRE2Emitter.swift",
    "bindings/swift/Sources/STRling/Essential.swift",
    "bindings/swift/Sources/STRling/Simply.swift",
    "bindings/swift/Sources/STRling/STRling.swift",
)
EXPECTED_COUNTS = {
    "tree": 204,
    "production": 32,
    "tests": 33,
    "public": 36,
    "semantic": 30,
}
EXPECTED_FINGERPRINTS = {
    "tree": "sha256:73e6e1cf7d3a5680b34168281a34f5d8f8cbea1a537fa4cf204a825f8fd1d705",
    "production": "sha256:d320dca43fb1a116257f1eda26d4536d37bbacde9260d45b381c0b5df5ef2dd2",
    "public": "sha256:966649cfc645494edb566f2aec2c71fc8fb58733d398ff6f4555882848214e65",
    "semantic": "sha256:f0b73a498f8eaf96ecf82e6748dea265b95b91f6a15c9893ed7f502a9026c539",
}
EXPECTED_FAMILIES = {
    "public_api": 9,
    "canonical_parity": 9,
    "compatibility_success": 6,
    "compatibility_refusal": 6,
    "marshaling_error": 9,
    "lifecycle_concurrency": 8,
    "unicode_resource": 6,
    "simply_stdlib": 6,
    "package_install": 6,
    "architecture_deletion": 6,
    "historical_preservation": 4,
    "platform_toolchain": 3,
}
EXPECTED_BINDINGS = {"go", "dart", "swift"}
EXPECTED_OPERATIONS = {
    "compile",
    "describe",
    "simply.compile",
    "target_profile.inspect",
}
EXPECTED_RUNNERS = {
    "architecture",
    "cross-language",
    "dart-adapter",
    "go-adapter",
    "historical-reference",
    "manifest",
    "native-lifecycle",
    "package",
    "platform-ci",
    "public-contract",
    "swift-adapter",
}
EXPECTED_RUNTIMES = {"go->=1.22,<1.23", "dart->=3.0,<4.0", "swift->=5.9,<7.0"}
EXPECTED_OBSERVATIONS = (
    (
        "go",
        "go->=1.22,<1.23",
        "unavailable",
        None,
        "The Go executable and cgo toolchain are absent on the task-start Windows host; no build, test, or platform claim is inferred.",
    ),
    (
        "dart",
        "dart->=3.0,<4.0",
        "unavailable",
        None,
        "The Dart executable is absent on the task-start Windows host; no VM/native build, analyzer, test, or platform claim is inferred.",
    ),
    (
        "swift",
        "swift->=5.9,<7.0",
        "unavailable",
        None,
        "The Swift executable and C interop toolchain are absent on the task-start Windows host; historical Apple metadata is not an executed support claim.",
    ),
)


class GoDartSwiftAdapterCertificationError(RuntimeError):
    """Raised when the Go/Dart/Swift evidence denominator is invalid."""


@dataclass(frozen=True)
class GoDartSwiftAdapterCertificationReport:
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
        raise GoDartSwiftAdapterCertificationError(
            f"cannot read {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise GoDartSwiftAdapterCertificationError(
            f"{path} must contain one JSON object"
        )
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
            process.stderr.strip()
            if text
            else process.stderr.decode(errors="replace")
        )
        raise GoDartSwiftAdapterCertificationError(
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
            "bindings/go",
            "bindings/dart",
            "bindings/swift",
        ).stdout.splitlines()
        if line
    )
    production = tuple(
        path
        for path in tree
        if (
            path.startswith("bindings/go/")
            and path.endswith(".go")
            and not path.endswith("_test.go")
        )
        or (path.startswith("bindings/dart/lib/") and path.endswith(".dart"))
        or (path.startswith("bindings/swift/Sources/") and path.endswith(".swift"))
    )
    tests = tuple(
        path
        for path in tree
        if (path.startswith("bindings/go/") and path.endswith("_test.go"))
        or (path.startswith("bindings/dart/test/") and path.endswith(".dart"))
        or (path.startswith("bindings/swift/Tests/") and path.endswith(".swift"))
    )
    public = tuple(sorted((*production, *PUBLIC_METADATA)))
    semantic = SEMANTIC_PATHS
    actual = {
        "tree": len(tree),
        "production": len(production),
        "tests": len(tests),
        "public": len(public),
        "semantic": len(semantic),
    }
    if actual != EXPECTED_COUNTS:
        raise GoDartSwiftAdapterCertificationError(
            f"task-start Go/Dart/Swift path denominator changed: {actual!r}"
        )
    if any(path not in tree for path in public + semantic):
        raise GoDartSwiftAdapterCertificationError(
            "task-start Go/Dart/Swift path set is incomplete"
        )
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


def _binding_cases(binding: str) -> list[dict[str, Any]]:
    runner = f"{binding}-adapter"
    cases: list[dict[str, Any]] = []

    def add(
        family: str,
        suffix: str,
        claim: str,
        *,
        case_runner: str = runner,
        operation: str | None = None,
    ) -> None:
        case: dict[str, Any] = {
            "id": f"{family.replace('_', '-')}-{binding}-{suffix}",
            "family": family,
            "bindings": [binding],
            "runner": case_runner,
            "claim": claim,
        }
        if operation:
            case["operation"] = operation
        cases.append(case)

    add("public_api", "canonical-facade", "The public facade exposes canonical data without binding semantic types.", case_runner="public-contract")
    add("public_api", "host-errors", "Native transport failures have stable host identities separate from canonical rejections.", case_runner="public-contract")
    add("public_api", "snapshot-reproducible", "The post-migration public snapshot reproduces deterministically.", case_runner="public-contract")
    add("canonical_parity", "compile", "Compile preserves the canonical response exactly.", operation="compile")
    add("canonical_parity", "describe", "Describe preserves the canonical response exactly.", operation="describe")
    add("canonical_parity", "target-profile", "Target profile inspection preserves canonical data exactly.", operation="target_profile.inspect")
    add("compatibility_success", "package-identity", "The governed package or module identity remains stable.", case_runner="package")
    add("compatibility_success", "simply-entrypoint", "Curated Simply entrypoints delegate to canonical requests.", operation="simply.compile")
    add("compatibility_refusal", "abi-mismatch", "ABI mismatch fails before any operation executes.")
    add("compatibility_refusal", "no-local-semantic-fallback", "A missing native boundary cannot fall back to binding semantics.", case_runner="architecture")
    add("marshaling_error", "request-utf8", "Request bytes are strict bounded UTF-8 JSON.")
    add("marshaling_error", "response-bounds", "Response descriptors and byte lengths are validated before decoding.")
    add("marshaling_error", "same-descriptor-release", "Every owned response is freed through its matching native symbol.", case_runner="native-lifecycle")
    add("lifecycle_concurrency", "close-idempotent", "Explicit close is idempotent where the ecosystem exposes it.", case_runner="native-lifecycle")
    add("lifecycle_concurrency", "concurrent-calls", "Concurrent calls remain reentrant and close-safe.", case_runner="native-lifecycle")
    add("unicode_resource", "multibyte", "Multibyte source and diagnostics preserve exact UTF-8 content.")
    add("unicode_resource", "embedded-nul", "Embedded NUL content is length-delimited rather than truncated.")
    add("simply_stdlib", "canonical-equivalence", "Simply output equals the canonical Simply protocol result.", operation="simply.compile")
    add("simply_stdlib", "lexical-not-semantic", "Lexical-shape helpers are not strengthened into semantic validators.")
    add("package_install", "clean-consumer", "A clean consumer can build against the governed local package.", case_runner="package")
    add("package_install", "release-graph-one-substrate", "The release graph contains one native substrate and no semantic copy.", case_runner="package")
    add("architecture_deletion", "semantic-copy-zero", "Every frozen product semantic-copy path is absent after migration.", case_runner="architecture")
    add("architecture_deletion", "runtime-no-fallback", "Runtime sources contain no subprocess, socket, download, or local semantic route.", case_runner="architecture")
    return cases


def _evidence_cases() -> list[dict[str, Any]]:
    cases = [
        case
        for binding in ("go", "dart", "swift")
        for case in _binding_cases(binding)
    ]
    cases.extend(
        [
            {
                "id": "lifecycle-process-exit-clean",
                "family": "lifecycle_concurrency",
                "bindings": ["go", "dart", "swift"],
                "runner": "native-lifecycle",
                "claim": "Process exit leaves no governed adapter allocation outstanding.",
            },
            {
                "id": "lifecycle-use-after-close-refused",
                "family": "lifecycle_concurrency",
                "bindings": ["go", "swift"],
                "runner": "native-lifecycle",
                "claim": "Go and Swift reject calls after explicit close without entering native code.",
            },
            {
                "id": "historical-source-bundle-replay",
                "family": "historical_preservation",
                "bindings": ["go", "dart", "swift"],
                "runner": "historical-reference",
                "claim": "All 204 task-start files materialize byte-for-byte from the authenticated bundle.",
            },
            {
                "id": "historical-public-package-denominator",
                "family": "historical_preservation",
                "bindings": ["go", "dart", "swift"],
                "runner": "manifest",
                "claim": "Thirty-six public, build, package, and lock inputs remain frozen.",
            },
            {
                "id": "historical-semantic-copy-denominator",
                "family": "historical_preservation",
                "bindings": ["go", "dart", "swift"],
                "runner": "architecture",
                "claim": "All thirty task-start product semantic-copy sources remain individually authenticated.",
            },
            {
                "id": "historical-differential-cross-language",
                "family": "historical_preservation",
                "bindings": ["go", "dart", "swift"],
                "runner": "cross-language",
                "claim": "Executed compatible behavior is compared with the historical bundle and canonical result.",
            },
        ]
    )
    for binding, runtime in (
        ("go", "go->=1.22,<1.23"),
        ("dart", "dart->=3.0,<4.0"),
        ("swift", "swift->=5.9,<7.0"),
    ):
        cases.append(
            {
                "id": f"platform-toolchain-{binding}",
                "family": "platform_toolchain",
                "bindings": [binding],
                "runner": "platform-ci",
                "runtime": runtime,
                "claim": "Only executed toolchain and platform rows may become support evidence.",
            }
        )
    return cases


def _build_baseline(root: Path) -> dict[str, Any]:
    resolved = _git(root, "rev-parse", f"{BASE_COMMIT}^{{commit}}").stdout.strip()
    if resolved != BASE_COMMIT:
        raise GoDartSwiftAdapterCertificationError(
            "Go/Dart/Swift task-start commit does not resolve exactly"
        )
    paths = _path_sets(root)
    fingerprints = {
        name: _git_fingerprint(root, paths[name])
        for name in ("tree", "production", "public", "semantic")
    }
    if fingerprints != EXPECTED_FINGERPRINTS:
        raise GoDartSwiftAdapterCertificationError(
            f"task-start Go/Dart/Swift fingerprints changed: {fingerprints!r}"
        )
    cache = {path: _git_blob(root, path) for path in paths["tree"]}
    baseline: dict[str, Any] = {
        "$schema": "evidence.schema.json#/$defs/LegacyBaseline",
        "suite_id": "strling.go-dart-swift-adapter-legacy-baseline",
        "suite_version": "3.0.0",
        "base_commit": BASE_COMMIT,
        "fingerprints": fingerprints,
        "public_files": [
            _blob(path, cache[path], include_content=False)
            for path in paths["public"]
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


def _build_manifest(root: Path) -> dict[str, Any]:
    cases = _evidence_cases()
    families = dict(Counter(str(case["family"]) for case in cases))
    manifest: dict[str, Any] = {
        "$schema": "evidence.schema.json",
        "suite_id": "strling.go-dart-swift-adapter-migration-evidence",
        "suite_version": "3.0.0",
        "contract": {
            "files": list(CONTRACT_FILES),
            "fingerprint": _files_fingerprint(root, CONTRACT_FILES),
        },
        "legacy": {
            "base_commit": BASE_COMMIT,
            "baseline_path": "tests/adapters/go-dart-swift-3.0/legacy-baseline.json",
            "tree_file_count": EXPECTED_COUNTS["tree"],
            "production_source_count": EXPECTED_COUNTS["production"],
            "test_source_count": EXPECTED_COUNTS["tests"],
            "public_input_count": EXPECTED_COUNTS["public"],
            "semantic_copy_count": EXPECTED_COUNTS["semantic"],
            "tree_fingerprint": EXPECTED_FINGERPRINTS["tree"],
            "production_fingerprint": EXPECTED_FINGERPRINTS["production"],
            "public_fingerprint": EXPECTED_FINGERPRINTS["public"],
            "semantic_copy_fingerprint": EXPECTED_FINGERPRINTS["semantic"],
        },
        "task_start_observations": [
            {
                "binding": binding,
                "runtime": runtime,
                "status": status,
                "tests": tests,
                "detail": detail,
            }
            for binding, runtime, status, tests, detail in EXPECTED_OBSERVATIONS
        ],
        "counts": {"total": len(cases), "families": families},
        "cases": cases,
    }
    manifest["fingerprint"] = _fingerprint_json(manifest)
    return manifest


def _schema() -> dict[str, Any]:
    fingerprint = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    path = {
        "type": "string",
        "minLength": 1,
        "pattern": r"^(?!/)(?!.*\\)(?!.*(?:^|/)\.\.(?:/|$)).+$",
    }
    blob = {
        "type": "object",
        "additionalProperties": False,
        "required": ["path", "sha256"],
        "properties": {"path": path, "sha256": fingerprint},
    }
    source_blob = {
        "type": "object",
        "additionalProperties": False,
        "required": ["path", "sha256", "content_base64"],
        "properties": {
            "path": path,
            "sha256": fingerprint,
            "content_base64": {
                "type": "string",
                "pattern": "^[A-Za-z0-9+/]*={0,2}$",
            },
        },
    }
    legacy_baseline = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "suite_id",
            "suite_version",
            "base_commit",
            "fingerprints",
            "public_files",
            "semantic_copy_files",
            "historical_source_files",
            "fingerprint",
        ],
        "properties": {
            "$schema": {"const": "evidence.schema.json#/$defs/LegacyBaseline"},
            "suite_id": {
                "const": "strling.go-dart-swift-adapter-legacy-baseline"
            },
            "suite_version": {"const": "3.0.0"},
            "base_commit": {"const": BASE_COMMIT},
            "fingerprints": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tree", "production", "public", "semantic"],
                "properties": {
                    name: fingerprint
                    for name in ("tree", "production", "public", "semantic")
                },
            },
            "public_files": {
                "type": "array",
                "minItems": EXPECTED_COUNTS["public"],
                "maxItems": EXPECTED_COUNTS["public"],
                "items": blob,
            },
            "semantic_copy_files": {
                "type": "array",
                "minItems": EXPECTED_COUNTS["semantic"],
                "maxItems": EXPECTED_COUNTS["semantic"],
                "items": blob,
            },
            "historical_source_files": {
                "type": "array",
                "minItems": EXPECTED_COUNTS["tree"],
                "maxItems": EXPECTED_COUNTS["tree"],
                "items": source_blob,
            },
            "fingerprint": fingerprint,
        },
    }
    case = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "family", "bindings", "runner", "claim"],
        "properties": {
            "id": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$",
            },
            "family": {"enum": list(EXPECTED_FAMILIES)},
            "bindings": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"enum": sorted(EXPECTED_BINDINGS)},
            },
            "runner": {"enum": sorted(EXPECTED_RUNNERS)},
            "operation": {"enum": sorted(EXPECTED_OPERATIONS)},
            "runtime": {"enum": sorted(EXPECTED_RUNTIMES)},
            "claim": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://strling.dev/tests/adapters/go-dart-swift-3.0/evidence.schema.json",
        "title": "STRling Go/Dart/Swift adapter migration evidence denominator 3.0",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "suite_id",
            "suite_version",
            "contract",
            "legacy",
            "task_start_observations",
            "counts",
            "cases",
            "fingerprint",
        ],
        "properties": {
            "$schema": {"const": "evidence.schema.json"},
            "suite_id": {
                "const": "strling.go-dart-swift-adapter-migration-evidence"
            },
            "suite_version": {"const": "3.0.0"},
            "contract": {
                "type": "object",
                "additionalProperties": False,
                "required": ["files", "fingerprint"],
                "properties": {
                    "files": {
                        "type": "array",
                        "minItems": len(CONTRACT_FILES),
                        "maxItems": len(CONTRACT_FILES),
                        "uniqueItems": True,
                        "items": path,
                    },
                    "fingerprint": fingerprint,
                },
            },
            "legacy": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "base_commit",
                    "baseline_path",
                    "tree_file_count",
                    "production_source_count",
                    "test_source_count",
                    "public_input_count",
                    "semantic_copy_count",
                    "tree_fingerprint",
                    "production_fingerprint",
                    "public_fingerprint",
                    "semantic_copy_fingerprint",
                ],
                "properties": {
                    "base_commit": {"const": BASE_COMMIT},
                    "baseline_path": {
                        "const": "tests/adapters/go-dart-swift-3.0/legacy-baseline.json"
                    },
                    "tree_file_count": {"const": EXPECTED_COUNTS["tree"]},
                    "production_source_count": {
                        "const": EXPECTED_COUNTS["production"]
                    },
                    "test_source_count": {"const": EXPECTED_COUNTS["tests"]},
                    "public_input_count": {"const": EXPECTED_COUNTS["public"]},
                    "semantic_copy_count": {
                        "const": EXPECTED_COUNTS["semantic"]
                    },
                    "tree_fingerprint": fingerprint,
                    "production_fingerprint": fingerprint,
                    "public_fingerprint": fingerprint,
                    "semantic_copy_fingerprint": fingerprint,
                },
            },
            "task_start_observations": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["binding", "runtime", "status", "tests", "detail"],
                    "properties": {
                        "binding": {"enum": sorted(EXPECTED_BINDINGS)},
                        "runtime": {"enum": sorted(EXPECTED_RUNTIMES)},
                        "status": {"const": "unavailable"},
                        "tests": {"type": "null"},
                        "detail": {"type": "string", "minLength": 1},
                    },
                },
            },
            "counts": {
                "type": "object",
                "additionalProperties": False,
                "required": ["total", "families"],
                "properties": {
                    "total": {"const": sum(EXPECTED_FAMILIES.values())},
                    "families": {
                        "type": "object",
                        "additionalProperties": {"type": "integer", "minimum": 1},
                        "minProperties": len(EXPECTED_FAMILIES),
                        "maxProperties": len(EXPECTED_FAMILIES),
                    },
                },
            },
            "cases": {
                "type": "array",
                "minItems": sum(EXPECTED_FAMILIES.values()),
                "maxItems": sum(EXPECTED_FAMILIES.values()),
                "items": case,
            },
            "fingerprint": fingerprint,
        },
        "$defs": {"LegacyBaseline": legacy_baseline},
    }


def _validate(schema: Mapping[str, Any], value: Mapping[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise GoDartSwiftAdapterCertificationError(
            f"{label} invalid at {location}: {error.message}"
        )


class GoDartSwiftAdapterCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.evidence_root = root / "tests" / "adapters" / "go-dart-swift-3.0"

    def certify(self) -> GoDartSwiftAdapterCertificationReport:
        schema = _read_json(self.evidence_root / "evidence.schema.json")
        manifest = _read_json(self.evidence_root / "manifest.json")
        baseline = _read_json(self.evidence_root / "legacy-baseline.json")
        Draft202012Validator.check_schema(schema)
        return self.certify_documents(schema, manifest, baseline)

    def certify_documents(
        self,
        schema: Mapping[str, Any],
        manifest: Mapping[str, Any],
        baseline: Mapping[str, Any],
        *,
        expected_schema: Mapping[str, Any] | None = None,
        expected_manifest: Mapping[str, Any] | None = None,
        expected_baseline: Mapping[str, Any] | None = None,
    ) -> GoDartSwiftAdapterCertificationReport:
        expected_schema = expected_schema or _schema()
        expected_manifest = expected_manifest or _build_manifest(self.root)
        expected_baseline = expected_baseline or _build_baseline(self.root)
        if schema != expected_schema:
            raise GoDartSwiftAdapterCertificationError(
                "Go/Dart/Swift evidence schema does not reproduce"
            )
        _validate(schema, manifest, "Go/Dart/Swift adapter evidence manifest")
        baseline_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": "#/$defs/LegacyBaseline",
        }
        _validate(baseline_schema, baseline, "Go/Dart/Swift legacy baseline")
        if manifest != expected_manifest:
            raise GoDartSwiftAdapterCertificationError(
                "Go/Dart/Swift evidence manifest does not reproduce"
            )
        if baseline != expected_baseline:
            raise GoDartSwiftAdapterCertificationError(
                "Go/Dart/Swift legacy baseline does not reproduce"
            )
        cases = manifest["cases"]
        ids = [str(case["id"]) for case in cases]
        if len(ids) != len(set(ids)):
            raise GoDartSwiftAdapterCertificationError(
                "Go/Dart/Swift evidence case ids must be unique"
            )
        families = dict(Counter(str(case["family"]) for case in cases))
        bindings = {str(item) for case in cases for item in case["bindings"]}
        runners = {str(case["runner"]) for case in cases}
        operations = {str(case["operation"]) for case in cases if "operation" in case}
        runtimes = {str(case["runtime"]) for case in cases if "runtime" in case}
        if families != EXPECTED_FAMILIES:
            raise GoDartSwiftAdapterCertificationError("evidence family denominator changed")
        if bindings != EXPECTED_BINDINGS:
            raise GoDartSwiftAdapterCertificationError("binding denominator changed")
        if runners != EXPECTED_RUNNERS:
            raise GoDartSwiftAdapterCertificationError("runner denominator changed")
        if operations != EXPECTED_OPERATIONS:
            raise GoDartSwiftAdapterCertificationError("operation denominator changed")
        if runtimes != EXPECTED_RUNTIMES:
            raise GoDartSwiftAdapterCertificationError("runtime denominator changed")
        return GoDartSwiftAdapterCertificationReport(
            contract_fingerprint=str(manifest["contract"]["fingerprint"]),
            evidence_fingerprint=str(manifest["fingerprint"]),
            baseline_fingerprint=str(baseline["fingerprint"]),
            case_count=len(cases),
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
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_evidence:
            _write_json(EVIDENCE_ROOT / "evidence.schema.json", _schema())
            _write_json(EVIDENCE_ROOT / "manifest.json", _build_manifest(ROOT))
            _write_json(EVIDENCE_ROOT / "legacy-baseline.json", _build_baseline(ROOT))
        report = GoDartSwiftAdapterCertificationSuite().certify()
        payload = {"status": "passed", **report.__dict__}
    except (GoDartSwiftAdapterCertificationError, OSError, ValueError) as error:
        if arguments.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f"Go/Dart/Swift adapter certification failed: {error}")
        return 1
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
