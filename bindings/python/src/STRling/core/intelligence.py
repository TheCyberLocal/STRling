"""
Module Pedagogy:
================
This module is STRling's unified "Language Intelligence" core. It is the
single entry point that LSP, CLI, and editor tooling use to obtain
diagnostics for a STRling pattern and to discover embedded STRling islands
inside host-language source files.

It exists to eliminate the previous split between
``bindings/python/src/STRling/cli_server.py`` (a long-running JSON-RPC
shadow process) and ``tooling/lsp-server/server.py`` (the real LSP
endpoint). Both used to encode the same parse → STRlingParseError →
``to_lsp_diagnostic()`` round-trip in slightly different shapes. Now the
LSP server imports :func:`analyze_content` directly, the CLI tool
``tooling/parse_strl.py`` calls into the same surface, and any future
binding-agnostic tooling has a single API to consume.

The diagnostic JSON shape returned here matches the LSP-friendly format
historically produced by the deleted CLI server, preserving the
``{"success", "diagnostics", "version"}`` contract used by external
callers and tests.

Island extraction is re-exported from :mod:`STRling.core.islands` so
callers can depend on a single namespace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .errors import STRlingParseError
from .islands import (  # re-exported for one-stop importing
    HostPosition,
    Island,
    boundary_calls,
    extract_islands,
    extract_islands_for_uri,
    language_for_uri,
    language_suffixes,
    reload_boundary_spec,
)
from .parser import parse


# Stable contract version for the diagnostic JSON shape. Bump only when
# the response schema changes in a backwards-incompatible way.
INTELLIGENCE_PROTOCOL_VERSION = "1.0.0"


def _internal_error_payload(message: str, code: str) -> Dict[str, Any]:
    """Build the diagnostic envelope used for non-parser failures.

    Both file-read errors and unexpected exceptions surface through this
    helper so the caller always receives a uniformly shaped diagnostic
    rather than a raw traceback.
    """
    return {
        "success": False,
        "diagnostics": [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 0},
                },
                "severity": 1,
                "message": message,
                "source": "STRling",
                "code": code,
            }
        ],
        "version": INTELLIGENCE_PROTOCOL_VERSION,
    }


def analyze_content(content: str) -> Dict[str, Any]:
    """Parse a STRling pattern and return LSP-shaped diagnostic JSON.

    Parameters
    ----------
    content : str
        The STRling DSL source to analyze. May be empty.

    Returns
    -------
    dict
        A JSON-serialisable dictionary with three keys: ``success`` (bool),
        ``diagnostics`` (list of LSP Diagnostic dicts — empty on success),
        and ``version`` (the intelligence protocol version string).
    """
    diagnostics: List[Dict[str, Any]] = []
    safety = detect_safety_diagnostics(content)
    try:
        parse(content)
        return {
            "success": True,
            "diagnostics": safety,
            "version": INTELLIGENCE_PROTOCOL_VERSION,
        }
    except STRlingParseError as e:
        diagnostics.append(e.to_lsp_diagnostic())
        diagnostics.extend(safety)
        return {
            "success": False,
            "diagnostics": diagnostics,
            "version": INTELLIGENCE_PROTOCOL_VERSION,
        }
    except Exception as e:  # pragma: no cover - defensive guard
        # Unexpected parser failures surface as an internal-error diagnostic
        # so the LSP/CLI layers never have to translate raw tracebacks.
        return _internal_error_payload(f"Unexpected error: {str(e)}", "internal_error")


def analyze_file(filepath: str) -> Dict[str, Any]:
    """Read ``filepath`` and analyze its contents as STRling DSL.

    Parameters
    ----------
    filepath : str
        Filesystem path to a ``.strl`` file or any UTF-8 readable file.

    Returns
    -------
    dict
        Same shape as :func:`analyze_content`. Returns a uniform
        diagnostic envelope (``success=False``) when the file cannot be
        read instead of raising, so CLI callers can serialize the result
        without bespoke error handling.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return _internal_error_payload(
                f"File not found: {filepath}", "file_not_found"
            )
        content = path.read_text(encoding="utf-8")
        return analyze_content(content)
    except Exception as e:  # pragma: no cover - defensive guard
        return _internal_error_payload(f"Error reading file: {str(e)}", "read_error")


# --------------------------------------------------------------------------- #
# Safety analysis: REDOS_RISK detection                                       #
# --------------------------------------------------------------------------- #
#
# Catastrophic backtracking arises when an unbounded quantifier is applied
# to a sub-expression that itself ends in an unbounded quantifier — the
# canonical ``(a+)+`` / ``(a*)+`` / ``(a*)*`` shapes. The engine then has
# exponentially many ways to distribute repetitions across the layers.
#
# This detector runs over the raw source text rather than the AST so the
# reported range stays anchored to the bytes the user can see; it also
# means the warning fires even when other parts of the pattern fail to
# parse, giving the user actionable feedback in the middle of an edit.
#
# Each diagnostic carries machine-readable ``data.replacements`` so the
# code-action handler can build a quick-fix without re-scanning the text.

import re as _re  # noqa: E402  (placed near consumers)


_REDOS_NESTED_PATTERN = _re.compile(
    # Outer:  ( ... )  (+|*|{n,})
    # Inner ends in an unbounded quantifier: + * or {n,}
    # Inner forbids parentheses to keep the scan robust against arbitrary
    # nesting; the deeply-nested case is rare in user code and would need
    # a balanced-paren parser to handle without false positives.
    r"\((?P<inner>[^()]+?(?P<inner_quant>\+|\*|\{\d+,\}))\)"
    r"(?P<outer_quant>\+|\*|\{\d+,\})"
)


