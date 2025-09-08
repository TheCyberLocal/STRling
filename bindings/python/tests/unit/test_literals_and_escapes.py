from __future__ import annotations

from typing import Any, Mapping, cast

import pytest
from STRling.core.parser import parse_to_artifact as p2a, ParseError


def node(art: Mapping[str, Any]) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], art["root"])


def test_literal_sequence_and_dot() -> None:
    art = p2a("ab.c")
    seq = node(art)
    assert seq["kind"] == "Seq"
    kinds = [p["kind"] for p in seq["parts"]]
    assert kinds == ["Lit", "Lit", "Dot", "Lit"]


def test_identity_escape_of_metachar() -> None:
    art = p2a(r"\.\(\)\[\]\{\}\^\$\*\+\?\|\\")
    vals = [p["value"] for p in node(art)["parts"]]
    assert "".join(vals) == ".()[]{}^$*+?|\\"


def test_null_and_hex_escapes() -> None:
    art = p2a(r"\0\x41")
    seq = node(art)
    vals = [p["value"] for p in seq["parts"]]
    assert vals == ["\x00", "A"]


def test_unicode_escapes_short_and_braced_and_long() -> None:
    art = p2a(r"\u0041\u{1F600}\U0000005A")  # A, 😀, Z
    vals = [p["value"] for p in node(art)["parts"]]
    assert vals == ["A", "😀", "Z"]


def test_bad_hex_raises() -> None:
    with pytest.raises(ParseError):
        p2a(r"\xG1")


def test_bad_unicode_raises() -> None:
    with pytest.raises(ParseError):
        p2a(r"\u12Z4")
