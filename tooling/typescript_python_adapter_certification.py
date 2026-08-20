"""Freeze and validate the P17-T03 TypeScript/WASM and Python adapter evidence."""

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
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "2.0"
MANIFEST_PATH = EVIDENCE_ROOT / "manifest.json"
SCHEMA_PATH = EVIDENCE_ROOT / "evidence.schema.json"
BASELINE_PATH = EVIDENCE_ROOT / "legacy-baseline.json"
BASE_COMMIT = "e6c87a1ae2fed088bff7ec22653fccf5d00becde"

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

PUBLIC_INPUTS = (
    "bindings/typescript/package.json",
    "bindings/typescript/package-lock.json",
    "bindings/typescript/tsconfig.json",
    "bindings/typescript/jest.config.mjs",
    "bindings/typescript/README.md",
    "bindings/typescript/src/index.ts",
    "bindings/typescript/src/STRling/compiler.ts",
    "bindings/typescript/src/STRling/simply/index.ts",
    "bindings/typescript/src/STRling/simply/preview.ts",
    "bindings/typescript/src/STRling/simply/stdlib.generated.ts",
    "bindings/python/pyproject.toml",
    "bindings/python/requirements.txt",
    "bindings/python/README.md",
    "bindings/python/src/STRling/__init__.py",
    "bindings/python/src/STRling/simply/__init__.py",
    "bindings/python/src/STRling/simply/pattern.py",
    "bindings/python/src/STRling/simply/preview.py",
    "bindings/python/src/STRling/simply/stdlib_generated.py",
)

SEMANTIC_COPY_PATHS = (
    "bindings/typescript/src/STRling/compiler.ts",
    "bindings/typescript/src/STRling/core/compiler.ts",
    "bindings/typescript/src/STRling/core/errors.ts",
    "bindings/typescript/src/STRling/core/hint_engine.ts",
    "bindings/typescript/src/STRling/core/ir.ts",
    "bindings/typescript/src/STRling/core/nodes.ts",
    "bindings/typescript/src/STRling/core/parser.ts",
    "bindings/typescript/src/STRling/core/validator.ts",
    "bindings/typescript/src/STRling/emitters/pcre2.ts",
    "bindings/typescript/src/STRling/simply/constructors.ts",
    "bindings/typescript/src/STRling/simply/lookarounds.ts",
    "bindings/typescript/src/STRling/simply/pattern.ts",
    "bindings/typescript/src/STRling/simply/sets.ts",
    "bindings/typescript/src/STRling/simply/static.ts",
    "bindings/python/src/STRling/core/__init__.py",
    "bindings/python/src/STRling/core/compiler.py",
    "bindings/python/src/STRling/core/errors.py",
    "bindings/python/src/STRling/core/hint_engine.py",
    "bindings/python/src/STRling/core/intelligence.py",
    "bindings/python/src/STRling/core/ir.py",
    "bindings/python/src/STRling/core/islands.py",
    "bindings/python/src/STRling/core/nodes.py",
    "bindings/python/src/STRling/core/parser.py",
    "bindings/python/src/STRling/core/validator.py",
    "bindings/python/src/STRling/emitters/__init__.py",
    "bindings/python/src/STRling/emitters/pcre2.py",
    "bindings/python/src/STRling/simply/constructors.py",
    "bindings/python/src/STRling/simply/lookarounds.py",
    "bindings/python/src/STRling/simply/pattern.py",
    "bindings/python/src/STRling/simply/sets.py",
    "bindings/python/src/STRling/simply/static.py",
)

