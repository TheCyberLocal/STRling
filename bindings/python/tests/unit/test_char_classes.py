from STRling.core.parser import parse_to_artifact as p2a


def test_simple_class_and_negation():
    art = p2a(r"[abc]")
    cc = art["root"]
    assert cc["kind"] == "CharClass" and cc["negated"] is False
    chars = {it["char"] for it in cc["items"] if it["kind"] == "Char"}
    assert chars == {"a", "b", "c"}

    art2 = p2a(r"[^abc]")
    cc2 = art2["root"]
    assert cc2["kind"] == "CharClass" and cc2["negated"] is True


def test_ranges_and_mixed_items():
    art = p2a(r"[A-Z0-9_-]")
    cc = art["root"]
    kinds = [it["kind"] for it in cc["items"]]
    assert "Range" in kinds and "Char" in kinds


def test_shorthand_and_property_escapes():
    art = p2a(r"[\d\w\s]")
    cc = art["root"]
    escs = [it for it in cc["items"] if it["kind"] == "Esc"]
    assert {e["type"] for e in escs} == {"d", "w", "s"}

    art2 = p2a(r"[\p{L}\P{Greek}]")
    cc2 = art2["root"]
    escs2 = [it for it in cc2["items"] if it["kind"] == "Esc"]
    assert any(e["type"] == "p" and e["property"] for e in escs2)
    assert any(e["type"] == "P" and e["property"] for e in escs2)


def test_class_endpoints_with_escapes_as_literals():
    art = p2a(r"[\x41-\x5a]")
    cc = art["root"]
    rngs = [it for it in cc["items"] if it["kind"] == "Range"]
    assert len(rngs) == 1 and rngs[0]["from"] == "A" and rngs[0]["to"] == "Z"
