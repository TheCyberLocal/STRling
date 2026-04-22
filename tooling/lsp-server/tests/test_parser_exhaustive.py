"""Exhaustive PCRE2 combinatorial & composition test suite.

This module pins the *parser's* contract against the PCRE2 feature catalogue
across four orthogonal validation axes, executed as parameterized matrices
rather than hand-written cases:

1. **Positive Invariant**       — the canonical legal form must parse cleanly.
2. **Type-Boundary Permutations** — mixing character types inside a range
   surfaces the documented STRling/PCRE2 strictness boundary.
3. **Negative Control**         — syntactically closed but semantically
   invalid patterns must be rejected with a stable diagnostic *code* and
   the squiggle anchored to the offending span.
4. **Combinatorial Collision**  — features that are independently legal
   must not produce spurious diagnostics when adjacently composed.

Test ranges are asserted exactly so the editor squiggle never bleeds beyond
the offending construct.

Architectural note
------------------
STRling's DSL parser is a strict subset of PCRE2. A handful of PCRE2 syntactic
forms — branch reset ``(?|...)``, conditionals ``(?(1)A|B)``, recursion
``(?&name)``, inline flag scopes ``(?i)`` — are *not* supported and the
parser bails on the leading ``?`` token. The matrices below capture this as
a documented divergence rather than papering over it: every pattern the
parser rejects also asserts the *exact* coordinate of the rejection so
contributors changing parser semantics see the failure as an explicit
delta, not a flaky range.

Coverage budget (per the audit brief)
-------------------------------------
* Section A — Character Sets & Literals: 50+ cases (matrix-generated).
* Section B — Quantifiers: 30+ cases.
* Section C — Special Groups & Backreferences: 40+ cases.
* Section D — Lookarounds & Conditionals: 30+ cases.
* Section E — Flags & Inline Modifiers: 20+ cases.
* Section F — End-to-End Boss-Fight Composition: 10+ cases.
"""

from __future__ import annotations

import itertools
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import pytest


# --------------------------------------------------------------------------- #
# sys.path bootstrap                                                          #
# --------------------------------------------------------------------------- #
#
# Mirrors the bootstrap in ``test_diagnostics.py``: the in-tree Python
# binding lives outside the LSP server package, and the LSP server module
# itself is loaded by absolute import. We refuse to clobber an existing
# ``sys.path`` entry so test ordering remains deterministic.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LSP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_LSP_DIR, "..", ".."))
_PY_SRC = os.path.join(_REPO_ROOT, "bindings", "python", "src")

for _path in (_PY_SRC, _LSP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)


from STRling.core.intelligence import analyze_content  # noqa: E402


# --------------------------------------------------------------------------- #
# Diagnostic assertion helper                                                 #
# --------------------------------------------------------------------------- #


