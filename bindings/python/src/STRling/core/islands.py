"""
Module Pedagogy:
================
This module is the canonical home of STRling's "Island Grammar" extractor.
Host-language source files (TypeScript, Python, Rust, Java) embed STRling
patterns inside string-literal arguments to well-known boundary calls such
as ``s.parse("...")`` or ``strl.simply.parse(`...`)``. The extractor here
finds those literals, captures their *raw* characters (no escape unfolding,
so a 1:1 host↔virtual coordinate mapping holds), and emits ``Island``
objects that the language-intelligence layer feeds to the parser.

The boundary-call regexes and the language-suffix routing table are NOT
defined here — they live in ``spec/tooling/island_boundaries.json`` so the
Python language-intelligence layer and the Node test extractor read from a
single source of truth. This module owns the *algorithm* (literal scanning,
coordinate mirroring); the JSON owns the *registry* (which calls open an
island, which suffixes pick which language).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Public data structures                                                      #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HostPosition:
    """A zero-based ``(line, character)`` coordinate inside the host file."""

    line: int
    character: int


@dataclass
class Island:
    """A single embedded STRling pattern extracted from a host document.

    Attributes
    ----------
    virtual_content : str
        Raw string-literal content (no unescaping) — fed to the parser.
    host_start : HostPosition
        Coordinate of the *first* character of ``virtual_content`` in the
        host file.
    line_offsets : List[HostPosition]
        ``line_offsets[v]`` gives the host ``(line, character)`` where the
        ``v``-th virtual line begins. Index 0 always equals ``host_start``.
    boundary_call : str
        The boundary expression that introduced the island (e.g. ``s.parse``).
        Useful for hover provenance and debug logging.
    """

    virtual_content: str
    host_start: HostPosition
    line_offsets: List[HostPosition] = field(default_factory=lambda: [])
    line_lengths: List[int] = field(default_factory=lambda: [])
    boundary_call: str = ""

    def to_host(self, vd_line: int, vd_character: int) -> HostPosition:
        """Project a virtual-document position back onto the host file."""
        if not self.line_offsets:
            return self.host_start
        if vd_line < 0:
            vd_line = 0
        lines = self.virtual_content.split("\n")
        if vd_line >= len(self.line_offsets):
            vd_line = len(self.line_offsets) - 1
        line_lengths = self.line_lengths or [len(line) for line in lines]
        line_len = line_lengths[vd_line] if vd_line < len(line_lengths) else 0
        if vd_character < 0:
            vd_character = 0
        if vd_character > line_len:
            vd_character = line_len
        base = self.line_offsets[vd_line]
        # The per-line host offset already points at the first raw character
        # for that virtual line, so the clamped virtual character can be
        # added directly.
        host_char = base.character + vd_character
        return HostPosition(line=base.line, character=host_char)

    def contains_host(self, line: int, character: int) -> bool:
        """Return True if a host coordinate lies inside this island."""
        if not self.line_offsets:
            return False
        last_line_idx = len(self.line_offsets) - 1
        last_base = self.line_offsets[last_line_idx]
        line_lengths = self.line_lengths or [
            len(line) for line in self.virtual_content.split("\n")
        ]
        last_len = (
            line_lengths[last_line_idx] if last_line_idx < len(line_lengths) else 0
        )
        last_end_char = last_base.character + last_len

        first = self.line_offsets[0]
        if line < first.line or line > last_base.line:
            return False
        if line == first.line and character < first.character:
            return False
        if line == last_base.line and character > last_end_char:
            return False
        return True

    def from_host(self, line: int, character: int) -> Optional[Tuple[int, int]]:
        """Inverse of :meth:`to_host`. Returns ``None`` if outside the island."""
        if not self.contains_host(line, character):
            return None
        for vd_line, base in enumerate(self.line_offsets):
            if base.line == line:
                vd_char = character - base.character if vd_line == 0 else character
                return (vd_line, max(0, vd_char))
        return None


# --------------------------------------------------------------------------- #
# Boundary registry — loaded from spec/tooling/island_boundaries.json         #
# --------------------------------------------------------------------------- #


# Built-in fallback used when the spec JSON cannot be located (e.g. when the
# package is installed outside the repository tree). Keeping the fallback
# here means installed users still get correct island extraction even if the
# spec file is missing — they only lose the ability to amend boundaries
# without a code change.
_DEFAULT_BOUNDARIES: Dict[str, List[str]] = {
    "python": [
        r"\bs\.parse\s*\(\s*",
        r"\bstrl\.parse\s*\(\s*",
        r"\bSTRling\.parse\s*\(\s*",
        r"\bPattern\s*\(\s*",
    ],
    "typescript": [
        r"\bstrl\.simply\.parse\s*\(\s*",
        r"\bsimply\.parse\s*\(\s*",
        r"\bstrl\.parse\s*\(\s*",
        r"\bs\.parse\s*\(\s*",
        r"\bSTRling\.parse\s*\(\s*",
        r"\bnew\s+Pattern\s*\(\s*",
    ],
    "rust": [
        r"\bstrling::parse!\s*\(\s*",
        r"\bstrl::parse\s*\(\s*",
        r"\bstrling::Pattern::new\s*\(\s*",
    ],
    "java": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bSTRlingPattern\s*\.\s*compile\s*\(\s*",
    ],
    "c": [
        r"\bstrling_parse\s*\(\s*",
        r"\bstrling_compile\s*\(\s*",
    ],
    "cpp": [
        r"\bstrling::parse\s*\(\s*",
        r"\bstrling::Parser::parse\s*\(\s*",
        r"\bparser\.parse\s*\(\s*",
    ],
    "csharp": [
        r"\bSTRling\.Parse\s*\(\s*",
        r"\bStrling\.Parse\s*\(\s*",
        r"\bSTRling\.Parser\.Parse\s*\(\s*",
    ],
    "fsharp": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bParser\.parse\s*\(\s*",
    ],
    "go": [
        r"\bstrling\.Parse\s*\(\s*",
        r"\bcore\.Parse\s*\(\s*",
        r"\bstrling\.MustParse\s*\(\s*",
    ],
    "kotlin": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bStrling\.parse\s*\(\s*",
        r"\bParser\.parse\s*\(\s*",
    ],
    "swift": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bStrling\.parse\s*\(\s*",
        r"\bParser\.parse\s*\(\s*",
    ],
    "dart": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bStrling\.parse\s*\(\s*",
    ],
    "php": [
        r"\bSTRling::parse\s*\(\s*",
        r"\bStrling\\Core\\Parser::parse\s*\(\s*",
        r"\\STRling::parse\s*\(\s*",
    ],
    "ruby": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bStrling\.parse\s*\(\s*",
        r"\bStrling::Core::Parser\.parse\s*\(\s*",
    ],
    "perl": [
        r"\bSTRling::parse\s*\(\s*",
        r"\bSTRling->parse\s*\(\s*",
    ],
    "lua": [
        r"\bstrling\.parse\s*\(\s*",
    ],
    "r": [
        r"\bstrling_parse\s*\(\s*",
        r"\bstrling::parse\s*\(\s*",
    ],
}

_DEFAULT_LANGUAGE_BY_SUFFIX: Dict[str, str] = {
    ".strl": "strl",
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".cs": "csharp",
    ".fs": "fsharp",
    ".fsi": "fsharp",
    ".fsx": "fsharp",
    ".go": "go",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".dart": "dart",
    ".php": "php",
    ".rb": "ruby",
    ".pl": "perl",
    ".pm": "perl",
    ".t": "perl",
    ".lua": "lua",
    ".r": "r",
    ".R": "r",
}


# Cache of the most recently loaded spec so we do not pay disk I/O per
# extraction call. The cache key is the resolved spec path (or ``None``
# when the fallback is in use).
_boundary_cache: Optional[Dict[str, List[str]]] = None
_suffix_cache: Optional[Dict[str, str]] = None
_spec_path_cache: Optional[Path] = None


def _candidate_spec_paths() -> List[Path]:
    """Return the ordered list of paths to probe for the boundary spec.

    Priority (highest first):

    1. ``$STRLING_ISLAND_BOUNDARIES_PATH`` — explicit override for tooling
       and tests that want to point at a non-default spec file.
    2. Repository-root ``spec/tooling/island_boundaries.json`` — discovered
       by walking up from this file. This is the path used during normal
       in-tree development, including the LSP server and the CLI tools.
    """
    paths: List[Path] = []
    env_override = os.environ.get("STRLING_ISLAND_BOUNDARIES_PATH")
    if env_override:
        paths.append(Path(env_override))

    # Walk up from this module until we hit a directory that contains the
    # canonical spec layout. Stop after a reasonable number of parents so we
    # do not scan the filesystem root in pathological install scenarios.
    here = Path(__file__).resolve()
    for parent in (here, *here.parents)[:10]:
        candidate = parent / "spec" / "tooling" / "island_boundaries.json"
        if candidate.is_file():
            paths.append(candidate)
            break
    return paths


def _load_spec() -> Tuple[Dict[str, List[str]], Dict[str, str], Optional[Path]]:
    """Load and cache the shared boundary registry.

    Returns a triple ``(boundaries, suffix_map, spec_path)``. ``spec_path``
    is ``None`` when the built-in fallback is in use.
    """
    global _boundary_cache, _suffix_cache, _spec_path_cache
    if _boundary_cache is not None and _suffix_cache is not None:
        return _boundary_cache, _suffix_cache, _spec_path_cache

    for candidate in _candidate_spec_paths():
        try:
            data: Any = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        languages: Dict[str, Any] = data.get("languages") or {}
        boundaries: Dict[str, List[str]] = {}
        suffixes: Dict[str, str] = {}
        for lang, entry in languages.items():
            patterns: List[Any] = list(entry.get("boundaries") or [])
            if patterns:
                boundaries[str(lang)] = [str(p) for p in patterns]
            entry_suffixes: List[Any] = list(entry.get("suffixes") or [])
            for suffix in entry_suffixes:
                suffixes[str(suffix).lower()] = str(lang)
        if boundaries and suffixes:
            _boundary_cache = boundaries
            _suffix_cache = suffixes
            _spec_path_cache = candidate
            return _boundary_cache, _suffix_cache, _spec_path_cache

    _boundary_cache = dict(_DEFAULT_BOUNDARIES)
    _suffix_cache = dict(_DEFAULT_LANGUAGE_BY_SUFFIX)
    _spec_path_cache = None
    return _boundary_cache, _suffix_cache, _spec_path_cache


def reload_boundary_spec() -> None:
    """Drop the cached spec so the next call re-reads disk.

    Provided for tests and long-running tools that may want to swap the
    spec file at runtime via ``STRLING_ISLAND_BOUNDARIES_PATH``.
    """
    global _boundary_cache, _suffix_cache, _spec_path_cache
    _boundary_cache = None
    _suffix_cache = None
    _spec_path_cache = None


def boundary_calls() -> Dict[str, List[str]]:
    """Return the boundary-call regex registry, indexed by language id."""
    boundaries, _suffixes, _path = _load_spec()
    return boundaries


def language_suffixes() -> Dict[str, str]:
    """Return the suffix → language id mapping."""
    _boundaries, suffixes, _path = _load_spec()
    return suffixes


def language_for_uri(uri: str) -> Optional[str]:
    """Return the boundary-language for a document URI, or ``None``."""
    suffixes = language_suffixes()
    lower = uri.lower()
    for suffix, lang in suffixes.items():
        if lower.endswith(suffix):
            return lang
    return None


# --------------------------------------------------------------------------- #
# String-literal scanners                                                     #
# --------------------------------------------------------------------------- #


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _scan_quoted_literal(
    source: str, start: int, opener: str, closer: str, allow_escape: bool
) -> Optional[Tuple[str, int, int, int]]:
    """Scan a quoted literal and return raw content with its end offset."""
    if not source.startswith(opener, start):
        return None
    content_start = start + len(opener)
    idx = content_start
    while idx < len(source):
        ch = source[idx]
        if allow_escape and ch == "\\" and idx + 1 < len(source):
            idx += 2
            continue
        if source.startswith(closer, idx):
            content = source[content_start:idx]
            return content, content_start, idx, idx + len(closer)
        idx += 1
    return None


def _scan_python_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Python string literal, including common prefixes."""
    if start >= len(source):
        return None
    if source[start] in ('"', "'"):
        quote_start = start
        prefix = ""
    else:
        if source[start] not in "rRuUbBfF" or (
            start > 0 and _is_identifier_char(source[start - 1])
        ):
            return None
        quote_start = start
        while (
            quote_start < len(source)
            and quote_start - start < 2
            and source[quote_start] in "rRuUbBfF"
        ):
            quote_start += 1
        if quote_start >= len(source) or source[quote_start] not in ('"', "'"):
            return None
        prefix = source[start:quote_start]
    quote = source[quote_start]
    triple = source.startswith(quote * 3, quote_start)
    opener = prefix + (quote * 3 if triple else quote)
    closer = quote * 3 if triple else quote
    allow_escape = "r" not in prefix.lower()
    return _scan_quoted_literal(source, start, opener, closer, allow_escape)


