"""Governed, source-identity-preserving embedded STRling extraction.

This module is a tooling coordinate adapter. It recognizes only literal forms
declared by ``spec/tooling/island_boundaries.json`` and never defines STRling
semantics, unfolds host escapes, interpolates values, or infers a target.
Missing, malformed, stale, or unsupported registry data fails closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple


_CONTRACT_VERSION = "1.0.0"
_REGISTRY_ID = "strling.tooling.island-boundaries"
_EXPECTED_HOSTS = (
    "strl",
    "c",
    "cpp",
    "csharp",
    "dart",
    "fsharp",
    "go",
    "java",
    "kotlin",
    "lua",
    "perl",
    "php",
    "python",
    "r",
    "ruby",
    "rust",
    "swift",
    "typescript",
)
_EXPECTED_LIMITS = {
    "boundary_expression_bytes": 1024,
    "comment_nesting": 64,
    "document_bytes": 1_048_576,
    "hosts": 18,
    "islands_per_document": 256,
    "literal_delimiter_bytes": 32,
    "literal_scan_bytes": 1_048_576,
    "mappings_per_document": 1_048_577,
    "per_host_boundaries": 16,
    "request_seconds": 5,
}
_SCANNERS = frozenset({"native", *_EXPECTED_HOSTS[1:]})
_LITERAL_KINDS = frozenset(
    {
        "double",
        "single",
        "triple_double",
        "triple_single",
        "template",
        "backtick_raw",
        "cpp_raw",
        "lua_long",
        "python_raw_double",
        "python_raw_single",
        "rust_raw",
        "swift_hashed",
    }
)


@dataclass(frozen=True)
class HostPosition:
    """A zero-based Unicode-scalar coordinate inside the host document."""

    line: int
    character: int


@dataclass
class Island:
    """One identity-mapped embedded STRling source unit."""

    virtual_content: str
    host_start: HostPosition
    line_offsets: List[HostPosition] = field(default_factory=list)
    line_lengths: List[int] = field(default_factory=list)
    boundary_call: str = ""

    def to_host(self, vd_line: int, vd_character: int) -> HostPosition:
        if not self.line_offsets:
            return self.host_start
        vd_line = min(max(vd_line, 0), len(self.line_offsets) - 1)
        lengths = self.line_lengths or [
            len(line) for line in self.virtual_content.split("\n")
        ]
        vd_character = min(max(vd_character, 0), lengths[vd_line])
        base = self.line_offsets[vd_line]
        return HostPosition(base.line, base.character + vd_character)

    def contains_host(self, line: int, character: int) -> bool:
        if not self.line_offsets:
            return False
        first = self.line_offsets[0]
        last_index = len(self.line_offsets) - 1
        last = self.line_offsets[last_index]
        lengths = self.line_lengths or [
            len(value) for value in self.virtual_content.split("\n")
        ]
        if line < first.line or line > last.line:
            return False
        if line == first.line and character < first.character:
            return False
        if line == last.line and character > last.character + lengths[last_index]:
            return False
        return True

    def from_host(self, line: int, character: int) -> Optional[Tuple[int, int]]:
        if not self.contains_host(line, character):
            return None
        for vd_line, base in enumerate(self.line_offsets):
            if base.line == line:
                return vd_line, max(0, character - base.character)
        return None


@dataclass(frozen=True)
class _Boundary:
    identity: str
    spelling: str
    expression: str
    compiled: Pattern[str]


@dataclass(frozen=True)
class _HostContract:
    language_id: str
    suffixes: Tuple[str, ...]
    frontend: str
    scanner: str
    line_comments: Tuple[str, ...]
    block_comments: Tuple[Tuple[str, str], ...]
    nested_comments: bool
    lua_long_bracket: bool
    boundaries: Tuple[_Boundary, ...]
    literal_forms: Dict[str, Dict[str, str]]


@dataclass(frozen=True)
class _Registry:
    hosts: Dict[str, _HostContract]
    suffixes: Dict[str, str]
    limits: Dict[str, int]
    fingerprint: str


@dataclass(frozen=True)
class _ScannedLiteral:
    kind: str
    content: str
    content_start: int
    content_end: int
    literal_end: int


_registry_cache: Optional[_Registry] = None
_registry_loaded = False
_registry_error: Optional[str] = None


def _candidate_registry_paths() -> List[Path]:
    paths: List[Path] = []
    override = os.environ.get("STRLING_ISLAND_BOUNDARIES_PATH")
    if override:
        paths.append(Path(override))
        return paths
    here = Path(__file__).resolve()
    for parent in (here, *here.parents)[:10]:
        candidate = parent / "spec" / "tooling" / "island_boundaries.json"
        if candidate.is_file():
            paths.append(candidate)
            break
    return paths


def _canonical_fingerprint(data: Dict[str, Any]) -> str:
    payload = dict(data)
    payload.pop("fingerprint", None)
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _exact_keys(value: Any, expected: set[str], label: str) -> Dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} has an invalid closed shape")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _validate_registry(data: Any) -> _Registry:
    root = _exact_keys(
        data,
        {
            "$schema",
            "contract_version",
            "registry_id",
            "source_model",
            "resource_limits",
            "hosts",
            "fingerprint",
        },
        "registry",
    )
    if root["$schema"] != "./island_boundaries.schema.json":
        raise ValueError("registry schema identity is invalid")
    if root["contract_version"] != _CONTRACT_VERSION:
        raise ValueError("unsupported registry version")
    if root["registry_id"] != _REGISTRY_ID:
        raise ValueError("registry identity is invalid")
    source_model = _exact_keys(
        root["source_model"],
        {
            "coordinate_system",
            "content_policy",
            "target_profile_policy",
            "native_language_id",
        },
        "source model",
    )
    if source_model != {
        "coordinate_system": "unicode-scalars",
        "content_policy": "identity_only",
        "target_profile_policy": "never_infer",
        "native_language_id": "strl",
    }:
        raise ValueError("source model is invalid")
    if root["resource_limits"] != _EXPECTED_LIMITS:
        raise ValueError("resource limits are invalid")
    fingerprint = _nonempty_string(root["fingerprint"], "fingerprint")
    if fingerprint != _canonical_fingerprint(root):
        raise ValueError("registry fingerprint mismatch")

    raw_hosts = root["hosts"]
    if not isinstance(raw_hosts, list) or len(raw_hosts) != _EXPECTED_LIMITS["hosts"]:
        raise ValueError("registry host count is invalid")
    host_ids = [
        host.get("language_id") if isinstance(host, dict) else None
        for host in raw_hosts
    ]
    if tuple(host_ids) != _EXPECTED_HOSTS or len(set(host_ids)) != len(host_ids):
        raise ValueError("registry hosts are duplicated or noncanonical")

    hosts: Dict[str, _HostContract] = {}
    suffixes: Dict[str, str] = {}
    boundary_ids: set[str] = set()
    literal_ids: set[str] = set()
    boundary_count = 0
    literal_count = 0
    for raw_host in raw_hosts:
        host = _exact_keys(
            raw_host,
            {
                "language_id",
                "suffixes",
                "frontend",
                "scanner",
                "target_profile_policy",
                "comments",
                "boundaries",
                "literal_forms",
            },
            "host",
        )
        language_id = _nonempty_string(host["language_id"], "language id")
        scanner = _nonempty_string(host["scanner"], "scanner")
        expected_scanner = "native" if language_id == "strl" else language_id
        if scanner not in _SCANNERS or scanner != expected_scanner:
            raise ValueError("unknown or mismatched scanner")
        frontend = host["frontend"]
        expected_frontend = "native" if language_id == "strl" else "regex"
        if frontend != expected_frontend:
            raise ValueError("host frontend is invalid")
        if host["target_profile_policy"] != "never_infer":
            raise ValueError("target profile inference is forbidden")

        raw_suffixes = host["suffixes"]
        if (
            not isinstance(raw_suffixes, list)
            or not raw_suffixes
            or raw_suffixes != sorted(raw_suffixes)
        ):
            raise ValueError("host suffixes are invalid or noncanonical")
        checked_suffixes: List[str] = []
        for suffix in raw_suffixes:
            if (
                not isinstance(suffix, str)
                or not re.fullmatch(r"\.[a-z0-9]+", suffix)
                or suffix in suffixes
            ):
                raise ValueError("registry suffix is invalid or duplicated")
            suffixes[suffix] = language_id
            checked_suffixes.append(suffix)

        comments = _exact_keys(
            host["comments"],
            {"line", "block", "nested", "lua_long_bracket"},
            "comments",
        )
        if not isinstance(comments["line"], list) or not all(
            isinstance(marker, str) and 0 < len(marker) <= 4
            for marker in comments["line"]
        ):
            raise ValueError("line comment declarations are invalid")
        if not isinstance(comments["block"], list):
            raise ValueError("block comment declarations are invalid")
        block_comments: List[Tuple[str, str]] = []
        for raw_pair in comments["block"]:
            pair = _exact_keys(raw_pair, {"open", "close"}, "block comment")
            opener = _nonempty_string(pair["open"], "block comment opener")
            closer = _nonempty_string(pair["close"], "block comment closer")
            if len(opener) > 4 or len(closer) > 4:
                raise ValueError("block comment delimiter is too long")
            block_comments.append((opener, closer))
        if not isinstance(comments["nested"], bool) or not isinstance(
            comments["lua_long_bracket"], bool
        ):
            raise ValueError("comment flags are invalid")

        raw_boundaries = host["boundaries"]
        if (
            not isinstance(raw_boundaries, list)
            or len(raw_boundaries) > _EXPECTED_LIMITS["per_host_boundaries"]
        ):
            raise ValueError("per-host boundary count is invalid")
        boundaries: List[_Boundary] = []
        for raw_boundary in raw_boundaries:
            boundary = _exact_keys(
                raw_boundary, {"id", "spelling", "expression"}, "boundary"
            )
            identity = _nonempty_string(boundary["id"], "boundary id")
            spelling = _nonempty_string(boundary["spelling"], "boundary spelling")
            expression = _nonempty_string(boundary["expression"], "boundary expression")
            if identity in boundary_ids:
                raise ValueError("duplicate boundary id")
            if (
                len(expression.encode("utf-8"))
                > _EXPECTED_LIMITS["boundary_expression_bytes"]
            ):
                raise ValueError("boundary expression is too long")
            try:
                compiled = re.compile(expression)
            except re.error as error:
                raise ValueError("invalid boundary expression") from error
            if compiled.match("") is not None:
                raise ValueError("boundary expression may not match empty input")
            boundary_ids.add(identity)
            boundaries.append(_Boundary(identity, spelling, expression, compiled))

        raw_forms = host["literal_forms"]
        if not isinstance(raw_forms, list):
            raise ValueError("literal forms are invalid")
        forms: Dict[str, Dict[str, str]] = {}
        for raw_form in raw_forms:
            form = _exact_keys(
                raw_form,
                {
                    "id",
                    "kind",
                    "content_policy",
                    "escape_policy",
                    "interpolation_policy",
                },
                "literal form",
            )
            identity = _nonempty_string(form["id"], "literal form id")
            kind = _nonempty_string(form["kind"], "literal kind")
            if identity in literal_ids or kind in forms or kind not in _LITERAL_KINDS:
                raise ValueError("literal form is duplicated or unknown")
            if (
                form["content_policy"] != "identity_only"
                or form["interpolation_policy"] != "forbid"
            ):
                raise ValueError("literal source policy is invalid")
            if form["escape_policy"] not in {"forbid", "raw_identity"}:
                raise ValueError("literal escape policy is invalid")
            literal_ids.add(identity)
            forms[kind] = dict(form)

        if language_id == "strl":
            if boundaries or forms:
                raise ValueError("native routing may not declare host literals")
        elif not boundaries or not forms:
            raise ValueError("host routing is incomplete")
        boundary_count += len(boundaries)
        literal_count += len(forms)
        hosts[language_id] = _HostContract(
            language_id=language_id,
            suffixes=tuple(checked_suffixes),
            frontend=frontend,
            scanner=scanner,
            line_comments=tuple(comments["line"]),
            block_comments=tuple(block_comments),
            nested_comments=comments["nested"],
            lua_long_bracket=comments["lua_long_bracket"],
            boundaries=tuple(boundaries),
            literal_forms=forms,
        )
    if len(suffixes) != 35 or boundary_count != 47 or literal_count != 36:
        raise ValueError("registry denominator is incomplete")
    return _Registry(hosts, suffixes, dict(_EXPECTED_LIMITS), fingerprint)


def _load_registry() -> Optional[_Registry]:
    global _registry_cache, _registry_loaded, _registry_error
    if _registry_loaded:
        return _registry_cache
    _registry_loaded = True
    paths = _candidate_registry_paths()
    if len(paths) != 1:
        _registry_error = "canonical island registry is unavailable"
        return None
    try:
        data = json.loads(paths[0].read_text(encoding="utf-8"))
        _registry_cache = _validate_registry(data)
        _registry_error = None
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        _registry_cache = None
        _registry_error = str(error)
    return _registry_cache


def reload_boundary_spec() -> None:
    """Clear the validated registry cache (primarily for mutation tests)."""

    global _registry_cache, _registry_loaded, _registry_error
    _registry_cache = None
    _registry_loaded = False
    _registry_error = None


def registry_status() -> Dict[str, Optional[str]]:
    registry = _load_registry()
    return {
        "status": "ready" if registry is not None else "unavailable",
        "fingerprint": registry.fingerprint if registry is not None else None,
        "error": _registry_error,
    }


def boundary_calls() -> Dict[str, List[str]]:
    registry = _load_registry()
    if registry is None:
        return {}
    return {
        language: [boundary.expression for boundary in host.boundaries]
        for language, host in registry.hosts.items()
        if host.boundaries
    }


def language_suffixes() -> Dict[str, str]:
    registry = _load_registry()
    return dict(registry.suffixes) if registry is not None else {}


def language_for_uri(uri: str) -> Optional[str]:
    lower = uri.lower()
    for suffix, language in sorted(
        language_suffixes().items(), key=lambda item: len(item[0]), reverse=True
    ):
        if lower.endswith(suffix):
            return language
    return None


def _scan_delimited(
    source: str,
    start: int,
    opener: str,
    closer: str,
    kind: str,
    *,
    escaped_delimiters: bool,
) -> Optional[_ScannedLiteral]:
    if not source.startswith(opener, start):
        return None
    content_start = start + len(opener)
    index = content_start
    while index < len(source):
        if escaped_delimiters and source[index] == "\\" and index + 1 < len(source):
            index += 2
            continue
        if source.startswith(closer, index):
            return _ScannedLiteral(
                kind,
                source[content_start:index],
                content_start,
                index,
                index + len(closer),
            )
        index += 1
    return None


def _scan_python(source: str, start: int) -> Optional[_ScannedLiteral]:
    if source.startswith(('f"', 'F"', "f'", "F'", 'fr"', 'rf"', "fr'", "rf'"), start):
        return None
    raw = False
    quote_start = start
    if start < len(source) and source[start] in "rR":
        raw = True
        quote_start += 1
    if quote_start >= len(source) or source[quote_start] not in {'"', "'"}:
        return None
    quote = source[quote_start]
    triple = source.startswith(quote * 3, quote_start)
    if raw and triple:
        return None
    if raw:
        kind = "python_raw_double" if quote == '"' else "python_raw_single"
        opener = source[start : quote_start + 1]
        return _scan_delimited(
            source, start, opener, quote, kind, escaped_delimiters=True
        )
    kind = (
        "triple_double"
        if triple and quote == '"'
        else "triple_single"
        if triple
        else "double"
        if quote == '"'
        else "single"
    )
    delimiter = quote * 3 if triple else quote
    return _scan_delimited(
        source, start, delimiter, delimiter, kind, escaped_delimiters=True
    )


def _scan_rust(source: str, start: int) -> Optional[_ScannedLiteral]:
    if start < len(source) and source[start] in "rR":
        index = start + 1
        while index < len(source) and source[index] == "#":
            index += 1
        if index - start - 1 > 30 or index >= len(source) or source[index] != '"':
            return None
        opener = source[start : index + 1]
        closer = '"' + ("#" * (index - start - 1))
        return _scan_delimited(
            source, start, opener, closer, "rust_raw", escaped_delimiters=False
        )
    return _scan_delimited(source, start, '"', '"', "double", escaped_delimiters=True)


_CPP_RAW_FORBIDDEN = set(" ()\\\t\n\r\v\f")


def _scan_cpp(source: str, start: int) -> Optional[_ScannedLiteral]:
    if source.startswith('R"', start):
        delimiter_start = start + 2
        index = delimiter_start
        while (
            index < len(source)
            and index - delimiter_start <= 16
            and source[index] not in _CPP_RAW_FORBIDDEN
            and source[index] != "("
        ):
            index += 1
        if index >= len(source) or source[index] != "(":
            return None
        delimiter = source[delimiter_start:index]
        opener = source[start : index + 1]
        closer = ")" + delimiter + '"'
        return _scan_delimited(
            source, start, opener, closer, "cpp_raw", escaped_delimiters=False
        )
    return _scan_delimited(source, start, '"', '"', "double", escaped_delimiters=True)


def _scan_swift(source: str, start: int) -> Optional[_ScannedLiteral]:
    if start < len(source) and source[start] == "#":
        index = start
        while index < len(source) and source[index] == "#":
            index += 1
        hashes = index - start
        if hashes > 30 or index >= len(source) or source[index] != '"':
            return None
        triple = source.startswith('"""', index)
        quotes = '"""' if triple else '"'
        opener = source[start : index + len(quotes)]
        closer = quotes + ("#" * hashes)
        return _scan_delimited(
            source, start, opener, closer, "swift_hashed", escaped_delimiters=False
        )
    if source.startswith('"""', start):
        return _scan_delimited(
            source, start, '"""', '"""', "triple_double", escaped_delimiters=True
        )
    return _scan_delimited(source, start, '"', '"', "double", escaped_delimiters=True)


