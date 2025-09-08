from STRling.core.parser import parse_to_artifact as p2a


def test_line_anchors_core():
    art = p2a(r"^foo$")
    parts = art["root"]["parts"]
    assert parts[0] == {"kind": "Anchor", "at": "Start"}
    assert parts[-1] == {"kind": "Anchor", "at": "End"}


def test_word_boundary():
    art = p2a(r"\bword\b")
    seq = art["root"]
    assert (
        seq["parts"][0]["kind"] == "Anchor" and seq["parts"][0]["at"] == "WordBoundary"
    )
    assert (
        seq["parts"][-1]["kind"] == "Anchor"
        and seq["parts"][-1]["at"] == "WordBoundary"
    )


def test_absolute_anchors_extension():
    art = p2a(r"\Afoo\Zbar\z")
    seq = art["root"]
    ats = [p["at"] for p in seq["parts"] if p["kind"] == "Anchor"]
    # AbsoluteStart, EndBeforeFinalNewline, AbsoluteEnd
    assert ats == ["AbsoluteStart", "EndBeforeFinalNewline", "AbsoluteEnd"]


def test_dot_vs_dotall_flag():
    a1 = p2a(r".")
    a2 = p2a("%flags s\n.")
    # structure identical; flag is on in a2
    assert a1["flags"]["dotAll"] is False and a2["flags"]["dotAll"] is True