def _scan_c_like_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a C/TS/Java-style string or template literal."""
    if start >= len(source):
        return None
    if source[start] == "`":
        return _scan_quoted_literal(source, start, "`", "`", True)
    if source[start] in ('"', "'"):
        return _scan_quoted_literal(source, start, source[start], source[start], True)
    return None


def _scan_rust_raw_string(
    source: str, start: int
) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Rust raw string like ``r#"..."#`` or ``br#"..."#``."""
    if start >= len(source):
        return None
    prefix_len = 0
    if source[start] in "bB":
        if start + 1 < len(source) and source[start + 1] in "rR":
            prefix_len = 2
        else:
            return None
    elif source[start] not in "rR":
        return None
    i = start + prefix_len
    hash_count = 0
    while i + hash_count < len(source) and source[i + hash_count] == "#":
        hash_count += 1
    if i + hash_count >= len(source) or source[i + hash_count] != '"':
        return None
    closer = '"' + ("#" * hash_count)
    content_start = i + hash_count + 1
    idx = content_start
    while idx < len(source):
        if source.startswith(closer, idx):
            content = source[content_start:idx]
            return content, content_start, idx, idx + len(closer)
        idx += 1
    return None


def _scan_rust_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Rust string literal, including byte and raw-string forms."""
    if start >= len(source):
        return None
    raw = _scan_rust_raw_string(source, start)
    if raw is not None:
        return raw
    if (
        source[start] in "bB"
        and start + 1 < len(source)
        and source[start + 1] in ('"', "'")
    ):
        return _scan_quoted_literal(
            source, start, source[start : start + 2], source[start + 1], True
        )
    if source[start] in ('"', "'"):
        return _scan_quoted_literal(source, start, source[start], source[start], True)
    return None


def _scan_swift_hashed_string(
    source: str, start: int
) -> Optional[Tuple[str, int, int, int]]:
    # Scan a Swift extended delimiter string. The opener is one or more
    # ``#`` characters followed by ``"`` or ``"""``; the closer mirrors
    # the same hash count, e.g. ``#"..."#`` or ``##"""..."""##``.
    if start >= len(source) or source[start] != "#":
        return None
    i = start
    hash_count = 0
    while i < len(source) and source[i] == "#":
        hash_count += 1
        i += 1
    if i >= len(source) or source[i] != '"':
        return None
    triple = source.startswith('"""', i)
    quote_run = '"""' if triple else '"'
    closer = quote_run + ("#" * hash_count)
    content_start = i + len(quote_run)
    idx = content_start
    while idx < len(source):
        if source.startswith(closer, idx):
            content = source[content_start:idx]
            return content, content_start, idx, idx + len(closer)
        idx += 1
    return None