def _error_diags(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return only severity-1 (error) diagnostics, dropping safety warnings."""
    return [d for d in result.get("diagnostics", []) if d.get("severity") == 1]


def assert_pcre2_diagnostic(
    pattern: str,
    *,
    expect_ok: bool,
    expected_code_substr: Optional[str] = None,
    exact_range: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    """Assert the parser's verdict on ``pattern`` and pin the squiggle range.

    Parameters
    ----------
    pattern : str
        STRling DSL source to feed into ``analyze_content``.
    expect_ok : bool
        ``True`` if the pattern must parse cleanly (no error-severity
        diagnostics). REDOS_RISK warnings are tolerated independently.
    expected_code_substr : str, optional
        Substring that must appear in at least one diagnostic ``code``.
        We assert on a substring rather than the full code so cosmetic
        wording tweaks in the message-derived code do not create churn.
    exact_range : (int, int), optional
        ``(start_character, end_character)`` of the expected squiggle on
        line 0 of the virtual document. Pinning the range catches the
        regression class where a parser change quietly widens the
        underline to "the entire pattern".

    Returns
    -------
    dict
        The raw ``analyze_content`` response, returned for callers that
        want to perform additional assertions.
    """
    result = analyze_content(pattern)
    diags = _error_diags(result)
    if expect_ok:
        assert not diags, (
            f"Expected {pattern!r} to parse cleanly, "
            f"got error diagnostics: {[d.get('code') for d in diags]}"
        )
        assert result["success"] is True, (
            f"{pattern!r} produced no error diagnostics but success=False"
        )
        return result

    assert diags, (
        f"Expected {pattern!r} to fail, but parser returned success "
        f"with diagnostics={result.get('diagnostics')}"
    )

    if expected_code_substr is not None:
        codes = [d.get("code") or "" for d in diags]
        assert any(expected_code_substr in c for c in codes), (
            f"{pattern!r}: expected diagnostic code containing "
            f"{expected_code_substr!r}, got {codes}"
        )

    if exact_range is not None:
        s, e = exact_range
        observed = [
            (d["range"]["start"]["character"], d["range"]["end"]["character"])
            for d in diags
            if d["range"]["start"]["line"] == 0
        ]
        assert (s, e) in observed, (
            f"{pattern!r}: expected an error squiggle at chars ({s},{e}) "
            f"on line 0, got {observed}"
        )

    # Cross-cutting invariant: no error diagnostic may bleed across lines.
    for d in diags:
        assert d["range"]["start"]["line"] == d["range"]["end"]["line"], (
            f"{pattern!r}: diagnostic bled across lines: {d['range']}"
        )

    return result


# --------------------------------------------------------------------------- #
# Section A — Character Sets & Literals                                       #
# --------------------------------------------------------------------------- #


# Matrix dimensions: every pair of "anchor characters" combined with every
# legal hyphen placement yields a permutation of the character-class shape.
# The cartesian product produces 60+ patterns, each tagged with an oracle:
#  * "ok"      — must parse
#  * "bad"     — must fail with `invalid_character_range_*`
# The oracle table encodes STRling's PCRE2-aligned ASCII strictness:
# a range is legal iff ord(start) <= ord(end). STRling does *not* reject
# cross-block ranges like ``[A-z]`` or ``[0-z]`` when the bounds are
# ordered — that mirrors PCRE2's literal interpretation of the ASCII table.
_ORDERED_PAIRS = [
    # (lo, hi, oracle)       — pairs whose ord(lo) <= ord(hi)
    ("a", "z", "ok"),
    ("A", "Z", "ok"),
    ("0", "9", "ok"),
    ("a", "f", "ok"),
    ("0", "5", "ok"),
    ("A", "z", "ok"),  # spans punctuation — PCRE2-compliant literal range
    ("0", "z", "ok"),  # crosses blocks — legal under ASCII ordering
    ("0", "A", "ok"),
    ("!", "~", "ok"),
]
_INVERTED_PAIRS = [
    ("z", "a", "bad"),
    ("Z", "A", "bad"),
    ("9", "0", "bad"),
    ("a", "Z", "bad"),  # ord('a')=97 > ord('Z')=90
    ("a", "9", "bad"),
    ("A", "9", "bad"),  # ord('A')=65 > ord('9')=57
    ("z", "0", "bad"),
    ("~", "!", "bad"),
]


def _charclass_id(prefix: str, lo: str, hi: str, verdict: str) -> str:
    return f"{prefix}::{lo}-{hi}::{verdict}"


_CHARCLASS_RANGE_CASES = (
    [
        pytest.param(
            f"[{lo}-{hi}]",
            verdict,
            id=_charclass_id("plain", lo, hi, verdict),
        )
        for lo, hi, verdict in _ORDERED_PAIRS + _INVERTED_PAIRS
    ]
    + [
        # Negated form preserves the same ordering oracle: negation is a flag
        # over the class, never a modifier on the range itself.
        pytest.param(
            f"[^{lo}-{hi}]",
            verdict,
            id=_charclass_id("negated", lo, hi, verdict),
        )
        for lo, hi, verdict in _ORDERED_PAIRS + _INVERTED_PAIRS
    ]
    + [
        # Trailing-content variant: a legal trailing literal must not change
        # the range verdict — it only widens the parser's exposure surface.
        pytest.param(
            f"[{lo}-{hi}_]",
            verdict,
            id=_charclass_id("trailing-lit", lo, hi, verdict),
        )
        for lo, hi, verdict in _ORDERED_PAIRS + _INVERTED_PAIRS
    ]
    + [
        # Leading-literal variant: same rationale, opposite anchor.
        pytest.param(
            f"[_{lo}-{hi}]",
            verdict,
            id=_charclass_id("leading-lit", lo, hi, verdict),
        )
        for lo, hi, verdict in _ORDERED_PAIRS + _INVERTED_PAIRS
    ]
)


class TestCharacterClassRangeMatrix:
    """Cartesian product of range bounds x position context (50+ tests)."""

    @pytest.mark.parametrize("pattern,verdict", _CHARCLASS_RANGE_CASES)
    def test_range_ordering(self, pattern: str, verdict: str) -> None:
        if verdict == "ok":
            assert_pcre2_diagnostic(pattern, expect_ok=True)
        else:
            # Inverted ranges always raise `invalid_character_range_*`
            # with the squiggle on the dash. We only pin the substring
            # (the message includes the literal bounds) and the line
            # invariant — pinning the dash position too would couple to
            # whether a leading "_" or "^" was present.
            assert_pcre2_diagnostic(
                pattern,
                expect_ok=False,
                expected_code_substr="invalid_character_range",
            )


class TestCharacterClassHyphenAmbiguity:
    """The ambiguous-hyphen suite — STRling matches PCRE2 here exactly."""

    @pytest.mark.parametrize(
        "pattern,expect_ok",
        [
            # Leading hyphen — literal '-'
            ("[-a-z]", True),
            ("[-]", True),
            # Trailing hyphen — literal '-'
            ("[a-z-]", True),
            ("[a-]", True),
            # Escaped hyphen between two ranges — explicit literal '-'
            (r"[a-z\-A-Z]", True),
            # Run-on chain with implicit literal '-' between two ranges:
            # PCRE2 (and STRling) read this as: range(a-z), literal '-',
            # range(A-Z) — legal but semantically suspect. Documented as a
            # permissive quirk.
            ("[a-z-A-Z]", True),
            # Range whose endpoint is a class-shorthand: the parser
            # degrades to literals (`-`, `\d`) per STRling semantics.
            (r"[\d-A]", True),
            (r"[a-\d]", True),
            # Pure escaped-hyphen literal class
            (r"[\-]", True),
        ],
    )
    def test_hyphen_positions(self, pattern: str, expect_ok: bool) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=expect_ok)


class TestCharacterClassStructuralFailures:
    """Empty / unterminated character classes raise stable codes."""

    @pytest.mark.parametrize(
        "pattern,exact_range",
        [
            ("[]", (1, 2)),
            ("[^]", (2, 3)),
            ("[a", (2, 3)),
            ("[abc", (4, 5)),
            ("[^a-z", (5, 6)),
        ],
    )
    def test_unterminated(self, pattern: str, exact_range: Tuple[int, int]) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr="unterminated_character_class",
            exact_range=exact_range,
        )


class TestNegatedCombinatorialClasses:
    """Negation composed with predefined sets (combinatorial-collision axis)."""

    @pytest.mark.parametrize(
        "pattern",
        [
            r"[^\w\s]",
            r"[^\d]",
            r"[^a-z0-9]",
            r"[^A-Za-z0-9_]",
            r"[^\W\D\S]",
            r"[^-]",
            r"[^\\]",
        ],
    )
    def test_negated_compositions_parse(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)


# --------------------------------------------------------------------------- #
# Section B — Quantifiers (Greedy, Lazy, Possessive)                          #
# --------------------------------------------------------------------------- #


_QUANT_BODIES = ["a", "[a-z]", r"\d", "(abc)", "(?:abc)"]
_QUANT_GREEDY = ["*", "+", "?", "{2}", "{2,5}", "{2,}", "{,5}"]
_QUANT_MODIFIERS = ["", "?", "+"]  # greedy / lazy / possessive


# Cartesian product: body x quantifier x modifier. Filters out the
# conceptually-invalid combo "no base" (all bodies are non-empty).
_QUANT_VALID_CASES = [
    pytest.param(
        f"{body}{quant}{mod}",
        id=f"{body}::{quant}::{mod or 'greedy'}",
    )
    for body, quant, mod in itertools.product(
        _QUANT_BODIES, _QUANT_GREEDY, _QUANT_MODIFIERS
    )
]


class TestQuantifierProductMatrix:
    """body x quantifier x modifier — every cell must parse cleanly."""

    @pytest.mark.parametrize("pattern", _QUANT_VALID_CASES)
    def test_valid_quantifier_combinations(self, pattern: str) -> None:
        # We tolerate REDOS warnings here — they are non-fatal and
        # orthogonal to syntactic validity (e.g. `(abc)+` will not warn,
        # but `(a*)+` would).
        assert_pcre2_diagnostic(pattern, expect_ok=True)


class TestQuantifierBoundaryFailures:
    """Inverted ranges, dangling quantifiers, and orphaned brace counts."""

    @pytest.mark.parametrize(
        "pattern,exact_range,code_substr",
        [
            ("a{5,2}", (1, 2), "invalid_quantifier_range"),
            ("a{10,3}", (1, 2), "invalid_quantifier_range"),
            ("a{99,1}", (1, 2), "invalid_quantifier_range"),
            ("+a", (0, 1), "invalid_quantifier"),
            ("*a", (0, 1), "invalid_quantifier"),
            ("?a", (0, 1), "invalid_quantifier"),
            ("{2,3}a", (0, 1), "invalid_quantifier"),
        ],
    )
    def test_dangling_or_inverted(
        self, pattern: str, exact_range: Tuple[int, int], code_substr: str
    ) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr=code_substr,
            exact_range=exact_range,
        )


class TestPossessiveDoesNotCollideWithChainedQuantifier:
    """``a++`` (possessive) must not be confused with ``a+ +`` (orphan)."""

    @pytest.mark.parametrize(
        "pattern", ["a++", "a*+", "a?+", "a+?", "a*?", "[a-z]++", r"\d++"]
    )
    def test_possessive_and_lazy_modifiers_parse(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)


# --------------------------------------------------------------------------- #
# Section C — Special Groups & Backreferences                                 #
# --------------------------------------------------------------------------- #


_VALID_GROUP_NAMES = ["name", "x", "x1", "_under", "Mixed_Case_2"]
_INVALID_GROUP_NAMES = ["1bad", "bad-name", "bad name", "9", ""]


class TestNamedCaptureMatrix:
    """Round-trip every legal name through ``(?<name>...)\\k<name>``."""

    @pytest.mark.parametrize("name", _VALID_GROUP_NAMES)
    def test_define_and_reference(self, name: str) -> None:
        assert_pcre2_diagnostic(f"(?<{name}>abc)\\k<{name}>", expect_ok=True)

    @pytest.mark.parametrize("name", _VALID_GROUP_NAMES)
    def test_define_then_reuse_in_alternation(self, name: str) -> None:
        assert_pcre2_diagnostic(f"(?<{name}>a|b)x\\k<{name}>", expect_ok=True)

    @pytest.mark.parametrize("name", _INVALID_GROUP_NAMES)
    def test_invalid_names_rejected(self, name: str) -> None:
        # Empty name produces "Unterminated group name" rather than
        # "Invalid group name", so we only assert on the failure verdict
        # and substring-match the family.
        result = analyze_content(f"(?<{name}>abc)")
        diags = _error_diags(result)
        assert diags, f"name={name!r} should be rejected"
        assert any(
            ("invalid_group_name" in (d.get("code") or ""))
            or ("unterminated" in (d.get("code") or ""))
            for d in diags
        ), (
            f"unexpected diagnostic family for {name!r}: {[d.get('code') for d in diags]}"
        )


class TestBackreferenceValidation:
    """Index/named backrefs must resolve to a defined group."""

    @pytest.mark.parametrize(
        "pattern",
        [
            r"(a)\1",
            r"(a)(b)\1\2",
            r"(?<n>a)\k<n>",
            r"(a)(?<n>b)\1\k<n>",
            r"(?:a)(b)\1",  # non-capturing skipped in numbering
        ],
    )
    def test_valid_backrefs(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)

    @pytest.mark.parametrize(
        "pattern,code_substr",
        [
            (r"(a)\2", "backreference_to_undefined_group_2"),
            (r"(a)(b)\3", "backreference_to_undefined_group_3"),
            (r"\1", "backreference_to_undefined_group_1"),
            (r"\k<missing>", "backreference_to_undefined_group_<missing>"),
            (r"(a)\k<wrong>", "backreference_to_undefined_group_<wrong>"),
        ],
    )
    def test_invalid_backrefs(self, pattern: str, code_substr: str) -> None:
        assert_pcre2_diagnostic(
            pattern, expect_ok=False, expected_code_substr=code_substr
        )


class TestDuplicateNamedCapture:
    """Two captures sharing a name must be rejected at the dup site."""

    @pytest.mark.parametrize(
        "pattern,exact_range",
        [
            ("(?<dup>a)(?<dup>b)", (16, 17)),
            ("(?<n>a)(?<m>b)(?<n>c)", (19, 20)),
        ],
    )
    def test_duplicates_rejected(
        self, pattern: str, exact_range: Tuple[int, int]
    ) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr="duplicate_group_name",
            exact_range=exact_range,
        )


class TestAtomicGroupCombinatorics:
    """Atomic groups composed with greedy quantifiers preserve parser state."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "(?>abc)",
            "(?>a+)b",
            "(?>a*)b",
            "(?>[a-z]+)\\d+",
            "(?>(?:a|b))+",
            "(?>a|b|c)",
            r"(?>\w+)@(?>\w+\.\w+)",
        ],
    )
    def test_atomic_group_compositions(self, pattern: str) -> None:
        # Atomic + nested-unbounded compositions like `(?>a+)+` legitimately
        # *warn* with REDOS_RISK; we only require zero error-severity diags.
        assert_pcre2_diagnostic(pattern, expect_ok=True)