def _scan_lua_long(source: str, start: int) -> Optional[_ScannedLiteral]:
    if start >= len(source) or source[start] != "[":
        return None
    index = start + 1
    while index < len(source) and source[index] == "=":
        index += 1
    equals = index - start - 1
    if equals > 28 or index >= len(source) or source[index] != "[":
        return None
    opener = source[start : index + 1]
    closer = "]" + ("=" * equals) + "]"
    return _scan_delimited(
        source, start, opener, closer, "lua_long", escaped_delimiters=False
    )


def _scan_literal(source: str, start: int, scanner: str) -> Optional[_ScannedLiteral]:
    if scanner == "python":
        return _scan_python(source, start)
    if scanner == "rust":
        return _scan_rust(source, start)
    if scanner == "cpp":
        return _scan_cpp(source, start)
    if scanner == "swift":
        return _scan_swift(source, start)
    if scanner == "lua" and start < len(source) and source[start] == "[":
        return _scan_lua_long(source, start)
    if scanner == "go" and start < len(source) and source[start] == "`":
        return _scan_delimited(
            source, start, "`", "`", "backtick_raw", escaped_delimiters=False
        )
    if scanner == "typescript" and start < len(source) and source[start] == "`":
        return _scan_delimited(
            source, start, "`", "`", "template", escaped_delimiters=True
        )
    if start < len(source) and source[start] == '"':
        return _scan_delimited(
            source, start, '"', '"', "double", escaped_delimiters=True
        )
    if start < len(source) and source[start] == "'":
        return _scan_delimited(
            source, start, "'", "'", "single", escaped_delimiters=True
        )
    return None