def _scan_swift_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Swift string literal, covering hashed and multiline forms."""
    if start >= len(source):
        return None
    if source[start] == "#":
        return _scan_swift_hashed_string(source, start)
    if source.startswith('"""', start):
        return _scan_quoted_literal(source, start, '"""', '"""', True)
    if source[start] in ('"', "'"):
        return _scan_quoted_literal(source, start, source[start], source[start], True)
    return None


_CPP_RAW_DELIM_FORBIDDEN = set(" ()\\\t\n\r\v\f")


def _scan_cpp_raw_string(
    source: str, start: int
) -> Optional[Tuple[str, int, int, int]]:
    """Scan a C++11 raw string literal: ``R"delim(content)delim"``."""
    if start >= len(source):
        return None
    prefix_len = 0
    # Allow optional encoding prefix: u8, u, U, L (followed by optional R).
    if source.startswith("u8", start):
        prefix_len = 2
    elif source[start] in "uUL":
        prefix_len = 1
    if start + prefix_len >= len(source) or source[start + prefix_len] != "R":
        return None
    if start + prefix_len + 1 >= len(source) or source[start + prefix_len + 1] != '"':
        return None
    delim_begin = start + prefix_len + 2
    delim_end = delim_begin
    while (
        delim_end < len(source)
        and delim_end - delim_begin < 16
        and source[delim_end] not in _CPP_RAW_DELIM_FORBIDDEN
        and source[delim_end] != "("
    ):
        delim_end += 1
    if delim_end >= len(source) or source[delim_end] != "(":
        return None
    delim = source[delim_begin:delim_end]
    content_start = delim_end + 1
    closer = ")" + delim + '"'
    idx = content_start
    while idx < len(source):
        if source.startswith(closer, idx):
            content = source[content_start:idx]
            return content, content_start, idx, idx + len(closer)
        idx += 1
    return None


