#!/usr/bin/env python3
"""Execute the shared versioned PCRE2 feature corpus through the exact 8-bit ABI."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PCRE2_CONFIG_VERSION = 11
PCRE2_ERROR_NOMATCH = -1
PCRE2_ERROR_MATCHLIMIT = -47
PCRE2_ERROR_DEPTHLIMIT = -53
PCRE2_ERROR_HEAPLIMIT = -63
PCRE2_INFO_CAPTURECOUNT = 4
PCRE2_INFO_NAMECOUNT = 17
PCRE2_INFO_NAMEENTRYSIZE = 18
PCRE2_INFO_NAMETABLE = 19
PCRE2_MULTILINE = 0x00000400
PCRE2_UCP = 0x00020000
PCRE2_UTF = 0x00080000
PCRE2_NEWLINE_ANY = 4
SUPPORTED_OPTIONS = {
    "pcre2.matcher_api",
    "pcre2.max_variable_lookbehind",
    "pcre2.multiline",
    "pcre2.newline",
    "pcre2.ucp",
    "pcre2.utf",
}


@dataclass(frozen=True)
class EngineConfiguration:
    compile_options: int
    matcher_api: str
    maximum_variable_lookbehind: int | None
    newline: int | None


@dataclass(frozen=True)
class MatchLimits:
    match: int
    depth: int
    heap_kib: int

    def __post_init__(self) -> None:
        for name, value in (
            ("match", self.match),
            ("depth", self.depth),
            ("heap_kib", self.heap_kib),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} limit must be a positive integer")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def profile_configuration(profile: Mapping[str, Any]) -> EngineConfiguration:
    options = {item["option_id"]: item["value"] for item in profile.get("options", [])}
    unknown = sorted(set(options) - SUPPORTED_OPTIONS)
    if unknown:
        raise ValueError(f"unsupported PCRE2 probe option(s): {', '.join(unknown)}")
    if options.get("pcre2.matcher_api") != "pcre2_match":
        raise ValueError("probe requires explicit pcre2.matcher_api=pcre2_match")

    compile_options = 0
    if options.get("pcre2.multiline") is True:
        compile_options |= PCRE2_MULTILINE
    elif "pcre2.multiline" in options:
        raise ValueError("pcre2.multiline must be true")
    if options.get("pcre2.ucp") is True:
        compile_options |= PCRE2_UCP
    elif "pcre2.ucp" in options:
        raise ValueError("pcre2.ucp must be true")
    if options.get("pcre2.utf") is True:
        compile_options |= PCRE2_UTF
    elif "pcre2.utf" in options:
        raise ValueError("pcre2.utf must be true")

    newline = None
    if "pcre2.newline" in options:
        if options["pcre2.newline"] != "any":
            raise ValueError("probe supports only explicit pcre2.newline=any")
        newline = PCRE2_NEWLINE_ANY

    maximum = options.get("pcre2.max_variable_lookbehind")
    if maximum is not None and (
        isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0
    ):
        raise ValueError("pcre2.max_variable_lookbehind must be a non-negative integer")

    return EngineConfiguration(
        compile_options=compile_options,
        matcher_api="pcre2_match",
        maximum_variable_lookbehind=maximum,
        newline=newline,
    )


class Engine:
    def __init__(self, library: Path):
        self.lib = ctypes.CDLL(str(library))
        self.config = self.lib.pcre2_config_8
        self.config.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        self.config.restype = ctypes.c_int

        self.compile_context_create = self.lib.pcre2_compile_context_create_8
        self.compile_context_create.argtypes = [ctypes.c_void_p]
        self.compile_context_create.restype = ctypes.c_void_p
        self.compile_context_free = self.lib.pcre2_compile_context_free_8
        self.compile_context_free.argtypes = [ctypes.c_void_p]
        self.compile_context_free.restype = None
        self.set_newline = self.lib.pcre2_set_newline_8
        self.set_newline.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.set_newline.restype = ctypes.c_int
        self.set_maximum = getattr(self.lib, "pcre2_set_max_varlookbehind_8", None)
        if self.set_maximum is not None:
            self.set_maximum.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            self.set_maximum.restype = ctypes.c_int

        self.compile = self.lib.pcre2_compile_8
        self.compile.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_void_p,
        ]
        self.compile.restype = ctypes.c_void_p
        self.code_free = self.lib.pcre2_code_free_8
        self.code_free.argtypes = [ctypes.c_void_p]
        self.code_free.restype = None
        self.pattern_info = self.lib.pcre2_pattern_info_8
        self.pattern_info.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        self.pattern_info.restype = ctypes.c_int

        self.match_data_create = self.lib.pcre2_match_data_create_from_pattern_8
        self.match_data_create.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.match_data_create.restype = ctypes.c_void_p
        self.match_data_free = self.lib.pcre2_match_data_free_8
        self.match_data_free.argtypes = [ctypes.c_void_p]
        self.match_data_free.restype = None
        self.ovector_pointer = self.lib.pcre2_get_ovector_pointer_8
        self.ovector_pointer.argtypes = [ctypes.c_void_p]
        self.ovector_pointer.restype = ctypes.POINTER(ctypes.c_size_t)
        self.match_context_create = self.lib.pcre2_match_context_create_8
        self.match_context_create.argtypes = [ctypes.c_void_p]
        self.match_context_create.restype = ctypes.c_void_p
        self.match_context_free = self.lib.pcre2_match_context_free_8
        self.match_context_free.argtypes = [ctypes.c_void_p]
        self.match_context_free.restype = None
        self.set_match_limit = self.lib.pcre2_set_match_limit_8
        self.set_match_limit.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.set_match_limit.restype = ctypes.c_int
        self.set_depth_limit = self.lib.pcre2_set_depth_limit_8
        self.set_depth_limit.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.set_depth_limit.restype = ctypes.c_int
        self.set_heap_limit = self.lib.pcre2_set_heap_limit_8
        self.set_heap_limit.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.set_heap_limit.restype = ctypes.c_int
        self.match = self.lib.pcre2_match_8
        self.match.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.match.restype = ctypes.c_int

    def version(self) -> str:
        target = ctypes.create_string_buffer(64)
        result = self.config(PCRE2_CONFIG_VERSION, target)
        if result < 0:
            raise RuntimeError(f"pcre2_config failed: {result}")
        return target.value.decode("ascii")

    @staticmethod
    def _buffer(value: str) -> tuple[Any, ctypes.POINTER(ctypes.c_uint8), int]:
        encoded = value.encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded, len(encoded) + 1)
        pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8))
        return buffer, pointer, len(encoded)

    def run_case(
        self,
        pattern: str,
        observations: Sequence[Mapping[str, Any]],
        configuration: EngineConfiguration,
    ) -> dict[str, Any]:
        context = self.compile_context_create(None)
        if not context:
            raise RuntimeError("PCRE2 compile-context allocation failed")
        try:
            if configuration.newline is not None:
                result = self.set_newline(context, configuration.newline)
                if result != 0:
                    raise RuntimeError(f"pcre2_set_newline failed: {result}")
            if configuration.maximum_variable_lookbehind is not None:
                if self.set_maximum is None:
                    raise RuntimeError(
                        "selected profile requires pcre2_set_max_varlookbehind"
                    )
                result = self.set_maximum(
                    context, configuration.maximum_variable_lookbehind
                )
                if result != 0:
                    raise RuntimeError(f"pcre2_set_max_varlookbehind failed: {result}")

            _pattern_buffer, pattern_pointer, pattern_length = self._buffer(pattern)
            error_code = ctypes.c_int()
            error_offset = ctypes.c_size_t()
            code = self.compile(
                pattern_pointer,
                pattern_length,
                configuration.compile_options,
                ctypes.byref(error_code),
                ctypes.byref(error_offset),
                context,
            )
            if not code:
                return {
                    "compile": "error",
                    "error_code": error_code.value,
                    "error_offset": error_offset.value,
                    "matches": [],
                }
            try:
                results = []
                for observation in observations:
                    subject = observation["subject"]
                    _subject_buffer, subject_pointer, subject_length = self._buffer(
                        subject
                    )
                    match_data = self.match_data_create(code, None)
                    if not match_data:
                        raise RuntimeError("PCRE2 match-data allocation failed")
                    try:
                        result = self.match(
                            code,
                            subject_pointer,
                            subject_length,
                            0,
                            0,
                            match_data,
                            None,
                        )
                    finally:
                        self.match_data_free(match_data)
                    results.append({"subject": subject, "matched": result >= 0})
                return {"compile": "ok", "matches": results}
            finally:
                self.code_free(code)
        finally:
            self.compile_context_free(context)

    def _pattern_u32(self, code: int, selector: int) -> int:
        value = ctypes.c_uint32()
        result = self.pattern_info(code, selector, ctypes.byref(value))
        if result != 0:
            raise RuntimeError(f"pcre2_pattern_info({selector}) failed: {result}")
        return value.value

    def _capture_names(self, code: int) -> dict[int, str]:
        name_count = self._pattern_u32(code, PCRE2_INFO_NAMECOUNT)
        if name_count == 0:
            return {}
        entry_size = self._pattern_u32(code, PCRE2_INFO_NAMEENTRYSIZE)
        table = ctypes.c_void_p()
        result = self.pattern_info(
            code,
            PCRE2_INFO_NAMETABLE,
            ctypes.byref(table),
        )
        if result != 0 or table.value is None:
            raise RuntimeError(
                f"pcre2_pattern_info({PCRE2_INFO_NAMETABLE}) failed: {result}"
            )
        names: dict[int, str] = {}
        for index in range(name_count):
            entry = ctypes.string_at(table.value + index * entry_size, entry_size)
            capture_index = (entry[0] << 8) | entry[1]
            names[capture_index] = entry[2:].split(b"\0", 1)[0].decode("utf-8")
        return names

    def _create_match_context(self, limits: MatchLimits) -> int:
        context = self.match_context_create(None)
        if not context:
            raise RuntimeError("PCRE2 match-context allocation failed")
        setters = (
            ("match", self.set_match_limit, limits.match),
            ("depth", self.set_depth_limit, limits.depth),
            ("heap", self.set_heap_limit, limits.heap_kib),
        )
        for name, setter, value in setters:
            result = setter(context, value)
            if result != 0:
                self.match_context_free(context)
                raise RuntimeError(f"pcre2_set_{name}_limit failed: {result}")
        return context

    @staticmethod
    def _match_outcome(result: int) -> str:
        return {
            PCRE2_ERROR_NOMATCH: "no_match",
            PCRE2_ERROR_MATCHLIMIT: "match_limit",
            PCRE2_ERROR_DEPTHLIMIT: "depth_limit",
            PCRE2_ERROR_HEAPLIMIT: "heap_limit",
        }.get(result, "match" if result >= 0 else "error")

    def run_detailed_case(
        self,
        pattern: str,
        observations: Sequence[Mapping[str, Any]],
        configuration: EngineConfiguration,
        limits: MatchLimits,
    ) -> dict[str, Any]:
        """Compile once and expose bounded match, span, and capture observations."""

        context = self.compile_context_create(None)
        if not context:
            raise RuntimeError("PCRE2 compile-context allocation failed")
        try:
            if configuration.newline is not None:
                result = self.set_newline(context, configuration.newline)
                if result != 0:
                    raise RuntimeError(f"pcre2_set_newline failed: {result}")
            if configuration.maximum_variable_lookbehind is not None:
                if self.set_maximum is None:
                    raise RuntimeError(
                        "selected profile requires pcre2_set_max_varlookbehind"
                    )
                result = self.set_maximum(
                    context, configuration.maximum_variable_lookbehind
                )
                if result != 0:
                    raise RuntimeError(f"pcre2_set_max_varlookbehind failed: {result}")

            _pattern_buffer, pattern_pointer, pattern_length = self._buffer(pattern)
            error_code = ctypes.c_int()
            error_offset = ctypes.c_size_t()
            code = self.compile(
                pattern_pointer,
                pattern_length,
                configuration.compile_options,
                ctypes.byref(error_code),
                ctypes.byref(error_offset),
                context,
            )
            if not code:
                return {
                    "compile": "error",
                    "error_code": error_code.value,
                    "error_offset": error_offset.value,
                    "captures": [],
                    "matches": [],
                }
            try:
                capture_count = self._pattern_u32(code, PCRE2_INFO_CAPTURECOUNT)
                capture_names = self._capture_names(code)
                results = []
                for observation in observations:
                    subject = observation["subject"]
                    subject_bytes = subject.encode("utf-8")
                    _subject_buffer, subject_pointer, subject_length = self._buffer(
                        subject
                    )
                    match_data = self.match_data_create(code, None)
                    if not match_data:
                        raise RuntimeError("PCRE2 match-data allocation failed")
                    match_context = self._create_match_context(limits)
                    try:
                        result = self.match(
                            code,
                            subject_pointer,
                            subject_length,
                            0,
                            0,
                            match_data,
                            match_context,
                        )
                        outcome = self._match_outcome(result)
                        captures = []
                        if result >= 0:
                            ovector = self.ovector_pointer(match_data)
                            unset = ctypes.c_size_t(-1).value
                            for capture_index in range(capture_count + 1):
                                start = ovector[2 * capture_index]
                                end = ovector[2 * capture_index + 1]
                                item: dict[str, Any] = {"index": capture_index}
                                if capture_index in capture_names:
                                    item["name"] = capture_names[capture_index]
                                if start == unset or end == unset:
                                    item.update({"span": None, "value": None})
                                else:
                                    item.update(
                                        {
                                            "span": [start, end],
                                            "value": subject_bytes[start:end].decode(
                                                "utf-8"
                                            ),
                                        }
                                    )
                                captures.append(item)
                        results.append(
                            {
                                "subject": subject,
                                "outcome": outcome,
                                "return_code": result,
                                "span": captures[0]["span"] if captures else None,
                                "captures": captures,
                            }
                        )
                    finally:
                        self.match_context_free(match_context)
                        self.match_data_free(match_data)
                return {
                    "compile": "ok",
                    "captures": [
                        {
                            "index": index,
                            **(
                                {"name": capture_names[index]}
                                if index in capture_names
                                else {}
                            ),
                        }
                        for index in range(capture_count + 1)
                    ],
                    "matches": results,
                }
            finally:
                self.code_free(code)
        finally:
            self.compile_context_free(context)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_probe(
    fixture_path: Path,
    profile_path: Path,
    library_path: Path,
    engine_factory: Callable[[Path], Engine] = Engine,
) -> dict[str, Any]:
    fixture = load_json(fixture_path)
    profile = load_json(profile_path)
    configuration = profile_configuration(profile)
    expected_version = profile["engine"]["version"]["value"]
    profile_id = profile["profile_id"]
    if profile_id != f"profile:pcre2/{expected_version}":
        raise ValueError("profile identity and engine version disagree")
    if expected_version not in fixture["profiles"]:
        raise ValueError(f"fixture does not declare profile {expected_version}")

    engine = engine_factory(library_path)
    engine_version = engine.version()
    if engine_version.split()[0] != expected_version:
        raise ValueError(
            f"loaded PCRE2 version {engine_version!r} does not match {expected_version}"
        )

    results = []
    for case in fixture["cases"]:
        expectation = case["profiles"][expected_version]
        actual = engine.run_case(case["pattern"], expectation["matches"], configuration)
        if actual["compile"] != expectation["compile"]:
            raise AssertionError(
                f"{case['id']}: expected compile={expectation['compile']}, "
                f"observed {actual['compile']}"
            )
        if actual["compile"] == "ok" and actual["matches"] != expectation["matches"]:
            raise AssertionError(
                f"{case['id']}: direct match observations differ: {actual['matches']!r}"
            )
        results.append(
            {
                "id": case["id"],
                "profile_status": expectation["status"],
                **actual,
            }
        )

    evidence = {
        "probe_version": "1.0.0",
        "profile": {
            "profile_id": profile_id,
            "profile_version": profile["profile_version"],
            "sha256": canonical_digest(profile),
        },
        "engine_version": engine_version,
        "library_sha256": file_digest(library_path),
        "fixture_sha256": canonical_digest(fixture),
        "configuration": {
            "compile_options": configuration.compile_options,
            "matcher_api": configuration.matcher_api,
            "maximum_variable_lookbehind": (configuration.maximum_variable_lookbehind),
            "newline": configuration.newline,
        },
        "cases": results,
    }
    return {**evidence, "result_sha256": canonical_digest(evidence)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    evidence = run_probe(args.fixture, args.profile, args.library)
    serialized = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if args.output is None:
        print(serialized)
    else:
        args.output.write_text(serialized + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