def _skip_comment(
    source: str, start: int, host: _HostContract, limit: int
) -> Optional[int]:
    if host.lua_long_bracket and source.startswith("--", start):
        scanned = _scan_lua_long(source, start + 2)
        if scanned is not None:
            return scanned.literal_end
    for marker in host.line_comments:
        if source.startswith(marker, start):
            end = source.find("\n", start)
            return len(source) if end < 0 else end
    for opener, closer in host.block_comments:
        if not source.startswith(opener, start):
            continue
        index = start + len(opener)
        depth = 1
        while index < len(source):
            if host.nested_comments and source.startswith(opener, index):
                depth += 1
                if depth > limit:
                    return len(source)
                index += len(opener)
            elif source.startswith(closer, index):
                depth -= 1
                index += len(closer)
                if depth == 0:
                    return index
            else:
                index += 1
        return len(source)
    return None


def _skip_non_code(
    source: str, start: int, host: _HostContract, limit: int
) -> Optional[int]:
    comment_end = _skip_comment(source, start, host, limit)
    if comment_end is not None:
        return comment_end
    scanned = _scan_literal(source, start, host.scanner)
    return scanned.literal_end if scanned is not None else None


def _interpolates(language: str, kind: str, content: str) -> bool:
    if language == "typescript" and "${" in content:
        return True
    if language == "swift" and re.search(r"\\#*\(", content):
        return True
    if language == "ruby" and kind == "double" and "#{" in content:
        return True
    if language in {"dart", "kotlin"} or (
        language in {"php", "perl"} and kind == "double"
    ):
        return re.search(r"\$(?:\{|[A-Za-z_])", content) is not None
    return False