def _scan_cpp_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a C++ string literal, including raw-string and encoding prefixes."""
    if start >= len(source):
        return None
    raw = _scan_cpp_raw_string(source, start)
    if raw is not None:
        return raw
    return _scan_c_like_string(source, start)


def _scan_lua_long_bracket(
    source: str, start: int
) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Lua long-bracket string ``[[...]]`` / ``[=[...]=]``."""
    if start >= len(source) or source[start] != "[":
        return None
    i = start + 1
    eq_count = 0
    while i < len(source) and source[i] == "=":
        eq_count += 1
        i += 1
    if i >= len(source) or source[i] != "[":
        return None
    content_start = i + 1
    closer = "]" + ("=" * eq_count) + "]"
    idx = content_start
    while idx < len(source):
        if source.startswith(closer, idx):
            content = source[content_start:idx]
            return content, content_start, idx, idx + len(closer)
        idx += 1
    return None


def _scan_lua_string(source: str, start: int) -> Optional[Tuple[str, int, int, int]]:
    """Scan a Lua string literal, including long-bracket form."""
    if start >= len(source):
        return None
    if source[start] == "[":
        return _scan_lua_long_bracket(source, start)
    if source[start] in ('"', "'"):
        return _scan_quoted_literal(source, start, source[start], source[start], True)
    return None


