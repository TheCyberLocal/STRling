from __future__ import annotations

from STRling.core.parser import parse, parse_to_artifact


def test_flags_none_default() -> None:
    flags, _ = parse("abc")
    assert flags.ignoreCase is False
    assert flags.multiline is False
    assert flags.dotAll is False
    assert flags.unicode is False
    assert flags.extended is False


def test_flags_all_via_directive() -> None:
    src = "%flags i, m, s, u, x\nabc"
    flags, _ = parse(src)
    assert (
        flags.ignoreCase,
        flags.multiline,
        flags.dotAll,
        flags.unicode,
        flags.extended,
    ) == (True, True, True, True, True)


def test_free_spacing_outside_class_ignores_ws_and_comments() -> None:
    src = "%flags x\n a  b  c   # comment\n"
    art = parse_to_artifact(src)
    # Expect Seq of three lits "a","b","c"
    parts = art["root"]["parts"]
    assert [p.get("value") for p in parts if p["kind"] == "Lit"] == ["a", "b", "c"]


def test_free_spacing_inside_class_is_literal() -> None:
    src = "%flags x\n[ #not-comment space and hash ]"
    art = parse_to_artifact(src)
    cc = art["root"]
    assert cc["kind"] == "CharClass"
    # Inside class, space and '#' are literal entries
    chars = {it["char"] for it in cc["items"] if it["kind"] == "Char"}
    assert " " in chars and "#" in chars
