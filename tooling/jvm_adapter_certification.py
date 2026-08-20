"""Freeze and validate the Java/Kotlin JVM adapter migration evidence."""

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

try:
    import jvm_adapter_package
    import jvm_adapter_runtime
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    from tooling import jvm_adapter_package, jvm_adapter_runtime


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "3.0"
BASE_COMMIT = "29158b75f78e7eb272d07374d6447c74c01c6f9c"
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
PUBLIC_BUILD_PATHS = (
    "bindings/java/pom.xml",
    "bindings/kotlin/build.gradle.kts",
    "bindings/kotlin/gradle/wrapper/gradle-wrapper.properties",
    "bindings/kotlin/settings.gradle.kts",
)
EXPECTED_TREE_FINGERPRINT = (
    "sha256:3512df75e0ccde7f5a958ec4c6a7ff9329177ba13404f1e976c86a4b1730ed3d"
)
EXPECTED_PRODUCTION_FINGERPRINT = (
    "sha256:811b6c9b9585cbbb8534057deaa4d33342887eca0b197b9fd85ff0eb8e0a728d"
)
EXPECTED_PUBLIC_FINGERPRINT = (
    "sha256:4784769e5bff0cdc1c27cd6bbcd19038c8b1d66805c62a781bfd6d1c7016fef5"
)
EXPECTED_SEMANTIC_FINGERPRINT = (
    "sha256:e023c47d5dbe9ff63870d04f46d4c0005f4e553398ef21a14ff0aeaed6975a9e"
)
EXPECTED_FAMILIES = {
    "public_api": 6,
    "canonical_parity": 8,
    "compatibility_success": 6,
    "compatibility_refusal": 6,
    "lifecycle_error": 8,
    "concurrency_classloader": 4,
    "unicode_resource": 6,
    "simply_stdlib": 8,
    "package_install": 4,
    "architecture_deletion": 6,
    "historical_preservation": 4,
    "runtime_jdk": 6,
}
EXPECTED_BINDINGS = {"jvm", "java", "kotlin"}
EXPECTED_OPERATIONS = {
    "compile",
    "describe",
    "simply.compile",
    "target_profile.inspect",
}
EXPECTED_RUNNERS = {
    "architecture",
    "cross-language",
    "historical-reference",
    "java-adapter",
    "jvm-bridge",
    "kotlin-adapter",
    "manifest",
    "native-lifecycle",
    "package",
    "platform-ci",
    "public-contract",
}
EXPECTED_RUNTIMES = {"jdk-11", "jdk-17", "jdk-21"}
EXPECTED_OBSERVATIONS = (
    (
        "java",
        "jdk-11",
        "baseline-build-failed",
        None,
        "Compilation is stopped by -Werror on three pre-existing serialVersionUID warnings.",
    ),
    (
        "java",
        "jdk-17",
        "baseline-build-failed",
        None,
        "Compilation is stopped by -Werror because source/target 11 omits the system module path.",
    ),
    (
        "java",
        "jdk-21",
        "baseline-build-failed",
        None,
        "Compilation is stopped by -Werror because source/target 11 omits the system module path.",
    ),
    (
        "kotlin",
        "jdk-11",
        "passed",
        664,
        "Gradle 8.5 and Kotlin 2.0.20 complete 664 tests with zero failures or skips.",
    ),
    (
        "kotlin",
        "jdk-17",
        "passed",
        664,
        "Gradle 8.5 and Kotlin 2.0.20 complete 664 tests with zero failures or skips.",
    ),
    (
        "kotlin",
        "jdk-21",
        "passed",
        664,
        "Gradle 8.5 and Kotlin 2.0.20 complete 664 tests with zero failures or skips.",
    ),
)
REQUIRED_CASE_IDS = {
    "public-shared-native-client",
    "parity-target-artifact-exact",
    "refusal-no-local-semantic-fallback",
    "lifecycle-same-descriptor-release",
    "concurrency-shared-client-reentrant",
    "simply-stdlib-lexical-not-semantic",
    "package-release-graph-one-bridge",
    "architecture-semantic-copy-denominator",
    "historical-source-bundle-replay",
    "runtime-java-jdk-11",
    "runtime-kotlin-jdk-21",
}


class JvmAdapterCertificationError(RuntimeError):
    """Raised when the JVM evidence denominator is invalid."""