# --------------------------------------------------------------------------- #
# Per-language lexer profiles                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LexerProfile:
    """Describe how to skip non-code regions for a host language.

    A profile is a small data record consumed by :func:`_skip_via_profile`.
    Adding a new language means adding a new entry to ``_LANGUAGE_PROFILES`` —
    no new scanner code is required unless the language has a string form
    not already covered by the existing scanners (currently: c-like,
    c-like-template, python, rust, swift, cpp, lua).
    """

    line_comments: Tuple[str, ...] = ()
    block_comments: Tuple[Tuple[str, str], ...] = ()
    block_comments_nest: bool = False
    string_scanner: str = "c-like"
    long_bracket_block_comment: bool = False  # Lua's ``--[[ ... ]]``


_STRING_SCANNERS = {
    "python": _scan_python_string,
    "rust": _scan_rust_string,
    "swift": _scan_swift_string,
    "cpp": _scan_cpp_string,
    "lua": _scan_lua_string,
    "c-like": _scan_c_like_string,
    "c-like-template": _scan_c_like_string,
}


_LANGUAGE_PROFILES: Dict[str, LexerProfile] = {
    "python": LexerProfile(line_comments=("#",), string_scanner="python"),
    "typescript": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like-template",
    ),
    "rust": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        block_comments_nest=True,
        string_scanner="rust",
    ),
    "java": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like",
    ),
    "c": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like",
    ),
    "cpp": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="cpp",
    ),
    "csharp": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like",
    ),
    "fsharp": LexerProfile(
        line_comments=("//",),
        block_comments=(("(*", "*)"),),
        block_comments_nest=True,
        string_scanner="c-like",
    ),
    "go": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like-template",
    ),
    "kotlin": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        block_comments_nest=True,
        string_scanner="c-like",
    ),
    "swift": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        block_comments_nest=True,
        string_scanner="swift",
    ),
    "dart": LexerProfile(
        line_comments=("//",),
        block_comments=(("/*", "*/"),),
        block_comments_nest=True,
        string_scanner="c-like",
    ),
    "php": LexerProfile(
        line_comments=("//", "#"),
        block_comments=(("/*", "*/"),),
        string_scanner="c-like",
    ),
    "ruby": LexerProfile(
        line_comments=("#",),
        string_scanner="c-like",
    ),
    "perl": LexerProfile(
        line_comments=("#",),
        string_scanner="c-like",
    ),
    "lua": LexerProfile(
        line_comments=("--",),
        string_scanner="lua",
        long_bracket_block_comment=True,
    ),
    "r": LexerProfile(
        line_comments=("#",),
        string_scanner="c-like",
    ),
}