HISTORICAL_SOURCE_PATHS = (
    "bindings/typescript/package.json",
    "bindings/typescript/package-lock.json",
    "bindings/typescript/tsconfig.json",
    "bindings/typescript/src/index.ts",
    "bindings/typescript/src/STRling/compiler.ts",
    "bindings/typescript/src/STRling/core/compiler.ts",
    "bindings/typescript/src/STRling/core/errors.ts",
    "bindings/typescript/src/STRling/core/hint_engine.ts",
    "bindings/typescript/src/STRling/core/ir.ts",
    "bindings/typescript/src/STRling/core/nodes.ts",
    "bindings/typescript/src/STRling/core/parser.ts",
    "bindings/typescript/src/STRling/core/validator.ts",
    "bindings/typescript/src/STRling/emitters/pcre2.ts",
    "bindings/typescript/src/STRling/simply/constructors.ts",
    "bindings/typescript/src/STRling/simply/index.ts",
    "bindings/typescript/src/STRling/simply/lookarounds.ts",
    "bindings/typescript/src/STRling/simply/pattern.ts",
    "bindings/typescript/src/STRling/simply/preview.ts",
    "bindings/typescript/src/STRling/simply/sets.ts",
    "bindings/typescript/src/STRling/simply/static.ts",
    "bindings/typescript/src/STRling/simply/stdlib.generated.ts",
    "bindings/typescript/src/types/ajv-dist-2020.d.ts",
    "bindings/python/pyproject.toml",
    "bindings/python/requirements.txt",
    "bindings/python/src/STRling/__init__.py",
    "bindings/python/src/STRling/core/__init__.py",
    "bindings/python/src/STRling/core/compiler.py",
    "bindings/python/src/STRling/core/errors.py",
    "bindings/python/src/STRling/core/hint_engine.py",
    "bindings/python/src/STRling/core/intelligence.py",
    "bindings/python/src/STRling/core/ir.py",
    "bindings/python/src/STRling/core/islands.py",
    "bindings/python/src/STRling/core/nodes.py",
    "bindings/python/src/STRling/core/parser.py",
    "bindings/python/src/STRling/core/validator.py",
    "bindings/python/src/STRling/emitters/__init__.py",
    "bindings/python/src/STRling/emitters/pcre2.py",
    "bindings/python/src/STRling/simply/__init__.py",
    "bindings/python/src/STRling/simply/constructors.py",
    "bindings/python/src/STRling/simply/lookarounds.py",
    "bindings/python/src/STRling/simply/pattern.py",
    "bindings/python/src/STRling/simply/preview.py",
    "bindings/python/src/STRling/simply/sets.py",
    "bindings/python/src/STRling/simply/static.py",
    "bindings/python/src/STRling/simply/stdlib_generated.py",
)

HISTORICAL_CORPORA = {
    "typescript": ("tooling/legacy_reference/corpus.json", 24),
    "python": ("tooling/legacy_reference/python_corpus.json", 20),
}

EXPECTED_FAMILIES = {
    "public_api": 6,
    "canonical_parity": 8,
    "compatibility_success": 6,
    "compatibility_refusal": 6,
    "lifecycle_error": 8,
    "concurrency_isolation": 4,
    "unicode_resource": 6,
    "simply_stdlib": 8,
    "package_install": 6,
    "architecture_deletion": 6,
    "historical_preservation": 4,
    "runtime_platform": 4,
}
EXPECTED_BINDINGS = {"typescript", "python"}
EXPECTED_OPERATIONS = {
    "compile",
    "describe",
    "simply.compile",
    "target_profile.inspect",
}
EXPECTED_RUNNERS = {
    "adapter-python",
    "adapter-typescript",
    "architecture",
    "browser-runtime",
    "cross-language",
    "historical-reference",
    "manifest",
    "native-lifecycle",
    "node-runtime",
    "package",
    "platform-ci",
    "public-contract",
    "wasm-lifecycle",
}
EXPECTED_RUNTIMES = {
    "browser-wasm",
    "cpython-3.8-min",
    "cpython-3.11-governed",
    "node-22",
}
REQUIRED_CASE_IDS = {
    "public-typescript-entrypoint-closure",
    "public-python-export-closure",
    "parity-target-artifact-exact",
    "refusal-no-local-semantic-fallback",
    "lifecycle-wasm-response-release",
    "lifecycle-python-owned-response",
    "concurrency-wasm-instance-isolation",
    "simply-stdlib-lexical-not-semantic",
    "package-typescript-clean-install",
    "package-python-wheel-import",
    "architecture-semantic-copy-denominator",
    "historical-source-bundle-replay",
    "runtime-node-22",
}


class AdapterCertificationError(RuntimeError):
    """Raised when the TypeScript/Python evidence denominator is invalid."""