def _identity_safe(
    source: str, scanned: _ScannedLiteral, host: _HostContract, limit: int
) -> bool:
    form = host.literal_forms.get(scanned.kind)
    if form is None or len(scanned.content.encode("utf-8")) > limit:
        return False
    if form["escape_policy"] == "forbid" and "\\" in scanned.content:
        return False
    if _interpolates(host.language_id, scanned.kind, scanned.content):
        return False
    if (
        host.language_id == "go"
        and scanned.kind == "backtick_raw"
        and "\r" in scanned.content
    ):
        return False
    if (
        host.language_id == "lua"
        and scanned.kind == "lua_long"
        and scanned.content.startswith(("\n", "\r\n"))
    ):
        return False
    return source[scanned.content_start : scanned.content_end] == scanned.content


def _offset_to_position(source: str, offset: int) -> HostPosition:
    prefix = source[: max(0, offset)]
    line = prefix.count("\n")
    last_newline = prefix.rfind("\n")
    return HostPosition(
        line, len(prefix) if last_newline < 0 else len(prefix) - last_newline - 1
    )


def _line_offsets(content: str, start: HostPosition) -> List[HostPosition]:
    offsets = [start]
    line = start.line
    for character in content:
        if character == "\n":
            line += 1
            offsets.append(HostPosition(line, 0))
    return offsets


