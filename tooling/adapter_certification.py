"""Freeze and validate the P17-T02 Rust, C, and C++ adapter evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "1.0"
MANIFEST_PATH = EVIDENCE_ROOT / "manifest.json"
SCHEMA_PATH = EVIDENCE_ROOT / "evidence.schema.json"
BASELINE_PATH = EVIDENCE_ROOT / "legacy-baseline.json"
BASE_COMMIT = "b0eecd19b7f4680f6c90f3fecde92df5c11eddf7"

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
    "bindings/c/include/strling.h",
    "bindings/c/include/strling_essential.h",
    "bindings/c/include/strling_simply.h",
    "bindings/cpp/include/strling/ast.hpp",
    "bindings/cpp/include/strling/compiler.hpp",
    "bindings/cpp/include/strling/core/hint_engine.hpp",
    "bindings/cpp/include/strling/core/ir.hpp",
    "bindings/cpp/include/strling/core/nodes.hpp",
    "bindings/cpp/include/strling/core/parser.hpp",
    "bindings/cpp/include/strling/core/strling_parse_error.hpp",
    "bindings/cpp/include/strling/essential.hpp",
    "bindings/cpp/include/strling/ir.hpp",
    "bindings/cpp/include/strling/simply.hpp",
    "bindings/cpp/include/strling/strling.hpp",
    "bindings/rust/Cargo.toml",
    "bindings/rust/src/core/compiler.rs",
    "bindings/rust/src/core/errors.rs",
    "bindings/rust/src/core/hint_engine.rs",
    "bindings/rust/src/core/ir.rs",
    "bindings/rust/src/core/mod.rs",
    "bindings/rust/src/core/nodes.rs",
    "bindings/rust/src/core/parser.rs",
    "bindings/rust/src/core/validator.rs",
    "bindings/rust/src/emitters/mod.rs",
    "bindings/rust/src/emitters/pcre2.rs",
    "bindings/rust/src/essential.rs",
    "bindings/rust/src/lib.rs",
    "bindings/rust/src/simply.rs",
)

SEMANTIC_COPY_PATHS = (
    "bindings/c/src/core/errors.c",
    "bindings/c/src/core/errors.h",
    "bindings/c/src/core/hint_engine.c",
    "bindings/c/src/core/hint_engine.h",
    "bindings/c/src/core/ir.c",
    "bindings/c/src/core/ir.h",
    "bindings/c/src/core/nodes.c",
    "bindings/c/src/core/nodes.h",
    "bindings/c/src/core/parser.c",
    "bindings/c/src/core/parser.h",
    "bindings/cpp/include/strling/ast.hpp",
    "bindings/cpp/include/strling/compiler.hpp",
    "bindings/cpp/include/strling/core/hint_engine.hpp",
    "bindings/cpp/include/strling/core/ir.hpp",
    "bindings/cpp/include/strling/core/nodes.hpp",
    "bindings/cpp/include/strling/core/parser.hpp",
    "bindings/cpp/include/strling/core/strling_parse_error.hpp",
    "bindings/cpp/include/strling/ir.hpp",
    "bindings/cpp/src/ast.cpp",
    "bindings/cpp/src/compiler.cpp",
    "bindings/cpp/src/core/hint_engine.cpp",
    "bindings/cpp/src/core/ir.cpp",
    "bindings/cpp/src/core/nodes.cpp",
    "bindings/cpp/src/core/parser.cpp",
    "bindings/cpp/src/core/strling_parse_error.cpp",
    "bindings/rust/src/core/compiler.rs",
    "bindings/rust/src/core/errors.rs",
    "bindings/rust/src/core/hint_engine.rs",
    "bindings/rust/src/core/ir.rs",
    "bindings/rust/src/core/mod.rs",
    "bindings/rust/src/core/nodes.rs",
    "bindings/rust/src/core/parser.rs",
    "bindings/rust/src/core/validator.rs",
    "bindings/rust/src/emitters/mod.rs",
    "bindings/rust/src/emitters/pcre2.rs",
)

EXPECTED_FAMILIES = {
    "public_api": 8,
    "canonical_parity": 10,
    "compatibility_success": 6,
    "compatibility_refusal": 6,
    "ownership_error": 5,
    "concurrency_raii": 4,
    "unicode": 4,
    "package_build_install": 5,
    "architecture_deletion": 6,
    "platform": 4,
}
EXPECTED_BINDINGS = {"rust", "c", "cpp"}
EXPECTED_OPERATIONS = {"compile", "simply.compile", "target_profile.inspect"}
EXPECTED_TARGETS = {
    "x86_64-unknown-linux-gnu",
    "x86_64-pc-windows-msvc",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
}
EXPECTED_RUNNERS = {
    "manifest",
    "public-contract",
    "adapter-rust",
    "adapter-c",
    "adapter-cpp",
    "cross-language",
    "native-lifecycle",
    "package",
    "architecture",
    "platform-ci",
    "sanitizer-ci",
}
REQUIRED_CASE_IDS = {
    "public-c-installed-header-closure",
    "public-cpp-installed-header-closure",
    "public-rust-feature-export-closure",
    "parity-source-success",
    "parity-target-profile-exact",
    "parity-simply-11-stdlib",
    "compat-targetless-pcre2-disclosed",
    "refusal-no-local-emitter-fallback",
    "ownership-c-zero-free",
    "raii-cpp-move-once",
    "unicode-astral-literal",
    "package-rust-msrv",
    "architecture-semantic-copy-denominator",
    "platform-linux-x64",
}


class AdapterCertificationError(RuntimeError):
    """Raised when the adapter migration denominator is invalid."""


@dataclass(frozen=True)
class AdapterCertificationReport:
    contract_fingerprint: str
    evidence_fingerprint: str
    baseline_fingerprint: str
    case_count: int
    family_counts: dict[str, int]
    public_input_count: int
    semantic_copy_count: int


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
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = "; ".join(error.message for error in errors[:5])
        raise AdapterCertificationError(f"invalid {label}: {rendered}")


def _git_blob(root: Path, commit: str, relative: str) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise AdapterCertificationError(
            f"cannot read legacy blob {commit}:{relative}: {detail}"
        )
    return process.stdout


def _blob_entry(path: str, content: bytes) -> dict[str, str]:
    return {"path": path, "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}"}


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
        "suite_id": "strling.adapter-legacy-baseline",
        "suite_version": "1.0.0",
        "base_commit": commit,
        "public_files": [
            _blob_entry(path, read(path)) for path in legacy["public_inputs"]
        ],
        "semantic_copy_files": [
            _blob_entry(path, read(path)) for path in legacy["semantic_copy_paths"]
        ],
    }
    baseline["fingerprint"] = _fingerprint_json(baseline)
    return baseline


class AdapterCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.evidence_root = root / "tests" / "adapters" / "1.0"

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
        expected_baseline = _build_baseline(self.root, manifest)
        return self.certify_documents(
            schema,
            manifest,
            baseline,
            contract_fingerprint=_files_fingerprint(self.root, CONTRACT_FILES),
            expected_baseline=expected_baseline,
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
        _validate(schema, manifest, "adapter evidence manifest")
        baseline_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": "#/$defs/LegacyBaseline",
        }
        _validate(baseline_schema, baseline, "adapter legacy baseline")

        contract = manifest["contract"]
        legacy = manifest["legacy"]
        counts = manifest["counts"]
        cases = manifest["cases"]
        assert isinstance(contract, dict)
        assert isinstance(legacy, dict)
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
        targets = {str(case["target"]) for case in cases if "target" in case}
        if targets != EXPECTED_TARGETS:
            raise AdapterCertificationError(
                f"adapter platform coverage changed: {targets!r}"
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
        )


def _expected_fingerprints(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    prepared = deepcopy(manifest)
    contract_fingerprint = _files_fingerprint(root, CONTRACT_FILES)
    prepared["contract"]["fingerprint"] = contract_fingerprint
    evidence_fingerprint = _fingerprint_json(prepared, {"fingerprint"})
    return {
        "contract_fingerprint": contract_fingerprint,
        "evidence_fingerprint": evidence_fingerprint,
    }


def _write_baseline(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _build_baseline(root, manifest)
    path = root / str(manifest["legacy"]["baseline_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=4, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return baseline


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the P17-T02 adapter migration evidence denominator."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write-baseline", action="store_true")
    mode.add_argument("--print-fingerprints", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = _read_json(MANIFEST_PATH)
        if args.print_fingerprints:
            print(json.dumps(_expected_fingerprints(ROOT, manifest), indent=4))
            return 0
        if args.write_baseline:
            baseline = _write_baseline(ROOT, manifest)
            print(
                "ADAPTER_BASELINE "
                f"status=written fingerprint={baseline['fingerprint']} "
                f"public_inputs={len(baseline['public_files'])} "
                f"semantic_copies={len(baseline['semantic_copy_files'])}"
            )
            return 0

        report = AdapterCertificationSuite(ROOT).certify()
    except AdapterCertificationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    payload = {
        "status": "passed",
        "contract_fingerprint": report.contract_fingerprint,
        "evidence_fingerprint": report.evidence_fingerprint,
        "baseline_fingerprint": report.baseline_fingerprint,
        "case_count": report.case_count,
        "family_counts": report.family_counts,
        "public_input_count": report.public_input_count,
        "semantic_copy_count": report.semantic_copy_count,
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "ADAPTER_CERTIFICATION "
            f"status=passed contract_fingerprint={report.contract_fingerprint} "
            f"evidence_fingerprint={report.evidence_fingerprint} "
            f"baseline_fingerprint={report.baseline_fingerprint} "
            f"cases={report.case_count} families={len(report.family_counts)} "
            f"public_inputs={report.public_input_count} "
            f"semantic_copies={report.semantic_copy_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
