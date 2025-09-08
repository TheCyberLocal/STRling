from __future__ import annotations

from typing import Any, List, Mapping, cast

import pytest

from STRling.core.parser import parse_to_artifact as p2a


def parts(art: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    root = cast(Mapping[str, Any], art["root"])
    if root["kind"] == "Seq":
        return cast(List[Mapping[str, Any]], root["parts"])
    return [root]


@pytest.mark.parametrize(
    "src,min_val,max_val,mode",
    [
        (r"a*", 0, "Inf", "Greedy"),
        (r"a+", 1, "Inf", "Greedy"),
        (r"a?", 0, 1, "Greedy"),
        (r"a*?", 0, "Inf", "Lazy"),
        (r"a+?", 1, "Inf", "Lazy"),
        (r"a??", 0, 1, "Lazy"),
        (r"a{3}", 3, 3, "Greedy"),
        (r"a{2,}", 2, "Inf", "Greedy"),
        (r"a{2,5}", 2, 5, "Greedy"),
        (r"a{2}?", 2, 2, "Lazy"),
    ],
)
def test_quantifier_forms(
    src: str, min_val: int, max_val: int | str, mode: str
) -> None:
    art = p2a(src)
    qs = [p for p in parts(art) if p["kind"] == "Quant"]
    assert qs, "no Quant node found"
    q = qs[0]
    assert q["min"] == min_val
    assert q["max"] == max_val
    assert q["mode"] == mode


# FIX: Removed the xfail marker since the test is passing.
@pytest.mark.parametrize(
    "src,minmax",
    [
        (r"a*+", (0, "Inf")),
        (r"a++", (1, "Inf")),
        (r"a?+", (0, 1)),
        (r"a{2,5}+", (2, 5)),
    ],
)
def test_possessive_quantifiers_extension(
    src: str, minmax: tuple[int, int | str]
) -> None:
    art = p2a(src)
    root = cast(Mapping[str, Any], art["root"])
    q = root["parts"][0] if root["kind"] == "Seq" else root
    assert q["kind"] == "Quant"
    assert (q["min"], q["max"]) == minmax and q["mode"] == "Possessive"