@dataclass(frozen=True)
class JvmAdapterCertificationReport:
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
        raise JvmAdapterCertificationError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise JvmAdapterCertificationError(f"{path} must contain one JSON object")
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
        path = root / relative
        try:
            content = path.read_bytes()
        except OSError as error:
            raise JvmAdapterCertificationError(
                f"cannot read {path}: {error}"
            ) from error
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
        raise JvmAdapterCertificationError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return process


def _git_paths(root: Path) -> tuple[str, ...]:
    output = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        BASE_COMMIT,
        "--",
        "bindings/java",
        "bindings/kotlin",
    ).stdout
    return tuple(line for line in output.splitlines() if line)


def _path_sets(root: Path) -> dict[str, tuple[str, ...]]:
    tree = _git_paths(root)
    production = tuple(
        path
        for path in tree
        if ("/src/main/java/" in path and path.endswith(".java"))
        or ("/src/main/kotlin/" in path and path.endswith(".kt"))
    )
    tests = tuple(
        path
        for path in tree
        if ("/src/test/java/" in path and path.endswith(".java"))
        or ("/src/test/kotlin/" in path and path.endswith(".kt"))
    )
    public = tuple(sorted((*production, *PUBLIC_BUILD_PATHS)))
    semantic = tuple(
        path for path in production if "/core/" in path or "/emitters/" in path
    )
    expected_counts = {
        "tree": 70,
        "production": 47,
        "tests": 12,
        "public": 51,
        "semantic": 35,
    }
    actual_counts = {
        "tree": len(tree),
        "production": len(production),
        "tests": len(tests),
        "public": len(public),
        "semantic": len(semantic),
    }
    if actual_counts != expected_counts:
        raise JvmAdapterCertificationError(
            f"task-start JVM path denominator changed: {actual_counts!r}"
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


def _git_files_fingerprint(root: Path, paths: Sequence[str]) -> str:
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
        raise JvmAdapterCertificationError(
            "JVM task-start commit does not resolve exactly"
        )
    paths = _path_sets(root)
    fingerprints = {
        "tree": _git_files_fingerprint(root, paths["tree"]),
        "production": _git_files_fingerprint(root, paths["production"]),
        "public": _git_files_fingerprint(root, paths["public"]),
        "semantic": _git_files_fingerprint(root, paths["semantic"]),
    }
    expected = {
        "tree": EXPECTED_TREE_FINGERPRINT,
        "production": EXPECTED_PRODUCTION_FINGERPRINT,
        "public": EXPECTED_PUBLIC_FINGERPRINT,
        "semantic": EXPECTED_SEMANTIC_FINGERPRINT,
    }
    if fingerprints != expected:
        raise JvmAdapterCertificationError(
            f"task-start JVM fingerprints changed: {fingerprints!r}"
        )
    cache = {path: _git_blob(root, path) for path in paths["tree"]}
    baseline: dict[str, Any] = {
        "$schema": "evidence.schema.json#/$defs/LegacyBaseline",
        "suite_id": "strling.jvm-adapter-legacy-baseline",
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
        raise JvmAdapterCertificationError(
            f"{label} invalid at {location}: {error.message}"
        )


class JvmAdapterCertificationSuite:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.evidence_root = root / "tests" / "adapters" / "3.0"

    def certify(self) -> JvmAdapterCertificationReport:
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
    ) -> JvmAdapterCertificationReport:
        _validate(schema, manifest, "JVM adapter evidence manifest")
        baseline_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": "#/$defs/LegacyBaseline",
        }
        _validate(baseline_schema, baseline, "JVM legacy baseline")
        contract = manifest["contract"]
        legacy = manifest["legacy"]
        counts = manifest["counts"]
        cases = manifest["cases"]
        observations = manifest["task_start_observations"]
        assert isinstance(contract, dict)
        assert isinstance(legacy, dict)
        assert isinstance(counts, dict)
        assert isinstance(cases, list)
        assert isinstance(observations, list)
        if tuple(contract["files"]) != CONTRACT_FILES:
            raise JvmAdapterCertificationError("JVM contract file set or order changed")
        if contract["fingerprint"] != contract_fingerprint:
            raise JvmAdapterCertificationError("JVM contract fingerprint changed")
        expected_legacy = {
            "base_commit": BASE_COMMIT,
            "baseline_path": "tests/adapters/3.0/legacy-baseline.json",
            "tree_file_count": 70,
            "production_source_count": 47,
            "test_source_count": 12,
            "public_input_count": 51,
            "semantic_copy_count": 35,
            "tree_fingerprint": EXPECTED_TREE_FINGERPRINT,
            "production_fingerprint": EXPECTED_PRODUCTION_FINGERPRINT,
            "public_fingerprint": EXPECTED_PUBLIC_FINGERPRINT,
            "semantic_copy_fingerprint": EXPECTED_SEMANTIC_FINGERPRINT,
        }
        if legacy != expected_legacy:
            raise JvmAdapterCertificationError("JVM legacy denominator changed")
        if baseline != expected_baseline:
            raise JvmAdapterCertificationError("JVM legacy baseline does not reproduce")
        ids = [str(case["id"]) for case in cases]
        if len(ids) != len(set(ids)):
            raise JvmAdapterCertificationError("JVM evidence case ids must be unique")
        families = dict(Counter(str(case["family"]) for case in cases))
        if families != EXPECTED_FAMILIES or counts["families"] != EXPECTED_FAMILIES:
            raise JvmAdapterCertificationError(
                f"JVM evidence family denominator changed: {families!r}"
            )
        if (
            counts["total"] != sum(EXPECTED_FAMILIES.values())
            or len(cases) != counts["total"]
        ):
            raise JvmAdapterCertificationError("JVM evidence total changed")
        bindings = {str(item) for case in cases for item in case["bindings"]}
        runners = {str(case["runner"]) for case in cases}
        operations = {str(case["operation"]) for case in cases if "operation" in case}
        runtimes = {str(case["runtime"]) for case in cases if "runtime" in case}
        if bindings != EXPECTED_BINDINGS:
            raise JvmAdapterCertificationError("JVM binding denominator changed")
        if runners != EXPECTED_RUNNERS:
            raise JvmAdapterCertificationError("JVM runner denominator changed")
        if operations != EXPECTED_OPERATIONS:
            raise JvmAdapterCertificationError("JVM operation denominator changed")
        if runtimes != EXPECTED_RUNTIMES:
            raise JvmAdapterCertificationError("JVM runtime denominator changed")
        if not REQUIRED_CASE_IDS.issubset(ids):
            raise JvmAdapterCertificationError(
                "required JVM evidence cases are missing"
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
            raise JvmAdapterCertificationError("task-start JVM observations changed")
        evidence_fingerprint = _fingerprint_json(manifest, {"fingerprint"})
        if manifest["fingerprint"] != evidence_fingerprint:
            raise JvmAdapterCertificationError("JVM evidence fingerprint changed")
        return JvmAdapterCertificationReport(
            contract_fingerprint=contract_fingerprint,
            evidence_fingerprint=evidence_fingerprint,
            baseline_fingerprint=str(baseline["fingerprint"]),
            case_count=len(cases),
            family_counts=families,
            tree_file_count=70,
            public_input_count=51,
            semantic_copy_count=35,
            historical_source_count=70,
        )


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=4) + "\n")