_REDOS_MESSAGE = (
    "Nested unbounded quantifier — pattern is vulnerable to catastrophic "
    "backtracking. Convert the inner repeat to possessive (++ / *+) or wrap "
    "the inner group atomically ((?>...)) to guarantee linear-time matching."
)


def _line_col(content: str, offset: int) -> Tuple[int, int]:
    """Convert a byte offset to ``(line, character)`` coordinates."""
    line = 0
    last_nl = -1
    for i in range(offset):
        if content[i] == "\n":
            line += 1
            last_nl = i
    return line, offset - last_nl - 1


def _redos_replacements(
    inner: str, inner_quant: str, outer_quant: str
) -> List[Dict[str, str]]:
    """Build the suggested rewrites for a nested unbounded quantifier match.

    Two safe rewrites are offered:
      * **Atomic group** wraps the inner sub-expression in ``(?>...)`` so the
        engine commits on first success and never reconsiders alternatives.
      * **Possessive quantifier** appends ``+`` to the inner quantifier so
        the inner repeat itself becomes non-backtracking.

    Both eliminate the cross-layer ambiguity that drives the exponential
    blow-up while preserving the matched language.
    """
    atomic = f"(?>{inner}){outer_quant}"
    # Possessive form: convert inner ``X+`` to ``X++``, leaving the outer
    # quantifier intact. The grouping parentheses are preserved so any
    # capture-group numbering downstream stays stable.
    possessive_inner = inner + ("+" if inner_quant in ("+", "*") else "+")
    possessive = f"({possessive_inner}){outer_quant}"
    return [
        {"title": "Convert inner group to atomic (?>...)", "newText": atomic},
        {
            "title": "Convert inner quantifier to possessive (++ / *+)",
            "newText": possessive,
        },
    ]


def detect_safety_diagnostics(content: str) -> List[Dict[str, Any]]:
    """Return safety warnings (currently REDOS_RISK) for ``content``.

    The output uses the same LSP-shaped diagnostic dict as
    :func:`analyze_content`; callers can concatenate the lists directly.
    Each warning carries a ``code`` of ``REDOS_RISK`` and a ``data``
    payload listing the available rewrites — the LSP code-action handler
    builds quick-fixes from that payload without re-scanning the source.
    """
    if not content:
        return []
    diagnostics: List[Dict[str, Any]] = []
    for match in _REDOS_NESTED_PATTERN.finditer(content):
        start_off = match.start()
        end_off = match.end()
        s_line, s_char = _line_col(content, start_off)
        e_line, e_char = _line_col(content, end_off)
        inner = match.group("inner")
        inner_quant = match.group("inner_quant")
        outer_quant = match.group("outer_quant")
        diagnostics.append(
            {
                "range": {
                    "start": {"line": s_line, "character": s_char},
                    "end": {"line": e_line, "character": e_char},
                },
                "severity": 2,  # Warning
                "message": _REDOS_MESSAGE,
                "source": "STRling",
                "code": "REDOS_RISK",
                "data": {
                    "replacements": _redos_replacements(
                        inner, inner_quant, outer_quant
                    ),
                    "match_text": match.group(0),
                },
            }
        )
    return diagnostics


__all__ = [
    "INTELLIGENCE_PROTOCOL_VERSION",
    "analyze_content",
    "analyze_file",
    "detect_safety_diagnostics",
    "emit_pcre2_for_pattern",
    "extract_document_symbols",
    "find_registry_definition",
    "format_pattern",
    "SEMANTIC_TOKEN_TYPES",
    "SEMANTIC_TOKEN_MODIFIERS",
    "tokenize_pattern",
    # Standard-library registry surface.
    "RegistryEntry",
    "RegistryManager",
    "registry",
    "get_completion_items",
    "get_registry_documentation",
    # Island re-exports — single import site for downstream tooling.
    "HostPosition",
    "Island",
    "boundary_calls",
    "extract_islands",
    "extract_islands_for_uri",
    "language_for_uri",
    "language_suffixes",
    "reload_boundary_spec",
]


# --------------------------------------------------------------------------- #
# Ambient intelligence: live hover + semantic tokens                          #
# --------------------------------------------------------------------------- #
#
# These helpers back the LSP's hover and semantic-token features. They live
# in the intelligence layer (rather than the LSP server) so any binding-
# agnostic tooling — the CLI, future Rust LSP, alternate editors — can reuse
# the same compile-then-render and tokenisation passes without depending on
# ``pygls`` or ``lsprotocol``.


def emit_pcre2_for_pattern(content: str) -> Dict[str, Any]:
    """Compile ``content`` and return a PCRE2 emission envelope.

    Used by the LSP hover feature to display the compiled regex alongside
    the source pattern. Errors propagate through the same diagnostic shape
    as :func:`analyze_content`, so the caller can surface a parse failure
    or an emitter safety guard (variable-length lookbehind, REDOS) the
    same way it surfaces ordinary diagnostics.

    Returns
    -------
    dict
        ``{"success": True, "emitted": "<pcre2>", "diagnostics": []}`` on
        success, or ``{"success": False, "emitted": None,
        "diagnostics": [<lsp diag>]}`` on failure.
    """
    # Lazy imports keep the module light for callers that only want
    # parse-level diagnostics.
    from .compiler import Compiler
    from ..emitters import pcre2 as pcre2_emitter

    try:
        flags, ast = parse(content)
    except STRlingParseError as e:
        return {
            "success": False,
            "emitted": None,
            "diagnostics": [e.to_lsp_diagnostic()],
            "version": INTELLIGENCE_PROTOCOL_VERSION,
        }

    try:
        ir_root = Compiler().compile(ast)
        flags_dict = flags.to_dict() if hasattr(flags, "to_dict") else None
        emitted = pcre2_emitter.emit(ir_root, flags_dict)
    except Exception as e:  # pragma: no cover - emitter safety guards
        return _internal_error_payload(f"Compilation failed: {str(e)}", "compile_error")

    return {
        "success": True,
        "emitted": emitted,
        "diagnostics": [],
        "version": INTELLIGENCE_PROTOCOL_VERSION,
    }