def _scan_literal(
    source: str, start: int, language: str
) -> Optional[Tuple[str, int, int, int]]:
    """Scan the STRling literal that follows a boundary call."""
    profile = _LANGUAGE_PROFILES.get(language)
    scanner_name = profile.string_scanner if profile is not None else "c-like"
    scanner = _STRING_SCANNERS.get(scanner_name, _scan_c_like_string)
    return scanner(source, start)


def _skip_line_comment(
    source: str, start: int, markers: Tuple[str, ...]
) -> Optional[int]:
    for marker in markers:
        if marker and source.startswith(marker, start):
            end = source.find("\n", start)
            return len(source) if end == -1 else end
    return None


def _skip_block_comment(
    source: str,
    start: int,
    pairs: Tuple[Tuple[str, str], ...],
    nest: bool,
) -> Optional[int]:
    for opener, closer in pairs:
        if not opener or not source.startswith(opener, start):
            continue
        idx = start + len(opener)
        depth = 1
        while idx < len(source):
            if nest and source.startswith(opener, idx):
                depth += 1
                idx += len(opener)
                continue
            if source.startswith(closer, idx):
                depth -= 1
                idx += len(closer)
                if depth == 0:
                    return idx
                continue
            idx += 1
        return len(source)
    return None


def _skip_via_profile(source: str, start: int, profile: LexerProfile) -> Optional[int]:
    # Lua-special: ``--[[ ... ]]`` must be detected BEFORE the line-comment
    # rule fires, because the same ``--`` prefix opens both forms.
    if profile.long_bracket_block_comment and source.startswith("--", start):
        scanned = _scan_lua_long_bracket(source, start + 2)
        if scanned is not None:
            return scanned[3]
    end = _skip_line_comment(source, start, profile.line_comments)
    if end is not None:
        return end
    end = _skip_block_comment(
        source, start, profile.block_comments, profile.block_comments_nest
    )
    if end is not None:
        return end
    scanner = _STRING_SCANNERS.get(profile.string_scanner, _scan_c_like_string)
    scanned = scanner(source, start)
    return scanned[3] if scanned is not None else None


