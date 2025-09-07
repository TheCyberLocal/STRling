
import json
from core.parser import parse_to_artifact

def test_named_groups_and_backref():
    src = r"""
    %flags i, u, x
    <(?<tag>\w+)>.*?</\k<tag>>
    """
    art = parse_to_artifact(src)
    assert art["flags"]["ignoreCase"] is True
    assert art["flags"]["unicode"] is True
    assert art["flags"]["extended"] is True
    assert art["root"]["kind"] in ("Seq", "Alt")  # structure exists

def test_charclass_and_quantifiers():
    src = r"[A-Za-z]{3,5}?"
    art = parse_to_artifact(src)
    q = art["root"]
    assert q["kind"] == "Quant"
    assert q["min"] == 3 and q["max"] == 5 and q["mode"] == "Lazy"
    assert q["child"]["kind"] == "CharClass"

def test_lookarounds_and_anchors():
    src = r"(?<=foo)bar$"
    art = parse_to_artifact(src)
    seq = art["root"]
    assert seq["kind"] == "Seq"
    assert seq["parts"][-1]["kind"] == "Anchor" and seq["parts"][-1]["at"] == "End"
