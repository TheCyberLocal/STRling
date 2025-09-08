import pytest
from STRling.core.parser import parse_to_artifact as p2a, ParseError


def test_capturing_noncapturing_atomic_groups():
    art = p2a(r"(abc)(?:x)(?>y)")
    seq = art["root"]
    assert [p["kind"] for p in seq["parts"]] == ["Group", "Group", "Group"]
    cap, noncap, atomic = seq["parts"]
    assert cap["capturing"] is True and noncap["capturing"] is False
    assert atomic.get("atomic") is True


def test_named_capture_and_backref():
    art = p2a(r"(?<num>\d+)-\k<num>")
    seq = art["root"]
    assert seq["parts"][0]["kind"] == "Group" and seq["parts"][0].get("name") == "num"
    assert (
        seq["parts"][2]["kind"] == "Backref" and seq["parts"][2].get("byName") == "num"
    )


def test_numeric_backref():
    art = p2a(r"(a)(b)\1")
    parts = art["root"]["parts"]
    assert parts[-1]["kind"] == "Backref" and parts[-1]["byIndex"] == 1


@pytest.mark.xfail(reason="Forward ref detection may not be implemented yet")
def test_forward_backref_should_error():
    with pytest.raises(ParseError):
        p2a(r"\1(a)")


def test_lookarounds_parse():
    for src, (dir, neg) in [
        (r"(?=foo)", ("Ahead", False)),
        (r"(?!foo)", ("Ahead", True)),
        (r"(?<=foo)", ("Behind", False)),
        (r"(?<!foo)", ("Behind", True)),
    ]:
        art = p2a(src)
        look = art["root"]
        assert look["kind"] == "Look" and look["dir"] == dir and look["neg"] == neg
