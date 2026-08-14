"""Validate the canonical STRling interop protocol and evidence denominator."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILES = (
    "spec/interop/1.0/README.md",
    "spec/interop/1.0/abi.json",
    "spec/interop/1.0/abi.schema.json",
    "spec/interop/1.0/interop.schema.json",
)
EXPECTED_FAMILIES = {
    "protocol_success": 10,
    "protocol_failure": 16,
    "native_memory": 12,
    "native_concurrency": 4,
    "wasm_memory": 12,
    "abi_snapshot": 6,
    "architecture_security": 4,
    "platform_build": 5,
    "fuzz_property": 6,
    "sanitizer": 2,
}
EXPECTED_OPERATIONS = {
    "describe",
    "compile",
    "target_profile.inspect",
    "simply.compile",
}
EXPECTED_TARGETS = {
    "x86_64-unknown-linux-gnu",
    "x86_64-pc-windows-msvc",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
    "wasm32-unknown-unknown",
}
EXPECTED_ERROR_CODES = {f"STRL-INTEROP-{index:04d}" for index in range(1, 11)}
REQUIRED_CASE_IDS = {
    "protocol-describe-identity",
    "protocol-compile-source-success",
    "protocol-compile-failed-result",
    "protocol-compile-target-success",
    "protocol-profile-inspect",
    "protocol-simply-10-success",
    "protocol-simply-11-stdlib",
    "failure-invalid-utf8",
    "failure-invalid-json",
    "failure-invalid-envelope",
    "failure-unsupported-version",
    "failure-unsupported-operation",
    "failure-request-too-large",
    "failure-invalid-payload",
    "failure-canonical-boundary",
    "failure-response-too-large",
    "failure-serialization-injection",
    "native-free-same-descriptor-twice",
    "native-panic-contained",
    "native-concurrent-success",
    "wasm-memory-growth-copy",
    "wasm-input-range",
    "wasm-instance-isolation",
    "abi-generated-header",
    "abi-native-symbol-snapshot",
    "abi-wasm-symbol-snapshot",
    "architecture-kernel-unsafe-free",
    "architecture-no-semantic-island",
    "fuzz-arbitrary-bytes",
    "fuzz-ownership-sequences",
    "sanitizer-native-address-leak",
    "sanitizer-wasm-host-memory",
}


class InteropContractError(RuntimeError):
    """Raised when the interop contract or evidence denominator is invalid."""


@dataclass(frozen=True)
class InteropContractReport:
    contract_fingerprint: str
    evidence_fingerprint: str
    case_count: int
    family_counts: dict[str, int]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InteropContractError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise InteropContractError(f"{path} must contain one JSON object")
    return value


def _fingerprint_json(value: dict[str, Any], excluded: set[str] | None = None) -> str:
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


def _contract_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in CONTRACT_FILES:
        path = root / relative
        try:
            content = path.read_bytes()
        except OSError as error:
            raise InteropContractError(f"cannot read {path}: {error}") from error
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


class InteropContractSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.contract_root = root / "spec" / "interop" / "1.0"
        self.evidence_root = root / "tests" / "interop" / "1.0"

    def certify(self) -> InteropContractReport:
        abi = _read_json(self.contract_root / "abi.json")
        manifest = _read_json(self.evidence_root / "manifest.json")
        return self.certify_documents(abi, manifest)

    def certify_documents(
        self,
        abi: dict[str, Any],
        manifest: dict[str, Any],
        *,
        contract_fingerprint: str | None = None,
    ) -> InteropContractReport:
        """Certify loaded documents; used by mutation tests without filesystem copies."""
        abi_schema = _read_json(self.contract_root / "abi.schema.json")
        interop_schema = _read_json(self.contract_root / "interop.schema.json")
        evidence_schema = _read_json(self.evidence_root / "evidence.schema.json")

        for schema in (abi_schema, interop_schema, evidence_schema):
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as error:
                raise InteropContractError(f"invalid JSON Schema: {error}") from error
        self._validate(abi_schema, abi, "ABI descriptor")
        self._validate(evidence_schema, manifest, "evidence manifest")
        self._validate_abi(abi)

        actual_contract_fingerprint = contract_fingerprint or _contract_fingerprint(
            self.root
        )
        if manifest["contract_fingerprint"] != actual_contract_fingerprint:
            raise InteropContractError(
                "interop contract fingerprint does not match governed inputs"
            )

        evidence_fingerprint = _fingerprint_json(manifest, {"fingerprint"})
        if manifest["fingerprint"] != evidence_fingerprint:
            raise InteropContractError(
                "interop evidence fingerprint does not match governed manifest"
            )

        cases = manifest["cases"]
        ids = [case["id"] for case in cases]
        if len(ids) != len(set(ids)):
            raise InteropContractError("interop evidence case ids must be unique")
        family_counts = dict(Counter(case["family"] for case in cases))
        if family_counts != EXPECTED_FAMILIES:
            raise InteropContractError(
                f"interop evidence family denominator changed: {family_counts!r}"
            )
        if manifest["counts"]["families"] != EXPECTED_FAMILIES:
            raise InteropContractError("declared evidence family counts changed")
        if manifest["counts"]["total"] != sum(EXPECTED_FAMILIES.values()):
            raise InteropContractError("declared evidence total changed")
        if len(cases) != sum(EXPECTED_FAMILIES.values()):
            raise InteropContractError("evidence case denominator changed")
        if not REQUIRED_CASE_IDS.issubset(ids):
            missing = sorted(REQUIRED_CASE_IDS.difference(ids))
            raise InteropContractError(f"required evidence cases missing: {missing!r}")

        operations = {case["operation"] for case in cases if "operation" in case}
        if operations != EXPECTED_OPERATIONS:
            raise InteropContractError(f"operation evidence changed: {operations!r}")
        targets = {case["target"] for case in cases if "target" in case}
        if targets != EXPECTED_TARGETS:
            raise InteropContractError(f"platform evidence changed: {targets!r}")
        runners = {case["runner"] for case in cases}
        required_runners = {
            "contract",
            "native-rust",
            "native-c",
            "wasm-host",
            "governance",
            "public-contract",
            "generated-artifact",
            "platform-ci",
            "cargo-fuzz",
            "sanitizer-ci",
        }
        if runners != required_runners:
            raise InteropContractError(f"evidence runner coverage changed: {runners!r}")

        return InteropContractReport(
            contract_fingerprint=actual_contract_fingerprint,
            evidence_fingerprint=evidence_fingerprint,
            case_count=len(cases),
            family_counts=family_counts,
        )

    @staticmethod
    def _validate(schema: dict[str, Any], instance: dict[str, Any], label: str) -> None:
        errors = sorted(
            Draft202012Validator(schema).iter_errors(instance),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            rendered = "; ".join(error.message for error in errors[:5])
            raise InteropContractError(f"{label} failed schema validation: {rendered}")

    @staticmethod
    def _validate_abi(abi: dict[str, Any]) -> None:
        if set(abi["operations"]) != EXPECTED_OPERATIONS:
            raise InteropContractError("ABI operation set changed")
        if abi["limits"] != {
            "request_bytes": 10_485_760,
            "response_bytes": 33_554_432,
        }:
            raise InteropContractError("ABI resource limits changed")
        error_codes = {item["code"] for item in abi["error_codes"]}
        if error_codes != EXPECTED_ERROR_CODES:
            raise InteropContractError("ABI error-code set changed")
        native_targets = set(abi["native_abi"]["certification_targets"])
        if native_targets != EXPECTED_TARGETS.difference({"wasm32-unknown-unknown"}):
            raise InteropContractError("native certification targets changed")
        if abi["wasm_abi"]["target"] != "wasm32-unknown-unknown":
            raise InteropContractError("WASM certification target changed")
        if abi["wasm_abi"]["host_imports"] or abi["wasm_abi"]["shared_memory"]:
            raise InteropContractError("WASM host capability boundary changed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON evidence")
    args = parser.parse_args(argv)
    try:
        report = InteropContractSuite().certify()
    except InteropContractError as error:
        print(f"INTEROP_CONTRACT status=failed error={error}")
        return 1
    payload = {
        "status": "passed",
        "contract_fingerprint": report.contract_fingerprint,
        "evidence_fingerprint": report.evidence_fingerprint,
        "case_count": report.case_count,
        "family_counts": report.family_counts,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "INTEROP_CONTRACT "
            + " ".join(f"{key}={value}" for key, value in payload.items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