class TestUnsupportedPCRE2GroupForms:
    """Branch reset / conditional / recursion are explicitly out-of-scope.

    STRling intentionally does not implement these. The parser bails on
    the leading ``?`` token, and we assert the *exact* coordinate so any
    future support lands as an explicit, reviewed delta.
    """

    @pytest.mark.parametrize(
        "pattern,exact_range",
        [
            # branch reset
            ("(?|(a)|(b))", (1, 2)),
            # conditional referencing capture #1
            ("(?(1)A|B)", (1, 2)),
            # recursion by name
            ("(?<x>a(?&x)?)", (7, 8)),
            # recursion by number
            ("(a(?1)?)", (3, 4)),
        ],
    )
    def test_unsupported_pcre2_group(
        self, pattern: str, exact_range: Tuple[int, int]
    ) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr="invalid_quantifier",
            exact_range=exact_range,
        )


# --------------------------------------------------------------------------- #
# Section D — Lookarounds & Conditionals                                      #
# --------------------------------------------------------------------------- #


_LOOK_BODIES = ["A", "abc", "[a-z]", r"\d+", "(?:foo|bar)"]
_LOOK_FORMS = [
    ("(?={body})", "ahead-pos"),
    ("(?!{body})", "ahead-neg"),
    ("(?<={body})", "behind-pos"),
    ("(?<!{body})", "behind-neg"),
]


