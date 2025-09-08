from __future__ import annotations

from typing import Final

import pytest

from STRling.core.parser import parse
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit


def compile_to_pcre(src: str) -> str:
    """
    DSL -> AST -> IR -> PCRE2 string.

    We always pass flags as a plain dict[str, bool] so the emitter
    doesn't need to import the Flags class.
    """
    flags, ast = parse(src)
    ir_root = Compiler().compile(ast)
    return emit(ir_root, flags.to_dict())


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (r"ab*c", r"ab*c"),
        (r"a|b", r"a|b"),
        (r"(?<num>\d+)-\k<num>", r"(?<num>\d+)-\k<num>"),
        (r"^foo$", r"^foo$"),
        (r"(?=bar)baz", r"(?=bar)baz"),
        (r"(?<=foo)bar", r"(?<=foo)bar"),
        (r"[A-Za-z_]\w*", r"[A-Za-z_]\w*"),
        (r"\Afoo\Zbar\z", r"\Afoo\Zbar\z"),  # absolute anchors
    ],
)
def test_emit_basic_shapes(src: str, expected: str) -> None:
    assert compile_to_pcre(src) == expected


def test_flags_prefix_rendering_im_ms() -> None:
    out: Final[str] = compile_to_pcre("%flags i, m\nabc")
    assert out.startswith("(?im)")
    assert out.endswith("abc")


# FIX: Removed the xfail marker since the test is passing.
@pytest.mark.parametrize(
    ("src", "expected"),
    [
        (r"a*+", r"a*+"),
        (r"a++", r"a++"),
        (r"a?+", r"a?+"),
        (r"a{2,5}+", r"a{2,5}+"),
    ],
)
def test_emit_possessive_quantifiers(src: str, expected: str) -> None:
    assert compile_to_pcre(src) == expected
