"""Validate the canonical STRling interop protocol and evidence denominator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
HEADER_PATH = ROOT / "bindings" / "interop" / "include" / "strling_interop.h"
WASM_HOST_PATH = ROOT / "tests" / "interop" / "wasm_host.mjs"
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


def cargo_target_directory() -> Path:
    configured = os.environ.get("CARGO_TARGET_DIR")
    if not configured:
        return ROOT / "bindings" / "interop" / "target"
    target = Path(configured).expanduser()
    return target if target.is_absolute() else ROOT / target


def wasm_module_paths() -> tuple[Path, Path]:
    raw = (
        cargo_target_directory()
        / "wasm32-unknown-unknown"
        / "release"
        / "strling_interop.wasm"
    )
    return raw, raw.with_name("strling_interop.closed.wasm")


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


def render_c_header(abi: dict[str, Any]) -> str:
    """Render the native C surface solely from the canonical ABI descriptor."""
    InteropContractSuite._validate_abi(abi)
    native = abi["native_abi"]
    descriptor = native["output_descriptor"]
    if descriptor != {
        "name": "strling_interop_owned_bytes_v1",
        "fields": [
            {"name": "data", "type": "uint8_pointer"},
            {"name": "len", "type": "size_t"},
        ],
    }:
        raise InteropContractError("unsupported native output descriptor")
    signatures = {
        "uint32_t(void)": "uint32_t {name}(void);",
        "status(const uint8_t*,size_t,owned_bytes*)": (
            "strling_interop_status_v1 {name}(const uint8_t *request_data, "
            "size_t request_len, strling_interop_owned_bytes_v1 *output);"
        ),
        "status(owned_bytes*)": (
            "strling_interop_status_v1 {name}(strling_interop_owned_bytes_v1 *output);"
        ),
    }
    declarations: list[str] = []
    for symbol in native["symbols"]:
        template = signatures.get(symbol["signature"])
        if template is None:
            raise InteropContractError(
                f"unsupported native symbol signature: {symbol['signature']}"
            )
        declarations.append(
            "STRLING_INTEROP_API " + template.format(name=symbol["name"])
        )
    statuses = "\n".join(
        f"    {item['name']} = {item['value']}," for item in native["status_values"]
    )
    symbols = "\n".join(declarations)
    return f"""/* Generated from spec/interop/1.0/abi.json. Do not edit. */
#ifndef STRLING_INTEROP_H
#define STRLING_INTEROP_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32) && defined(STRLING_INTEROP_SHARED)
#  if defined(STRLING_INTEROP_BUILD)
#    define STRLING_INTEROP_API __declspec(dllexport)
#  else
#    define STRLING_INTEROP_API __declspec(dllimport)
#  endif
#elif defined(__GNUC__) && defined(STRLING_INTEROP_SHARED)
#  define STRLING_INTEROP_API __attribute__((visibility("default")))
#else
#  define STRLING_INTEROP_API
#endif

#ifdef __cplusplus
extern "C" {{
#endif

typedef uint32_t strling_interop_status_v1;

enum {{
{statuses}
}};

typedef struct strling_interop_owned_bytes_v1 {{
    uint8_t *data;
    size_t len;
}} strling_interop_owned_bytes_v1;

{symbols}

#ifdef __cplusplus
}}
#endif

#endif /* STRLING_INTEROP_H */
"""


def write_or_check_header(*, check: bool) -> None:
    abi = _read_json(ROOT / "spec" / "interop" / "1.0" / "abi.json")
    expected = render_c_header(abi)
    if check:
        try:
            actual = HEADER_PATH.read_text(encoding="utf-8")
        except OSError as error:
            raise InteropContractError(f"cannot read {HEADER_PATH}: {error}") from error
        if actual != expected:
            raise InteropContractError("generated interop C header is stale")
        return
    HEADER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HEADER_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(expected)


def certify_runtime() -> dict[str, Any]:
    """Seal and execute the already-built WASM artifact through the Node host."""
    try:
        from tooling.interop_wasm import WasmContractError, inspect_module, seal_module
    except ModuleNotFoundError:
        from interop_wasm import WasmContractError, inspect_module, seal_module

    write_or_check_header(check=True)
    raw_path, closed_path = wasm_module_paths()
    try:
        sealed = seal_module(raw_path.read_bytes())
        closed_path.write_bytes(sealed)
        exports = inspect_module(sealed)
        completed = subprocess.run(
            ["node", str(WASM_HOST_PATH), str(closed_path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, WasmContractError) as error:
        raise InteropContractError(
            f"WASM certification setup failed: {error}"
        ) from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise InteropContractError(f"WASM host certification failed: {detail}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        host = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as error:
        raise InteropContractError("WASM host emitted no structured result") from error
    if not isinstance(host, dict) or host.get("status") != "passed":
        raise InteropContractError("WASM host did not report a passing result")
    return {
        "wasm_exports": len(exports),
        "wasm_imports": 0,
        "wasm_instances": host.get("instances"),
        "wasm_lifecycle": host.get("lifecycle"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON evidence")
    header = parser.add_mutually_exclusive_group()
    header.add_argument("--write-header", action="store_true")
    header.add_argument("--check-header", action="store_true")
    header.add_argument("--certify", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = InteropContractSuite().certify()
        if args.write_header or args.check_header:
            write_or_check_header(check=args.check_header)
        runtime = certify_runtime() if args.certify else {}
    except InteropContractError as error:
        print(f"INTEROP_CONTRACT status=failed error={error}")
        return 1
    payload = {
        "status": "passed",
        "contract_fingerprint": report.contract_fingerprint,
        "evidence_fingerprint": report.evidence_fingerprint,
        "case_count": report.case_count,
        "family_counts": report.family_counts,
        **runtime,
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