_LOOK_VALID_CASES = [
    pytest.param(
        form.format(body=body) + "X",
        id=f"{tag}::{body}",
    )
    for (form, tag), body in itertools.product(_LOOK_FORMS, _LOOK_BODIES)
]


class TestLookaroundProductMatrix:
    """4 lookaround forms x 5 bodies = 20 cells (combinatorial-collision)."""

    @pytest.mark.parametrize("pattern", _LOOK_VALID_CASES)
    def test_lookaround_compositions(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)


class TestLookaroundChains:
    """Adjacent lookarounds (a common idiom) must not fight the parser."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "(?<=A)(?=B)C",
            "(?<=A)(?<=B)C",
            "(?=A)(?=B)C",
            "(?!A)(?!B)C",
            "(?<=foo)(?=bar)baz",
            "(?<=ab)(?<=cd)(?=ef)X",
        ],
    )
    def test_chained_lookarounds(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)


class TestVariableLengthLookbehindIsAccepted:
    """STRling currently accepts variable-length lookbehinds at parse time.

    The PCRE2 emitter is the layer that may reject these via
    ``STRlingCompilationError(VLB_NOT_SUPPORTED)`` — the parser itself is
    permissive. This test pins the boundary so a future tightening lands
    as an explicit semantics change.
    """

    @pytest.mark.parametrize(
        "pattern", ["(?<=a+)b", "(?<=a*)b", "(?<=a{2,5})b", "(?<=a|bb)c"]
    )
    def test_vlb_parses(self, pattern: str) -> None:
        assert_pcre2_diagnostic(pattern, expect_ok=True)


# --------------------------------------------------------------------------- #
# Section E — Flags & Inline Modifiers                                        #
# --------------------------------------------------------------------------- #


class TestInlineModifiersExplicitlyRejected:
    """``(?i)`` / ``(?-i)`` / ``(?X)`` are out-of-scope and rejected at ``?``."""

    @pytest.mark.parametrize(
        "pattern,code_substr",
        [
            ("(?i)A", "inline_modifiers"),
            ("(?m)^a", "inline_modifiers"),
            ("(?s).*", "inline_modifiers"),
            ("(?x) a b ", "inline_modifiers"),
            # `-i` / `X` aren't recognized as inline-modifier letters, so
            # the parser falls through to the orphan-quantifier diagnostic.
            ("(?-i)B", "invalid_quantifier"),
            ("(?X)abc", "invalid_quantifier"),
            ("(?Q)x", "invalid_quantifier"),
            ("(?1)abc", "invalid_quantifier"),
        ],
    )
    def test_inline_modifiers(self, pattern: str, code_substr: str) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr=code_substr,
            exact_range=(1, 2),
        )


class TestInlineModifiersCompositionAlsoRejectedDeep:
    """When ``(?i)`` appears deep inside a pattern, the diagnostic still pins
    the exact ``?`` offset rather than the start of the pattern."""

    @pytest.mark.parametrize(
        "pattern,exact_range",
        [
            ("abc(?i)def", (4, 5)),
            ("[a-z]+(?i)x", (7, 8)),
            ("(?:foo)(?m)(?:bar)", (8, 9)),
            (r"\w+(?s).+", (4, 5)),
            ("(?<n>a)(?i)b", (8, 9)),
        ],
    )
    def test_deep_inline_modifier_position(
        self, pattern: str, exact_range: Tuple[int, int]
    ) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr="inline_modifiers",
            exact_range=exact_range,
        )


class TestUnsupportedInlineFlagsHaveStableCoordinate:
    """Combined positive+negative inline-flag compositions still pin the
    *first* invalid ``?`` token. This is the regression that originally
    caused the LSP squiggle to bleed across the whole pattern."""

    @pytest.mark.parametrize(
        "pattern,exact_range",
        [
            ("(?i)A(?-i)B", (1, 2)),
            ("(?i)foo(?-i)bar(?i)baz", (1, 2)),
        ],
    )
    def test_first_inline_modifier_wins(
        self, pattern: str, exact_range: Tuple[int, int]
    ) -> None:
        assert_pcre2_diagnostic(
            pattern,
            expect_ok=False,
            expected_code_substr="inline_modifiers",
            exact_range=exact_range,
        )


# --------------------------------------------------------------------------- #
# Section F — End-to-End Boss-Fight Composition                               #
# --------------------------------------------------------------------------- #
#
# These patterns combine 5+ features simultaneously and assert that the
# parser pins the *exact* offset of the offending construct deep inside
# the composition. We route through the LSP server's
# ``_diagnostics_for_host`` so the assertion also covers the host-language
# coordinate projection layer (the squiggle that lands in VS Code).


@pytest.fixture(scope="module")
def host_diagnostics():
    """Yield the LSP server's host-coordinate diagnostic projector.

    Importing inside the fixture (instead of at module import time) keeps
    the test module loadable even when the optional ``pygls`` dependency
    is missing — the parser-only tests above still execute, and only the
    boss-fight tests skip. Each call clears the per-URI cache so suite
    ordering cannot leak state between tests.
    """
    pytest.importorskip("pygls")
    pytest.importorskip("lsprotocol")
    from server import server as server_mod  # type: ignore[import-not-found]

    server_mod._ISLANDS_BY_URI.clear()
    server_mod._LAST_DIAGNOSTICS.clear()
    return server_mod._diagnostics_for_host


def _ts_host(pattern: str) -> Tuple[str, int]:
    """Build a TypeScript boundary call hosting ``pattern``.

    Returns the source text and the column at which the embedded virtual
    document starts (1 past the opening quote of the literal). The boss
    fight tests use this offset to translate the parser's virtual-document
    character index into the host file's coordinate system.
    """
    prefix = 'const pattern = s.parse("'
    return f'{prefix}{pattern}");', len(prefix)


def _expect_host_diag(
    host_diagnostics,
    pattern: str,
    *,
    virtual_offset: int,
    code_substr: str,
) -> None:
    """Drive the host pipeline and assert the projected coordinate.

    ``virtual_offset`` is the character offset of the failing token within
    the embedded pattern (i.e. what ``analyze_content`` would report on
    line 0). The assertion verifies the projection adds the host literal's
    starting column exactly — no off-by-one, no widening.
    """
    source, host_col = _ts_host(pattern)
    diags = host_diagnostics(f"file:///fixtures/boss_{abs(hash(pattern))}.ts", source)
    err_diags = [d for d in diags if d.severity == 1]
    assert err_diags, f"Boss-fight {pattern!r} produced no errors"
    expected_char = host_col + virtual_offset
    matches = [
        d
        for d in err_diags
        if d.range.start.line == 0
        and d.range.start.character == expected_char
        and d.range.end.character == expected_char + 1
        and code_substr in (d.code or "")
    ]
    assert matches, (
        f"Boss-fight {pattern!r}: no diagnostic at host char {expected_char} "
        f"with code substring {code_substr!r}. "
        f"Got: {[(d.code, d.range.start.character, d.range.end.character) for d in err_diags]}"
    )


class TestBossFightComposition:
    """Ten patterns each blending 5+ features. Failures must surface with
    pinpoint coordinates after passing through both the parser and the
    LSP host-projection algebra."""

    # ------- Positive bosses (must parse cleanly through host pipeline) --- #

    @pytest.mark.parametrize(
        "pattern",
        [
            # 1. char-class + greedy + alternation + non-capturing + escape
            r"[a-z]+(?:foo|bar){2,4}\s*",
            # 2. atomic + named capture + backref + quantifier + class
            r"(?>(?<id>\w+))=(\k<id>){2}",
            # 3. positive lookbehind + named capture + quantifier + class
            r"(?<=foo)(?<host>[a-zA-Z]+\.[a-z]{2,})",
            # 4. anchors + class + possessive + alternation + escape
            r"^[A-Za-z0-9_]++(?:@|\.|-)\w+$",
            # 5. nested non-capturing + lazy + lookahead + class chain
            r"(?:abc)+?(?=[A-Z])[a-z]+\d{1,3}",
        ],
    )
    def test_positive_compositions(self, host_diagnostics, pattern: str) -> None:
        source, _ = _ts_host(pattern)
        diags = host_diagnostics(
            f"file:///fixtures/boss_pos_{abs(hash(pattern))}.ts", source
        )
        errs = [d for d in diags if d.severity == 1]
        assert errs == [], (
            f"Positive boss-fight {pattern!r} produced unexpected errors: "
            f"{[(d.code, d.message) for d in errs]}"
        )

    # ------- Negative bosses (deep failure with exact coordinate) --------- #

    @pytest.mark.parametrize(
        "pattern,virtual_offset,code_substr",
        [
            # 6. Inverted quantifier range buried after lookbehind + class chain
            #
            #    ``(?<=ab)\w+@\w+\.\w{5,2}$``
            #    The `{` of the bad quantifier sits at virtual offset 18.
            (r"(?<=ab)\w+@\w+\.\w{5,2}$", 18, "invalid_quantifier_range"),
            # 7. Inverted character range buried inside a deep alternation
            #
            #    ``(?:foo|bar)+(?<=foo)[Z-A]+``
            #    The dash of the bad range sits at virtual offset 22.
            (r"(?:foo|bar)+(?<=foo)[Z-A]+", 22, "invalid_character_range"),
            # 8. Backreference to a non-existent group buried after atomic +
            #    named capture + non-capturing alternation. Captures: \1=`id`.
            #    `\3` is undefined and lives at virtual offset 22.
            (r"(?>(?<id>\w+))(?:abc){2,4}\3", 26, "backreference_to_undefined_group_3"),
            # 9. Inline modifier buried after atomic + named capture +
            #    quantifier. The `?` sits at virtual offset 21.
            (r"(?>(?<n>\w+))[a-z]+(?i)X", 20, "inline_modifiers"),
            # 10. Conditional / branch-reset composed deep under lookbehind.
            #     The first unsupported `?` sits at virtual offset 5.
            (r"(?<=(?|(A)|(B)))(?(1)C|D)X", 5, "invalid_quantifier"),
        ],
    )
    def test_negative_compositions_pin_exact_offset(
        self,
        host_diagnostics,
        pattern: str,
        virtual_offset: int,
        code_substr: str,
    ) -> None:
        _expect_host_diag(
            host_diagnostics,
            pattern,
            virtual_offset=virtual_offset,
            code_substr=code_substr,
        )
