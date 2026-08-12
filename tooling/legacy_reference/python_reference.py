#!/usr/bin/env python3
"""Deterministic observations of the checked-in historical Python package."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = ROOT / "bindings" / "python"
PYTHON_SOURCE = PYTHON_ROOT / "src"
if str(PYTHON_SOURCE) not in sys.path:
    sys.path.insert(0, str(PYTHON_SOURCE))

simply = importlib.import_module("STRling.simply")
Compiler = importlib.import_module("STRling.core.compiler").Compiler
parser_module = importlib.import_module("STRling.core.parser")
parse = parser_module.parse
parse_to_artifact = parser_module.parse_to_artifact
emitter_module = importlib.import_module("STRling.emitters.pcre2")
emit = emitter_module.emit
emit_with_diagnostics = emitter_module.emit_with_diagnostics


PROTOCOL_VERSION = "1.0.0"
OBSERVATION_SCHEMA_VERSION = "1.1.0"
BATCH_SCHEMA_VERSION = "1.1.0"
CERTIFICATION_SCHEMA_VERSION = "1.1.0"
CORPUS_VERSION = "1.0.0"
REQUEST_KIND = "strling.legacy-reference-request"
OBSERVATION_KIND = "strling.legacy-reference-observation"
PROTOCOL_FAILURE_KIND = "strling.legacy-reference-protocol-failure"
CORPUS_KIND = "strling.legacy-reference-corpus"
BATCH_KIND = "strling.legacy-reference-batch"
CERTIFICATION_KIND = "strling.legacy-reference-certification"
RUNNER = {
    "id": "python",
    "kind": "strling.legacy-reference-runner",
    "language": "python",
    "version": "1.0.0",
}
DEFAULT_CORPUS_PATH = Path(__file__).with_name("python_corpus.json")

OperationSpec = Mapping[str, Any]
OPERATION_SPECS: dict[str, OperationSpec] = {
    "parser.parse": {
        "exposed": True,
        "input": "source",
        "options": (),
        "stage": "parser",
        "surface": "python.core.parser.parse",
    },
    "parser.parse_to_artifact": {
        "exposed": True,
        "input": "source",
        "options": (),
        "stage": "parser",
        "surface": "python.core.parser.parse_to_artifact",
    },
    "compiler.compile": {
        "exposed": True,
        "input": "source",
        "options": (),
        "stage": "compiler",
        "surface": "python.core.Compiler.compile",
    },
    "compiler.compile_with_metadata": {
        "exposed": True,
        "input": "source",
        "options": (),
        "stage": "compiler",
        "surface": "python.core.Compiler.compile_with_metadata",
    },
    "emitter.pcre2.emit": {
        "exposed": True,
        "input": "source",
        "options": ("max_depth",),
        "stage": "emitter",
        "surface": "python.emitters.pcre2.emit",
    },
    "emitter.pcre2.emit_with_diagnostics": {
        "exposed": True,
        "input": "source",
        "options": ("max_depth",),
        "stage": "emitter",
        "surface": "python.emitters.pcre2.emit_with_diagnostics",
    },
    "api.root.parse": {
        "exposed": False,
        "input": "source",
        "options": (),
        "reason": "the historical Python package root exports simply but not parse",
        "stage": "public_api",
        "surface": "python.package-root.parse",
    },
    "api.root.parse_to_artifact": {
        "exposed": False,
        "input": "source",
        "options": (),
        "reason": (
            "the historical Python package root exports simply but not "
            "parse_to_artifact"
        ),
        "stage": "public_api",
        "surface": "python.package-root.parse_to_artifact",
    },
    "api.simply.literal_to_string": {
        "exposed": True,
        "input": "literal",
        "options": (),
        "stage": "public_api",
        "surface": "python.simply.Pattern.__str__",
    },
    "api.simply.compile_node": {
        "exposed": False,
        "input": "literal",
        "options": ("flags", "target"),
        "reason": "the historical Python Simply API does not expose compile_node",
        "stage": "public_api",
        "surface": "python.simply.compile_node",
    },
    "api.simply.to_regexp": {
        "exposed": False,
        "input": "literal",
        "options": ("flags", "target"),
        "reason": "the historical Python Simply API does not expose to_regexp",
        "stage": "public_api",
        "surface": "python.simply.to_regexp",
    },
}
OPERATION_IDS = tuple(OPERATION_SPECS)


class ProtocolError(Exception):
    """A request, corpus, or runner contract failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class LegacySurfaceFailure(Exception):
    """An exception attributed to the historical stage that produced it."""

    def __init__(self, stage: str, error: Exception) -> None:
        super().__init__(str(error))
        self.stage = stage
        self.error = error


