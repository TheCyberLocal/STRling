#!/usr/bin/env python3
"""Freeze and validate Ruby/PHP/Perl/Lua/R adapter migration evidence."""

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
EVIDENCE_ROOT = ROOT / "tests" / "adapters" / "dynamic-languages-3.0"
BASE_COMMIT = "4504a35fdff420c5461beaedeeea6a2f184d2c5d"
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
    "bindings/ruby/Gemfile",
    "bindings/ruby/Gemfile.lock",
    "bindings/ruby/strling.gemspec",
    "bindings/ruby/lib/strling.rb",
    "bindings/ruby/README.md",
    "bindings/ruby/docs/api_reference.md",
    "bindings/php/composer.json",
    "bindings/php/composer.lock",
    "bindings/php/phpunit.xml",
    "bindings/php/src/STRling.php",
    "bindings/php/README.md",
    "bindings/php/docs/api_reference.md",
    "bindings/perl/Makefile.PL",
    "bindings/perl/dist.ini",
    "bindings/perl/lib/STRling.pm",
    "bindings/perl/README.md",
    "bindings/perl/docs/api_reference.md",
    "bindings/lua/strling-template.rockspec",
    "bindings/lua/src/strling.lua",
    "bindings/lua/src/simply.lua",
    "bindings/lua/README.md",
    "bindings/lua/docs/api_reference.md",
    "bindings/r/DESCRIPTION",
    "bindings/r/NAMESPACE",
    "bindings/r/setup.R",
    "bindings/r/README.md",
    "bindings/r/docs/api_reference.md",
    "governance/contracts/snapshots/r-public-api.json",
)
BINDINGS = ("ruby", "php", "perl", "lua", "r")
RUNTIMES = {
    "ruby": "ruby->=3.0,<4.0",
    "php": "php->=8.2,<9.0",
    "perl": "perl->=5.10,<6.0",
    "lua": "lua->=5.1,<5.5",
    "r": "r->deferred",
}
RUNNERS = {
    "architecture",
    "cross-language",
    "historical-reference",
    "lua-adapter",
    "manifest",
    "native-lifecycle",
    "package",
    "perl-adapter",
    "php-adapter",
    "platform-ci",
    "public-contract",
    "r-adapter",
    "ruby-adapter",
    "support-disposition",
}
OPERATIONS = {"compile", "describe", "simply.compile", "target_profile.inspect"}
EXPECTED_COUNTS = {
    "tree": 157,
    "production": 86,
    "tests": 39,
    "public": 28,
    "semantic": 83,
    "cases": 129,
}
EXPECTED_FINGERPRINTS = {
    "tree": "sha256:1ba12f0e78fe407c7fdae5ee8839d4c9fb4dd625fe6399a015ce7fbe5c22b1b1",
    "production": "sha256:f038f043704bfb5f4d50e2ee1d4ea24b88040cccab947f7156a1daf1fd3abdd2",
    "tests": "sha256:2a0c9927b75b897fb308b94c263fc634e55ccd5fe2009823ad5d01ba29a6c286",
    "public": "sha256:849e8aedb8bd2c589173d03689ca5dd2514997c0e0430b6331dfe9d2a7afccbc",
    "semantic": "sha256:6b4db0f70e7c32c535d25620d1f9969f15323c760b1fcfa739828251051798cd",
}
EXPECTED_FAMILIES = {
    "public_api": 15,
    "canonical_parity": 15,
    "compatibility_success": 10,
    "compatibility_refusal": 10,
    "marshaling_error": 15,
    "lifecycle_concurrency": 8,
    "unicode_resource": 10,
    "simply_stdlib": 10,
    "package_install": 10,
    "architecture_deletion": 10,
    "historical_preservation": 6,
    "platform_toolchain": 5,
    "support_disposition": 5,
}


class DynamicLanguageAdapterCertificationError(RuntimeError):
    """Raised when the dynamic-language evidence denominator is invalid."""