@dataclass(frozen=True)
class AdapterCertificationReport:
    contract_fingerprint: str
    evidence_fingerprint: str
    baseline_fingerprint: str
    case_count: int
    family_counts: dict[str, int]
    public_input_count: int
    semantic_copy_count: int
    historical_source_count: int
    historical_case_count: int


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdapterCertificationError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise AdapterCertificationError(f"{path} must contain one JSON object")
    return value


def _fingerprint_json(
    value: Mapping[str, Any], excluded: set[str] | None = None
) -> str:
    normalized = {
        key: item for key, item in value.items() if key not in (excluded or set())
    }
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _files_fingerprint(root: Path, paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        path = root / relative
        try:
            content = path.read_bytes()
        except OSError as error:
            raise AdapterCertificationError(f"cannot read {path}: {error}") from error
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def _validate(
    schema: Mapping[str, Any], instance: Mapping[str, Any], label: str
) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise AdapterCertificationError(
            f"{label} invalid at {location}: {error.message}"
        )


def _git_blob(root: Path, commit: str, relative: str) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise AdapterCertificationError(
            f"cannot read {relative} from {commit}: {detail}"
        )
    return process.stdout


def _blob_entry(path: str, content: bytes, *, include_content: bool) -> dict[str, str]:
    entry = {
        "path": path,
        "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }
    if include_content:
        entry["content_base64"] = base64.b64encode(content).decode("ascii")
    return entry


def _build_baseline(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    legacy = manifest["legacy"]
    assert isinstance(legacy, dict)
    commit = str(legacy["base_commit"])
    resolved = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != commit:
        raise AdapterCertificationError(
            f"legacy base commit does not resolve exactly: {commit}"
        )

    cache: dict[str, bytes] = {}

    def read(relative: str) -> bytes:
        if relative not in cache:
            cache[relative] = _git_blob(root, commit, relative)
        return cache[relative]

    baseline: dict[str, Any] = {
        "$schema": "evidence.schema.json#/$defs/LegacyBaseline",
        "suite_id": "strling.typescript-python-adapter-legacy-baseline",
        "suite_version": "2.0.0",
        "base_commit": commit,
        "public_files": [
            _blob_entry(path, read(path), include_content=False)
            for path in legacy["public_inputs"]
        ],
        "semantic_copy_files": [
            _blob_entry(path, read(path), include_content=False)
            for path in legacy["semantic_copy_paths"]
        ],
        "historical_source_files": [
            _blob_entry(path, read(path), include_content=True)
            for path in legacy["historical_source_paths"]
        ],
    }
    baseline["fingerprint"] = _fingerprint_json(baseline)
    return baseline


def _historical_corpus_details(root: Path) -> tuple[dict[str, Any], int]:
    details: dict[str, Any] = {}
    total = 0
    for runner, (relative, expected_count) in HISTORICAL_CORPORA.items():
        corpus = _read_json(root / relative)
        cases = corpus.get("cases")
        if not isinstance(cases, list) or len(cases) != expected_count:
            raise AdapterCertificationError(
                f"historical {runner} corpus must contain exactly {expected_count} cases"
            )
        ids = [case.get("id") for case in cases if isinstance(case, dict)]
        if len(ids) != expected_count or len(set(ids)) != expected_count:
            raise AdapterCertificationError(
                f"historical {runner} corpus ids are missing or duplicated"
            )
        details[runner] = {
            "path": relative,
            "case_count": expected_count,
            "fingerprint": _fingerprint_json(corpus),
        }
        total += expected_count
    return details, total


class TypeScriptPythonAdapterCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.evidence_root = root / "tests" / "adapters" / "2.0"

    def certify(self) -> AdapterCertificationReport:
        schema = _read_json(self.evidence_root / "evidence.schema.json")
        manifest = _read_json(self.evidence_root / "manifest.json")
        baseline = _read_json(self.evidence_root / "legacy-baseline.json")
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            raise AdapterCertificationError(
                f"invalid adapter evidence JSON Schema: {error}"
            ) from error
        return self.certify_documents(
            schema,
            manifest,
            baseline,
            contract_fingerprint=_files_fingerprint(self.root, CONTRACT_FILES),
            expected_baseline=_build_baseline(self.root, manifest),
        )

    def certify_documents(
        self,
        schema: Mapping[str, Any],
        manifest: Mapping[str, Any],
        baseline: Mapping[str, Any],
        *,
        contract_fingerprint: str,
        expected_baseline: Mapping[str, Any],
    ) -> AdapterCertificationReport:
        _validate(schema, manifest, "TypeScript/Python adapter evidence manifest")
        baseline_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": "#/$defs/LegacyBaseline",
        }
        _validate(baseline_schema, baseline, "TypeScript/Python legacy baseline")

        contract = manifest["contract"]
        legacy = manifest["legacy"]
        historical = manifest["historical"]
        counts = manifest["counts"]
        cases = manifest["cases"]
        assert isinstance(contract, dict)
        assert isinstance(legacy, dict)
        assert isinstance(historical, dict)
        assert isinstance(counts, dict)
        assert isinstance(cases, list)

        if tuple(contract["files"]) != CONTRACT_FILES:
            raise AdapterCertificationError(
                "adapter contract file set or order changed"
            )
        if contract["fingerprint"] != contract_fingerprint:
            raise AdapterCertificationError(
                "adapter contract fingerprint does not match governed inputs"
            )
        if tuple(legacy["public_inputs"]) != PUBLIC_INPUTS:
            raise AdapterCertificationError("legacy public-input denominator changed")
        if tuple(legacy["semantic_copy_paths"]) != SEMANTIC_COPY_PATHS:
            raise AdapterCertificationError("legacy semantic-copy denominator changed")
        if tuple(legacy["historical_source_paths"]) != HISTORICAL_SOURCE_PATHS:
            raise AdapterCertificationError("historical source denominator changed")

        expected_corpora, historical_case_count = _historical_corpus_details(self.root)
        if historical["corpora"] != expected_corpora:
            raise AdapterCertificationError(
                "historical corpus identity, count, or fingerprint changed"
            )
        if historical["total_case_count"] != historical_case_count:
            raise AdapterCertificationError("historical total case count changed")

        evidence_fingerprint = _fingerprint_json(manifest, {"fingerprint"})
        if manifest["fingerprint"] != evidence_fingerprint:
            raise AdapterCertificationError(
                "adapter evidence fingerprint does not match governed manifest"
            )

        ids = [str(case["id"]) for case in cases]
        if len(ids) != len(set(ids)):
            raise AdapterCertificationError("adapter evidence case ids must be unique")
        family_counts = dict(Counter(str(case["family"]) for case in cases))
        if family_counts != EXPECTED_FAMILIES:
            raise AdapterCertificationError(
                f"adapter evidence family denominator changed: {family_counts!r}"
            )
        if counts["families"] != EXPECTED_FAMILIES:
            raise AdapterCertificationError("declared adapter family counts changed")
        if counts["total"] != sum(EXPECTED_FAMILIES.values()):
            raise AdapterCertificationError("declared adapter total changed")
        if len(cases) != sum(EXPECTED_FAMILIES.values()):
            raise AdapterCertificationError("adapter case denominator changed")
        if not REQUIRED_CASE_IDS.issubset(ids):
            missing = sorted(REQUIRED_CASE_IDS.difference(ids))
            raise AdapterCertificationError(
                f"required adapter evidence cases missing: {missing!r}"
            )

        runners = {str(case["runner"]) for case in cases}
        if runners != EXPECTED_RUNNERS:
            raise AdapterCertificationError(
                f"adapter runner coverage changed: {runners!r}"
            )
        operations = {str(case["operation"]) for case in cases if "operation" in case}
        if operations != EXPECTED_OPERATIONS:
            raise AdapterCertificationError(
                f"adapter operation coverage changed: {operations!r}"
            )
        runtimes = {str(case["runtime"]) for case in cases if "runtime" in case}
        if runtimes != EXPECTED_RUNTIMES:
            raise AdapterCertificationError(
                f"adapter runtime coverage changed: {runtimes!r}"
            )
        for family in EXPECTED_FAMILIES:
            covered = {
                str(binding)
                for case in cases
                if case["family"] == family
                for binding in case["bindings"]
            }
            if covered != EXPECTED_BINDINGS:
                raise AdapterCertificationError(
                    f"adapter binding coverage changed for {family}: {covered!r}"
                )
        for case in cases:
            fixture = case.get("fixture")
            if fixture is not None and not (self.root / str(fixture)).is_file():
                raise AdapterCertificationError(
                    f"adapter case fixture does not exist: {fixture}"
                )

        if baseline != expected_baseline:
            raise AdapterCertificationError(
                "adapter legacy baseline does not reproduce from the exact base commit"
            )
        baseline_fingerprint = _fingerprint_json(baseline, {"fingerprint"})
        if baseline["fingerprint"] != baseline_fingerprint:
            raise AdapterCertificationError(
                "adapter legacy baseline fingerprint does not match its content"
            )

        return AdapterCertificationReport(
            contract_fingerprint=contract_fingerprint,
            evidence_fingerprint=evidence_fingerprint,
            baseline_fingerprint=baseline_fingerprint,
            case_count=len(cases),
            family_counts=family_counts,
            public_input_count=len(PUBLIC_INPUTS),
            semantic_copy_count=len(SEMANTIC_COPY_PATHS),
            historical_source_count=len(HISTORICAL_SOURCE_PATHS),
            historical_case_count=historical_case_count,
        )


def _write_baseline(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _build_baseline(root, manifest)
    path = root / str(manifest["legacy"]["baseline_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return baseline


def materialize_historical_sources(destination: Path, root: Path = ROOT) -> None:
    """Materialize the checked-in immutable task-start source bundle."""

    baseline = _read_json(root / "tests" / "adapters" / "2.0" / "legacy-baseline.json")
    files = baseline.get("historical_source_files")
    if not isinstance(files, list):
        raise AdapterCertificationError("historical source bundle is missing")
    for entry in files:
        if not isinstance(entry, dict):
            raise AdapterCertificationError("historical source entry must be an object")
        relative = str(entry.get("path", ""))
        encoded = entry.get("content_base64")
        expected = entry.get("sha256")
        if relative not in HISTORICAL_SOURCE_PATHS or not isinstance(encoded, str):
            raise AdapterCertificationError(
                "historical source entry is outside the lock"
            )
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise AdapterCertificationError(
                f"historical source entry is not valid base64: {relative}"
            ) from error
        actual = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if actual != expected:
            raise AdapterCertificationError(
                f"historical source content fingerprint mismatch: {relative}"
            )
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate P17-T03 TypeScript/Python adapter evidence."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write-baseline", action="store_true")
    mode.add_argument("--print-fingerprints", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = _read_json(MANIFEST_PATH)
        if args.write_baseline:
            baseline = _write_baseline(ROOT, manifest)
            print(f"wrote {BASELINE_PATH.relative_to(ROOT).as_posix()}")
            print(f"baseline_fingerprint={baseline['fingerprint']}")
            return 0
        if args.print_fingerprints:
            corpora, historical_count = _historical_corpus_details(ROOT)
            prepared = dict(manifest)
            prepared["contract"] = dict(manifest["contract"])
            prepared["historical"] = dict(manifest["historical"])
            prepared["contract"]["fingerprint"] = _files_fingerprint(
                ROOT, CONTRACT_FILES
            )
            prepared["historical"]["corpora"] = corpora
            prepared["historical"]["total_case_count"] = historical_count
            payload = {
                "contract_fingerprint": prepared["contract"]["fingerprint"],
                "evidence_fingerprint": _fingerprint_json(prepared, {"fingerprint"}),
                "historical": prepared["historical"],
            }
            print(json.dumps(payload, indent=4, sort_keys=True))
            return 0

        report = TypeScriptPythonAdapterCertificationSuite(ROOT).certify()
    except AdapterCertificationError as error:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f"TYPE_SCRIPT_PYTHON_ADAPTER_CERTIFICATION failed: {error}")
        return 1

    payload = {
        "status": "passed",
        "contract_fingerprint": report.contract_fingerprint,
        "evidence_fingerprint": report.evidence_fingerprint,
        "baseline_fingerprint": report.baseline_fingerprint,
        "cases": report.case_count,
        "families": len(report.family_counts),
        "public_inputs": report.public_input_count,
        "semantic_copies": report.semantic_copy_count,
        "historical_sources": report.historical_source_count,
        "historical_cases": report.historical_case_count,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "TYPESCRIPT_PYTHON_ADAPTER_CERTIFICATION "
            + " ".join(f"{key}={value}" for key, value in payload.items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