def _native_line_islands(source: str) -> List[Island]:
    return [
        Island(
            line, HostPosition(index, 0), [HostPosition(index, 0)], [len(line)], ".strl"
        )
        for index, line in enumerate(source.splitlines())
    ]


def _is_concatenated(source: str, literal_end: int, host: _HostContract) -> bool:
    index = literal_end
    while index < len(source) and source[index].isspace():
        index += 1
    if index < len(source) and source[index] == "+":
        return True
    return _scan_literal(source, index, host.scanner) is not None


def extract_islands(source: str, language: str) -> List[Island]:
    """Extract declared identity-mapped literals, or return no islands."""

    registry = _load_registry()
    if (
        registry is None
        or len(source.encode("utf-8")) > registry.limits["document_bytes"]
    ):
        return []
    host = registry.hosts.get(language)
    if host is None:
        return []
    if language == "strl":
        islands = _native_line_islands(source)
        return (
            islands if len(islands) <= registry.limits["islands_per_document"] else []
        )

    islands: List[Island] = []
    index = 0
    while index < len(source):
        skipped = _skip_non_code(
            source, index, host, registry.limits["comment_nesting"]
        )
        if skipped is not None:
            index = max(index + 1, skipped)
            continue
        matched = False
        for boundary in host.boundaries:
            match = boundary.compiled.match(source, index)
            if match is None:
                continue
            literal_start = match.end()
            if any(
                candidate.compiled.match(source, literal_start) is not None
                for candidate in host.boundaries
            ):
                return []
            scanned = _scan_literal(source, literal_start, host.scanner)
            if scanned is None:
                continue
            matched = True
            index = scanned.literal_end
            if not _identity_safe(
                source, scanned, host, registry.limits["literal_scan_bytes"]
            ) or _is_concatenated(source, scanned.literal_end, host):
                break
            start = _offset_to_position(source, scanned.content_start)
            offsets = _line_offsets(scanned.content, start)
            if (
                sum(len(value) + 1 for value in scanned.content.split("\n"))
                > registry.limits["mappings_per_document"]
            ):
                return []
            islands.append(
                Island(
                    virtual_content=scanned.content,
                    host_start=start,
                    line_offsets=offsets,
                    line_lengths=[len(value) for value in scanned.content.split("\n")],
                    boundary_call=boundary.spelling,
                )
            )
            if len(islands) > registry.limits["islands_per_document"]:
                return []
            break
        if not matched:
            index += 1
    return islands


def extract_islands_for_uri(source: str, uri: str) -> List[Island]:
    language = language_for_uri(uri)
    return extract_islands(source, language) if language is not None else []


__all__ = [
    "HostPosition",
    "Island",
    "boundary_calls",
    "extract_islands",
    "extract_islands_for_uri",
    "language_for_uri",
    "language_suffixes",
    "registry_status",
    "reload_boundary_spec",
]