# Standard LSP semantic token type & modifier legends. The LSP spec lets
# servers declare any subset of the well-known catalogue — we ship the
# slice that maps cleanly onto STRling lexical categories. Order is
# significant: clients receive these arrays as the legend and reference
# them by index in token streams.
SEMANTIC_TOKEN_TYPES: Tuple[str, ...] = (
    "string",  # 0 — literal characters
    "number",  # 1 — quantifiers (?, *, +, {n,m}, lazy/possessive suffix)
    "operator",  # 2 — alternation, group parens, range hyphen
    "regexp",  # 3 — character classes and predefined escapes (\d, \w, ...)
    "keyword",  # 4 — anchors (^, $, \b, \A, \z, \Z, \B)
    "function",  # 5 — group names (`(?<name>...)`)
    "variable",  # 6 — backreferences (`\1`, `\k<name>`)
    "comment",  # 7 — extended-mode comments
)
SEMANTIC_TOKEN_MODIFIERS: Tuple[str, ...] = ()


# Internal token-type indices — keeping these as named constants prevents
# magic numbers from leaking into the scanner below.
_TT_STRING = 0
_TT_NUMBER = 1
_TT_OPERATOR = 2
_TT_REGEXP = 3
_TT_KEYWORD = 4
_TT_FUNCTION = 5
_TT_VARIABLE = 6
_TT_COMMENT = 7


def _emit_token(
    out: List[Tuple[int, int, int, int, int]],
    line: int,
    char: int,
    length: int,
    token_type: int,
) -> None:
    """Append a single absolute-position semantic token to ``out``.

    Tokens are emitted in absolute (line, character) coordinates here; the
    LSP transport layer converts to delta-encoded form. Zero-length spans
    are filtered to keep the wire payload tidy.
    """
    if length <= 0:
        return
    out.append((line, char, length, token_type, 0))