def certify_live(native_library: Path, repeat_runs: int) -> dict[str, Any]:
    evidence = JvmAdapterCertificationSuite().certify()
    runtime = jvm_adapter_runtime.execute(native_library, repeat_runs)
    packages = jvm_adapter_package.certify_packages(native_library)
    return {
        "status": "passed",
        "evidence": evidence.__dict__,
        "runtime": runtime.__dict__,
        "packages": packages,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--write-manifest-fingerprint", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--certify", action="store_true")
    parser.add_argument(
        "--native-library",
        type=Path,
        default=jvm_adapter_runtime._native_default(),
    )
    parser.add_argument("--repeat-runs", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_baseline:
            _write_json(EVIDENCE_ROOT / "legacy-baseline.json", _build_baseline(ROOT))
        if arguments.write_manifest_fingerprint:
            manifest = _read_json(EVIDENCE_ROOT / "manifest.json")
            manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
            _write_json(EVIDENCE_ROOT / "manifest.json", manifest)
        if arguments.certify:
            payload = certify_live(arguments.native_library, arguments.repeat_runs)
        else:
            report = JvmAdapterCertificationSuite().certify()
            payload = {"status": "passed", **report.__dict__}
    except (
        JvmAdapterCertificationError,
        jvm_adapter_package.JvmPackageCertificationError,
        jvm_adapter_runtime.JvmAdapterRuntimeError,
        OSError,
        ValueError,
    ) as error:
        if arguments.json:
            print(json.dumps({"status": "failed", "error": str(error)}))
        else:
            print(f"JVM adapter certification failed: {error}")
        return 1
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