@dataclass(frozen=True)
class DynamicLanguageAdapterCertificationReport:
    contract_fingerprint: str
    evidence_fingerprint: str
    baseline_fingerprint: str
    case_count: int
    family_counts: dict[str, int]
    tree_file_count: int
    public_input_count: int
    semantic_copy_count: int
    historical_source_count: int


def _git(*arguments: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
    process = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=text, check=False
    )
    if process.returncode != 0:
        detail = process.stderr.strip() if text else process.stderr.decode(errors="replace")
        raise DynamicLanguageAdapterCertificationError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return process


def _git_blob(path: str) -> bytes:
    return _git("show", f"{BASE_COMMIT}:{path}", text=False).stdout


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


def _files_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        content = _git_blob(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def _path_sets() -> dict[str, tuple[str, ...]]:
    tree = tuple(
        line
        for line in _git(
            "ls-tree",
            "-r",
            "--name-only",
            BASE_COMMIT,
            "--",
            *(f"bindings/{binding}" for binding in BINDINGS),
        ).stdout.splitlines()
        if line
    )
    production = tuple(
        path
        for path in tree
        if (path.startswith("bindings/ruby/lib/") and path.endswith(".rb"))
        or (path.startswith("bindings/php/src/") and path.endswith(".php"))
        or (path.startswith("bindings/perl/lib/") and path.endswith(".pm"))
        or (path.startswith("bindings/lua/src/") and path.endswith(".lua"))
        or (path.startswith("bindings/r/R/") and path.endswith(".R"))
    )
    tests = tuple(
        path
        for path in tree
        if (path.endswith(".rb") and ("/test/" in path or "/spec/" in path))
        or (path.endswith(".php") and "/tests/" in path)
        or (path.endswith(".t") and "/t/" in path)
        or (
            path.endswith(".lua")
            and (
                "/spec/" in path
                or path in {"bindings/lua/test.lua", "bindings/lua/verify_simply.lua"}
            )
        )
        or (
            path.endswith(".R")
            and ("/tests/" in path or path == "bindings/r/run_tests.R")
        )
    )
    semantic = tuple(
        path
        for path in production
        if path
        not in {
            "bindings/ruby/lib/strling.rb",
            "bindings/php/src/STRling.php",
            "bindings/perl/lib/STRling.pm",
        }
    )
    return {
        "tree": tree,
        "production": production,
        "tests": tests,
        "public": PUBLIC_METADATA,
        "semantic": semantic,
    }


def _case(
    identity: str,
    family: str,
    bindings: Sequence[str],
    runner: str,
    claim: str,
    *,
    operation: str | None = None,
    runtime: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": identity,
        "family": family,
        "bindings": list(bindings),
        "runner": runner,
        "claim": claim,
    }
    if operation:
        value["operation"] = operation
    if runtime:
        value["runtime"] = runtime
    return value


def _binding_cases(binding: str) -> list[dict[str, Any]]:
    runner = f"{binding}-adapter"
    cases = [
        _case(f"public-api-{binding}-canonical-facade", "public_api", [binding], "public-contract", "The public facade exposes canonical data without binding semantic types."),
        _case(f"public-api-{binding}-host-errors", "public_api", [binding], "public-contract", "Native transport failures have stable host identities separate from canonical rejections."),
        _case(f"public-api-{binding}-snapshot-reproducible", "public_api", [binding], "public-contract", "The post-migration public snapshot reproduces deterministically."),
        _case(f"canonical-parity-{binding}-compile", "canonical_parity", [binding], runner, "Compile preserves the canonical response exactly.", operation="compile"),
        _case(f"canonical-parity-{binding}-describe", "canonical_parity", [binding], runner, "Describe preserves the canonical response exactly.", operation="describe"),
        _case(f"canonical-parity-{binding}-target-profile", "canonical_parity", [binding], runner, "Target profile inspection preserves canonical data exactly.", operation="target_profile.inspect"),
        _case(f"compatibility-success-{binding}-package-identity", "compatibility_success", [binding], "package", "The governed package identity remains stable."),
        _case(f"compatibility-success-{binding}-simply-entrypoint", "compatibility_success", [binding], runner, "Curated Simply entrypoints delegate to canonical requests.", operation="simply.compile"),
        _case(f"compatibility-refusal-{binding}-abi-mismatch", "compatibility_refusal", [binding], runner, "ABI mismatch fails before any operation executes."),
        _case(f"compatibility-refusal-{binding}-no-local-fallback", "compatibility_refusal", [binding], "architecture", "A missing native boundary cannot fall back to binding semantics."),
        _case(f"marshaling-error-{binding}-request-utf8", "marshaling_error", [binding], runner, "Request bytes are strict bounded UTF-8 JSON."),
        _case(f"marshaling-error-{binding}-response-bounds", "marshaling_error", [binding], runner, "Response descriptors and byte lengths are validated before decoding."),
        _case(f"marshaling-error-{binding}-same-descriptor-release", "marshaling_error", [binding], "native-lifecycle", "Every owned response is freed through its matching native symbol."),
        _case(f"lifecycle-concurrency-{binding}-close-idempotent", "lifecycle_concurrency", [binding], "native-lifecycle", "Explicit close is idempotent within the declared host model."),
        _case(f"unicode-resource-{binding}-multibyte", "unicode_resource", [binding], runner, "Multibyte source and diagnostics preserve exact UTF-8 content."),
        _case(f"unicode-resource-{binding}-embedded-nul", "unicode_resource", [binding], runner, "Embedded NUL content is length-delimited rather than truncated."),
        _case(f"simply-stdlib-{binding}-canonical-equivalence", "simply_stdlib", [binding], runner, "Simply output equals the canonical Simply protocol result.", operation="simply.compile"),
        _case(f"simply-stdlib-{binding}-lexical-not-semantic", "simply_stdlib", [binding], runner, "Lexical-shape helpers are not strengthened into semantic validators."),
        _case(f"package-install-{binding}-clean-consumer", "package_install", [binding], "package", "A clean consumer can build or install the governed local package."),
        _case(f"package-install-{binding}-release-graph", "package_install", [binding], "package", "The release graph contains one canonical transport and no semantic copy."),
        _case(f"architecture-deletion-{binding}-semantic-copy-zero", "architecture_deletion", [binding], "architecture", "Every frozen product semantic-copy source is retired after migration."),
        _case(f"architecture-deletion-{binding}-runtime-no-fallback", "architecture_deletion", [binding], "architecture", "Runtime sources contain no subprocess, socket, download, or local semantic route."),
    ]
    if binding in {"ruby", "php", "perl"}:
        cases.insert(
            14,
            _case(
                f"lifecycle-concurrency-{binding}-concurrent-calls",
                "lifecycle_concurrency",
                [binding],
                "native-lifecycle",
                "Concurrent calls remain reentrant and close-safe.",
            ),
        )
    return cases


def _cases() -> list[dict[str, Any]]:
    values = [case for binding in BINDINGS for case in _binding_cases(binding)]
    all_bindings = list(BINDINGS)
    values.extend(
        [
            _case("historical-preservation-source-bundle", "historical_preservation", all_bindings, "historical-reference", "Every task-start source is embedded and authenticated from the immutable base commit."),
            _case("historical-preservation-public-inputs", "historical_preservation", all_bindings, "historical-reference", "Public and package inputs remain exact compatibility evidence."),
            _case("historical-preservation-no-authority-promotion", "historical_preservation", all_bindings, "architecture", "Historical behavior cannot become canonical semantic authority."),
            _case("historical-preservation-closed-denominator", "historical_preservation", all_bindings, "manifest", "Case, source, public, and semantic-copy denominators cannot shrink or substitute identities."),
            _case("historical-preservation-cross-binding-result", "historical_preservation", all_bindings, "cross-language", "Retained adapters project one canonical result rather than peer-derived expectations."),
            _case("historical-preservation-lexical-guarantee", "historical_preservation", all_bindings, "cross-language", "Five lexical helpers remain lexical rather than becoming semantic validators."),
        ]
    )
    for binding in BINDINGS:
        values.append(
            _case(
                f"platform-toolchain-{binding}-declared-range",
                "platform_toolchain",
                [binding],
                "platform-ci",
                "Only executed declared runtime and platform rows can become certified evidence.",
                runtime=RUNTIMES[binding],
            )
        )
        values.append(
            _case(
                f"support-disposition-{binding}-provisional-preview",
                "support_disposition",
                [binding],
                "support-disposition",
                "Retention is provisional Preview-level evidence and not permanent support-policy ratification.",
            )
        )
    return values


def _observations() -> list[dict[str, Any]]:
    details = {
        "ruby": "Ruby and Bundler are absent on the task-start Windows host; no gem build, test, or platform claim is inferred.",
        "php": "PHP and Composer are absent on the task-start Windows host; no extension, package, test, or platform claim is inferred.",
        "perl": "Perl is absent on the task-start Windows host; the separately observed Linux executable is not a completed adapter test row.",
        "lua": "Lua and LuaRocks are absent on the task-start Windows host; no C-module ABI or platform claim is inferred.",
        "r": "R and Rscript are absent and no runtime range is governed at task start; no package or platform claim is inferred.",
    }
    return [
        {
            "binding": binding,
            "runtime": RUNTIMES[binding],
            "status": "unavailable",
            "tests": None,
            "detail": details[binding],
        }
        for binding in BINDINGS
    ]


def _dispositions() -> list[dict[str, str]]:
    return [
        {
            "binding": binding,
            "status": "preview_candidate",
            "permanent_policy": "deferred_to_p20_t01",
            "failed_retention": "legacy_or_unsupported_recommendation",
        }
        for binding in BINDINGS
    ]


def _file_entry(path: str, *, include_content: bool) -> dict[str, Any]:
    content = _git_blob(path)
    value: dict[str, Any] = {
        "path": path,
        "size": len(content),
        "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }
    if include_content:
        value["content_base64"] = base64.b64encode(content).decode("ascii")
    return value


def _build_baseline() -> dict[str, Any]:
    paths = _path_sets()
    value: dict[str, Any] = {
        "$schema": "evidence.schema.json#/$defs/LegacyBaseline",
        "suite_id": "strling.dynamic-language-adapter-legacy-baseline",
        "suite_version": "3.0.0",
        "base_commit": BASE_COMMIT,
        "fingerprints": {name: _files_fingerprint(items) for name, items in paths.items()},
        "public_files": [_file_entry(path, include_content=False) for path in paths["public"]],
        "semantic_copy_files": [_file_entry(path, include_content=False) for path in paths["semantic"]],
        "historical_source_files": [_file_entry(path, include_content=True) for path in paths["tree"]],
    }
    value["fingerprint"] = _fingerprint_json(value)
    return value


def _build_manifest() -> dict[str, Any]:
    paths = _path_sets()
    contract_fingerprint = _files_fingerprint(CONTRACT_FILES)
    cases = _cases()
    family_counts = dict(sorted(Counter(case["family"] for case in cases).items()))
    value: dict[str, Any] = {
        "$schema": "evidence.schema.json",
        "suite_id": "strling.dynamic-language-adapter-migration-evidence",
        "suite_version": "3.0.0",
        "contract": {"files": list(CONTRACT_FILES), "fingerprint": contract_fingerprint},
        "legacy": {
            "base_commit": BASE_COMMIT,
            "baseline_path": "tests/adapters/dynamic-languages-3.0/legacy-baseline.json",
            "tree_file_count": len(paths["tree"]),
            "production_source_count": len(paths["production"]),
            "test_source_count": len(paths["tests"]),
            "public_input_count": len(paths["public"]),
            "semantic_copy_count": len(paths["semantic"]),
            "tree_fingerprint": _files_fingerprint(paths["tree"]),
            "production_fingerprint": _files_fingerprint(paths["production"]),
            "test_fingerprint": _files_fingerprint(paths["tests"]),
            "public_fingerprint": _files_fingerprint(paths["public"]),
            "semantic_copy_fingerprint": _files_fingerprint(paths["semantic"]),
        },
        "task_start_observations": _observations(),
        "provisional_dispositions": _dispositions(),
        "counts": {"total": len(cases), "families": family_counts},
        "cases": cases,
    }
    value["fingerprint"] = _fingerprint_json(value)
    return value


def _schema() -> dict[str, Any]:
    sha = {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    path = {"type": "string", "minLength": 1, "pattern": r"^(?!/)(?!.*\\)(?!.*(?:^|/)\.\.(?:/|$)).+$"}
    file_entry = {
        "type": "object",
        "additionalProperties": False,
        "required": ["path", "size", "sha256"],
        "properties": {"path": path, "size": {"type": "integer", "minimum": 0}, "sha256": sha, "content_base64": {"type": "string"}},
    }
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://strling.dev/tests/adapters/dynamic-languages-3.0/evidence.schema.json",
        "title": "STRling dynamic-language adapter migration evidence denominator 3.0",
        "type": "object",
        "additionalProperties": False,
        "required": ["$schema", "suite_id", "suite_version", "contract", "legacy", "task_start_observations", "provisional_dispositions", "counts", "cases", "fingerprint"],
        "properties": {
            "$schema": {"const": "evidence.schema.json"},
            "suite_id": {"const": "strling.dynamic-language-adapter-migration-evidence"},
            "suite_version": {"const": "3.0.0"},
            "contract": {"type": "object", "additionalProperties": False, "required": ["files", "fingerprint"], "properties": {"files": {"type": "array", "minItems": 17, "maxItems": 17, "uniqueItems": True, "items": path}, "fingerprint": sha}},
            "legacy": {"type": "object", "additionalProperties": False, "required": ["base_commit", "baseline_path", "tree_file_count", "production_source_count", "test_source_count", "public_input_count", "semantic_copy_count", "tree_fingerprint", "production_fingerprint", "test_fingerprint", "public_fingerprint", "semantic_copy_fingerprint"], "properties": {"base_commit": {"const": BASE_COMMIT}, "baseline_path": {"const": "tests/adapters/dynamic-languages-3.0/legacy-baseline.json"}, "tree_file_count": {"const": EXPECTED_COUNTS["tree"]}, "production_source_count": {"const": EXPECTED_COUNTS["production"]}, "test_source_count": {"const": EXPECTED_COUNTS["tests"]}, "public_input_count": {"const": EXPECTED_COUNTS["public"]}, "semantic_copy_count": {"const": EXPECTED_COUNTS["semantic"]}, "tree_fingerprint": sha, "production_fingerprint": sha, "test_fingerprint": sha, "public_fingerprint": sha, "semantic_copy_fingerprint": sha}},
            "task_start_observations": {"type": "array", "minItems": 5, "maxItems": 5, "items": {"type": "object", "additionalProperties": False, "required": ["binding", "runtime", "status", "tests", "detail"], "properties": {"binding": {"enum": list(BINDINGS)}, "runtime": {"enum": list(RUNTIMES.values())}, "status": {"const": "unavailable"}, "tests": {"type": "null"}, "detail": {"type": "string", "minLength": 1}}}},
            "provisional_dispositions": {"type": "array", "minItems": 5, "maxItems": 5, "items": {"type": "object", "additionalProperties": False, "required": ["binding", "status", "permanent_policy", "failed_retention"], "properties": {"binding": {"enum": list(BINDINGS)}, "status": {"const": "preview_candidate"}, "permanent_policy": {"const": "deferred_to_p20_t01"}, "failed_retention": {"const": "legacy_or_unsupported_recommendation"}}}},
            "counts": {"type": "object", "additionalProperties": False, "required": ["total", "families"], "properties": {"total": {"const": EXPECTED_COUNTS["cases"]}, "families": {"type": "object", "minProperties": 13, "maxProperties": 13, "additionalProperties": {"type": "integer", "minimum": 1}}}},
            "cases": {"type": "array", "minItems": EXPECTED_COUNTS["cases"], "maxItems": EXPECTED_COUNTS["cases"], "items": {"type": "object", "additionalProperties": False, "required": ["id", "family", "bindings", "runner", "claim"], "properties": {"id": {"type": "string", "pattern": "^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$"}, "family": {"enum": list(EXPECTED_FAMILIES)}, "bindings": {"type": "array", "minItems": 1, "maxItems": 5, "uniqueItems": True, "items": {"enum": list(BINDINGS)}}, "runner": {"enum": sorted(RUNNERS)}, "operation": {"enum": sorted(OPERATIONS)}, "runtime": {"enum": list(RUNTIMES.values())}, "claim": {"type": "string", "minLength": 1}}}},
            "fingerprint": sha,
        },
        "$defs": {
            "LegacyBaseline": {
                "type": "object",
                "additionalProperties": False,
                "required": ["$schema", "suite_id", "suite_version", "base_commit", "fingerprints", "public_files", "semantic_copy_files", "historical_source_files", "fingerprint"],
                "properties": {
                    "$schema": {"const": "evidence.schema.json#/$defs/LegacyBaseline"},
                    "suite_id": {"const": "strling.dynamic-language-adapter-legacy-baseline"},
                    "suite_version": {"const": "3.0.0"},
                    "base_commit": {"const": BASE_COMMIT},
                    "fingerprints": {"type": "object", "additionalProperties": False, "required": ["tree", "production", "tests", "public", "semantic"], "properties": {name: sha for name in ("tree", "production", "tests", "public", "semantic")}},
                    "public_files": {"type": "array", "minItems": EXPECTED_COUNTS["public"], "maxItems": EXPECTED_COUNTS["public"], "items": file_entry},
                    "semantic_copy_files": {"type": "array", "minItems": EXPECTED_COUNTS["semantic"], "maxItems": EXPECTED_COUNTS["semantic"], "items": file_entry},
                    "historical_source_files": {"type": "array", "minItems": EXPECTED_COUNTS["tree"], "maxItems": EXPECTED_COUNTS["tree"], "items": file_entry},
                    "fingerprint": sha,
                },
            }
        },
    }
    return schema


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DynamicLanguageAdapterCertificationError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise DynamicLanguageAdapterCertificationError(f"{path} must contain an object")
    return value


def _validate(instance: Mapping[str, Any], schema: Mapping[str, Any], label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors[:5])
        raise DynamicLanguageAdapterCertificationError(f"{label} schema validation failed: {detail}")


class DynamicLanguageAdapterCertificationSuite:
    def certify_documents(
        self,
        schema: dict[str, Any],
        manifest: dict[str, Any],
        baseline: dict[str, Any],
        *,
        expected_schema: dict[str, Any],
        expected_manifest: dict[str, Any],
        expected_baseline: dict[str, Any],
    ) -> DynamicLanguageAdapterCertificationReport:
        if schema != expected_schema:
            raise DynamicLanguageAdapterCertificationError("schema does not reproduce")
        if manifest != expected_manifest:
            raise DynamicLanguageAdapterCertificationError("manifest does not reproduce")
        if baseline != expected_baseline:
            raise DynamicLanguageAdapterCertificationError("baseline does not reproduce")
        _validate(manifest, schema, "manifest")
        _validate(baseline, schema["$defs"]["LegacyBaseline"], "baseline")
        if manifest["fingerprint"] != _fingerprint_json(manifest, {"fingerprint"}):
            raise DynamicLanguageAdapterCertificationError("manifest fingerprint is not canonical")
        if baseline["fingerprint"] != _fingerprint_json(baseline, {"fingerprint"}):
            raise DynamicLanguageAdapterCertificationError("baseline fingerprint is not canonical")
        family_counts = dict(sorted(Counter(case["family"] for case in manifest["cases"]).items()))
        if family_counts != EXPECTED_FAMILIES:
            raise DynamicLanguageAdapterCertificationError("case family denominator changed")
        if len({case["id"] for case in manifest["cases"]}) != EXPECTED_COUNTS["cases"]:
            raise DynamicLanguageAdapterCertificationError("case identities are not unique")
        if {item["binding"] for item in manifest["task_start_observations"]} != set(BINDINGS):
            raise DynamicLanguageAdapterCertificationError("task-start observations are incomplete")
        if {item["binding"] for item in manifest["provisional_dispositions"]} != set(BINDINGS):
            raise DynamicLanguageAdapterCertificationError("provisional dispositions are incomplete")
        for entry in baseline["historical_source_files"]:
            content = base64.b64decode(entry["content_base64"], validate=True)
            if content != _git_blob(entry["path"]):
                raise DynamicLanguageAdapterCertificationError(f"historical source does not reproduce: {entry['path']}")
        return DynamicLanguageAdapterCertificationReport(
            contract_fingerprint=manifest["contract"]["fingerprint"],
            evidence_fingerprint=manifest["fingerprint"],
            baseline_fingerprint=baseline["fingerprint"],
            case_count=manifest["counts"]["total"],
            family_counts=family_counts,
            tree_file_count=manifest["legacy"]["tree_file_count"],
            public_input_count=manifest["legacy"]["public_input_count"],
            semantic_copy_count=manifest["legacy"]["semantic_copy_count"],
            historical_source_count=len(baseline["historical_source_files"]),
        )

    def certify(self) -> DynamicLanguageAdapterCertificationReport:
        expected_schema = _schema()
        expected_manifest = _build_manifest()
        expected_baseline = _build_baseline()
        return self.certify_documents(
            _load(EVIDENCE_ROOT / "evidence.schema.json"),
            _load(EVIDENCE_ROOT / "manifest.json"),
            _load(EVIDENCE_ROOT / "legacy-baseline.json"),
            expected_schema=expected_schema,
            expected_manifest=expected_manifest,
            expected_baseline=expected_baseline,
        )


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def _report_value(report: DynamicLanguageAdapterCertificationReport) -> dict[str, Any]:
    return {
        "status": "passed",
        "contract_fingerprint": report.contract_fingerprint,
        "evidence_fingerprint": report.evidence_fingerprint,
        "baseline_fingerprint": report.baseline_fingerprint,
        "case_count": report.case_count,
        "family_counts": report.family_counts,
        "tree_file_count": report.tree_file_count,
        "public_input_count": report.public_input_count,
        "semantic_copy_count": report.semantic_copy_count,
        "historical_source_count": report.historical_source_count,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_evidence:
            _write(EVIDENCE_ROOT / "evidence.schema.json", _schema())
            _write(EVIDENCE_ROOT / "manifest.json", _build_manifest())
            _write(EVIDENCE_ROOT / "legacy-baseline.json", _build_baseline())
        report = DynamicLanguageAdapterCertificationSuite().certify()
    except DynamicLanguageAdapterCertificationError as error:
        if arguments.json:
            print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        else:
            print(f"[failed] {error}")
        return 2
    value = _report_value(report)
    print(json.dumps(value, sort_keys=True) if arguments.json else value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