def canonicalize(value: Any, location: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"{location} contains a non-finite number")
        return 0 if value == 0 else value
    if isinstance(value, (list, tuple)):
        return [
            canonicalize(item, f"{location}/{index}")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError(f"{location} contains a non-string key")
        return {
            key: canonicalize(value[key], f"{location}/{key}") for key in sorted(value)
        }
    raise TypeError(f"{location} is not a canonical JSON value")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonicalize(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_line(value: Any) -> str:
    return canonical_json(value) + "\n"


def sha256_bytes(value: bytes | str) -> str:
    encoded = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(encoded).hexdigest()


def canonical_fingerprint(value: Any) -> str:
    return f"sha256:{sha256_bytes(canonical_json(value))}"


def _exact_keys(
    value: Mapping[str, Any], expected: Sequence[str], location: str
) -> None:
    if sorted(value) != sorted(expected):
        wanted = ", ".join(sorted(expected))
        raise ProtocolError(
            "INVALID_SHAPE", f"{location} keys must be exactly: {wanted}"
        )


def _validate_flags(value: Any) -> str | dict[str, bool]:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        raise ProtocolError(
            "INVALID_OPTIONS",
            "options.flags must be a string or historical flag object",
        )
    allowed = {"dotAll", "extended", "ignoreCase", "multiline", "unicode"}
    if any(
        key not in allowed or not isinstance(enabled, bool)
        for key, enabled in value.items()
    ):
        raise ProtocolError(
            "INVALID_OPTIONS",
            "options.flags contains an unknown key or non-boolean value",
        )
    return canonicalize(value)


def _validate_options(options: Any, spec: OperationSpec) -> dict[str, Any]:
    if not isinstance(options, dict):
        raise ProtocolError("INVALID_OPTIONS", "options must be an object")
    allowed = set(spec["options"])
    for key in options:
        if key not in allowed:
            raise ProtocolError(
                "INVALID_OPTIONS",
                f"option '{key}' is not supported by this operation",
            )
    normalized: dict[str, Any] = {}
    if "max_depth" in options:
        max_depth = options["max_depth"]
        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or max_depth < 1
        ):
            raise ProtocolError(
                "INVALID_OPTIONS",
                "options.max_depth must be a positive integer",
            )
        normalized["max_depth"] = max_depth
    if "target" in options:
        if not isinstance(options["target"], str):
            raise ProtocolError("INVALID_OPTIONS", "options.target must be a string")
        normalized["target"] = options["target"]
    if "flags" in options:
        normalized["flags"] = _validate_flags(options["flags"])
    return normalized


def validate_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError("INVALID_REQUEST", "request must be an object")
    _exact_keys(
        value,
        (
            "expected_legacy_surface",
            "input",
            "kind",
            "operation",
            "options",
            "protocol_version",
        ),
        "request",
    )
    if value["kind"] != REQUEST_KIND:
        raise ProtocolError("UNSUPPORTED_KIND", f"kind must be '{REQUEST_KIND}'")
    if value["protocol_version"] != PROTOCOL_VERSION:
        raise ProtocolError(
            "UNSUPPORTED_PROTOCOL_VERSION",
            f"protocol_version must be '{PROTOCOL_VERSION}'",
        )
    operation = value["operation"]
    if not isinstance(operation, str):
        raise ProtocolError("INVALID_OPERATION", "operation must be a string")
    spec = OPERATION_SPECS.get(operation)
    if spec is None:
        raise ProtocolError("UNKNOWN_OPERATION", f"unknown operation '{operation}'")
    if value["expected_legacy_surface"] != spec["surface"]:
        raise ProtocolError(
            "SURFACE_MISMATCH",
            (
                f"operation '{operation}' requires expected historical surface "
                f"'{spec['surface']}'"
            ),
        )
    input_value = value["input"]
    if not isinstance(input_value, dict):
        raise ProtocolError("INVALID_INPUT", "input must be an object")
    input_key = spec["input"]
    _exact_keys(input_value, (input_key,), "input")
    if not isinstance(input_value[input_key], str):
        raise ProtocolError("INVALID_INPUT", f"input.{input_key} must be a string")
    return {
        "expected_legacy_surface": value["expected_legacy_surface"],
        "input": {input_key: input_value[input_key]},
        "kind": REQUEST_KIND,
        "operation": operation,
        "options": _validate_options(value["options"], spec),
        "protocol_version": PROTOCOL_VERSION,
    }


def governed_implementation_paths(root: Path = ROOT) -> list[str]:
    sources = [
        path.relative_to(root).as_posix()
        for path in (root / "bindings" / "python" / "src" / "STRling").rglob("*.py")
        if path.is_file()
    ]
    fixed = [
        "bindings/python/pyproject.toml",
        "bindings/python/requirements.txt",
    ]
    return sorted([*fixed, *sources])


def read_implementation_manifest(root: Path = ROOT) -> list[dict[str, Any]]:
    result = []
    for relative in governed_implementation_paths(root):
        content = (root / relative).read_bytes()
        result.append(
            {
                "bytes": len(content),
                "path": relative,
                "sha256": sha256_bytes(content),
            }
        )
    return result


def fingerprint_implementation_manifest(
    manifest: Sequence[Mapping[str, Any]], python_version: str
) -> str:
    return canonical_fingerprint(
        {
            "inputs": list(manifest),
            "runtime": {"name": "python", "version": python_version},
        }
    )


def create_implementation_identity(
    root: Path = ROOT, python_version: str | None = None
) -> dict[str, Any]:
    version = python_version or platform.python_version()
    inputs = read_implementation_manifest(root)
    return {
        "algorithm": "sha256",
        "fingerprint": fingerprint_implementation_manifest(inputs, version),
        "inputs": inputs,
        "kind": "strling.legacy-python-implementation",
        "manifest_encoding": "canonical-json-v1",
        "runtime": {"name": "python", "version": version},
    }


def _failure_category(name: str) -> str:
    return {
        "STRlingParseError": "parse_error",
        "STRlingCompilationError": "compilation_error",
        "SyntaxError": "syntax_error",
        "TypeError": "type_error",
        "ValueError": "value_error",
        "RecursionError": "recursion_error",
    }.get(name, "legacy_exception")


def project_legacy_failure(error: Exception, stage: str) -> dict[str, Any]:
    name = type(error).__name__
    historical_message = getattr(error, "message", None)
    message = historical_message if isinstance(historical_message, str) else str(error)
    failure: dict[str, Any] = {
        "category": _failure_category(name),
        "class": name,
        "message": message,
        "name": name,
        "stage": stage,
    }
    for source_key, target_key in (
        ("code", "code"),
        ("engine", "engine"),
        ("pos", "position"),
        ("text", "source_text"),
        ("hint", "hint"),
    ):
        if hasattr(error, source_key):
            child = getattr(error, source_key)
            if child is not None:
                failure[target_key] = canonicalize(child)
    formatted = str(error)
    if formatted != message:
        failure["formatted"] = formatted
    return failure


def _parse_for_pipeline(source: str) -> tuple[Any, Any]:
    try:
        return parse(source)
    except Exception as error:
        raise LegacySurfaceFailure("parser", error) from error


def _compile_for_pipeline(root: Any, with_metadata: bool = False) -> Any:
    try:
        compiler = Compiler()
        return (
            compiler.compile_with_metadata(root)
            if with_metadata
            else compiler.compile(root)
        )
    except Exception as error:
        raise LegacySurfaceFailure("compiler", error) from error


def _flags_projection(flags: Any) -> dict[str, bool]:
    return flags.to_dict()


def invoke_python(request: Mapping[str, Any]) -> dict[str, Any]:
    operation = request["operation"]
    input_value = request["input"]
    options = request["options"]

    if operation == "parser.parse":
        flags, root = parse(input_value["source"])
        return {
            "flags": _flags_projection(flags),
            "return_shape": "tuple",
            "root": root.to_dict(),
        }
    if operation == "parser.parse_to_artifact":
        return {
            "artifact": parse_to_artifact(input_value["source"]),
            "return_shape": "dict",
        }
    if operation == "compiler.compile":
        flags, root = _parse_for_pipeline(input_value["source"])
        ir = _compile_for_pipeline(root)
        return {
            "input_flags": _flags_projection(flags),
            "ir": ir.to_dict(),
            "return_shape": type(ir).__name__,
        }
    if operation == "compiler.compile_with_metadata":
        flags, root = _parse_for_pipeline(input_value["source"])
        result = _compile_for_pipeline(root, with_metadata=True)
        return {
            "input_flags": _flags_projection(flags),
            "ir": result["ir"].to_dict(),
            "metadata": result["metadata"],
            "return_shape": "dict",
        }
    if operation in (
        "emitter.pcre2.emit",
        "emitter.pcre2.emit_with_diagnostics",
    ):
        flags, root = _parse_for_pipeline(input_value["source"])
        ir = _compile_for_pipeline(root)
        max_depth = options.get("max_depth")
        try:
            if operation == "emitter.pcre2.emit":
                pattern = emit(ir, flags, max_depth=max_depth)
                warnings: list[dict[str, str]] | None = None
                return_shape = "str"
            else:
                result = emit_with_diagnostics(ir, flags, max_depth=max_depth)
                pattern = result.pattern
                warnings = [
                    {"code": warning.code, "message": warning.message}
                    for warning in result.warnings
                ]
                return_shape = "EmitResult"
        except Exception as error:
            raise LegacySurfaceFailure("emitter", error) from error
        evidence: dict[str, Any] = {
            "emitted_flags": _flags_projection(flags),
            "emitted_pattern": pattern,
            "return_shape": return_shape,
            "target": "pcre2",
        }
        if warnings is not None:
            evidence["warnings"] = warnings
        return evidence
    if operation == "api.simply.literal_to_string":
        try:
            pattern = simply.lit(input_value["literal"])
            return {
                "emitted_pattern": str(pattern),
                "named_groups": list(pattern.named_groups),
                "node": pattern.node.to_dict(),
                "return_shape": "str",
            }
        except Exception as error:
            raise LegacySurfaceFailure("public_api", error) from error
    raise ProtocolError(
        "OPERATION_NOT_AVAILABLE",
        f"operation '{operation}' has no historical Python invocation",
    )


def observe_request(
    raw_request: Any,
    implementation: Mapping[str, Any] | None = None,
    invoke: Callable[[Mapping[str, Any]], Mapping[str, Any]] = invoke_python,
) -> dict[str, Any]:
    request = validate_request(raw_request)
    spec = OPERATION_SPECS[request["operation"]]
    identity = (
        canonicalize(dict(implementation))
        if implementation is not None
        else create_implementation_identity()
    )
    if not spec["exposed"]:
        outcome: dict[str, Any] = {
            "reason": spec["reason"],
            "status": "unsupported",
        }
    else:
        try:
            outcome = {
                "evidence": canonicalize(dict(invoke(request))),
                "status": "success",
            }
        except ProtocolError:
            raise
        except Exception as caught:
            wrapped = (
                caught
                if isinstance(caught, LegacySurfaceFailure)
                else LegacySurfaceFailure(spec["stage"], caught)
            )
            outcome = {
                "failure": project_legacy_failure(wrapped.error, wrapped.stage),
                "status": "legacy_failure",
            }
    return {
        "implementation": identity,
        "kind": OBSERVATION_KIND,
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "operation": request["operation"],
        "outcome": outcome,
        "protocol_version": PROTOCOL_VERSION,
        "request": {
            "algorithm": "sha256",
            "fingerprint": canonical_fingerprint(request),
            "value": request,
        },
        "runner": RUNNER,
        "surface": request["expected_legacy_surface"],
    }


def _validate_corpus(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError("INVALID_CORPUS", "reference corpus must be an object")
    _exact_keys(
        value,
        ("cases", "corpus_kind", "corpus_version", "description"),
        "corpus",
    )
    if value["corpus_kind"] != CORPUS_KIND:
        raise ProtocolError("INVALID_CORPUS", f"corpus_kind must be '{CORPUS_KIND}'")
    if value["corpus_version"] != CORPUS_VERSION:
        raise ProtocolError(
            "UNSUPPORTED_CORPUS_VERSION",
            f"corpus_version must be '{CORPUS_VERSION}'",
        )
    if not isinstance(value["description"], str) or not value["description"]:
        raise ProtocolError("INVALID_CORPUS", "description must be a non-empty string")
    if not isinstance(value["cases"], list) or not value["cases"]:
        raise ProtocolError("INVALID_CORPUS", "cases must be a non-empty array")

    cases = []
    ids: set[str] = set()
    operations: set[str] = set()
    for index, entry in enumerate(value["cases"]):
        location = f"cases/{index}"
        if not isinstance(entry, dict):
            raise ProtocolError("INVALID_CORPUS", f"{location} must be an object")
        _exact_keys(
            entry,
            ("behavior_family", "id", "provenance", "request"),
            location,
        )
        case_id = entry["id"]
        if (
            not isinstance(case_id, str)
            or not case_id
            or any(
                not part or not part.isalnum() or not part.islower()
                for part in case_id.split("-")
            )
        ):
            raise ProtocolError(
                "INVALID_CORPUS",
                f"{location}.id is not a stable kebab-case identifier",
            )
        if case_id in ids:
            raise ProtocolError("INVALID_CORPUS", f"duplicate case id '{case_id}'")
        ids.add(case_id)
        for key in ("behavior_family", "provenance"):
            if not isinstance(entry[key], str) or not entry[key]:
                raise ProtocolError(
                    "INVALID_CORPUS",
                    f"{location}.{key} must be a non-empty string",
                )
        request = validate_request(entry["request"])
        operations.add(request["operation"])
        cases.append(
            {
                "behavior_family": entry["behavior_family"],
                "id": case_id,
                "provenance": entry["provenance"],
                "request": request,
            }
        )
    missing = sorted(set(OPERATION_IDS) - operations)
    if missing:
        raise ProtocolError(
            "INCOMPLETE_CORPUS",
            f"corpus does not cover operations: {', '.join(missing)}",
        )
    corpus = {
        "cases": cases,
        "corpus_kind": CORPUS_KIND,
        "corpus_version": CORPUS_VERSION,
        "description": value["description"],
    }
    forbidden = (
        '"classification"',
        '"disposition"',
        '"expected_semantics"',
    )
    text = canonical_json(corpus)
    if any(marker in text for marker in forbidden):
        raise ProtocolError(
            "CORPUS_DISPOSITION",
            "corpus contains comparison disposition fields",
        )
    return corpus


def load_corpus(corpus_path: Path = DEFAULT_CORPUS_PATH) -> dict[str, Any]:
    try:
        parsed = json.loads(corpus_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProtocolError(
            "MALFORMED_CORPUS", "reference corpus is not valid JSON"
        ) from error
    return _validate_corpus(parsed)


def case_identity(
    entry: Mapping[str, Any], corpus_version: str = CORPUS_VERSION
) -> str:
    return canonical_fingerprint(
        {
            "case_id": entry["id"],
            "corpus_version": corpus_version,
            "request": entry["request"],
        }
    )


def execute_corpus(
    corpus: Mapping[str, Any],
    implementation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = implementation or create_implementation_identity()
    observations = []
    for entry in corpus["cases"]:
        observations.append(
            {
                "behavior_family": entry["behavior_family"],
                "case_id": entry["id"],
                "case_identity": case_identity(entry, corpus["corpus_version"]),
                "observation": observe_request(
                    entry["request"], implementation=identity
                ),
                "provenance": entry["provenance"],
            }
        )
    return {
        "batch_kind": BATCH_KIND,
        "batch_schema_version": BATCH_SCHEMA_VERSION,
        "corpus": {
            "algorithm": "sha256",
            "fingerprint": canonical_fingerprint(corpus),
            "version": corpus["corpus_version"],
        },
        "implementation": identity,
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "observations": observations,
        "protocol_version": PROTOCOL_VERSION,
        "runner": RUNNER,
    }


def certify_corpus(
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    repeat_runs: int = 3,
) -> dict[str, Any]:
    if isinstance(repeat_runs, bool) or repeat_runs < 2:
        raise ProtocolError(
            "INVALID_CERTIFICATION",
            "repeat_runs must be an integer of at least 2",
        )
    corpus_bytes_before = corpus_path.read_bytes()
    corpus = load_corpus(corpus_path)
    implementation = create_implementation_identity()
    batches = [
        execute_corpus(corpus, implementation=implementation)
        for _ in range(repeat_runs)
    ]
    lines = [canonical_line(batch) for batch in batches]
    mismatches = sum(line != lines[0] for line in lines)
    corpus_unchanged = sha256_bytes(corpus_bytes_before) == sha256_bytes(
        corpus_path.read_bytes()
    )
    implementation_after = create_implementation_identity()
    implementation_unchanged = canonical_line(implementation) == canonical_line(
        implementation_after
    )
    if not corpus_unchanged or not implementation_unchanged:
        raise ProtocolError(
            "REFERENCE_INPUT_MUTATION",
            (
                "reference execution modified the corpus or governed "
                "implementation inputs"
            ),
        )
    if mismatches:
        raise ProtocolError(
            "NONDETERMINISTIC_OBSERVATION",
            "repeat corpus executions produced different canonical observations",
        )

    first = batches[0]
    outcome_counts: dict[str, int] = {}
    operation_counts: dict[str, int] = {}
    for entry in first["observations"]:
        status = entry["observation"]["outcome"]["status"]
        outcome_counts[status] = outcome_counts.get(status, 0) + 1
        operation = entry["observation"]["operation"]
        operation_counts[operation] = operation_counts.get(operation, 0) + 1
    malformed_cases = sum(
        entry["behavior_family"] == "malformed-input" for entry in corpus["cases"]
    )
    return {
        "case_summaries": [
            {
                "case_id": entry["case_id"],
                "case_identity": entry["case_identity"],
                "observation_fingerprint": canonical_fingerprint(entry["observation"]),
                "operation": entry["observation"]["operation"],
                "outcome_status": entry["observation"]["outcome"]["status"],
                "repeat_equivalent": True,
            }
            for entry in first["observations"]
        ],
        "certification_kind": CERTIFICATION_KIND,
        "certification_schema_version": CERTIFICATION_SCHEMA_VERSION,
        "corpus": first["corpus"],
        "fixture_immutability": {
            "corpus_unchanged": corpus_unchanged,
            "governed_implementation_inputs_unchanged": (implementation_unchanged),
        },
        "implementation": implementation,
        "malformed_cases": malformed_cases,
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "operation_counts": operation_counts,
        "outcome_counts": outcome_counts,
        "protocol_version": PROTOCOL_VERSION,
        "repeatability": {
            "canonical_batches_compared": repeat_runs,
            "canonical_observations_compared": (len(corpus["cases"]) * repeat_runs),
            "mismatches": mismatches,
            "repeat_runs": repeat_runs,
        },
        "runner": RUNNER,
        "status": "passed",
        "unexplained_failures": 0,
    }


def protocol_failure(error: Exception) -> dict[str, Any]:
    normalized = (
        error
        if isinstance(error, ProtocolError)
        else ProtocolError("PROTOCOL_FAILURE", str(error))
    )
    return {
        "error": {
            "category": "protocol",
            "class": type(normalized).__name__,
            "code": normalized.code,
            "message": str(normalized),
        },
        "kind": PROTOCOL_FAILURE_KIND,
        "protocol_version": PROTOCOL_VERSION,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the controlled historical Python reference harness."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--request", type=Path)
    modes.add_argument("--corpus", action="store_true")
    modes.add_argument("--certify", action="store_true")
    return parser.parse_args(argv)


def _read_request(path: Path | None) -> Any:
    text = path.read_text(encoding="utf-8") if path is not None else sys.stdin.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ProtocolError("MALFORMED_JSON", "request is not valid JSON") from error


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.certify:
            sys.stdout.write(canonical_line(certify_corpus()))
            return 0
        corpus = load_corpus()
        if args.corpus:
            sys.stdout.write(canonical_line(execute_corpus(corpus)))
            return 0
        request = _read_request(args.request)
        sys.stdout.write(canonical_line(observe_request(request)))
        return 0
    except ProtocolError as error:
        sys.stderr.write(canonical_line(protocol_failure(error)))
        return 2
    except Exception:
        failure = ProtocolError(
            "RUNNER_FAILURE",
            "the historical Python reference runner could not complete",
        )
        sys.stderr.write(canonical_line(protocol_failure(failure)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
