import pytest

from STRling.simply import Pattern, STRlingError
from STRling.core import nodes


def test_numbered_group_requires_count():
    p = Pattern(nodes.Literal("x"), numbered_group=True)
    with pytest.raises(STRlingError) as exc:
        p()
    assert "Numbered (captured) groups require an explicit exact count" in str(
        exc.value
    )


def test_quantifier_min_defaults_to_zero_when_only_max_provided():
    p = Pattern(nodes.Literal("a"))
    p2 = p(max_rep=3)
    assert isinstance(p2.node, nodes.Quantifier)
    assert p2.node.min == 0
    assert p2.node.max == 3