def _skip_code_region(source: str, start: int, language: str) -> Optional[int]:
    profile = _LANGUAGE_PROFILES.get(language)
    if profile is None:
        return None
    return _skip_via_profile(source, start, profile)


def _normalize_boundary_call(raw: str) -> str:
    """Strip trailing call punctuation from a matched boundary."""
    return re.sub(r"[!\s(]+$", "", raw)


# --------------------------------------------------------------------------- #
# Offset bookkeeping                                                          #
# --------------------------------------------------------------------------- #


def _offset_to_position(source: str, offset: int) -> HostPosition:
    """Convert an absolute byte offset to a zero-based ``(line, char)``."""
    if offset <= 0:
        return HostPosition(0, 0)
    prefix = source[:offset]
    line = prefix.count("\n")
    last_nl = prefix.rfind("\n")
    char = offset if last_nl == -1 else offset - last_nl - 1
    return HostPosition(line=line, character=char)


def _build_line_offsets(content: str, start: HostPosition) -> List[HostPosition]:
    """Compute per-virtual-line host positions for an extracted island."""
    offsets = [start]
    line_no = start.line
    for ch in content:
        if ch == "\n":
            line_no += 1
            offsets.append(HostPosition(line=line_no, character=0))
    return offsets


def _build_line_lengths(content: str) -> List[int]:
    """Compute the virtual line lengths for an extracted island."""
    return [len(line) for line in content.split("\n")]


def _extract_pure_line_islands(source: str) -> List[Island]:
    """Treat each ``.strl`` line as a standalone island.

    The STRling editor contract treats native ``.strl`` buffers as pure DSL
    text with no host wrapper. Splitting by line keeps diagnostics local to the
    line being edited, which prevents unterminated constructs from projecting a
    range all the way to the document EOF.
    """
    return [
        Island(
            virtual_content=line,
            host_start=HostPosition(index, 0),
            line_offsets=[HostPosition(index, 0)],
            line_lengths=[len(line)],
            boundary_call=".strl",
        )
        for index, line in enumerate(source.splitlines())
    ]


# --------------------------------------------------------------------------- #
# Public extraction entry points                                              #
# --------------------------------------------------------------------------- #


def extract_islands(source: str, language: str) -> List[Island]:
    """Sweep ``source`` for STRling boundary calls and return all islands."""
    if language == "strl":
        return _extract_pure_line_islands(source)

    boundaries = boundary_calls().get(language)
    if not boundaries:
        return []

    compiled_boundaries = [re.compile(pattern) for pattern in boundaries]
    islands: List[Island] = []
    i = 0
    n = len(source)
    while i < n:
        skipped = _skip_code_region(source, i, language)
        if skipped is not None:
            i = max(i + 1, skipped)
            continue

        matched = False
        for boundary in compiled_boundaries:
            match = boundary.match(source, i)
            if match is None:
                continue
            literal_start = match.end()
            scanned = _scan_literal(source, literal_start, language)
            if scanned is None:
                continue
            content, content_start, _content_end, literal_end = scanned
            host_start = _offset_to_position(source, content_start)
            line_offsets = _build_line_offsets(content, host_start)
            islands.append(
                Island(
                    virtual_content=content,
                    host_start=host_start,
                    line_offsets=line_offsets,
                    line_lengths=_build_line_lengths(content),
                    boundary_call=_normalize_boundary_call(match.group(0)),
                )
            )
            i = literal_end
            matched = True
            break
        if not matched:
            i += 1
    return islands


def extract_islands_for_uri(source: str, uri: str) -> List[Island]:
    """Convenience wrapper that derives the language from the URI suffix."""
    lang = language_for_uri(uri)
    if lang is None:
        return []
    return extract_islands(source, lang)


__all__ = [
    "HostPosition",
    "Island",
    "boundary_calls",
    "extract_islands",
    "extract_islands_for_uri",
    "language_for_uri",
    "language_suffixes",
    "reload_boundary_spec",
]