def tokenize_pattern(content: str) -> List[Tuple[int, int, int, int, int]]:
    """Produce semantic tokens for a STRling pattern in absolute coordinates.

    The scanner is a deliberately light-weight pass over the raw source —
    it does **not** require a successful parse, which means the editor can
    keep colourising while the user is mid-edit. Output is a list of
    5-tuples ``(line, character, length, token_type, modifier)`` sorted by
    position; the LSP server delta-encodes them before transmission.

    The token types correspond by index to :data:`SEMANTIC_TOKEN_TYPES`.
    """
    tokens: List[Tuple[int, int, int, int, int]] = []
    line = 0
    col = 0
    i = 0
    n = len(content)

    while i < n:
        ch = content[i]

        # Track newlines first so token coordinates stay accurate even when
        # patterns span multiple lines (extended mode).
        if ch == "\n":
            line += 1
            col = 0
            i += 1
            continue

        # Anchors — single char tokens with keyword colour.
        if ch in ("^", "$"):
            _emit_token(tokens, line, col, 1, _TT_KEYWORD)
            i += 1
            col += 1
            continue

        # Alternation and group parens map to operators. Group-open also
        # carries optional metadata (`(?:`, `(?<name>`, `(?=...)`) which
        # we colourise as a single operator span; the inner group name
        # gets its own `function` token below.
        if ch == "|":
            _emit_token(tokens, line, col, 1, _TT_OPERATOR)
            i += 1
            col += 1
            continue

        if ch == "(":
            # Detect a group prefix like ``(?<name>`` and emit the name as
            # a `function` token after the operator span.
            j = i + 1
            prefix_end = j
            name_start: int = -1
            name_end: int = -1
            if j < n and content[j] == "?":
                prefix_end = j + 1
                # Named group: (?<name>...) or (?P<name>...)
                k = prefix_end
                if k < n and content[k] == "P":
                    k += 1
                if k < n and content[k] == "<":
                    name_start = k + 1
                    m = name_start
                    while m < n and (content[m].isalnum() or content[m] == "_"):
                        m += 1
                    if m < n and content[m] == ">":
                        name_end = m
                        prefix_end = m + 1
            span = prefix_end - i
            _emit_token(tokens, line, col, span, _TT_OPERATOR)
            if name_start >= 0 and name_end > name_start:
                _emit_token(
                    tokens,
                    line,
                    col + (name_start - i),
                    name_end - name_start,
                    _TT_FUNCTION,
                )
            col += span
            i = prefix_end
            continue

        if ch == ")":
            _emit_token(tokens, line, col, 1, _TT_OPERATOR)
            i += 1
            col += 1
            continue

        # Quantifiers — single char or braced form. Trailing `?`/`+` for
        # lazy/possessive modes are folded into the same span.
        if ch in ("*", "+", "?"):
            length = 1
            if i + 1 < n and content[i + 1] in ("?", "+"):
                length = 2
            _emit_token(tokens, line, col, length, _TT_NUMBER)
            i += length
            col += length
            continue

        if ch == "{":
            close = content.find("}", i)
            if close != -1 and "\n" not in content[i:close]:
                length = (close - i) + 1
                if close + 1 < n and content[close + 1] in ("?", "+"):
                    length += 1
                _emit_token(tokens, line, col, length, _TT_NUMBER)
                i += length
                col += length
                continue

        # Character classes — colour the entire `[...]` as a `regexp`
        # span. We don't recurse into class internals at this phase.
        if ch == "[":
            j = i + 1
            if j < n and content[j] == "^":
                j += 1
            depth = 1
            while j < n and depth > 0:
                if content[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if content[j] == "]":
                    depth -= 1
                    j += 1
                    continue
                if content[j] == "\n":
                    break
                j += 1
            length = j - i
            _emit_token(tokens, line, col, length, _TT_REGEXP)
            i += length
            col += length
            continue

        # Escapes — predefined classes (\d, \w, \s, ...) and anchors
        # (\b, \B, \A, \z, \Z) and backreferences (\1, \k<name>).
        if ch == "\\" and i + 1 < n:
            nxt = content[i + 1]
            if nxt in ("b", "B", "A", "z", "Z"):
                _emit_token(tokens, line, col, 2, _TT_KEYWORD)
                i += 2
                col += 2
                continue
            if nxt == "k" and i + 2 < n and content[i + 2] == "<":
                end = content.find(">", i + 3)
                if end != -1:
                    length = (end - i) + 1
                    _emit_token(tokens, line, col, length, _TT_VARIABLE)
                    i += length
                    col += length
                    continue
            if nxt.isdigit():
                j = i + 2
                while j < n and content[j].isdigit():
                    j += 1
                _emit_token(tokens, line, col, j - i, _TT_VARIABLE)
                col += j - i
                i = j
                continue
            # Unicode property escapes \p{...} / \P{...}
            if nxt in ("p", "P") and i + 2 < n and content[i + 2] == "{":
                end = content.find("}", i + 3)
                if end != -1:
                    length = (end - i) + 1
                    _emit_token(tokens, line, col, length, _TT_REGEXP)
                    i += length
                    col += length
                    continue
            # All other escapes (\d \w \s \D \W \S \. \\ etc.) fall here.
            _emit_token(tokens, line, col, 2, _TT_REGEXP)
            i += 2
            col += 2
            continue

        # Extended-mode comment: `# ...` to end of line. We always emit
        # this as a comment token; if extended mode is off the host will
        # have rejected the parse anyway, but colourisation is harmless.
        if ch == "#":
            end = content.find("\n", i)
            if end == -1:
                end = n
            _emit_token(tokens, line, col, end - i, _TT_COMMENT)
            col += end - i
            i = end
            continue

        # Whitespace — no token, just advance the column.
        if ch in (" ", "\t"):
            i += 1
            col += 1
            continue

        # Default: a literal character. Coalesce a run of literals into a
        # single span so the editor renders one continuous string colour.
        j = i
        while j < n and content[j] not in (
            "^",
            "$",
            "|",
            "(",
            ")",
            "*",
            "+",
            "?",
            "{",
            "[",
            "\\",
            "#",
            "\n",
            " ",
            "\t",
        ):
            j += 1
        _emit_token(tokens, line, col, j - i, _TT_STRING)
        col += j - i
        i = j

    return tokens


# --------------------------------------------------------------------------- #
# Standard library registry                                                   #
# --------------------------------------------------------------------------- #
#
# This historical compatibility manifest supplies names, AST references,
# scoped references, and editor-trigger metadata for the current Essential 5.
# The ratified guarantee decisions live in ``stdlib-guarantee-audit.json``;
# P14-T02 will create the future canonical registry. Editor surfaces load
# ``spec/stdlib/registry.json`` so their current lexical claims stay aligned.

from dataclasses import dataclass, field  # noqa: E402  (placed near consumers)


_REGISTRY_ENV_VAR = "STRLING_STDLIB_REGISTRY_PATH"
_REGISTRY_DEFAULT_RELATIVE = ("spec", "stdlib", "registry.json")


@dataclass
class RegistryEntry:
    """A single stdlib pattern as seen by the language-intelligence core."""

    name: str
    summary: str
    documentation: str
    rfc: str
    rfc_url: str
    regex: str
    snippet: str
    trigger_keywords: List[str] = field(default_factory=lambda: [])
    ast_ref: str = ""
    ast: Dict[str, Any] = field(default_factory=lambda: {})

    def to_completion_item(self) -> Dict[str, Any]:
        """Serialise the entry into an LSP-shaped completion item dict.

        The dict keys mirror the ``CompletionItem`` interface: ``label``,
        ``kind`` (the integer enum value for *Function*), ``detail``,
        ``documentation`` (Markdown), ``insertText``, and the auxiliary
        ``filterText`` so that any of the trigger keywords brings the
        entry to the top of the completion list.
        """
        markdown = self.documentation_markdown()
        return {
            "label": self.name,
            "kind": 3,  # CompletionItemKind.Function
            "detail": self.summary,
            "documentation": {"kind": "markdown", "value": markdown},
            "insertText": self.snippet or self.name,
            "filterText": " ".join([self.name] + list(self.trigger_keywords)),
            "data": {"registry_name": self.name},
        }

    def documentation_markdown(self) -> str:
        """Render the registry entry as a Markdown hover/help card."""
        body = self.documentation or self.summary
        link = (
            f"[{self.rfc}]({self.rfc_url})"
            if self.rfc and self.rfc_url
            else self.rfc or ""
        )
        regex_block = f"\n\n```regex\n{self.regex}\n```" if self.regex else ""
        link_block = f"\n\n_Reference scope:_ {link}" if link else ""
        return f"**`{self.name}`** \u2014 {body}{regex_block}{link_block}"


def _candidate_registry_paths() -> List[Path]:
    """Locate possible on-disk locations for the stdlib registry.

    The lookup honours the ``STRLING_STDLIB_REGISTRY_PATH`` env var first
    (useful for tests and bundling), then walks parent directories from
    this file looking for ``spec/stdlib/registry.json``. The walk lets the
    registry resolve correctly whether the package is imported from the
    repo, an editable install, or a wheel bundling the spec directory.
    """
    import os

    candidates: List[Path] = []
    env_value = os.environ.get(_REGISTRY_ENV_VAR)
    if env_value:
        candidates.append(Path(env_value))
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidates.append(parent.joinpath(*_REGISTRY_DEFAULT_RELATIVE))
    return candidates


class RegistryManager:
    """Loads and caches the stdlib registry, exposing query helpers.

    Use the module-level :data:`registry` singleton for normal access;
    construct your own instance when a test wants to point at an
    alternate manifest via the ``path`` argument or env var.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._explicit_path = path
        self._entries: List[RegistryEntry] = []
        self._by_name: Dict[str, RegistryEntry] = {}
        self._by_keyword: Dict[str, RegistryEntry] = {}
        self._loaded_path: Optional[Path] = None
        self.reload()

    @property
    def loaded_path(self) -> Optional[Path]:
        return self._loaded_path

    def reload(self) -> None:
        """Re-read the manifest from disk, refreshing cached lookups."""
        import json

        candidates: List[Path] = []
        if self._explicit_path is not None:
            candidates.append(self._explicit_path)
        else:
            candidates.extend(_candidate_registry_paths())

        data: Optional[Dict[str, Any]] = None
        chosen: Optional[Path] = None
        for candidate in candidates:
            try:
                if candidate.is_file():
                    with candidate.open("r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    chosen = candidate
                    break
            except OSError:
                continue

        self._entries = []
        self._by_name = {}
        self._by_keyword = {}
        self._loaded_path = chosen

        if not data:
            return

        raw_patterns = data.get("patterns", [])
        if isinstance(raw_patterns, dict):
            # Tolerate the alternative dict-shaped manifest used by
            # ``essential_5.json`` so the loader stays forward-compatible.
            raw_patterns = list(raw_patterns.values())

        for raw in raw_patterns:
            if not isinstance(raw, dict) or "name" not in raw:
                continue
            entry = RegistryEntry(
                name=str(raw.get("name", "")),
                summary=str(raw.get("summary", "")),
                documentation=str(raw.get("documentation", raw.get("summary", ""))),
                rfc=str(raw.get("rfc", "")),
                rfc_url=str(raw.get("rfc_url", "")),
                regex=str(raw.get("regex", raw.get("regex_default", ""))),
                snippet=str(raw.get("snippet", raw.get("name", ""))),
                trigger_keywords=[str(k) for k in raw.get("trigger_keywords", [])],
                ast_ref=str(raw.get("ast_ref", "")),
                ast=raw.get("ast", {}) if isinstance(raw.get("ast", {}), dict) else {},
            )
            self._entries.append(entry)
            self._by_name[entry.name.lower()] = entry
            for kw in [entry.name, *entry.trigger_keywords]:
                if kw:
                    self._by_keyword.setdefault(kw.lower(), entry)

    def entries(self) -> List[RegistryEntry]:
        """Return all registered patterns in declaration order."""
        return list(self._entries)

    def get(self, name: str) -> Optional[RegistryEntry]:
        """Lookup an entry by canonical name (case-insensitive)."""
        if not name:
            return None
        return self._by_name.get(name.lower())

    def lookup_keyword(self, word: str) -> Optional[RegistryEntry]:
        """Resolve an arbitrary identifier (name or trigger) to an entry."""
        if not word:
            return None
        return self._by_keyword.get(word.lower())

    def get_completion_items(self) -> List[Dict[str, Any]]:
        """Return LSP-shaped completion items for every registered pattern.

        Editor servers can forward the result directly to clients; the
        wire format follows the LSP ``CompletionItem`` contract so no
        additional adaptation is required at the transport boundary.
        """
        return [entry.to_completion_item() for entry in self._entries]


# Module-level singleton — created lazily on first import. Subsequent
# `reload()` calls refresh the cache in place so no consumer needs to be
# notified.
from typing import Optional  # noqa: E402  (imported here to keep diff small)


registry: RegistryManager = RegistryManager()


def get_completion_items() -> List[Dict[str, Any]]:
    """Convenience wrapper around :meth:`RegistryManager.get_completion_items`."""
    return registry.get_completion_items()


def get_registry_documentation(word: str) -> Optional[str]:
    """Return Markdown documentation for ``word`` if it matches a registered pattern."""
    entry = registry.lookup_keyword(word)
    return entry.documentation_markdown() if entry is not None else None


# --------------------------------------------------------------------------- #
# Document symbols: structural outline                                        #
# --------------------------------------------------------------------------- #
#
# The AST nodes do not carry source coordinates, so the outline scanner
# walks the raw source directly and emits a hierarchical tree of
# ``(name, kind, range, selection_range, children)`` tuples. The shape
# matches the LSP ``DocumentSymbol`` contract one-for-one so the LSP
# layer is a thin adapter rather than a second parser.
#
# Recognised structural elements:
#   * Capturing groups, named groups, non-capturing groups, atomic groups,
#     lookaheads and lookbehinds   \u2192 a single nested symbol per group
#   * Top-level alternation branches inside a group               \u2192 child symbols
#
# The kind index mirrors the LSP ``SymbolKind`` enum so the LSP server
# can hand the result through without re-mapping.

# LSP SymbolKind values used by the outline.
_SK_CLASS = 5
_SK_METHOD = 6
_SK_FIELD = 8
_SK_VARIABLE = 13
_SK_NAMESPACE = 3


@dataclass
class _SymbolSpan:
    """Internal node used while building the document-symbol tree."""

    name: str
    detail: str
    kind: int
    start_offset: int
    end_offset: int
    selection_start: int
    selection_end: int
    children: List["_SymbolSpan"] = field(default_factory=lambda: [])


def _offset_to_position(content: str, offset: int) -> Dict[str, int]:
    """Convert a byte offset to ``{"line": l, "character": c}`` (LSP shape)."""
    line, character = _line_col(content, offset)
    return {"line": line, "character": character}


def _scan_group_header(content: str, open_paren: int) -> Tuple[str, str, int, int, int]:
    """Inspect the characters following ``(`` and classify the group.

    Returns a tuple ``(name, detail, kind, header_end, sel_end)`` where
    ``header_end`` is the offset just past the opening syntactic prefix
    (so a recursive scan can resume from the body) and ``sel_end`` is
    the offset of the last character of the *selection* span used by the
    editor's outline highlight (the group name when present, otherwise
    the syntactic introducer).
    """
    n = len(content)
    i = open_paren + 1
    if i >= n or content[i] != "?":
        return ("group", "capturing group", _SK_VARIABLE, i, open_paren + 1)

    # ( ?  ...
    j = i + 1
    if j >= n:
        return ("group", "capturing group", _SK_VARIABLE, i, open_paren + 1)
    ch = content[j]

    # Non-capturing: (?: ...)
    if ch == ":":
        return ("group", "non-capturing", _SK_NAMESPACE, j + 1, j + 1)

    # Atomic: (?> ...)
    if ch == ">":
        return ("atomic", "atomic group", _SK_NAMESPACE, j + 1, j + 1)

    # Lookahead: (?= ...) or (?! ...)
    if ch == "=":
        return ("lookahead", "positive lookahead", _SK_METHOD, j + 1, j + 1)
    if ch == "!":
        return ("lookahead", "negative lookahead", _SK_METHOD, j + 1, j + 1)

    # Lookbehind: (?<= ...) or (?<! ...) or named (?<name>...)
    if ch == "<":
        if j + 1 < n and content[j + 1] == "=":
            return ("lookbehind", "positive lookbehind", _SK_METHOD, j + 2, j + 2)
        if j + 1 < n and content[j + 1] == "!":
            return ("lookbehind", "negative lookbehind", _SK_METHOD, j + 2, j + 2)
        # Named group ``(?<name>...)``
        name_start = j + 1
        k = name_start
        while k < n and (content[k].isalnum() or content[k] == "_"):
            k += 1
        if k < n and content[k] == ">":
            return (content[name_start:k], "named group", _SK_FIELD, k + 1, k)

    # ``(?P<name>...)`` Python-style named group.
    if ch == "P" and j + 1 < n and content[j + 1] == "<":
        name_start = j + 2
        k = name_start
        while k < n and (content[k].isalnum() or content[k] == "_"):
            k += 1
        if k < n and content[k] == ">":
            return (content[name_start:k], "named group", _SK_FIELD, k + 1, k)

    # Inline flag changes ``(?i)`` etc. \u2014 skip; not a structural symbol.
    return ("group", "group", _SK_VARIABLE, j, open_paren + 1)


def _build_symbol_tree(content: str) -> List[_SymbolSpan]:
    """Walk the source and return the top-level structural symbols.

    The scanner skips character classes wholesale (``[...]``) so a
    bracketed ``(`` does not confuse the group counter. It also handles
    backslash escapes and tolerates unbalanced parens by closing any
    still-open groups at end-of-input.
    """
    n = len(content)
    # Stack of open group spans together with the offset where the
    # currently-accumulating alternation branch began.
    open_stack: List[Tuple[_SymbolSpan, int, List[_SymbolSpan]]] = []
    roots: List[_SymbolSpan] = []
    i = 0
    while i < n:
        ch = content[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == "[":
            # Skip a character class; close-bracket terminates.
            j = i + 1
            while j < n:
                if content[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if content[j] == "]":
                    break
                j += 1
            i = j + 1 if j < n else n
            continue
        if ch == "(":
            name, detail, kind, header_end, sel_end = _scan_group_header(content, i)
            span = _SymbolSpan(
                name=name,
                detail=detail,
                kind=kind,
                start_offset=i,
                end_offset=header_end,
                selection_start=i,
                selection_end=sel_end,
            )
            open_stack.append((span, header_end, []))
            i = header_end
            continue
        if ch == ")" and open_stack:
            span, branch_start, branches = open_stack.pop()
            span.end_offset = i + 1
            # When the group contained ``|`` separators the trailing
            # branch (between the last bar and this paren) has not been
            # emitted yet -- flush it now so the outline shows every
            # disjunct, not only the leading ones.
            if branches:
                label = content[branch_start:i].strip() or "(empty)"
                branches.append(
                    _SymbolSpan(
                        name=label,
                        detail="alt branch",
                        kind=_SK_METHOD,
                        start_offset=branch_start,
                        end_offset=i,
                        selection_start=branch_start,
                        selection_end=i,
                    )
                )
                span.children = branches + span.children
            if open_stack:
                open_stack[-1][0].children.append(span)
            else:
                roots.append(span)
            i += 1
            continue
        if ch == "|" and open_stack:
            # Record an alternation branch as a child symbol covering
            # the text between the previous ``|`` (or group header) and
            # the current bar.
            span, branch_start, branches = open_stack[-1]
            label = content[branch_start:i].strip() or "(empty)"
            branch = _SymbolSpan(
                name=label,
                detail="alt branch",
                kind=_SK_METHOD,
                start_offset=branch_start,
                end_offset=i,
                selection_start=branch_start,
                selection_end=i,
            )
            branches.append(branch)
            open_stack[-1] = (span, i + 1, branches)
            i += 1
            continue
        i += 1

    # Close any groups that the user has not yet finished typing so the
    # outline still shows useful structure during mid-edit states.
    while open_stack:
        span, _, branches = open_stack.pop()
        span.end_offset = n
        if branches:
            span.children = branches + span.children
        if open_stack:
            open_stack[-1][0].children.append(span)
        else:
            roots.append(span)
    return roots


def _symbol_span_to_dict(content: str, span: _SymbolSpan) -> Dict[str, Any]:
    """Convert an internal ``_SymbolSpan`` to the LSP ``DocumentSymbol`` dict."""
    return {
        "name": span.name,
        "detail": span.detail,
        "kind": span.kind,
        "range": {
            "start": _offset_to_position(content, span.start_offset),
            "end": _offset_to_position(content, span.end_offset),
        },
        "selectionRange": {
            "start": _offset_to_position(content, span.selection_start),
            "end": _offset_to_position(
                content, max(span.selection_end, span.selection_start + 1)
            ),
        },
        "children": [_symbol_span_to_dict(content, c) for c in span.children],
    }


def extract_document_symbols(content: str) -> List[Dict[str, Any]]:
    """Return a hierarchical outline of a STRling pattern as LSP-shaped dicts.

    The output mirrors the ``DocumentSymbol[]`` LSP response. Callers
    that need the legacy ``SymbolInformation[]`` flat shape should
    flatten the tree themselves \u2014 modern editors prefer the nested form.
    """
    if not content:
        return []
    return [_symbol_span_to_dict(content, s) for s in _build_symbol_tree(content)]


# --------------------------------------------------------------------------- #
# Definition resolution: jump to registry entries                             #
# --------------------------------------------------------------------------- #
#
# Pressing Go-to-Definition on a stdlib pattern name (``email``, ``ip``,
# \u2026) lands the cursor on the corresponding ``"name"`` field inside the
# registry manifest. The line index is computed lazily from the loaded
# manifest path so the lookup stays correct when the registry is
# replaced via ``RegistryManager.reload()``.


def _registry_definition_index() -> Dict[str, Dict[str, Any]]:
    """Build a ``name \u2192 {uri, line, character}`` index from the registry file.

    Returns an empty dict when the registry path is unknown or unreadable
    (which can happen in stripped-down installs that omit ``spec/``).
    \u201cline\u201d and \u201ccharacter\u201d are zero-based to match LSP positions.
    """
    path = registry.loaded_path
    if path is None or not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    index: Dict[str, Dict[str, Any]] = {}
    uri = path.as_uri()
    for entry in registry.entries():
        # Find the *first* occurrence of ``"name": "<entry.name>"`` so the
        # line points at the canonical declaration, not a later mention
        # inside ``trigger_keywords`` or documentation.
        needle = f'"name": "{entry.name}"'
        offset = text.find(needle)
        if offset < 0:
            continue
        line, character = _line_col(text, offset)
        index[entry.name.lower()] = {
            "uri": uri,
            "line": line,
            "character": character,
            "length": len(needle),
        }
    return index


def find_registry_definition(word: str) -> Optional[Dict[str, Any]]:
    """Return an LSP ``Location`` dict for the registry entry matching ``word``.

    Matches against canonical names *and* trigger keywords so jumping
    from ``mail`` lands on the ``email`` definition the same way hover
    routing does. Returns ``None`` when the word is unknown or the
    registry file is missing.
    """
    if not word:
        return None
    entry = registry.lookup_keyword(word)
    if entry is None:
        return None
    index = _registry_definition_index()
    location = index.get(entry.name.lower())
    if location is None:
        return None
    return {
        "uri": location["uri"],
        "range": {
            "start": {"line": location["line"], "character": location["character"]},
            "end": {
                "line": location["line"],
                "character": location["character"] + location["length"],
            },
        },
    }


# --------------------------------------------------------------------------- #
# Pretty printer: AST \u2192 indented STRling DSL                                  #
# --------------------------------------------------------------------------- #
#
# The formatter walks the parsed AST and emits a multi-line, indented
# representation. Indentation depth grows with each nested group or
# alternation; literal runs and atoms stay on a single line so the
# output remains a syntactically-valid STRling pattern that round-trips
# through ``parse()`` without semantic change.


def _format_node(node: Any, depth: int, indent: str) -> str:
    """Render a single AST node, recursing into composite shapes."""
    # Lazy import so the module loads cleanly even when the parser is
    # unavailable (e.g. during partial installs in CI).
    from .nodes import (
        Alternation,
        Anchor,
        BackReference,
        CharacterClass,
        ClassEscape,
        ClassLiteral,
        ClassRange,
        Dot,
        Group,
        Literal,
        Lookaround,
        Quantifier,
        Sequence,
    )

    pad = indent * depth
    if isinstance(node, Literal):
        return _quote_literal(node.value)
    if isinstance(node, Dot):
        return "."
    if isinstance(node, Anchor):
        return _anchor_token(node.at)
    if isinstance(node, BackReference):
        if node.byName is not None:
            return f"\\k<{node.byName}>"
        return f"\\{node.byIndex}"
    if isinstance(node, CharacterClass):
        body = "".join(_format_class_item(it) for it in node.items)
        return f"[{'^' if node.negated else ''}{body}]"
    if isinstance(node, Quantifier):
        inner = _format_node(node.child, depth, indent).lstrip()
        return f"{inner}{_quantifier_suffix(node)}"
    if isinstance(node, Group):
        prefix = _group_prefix(node)
        body = _format_node(node.body, depth + 1, indent)
        return f"{prefix}\n{body}\n{pad})"
    if isinstance(node, Lookaround):
        prefix = "(?" + ("<" if node.dir == "Behind" else "=")
        prefix = "(?<" if node.dir == "Behind" else "(?"
        head = "(?<" if node.dir == "Behind" else "(?"
        sign = "!" if node.neg else "="
        head = head + sign
        body = _format_node(node.body, depth + 1, indent)
        return f"{head}\n{body}\n{pad})"
    if isinstance(node, Alternation):
        # One branch per line, joined by ``|`` on the indentation column.
        rendered = [_format_node(b, depth, indent).lstrip() for b in node.branches]
        sep = f"\n{pad}| "
        return (
            f"{rendered[0]}{sep}" + sep.join(rendered[1:])
            if len(rendered) > 1
            else rendered[0]
        )
    if isinstance(node, Sequence):
        rendered = [_format_node(p, depth, indent).lstrip() for p in node.parts]
        return f"{pad}" + " ".join(rendered)
    # Class items are not standalone nodes but guard against odd inputs.
    if isinstance(node, (ClassLiteral, ClassRange, ClassEscape)):
        return _format_class_item(node)
    return ""


def _quote_literal(value: str) -> str:
    """Escape a literal so it round-trips through the parser unchanged."""
    out = []
    for ch in value:
        if ch in r".^$*+?()[]{}|\\":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _anchor_token(at: str) -> str:
    mapping = {
        "Start": "^",
        "End": "$",
        "WordBoundary": "\\b",
        "NotWordBoundary": "\\B",
        "AbsoluteStart": "\\A",
        "AbsoluteEnd": "\\z",
        "AbsoluteEndOrBeforeNewline": "\\Z",
    }
    return mapping.get(at, "")


def _quantifier_suffix(node: Any) -> str:
    """Render ``min/max/mode`` triple as a regex quantifier suffix."""
    lo, hi, mode = node.min, node.max, getattr(node, "mode", "Greedy")
    if lo == 0 and hi == "Inf":
        base = "*"
    elif lo == 1 and hi == "Inf":
        base = "+"
    elif lo == 0 and hi == 1:
        base = "?"
    elif hi == "Inf":
        base = "{" + str(lo) + ",}"
    elif lo == hi:
        base = "{" + str(lo) + "}"
    else:
        base = "{" + str(lo) + "," + str(hi) + "}"
    if mode == "Lazy":
        return base + "?"
    if mode == "Possessive":
        return base + "+"
    return base


def _group_prefix(node: Any) -> str:
    """Render the opening syntactic prefix of a group, sans body."""
    if getattr(node, "atomic", False):
        return "(?>"
    if not node.capturing:
        return "(?:"
    if node.name:
        return f"(?<{node.name}>"
    return "("


def _format_class_item(item: Any) -> str:
    from .nodes import ClassEscape, ClassLiteral, ClassRange

    if isinstance(item, ClassRange):
        return f"{item.from_ch}-{item.to_ch}"
    if isinstance(item, ClassLiteral):
        return item.ch
    if isinstance(item, ClassEscape):
        if item.type in ("p", "P") and item.property:
            return f"\\{item.type}{{{item.property}}}"
        return f"\\{item.type}"
    return ""


def format_pattern(content: str, indent: str = "  ") -> Dict[str, Any]:
    """Pretty-print a STRling pattern as multi-line indented DSL.

    Returns ``{"success": True, "formatted": "<text>", "diagnostics": []}``
    on success. When the source fails to parse, returns ``success=False``
    with the underlying parse diagnostic so the caller can surface a
    meaningful error instead of silently returning the original text.
    """
    if not content.strip():
        return {
            "success": True,
            "formatted": content,
            "diagnostics": [],
            "version": INTELLIGENCE_PROTOCOL_VERSION,
        }
    try:
        _flags, ast_root = parse(content)
    except STRlingParseError as e:
        return {
            "success": False,
            "formatted": None,
            "diagnostics": [e.to_lsp_diagnostic()],
            "version": INTELLIGENCE_PROTOCOL_VERSION,
        }
    rendered = _format_node(ast_root, 0, indent).rstrip() + "\n"
    return {
        "success": True,
        "formatted": rendered,
        "diagnostics": [],
        "version": INTELLIGENCE_PROTOCOL_VERSION,
    }
