from STRling.core.parser import parse
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit


def compile_to_pcre(src: str) -> str:
    flags, ast = parse(src)
    ir_root = Compiler().compile(ast)
    return emit(ir_root, flags.to_dict())


def test_simple_concat_and_quant():
    assert compile_to_pcre(r"ab*c") == r"ab*c"


def test_alt_needs_group_in_seq():
    assert compile_to_pcre(r"a|b") == r"a|b"
    assert compile_to_pcre(r"ba|ab") == r"ba|ab"
    assert compile_to_pcre(r"(?:a|b)c") == r"(?:a|b)c"


def test_named_group_and_backref():
    out = compile_to_pcre(r"(?<num>\d+)-\k<num>")
    assert out == r"(?<num>\d+)-\k<num>"


def test_charclass_and_lazy_quant():
    assert compile_to_pcre(r"[A-Za-z]{3,5}?") == r"[A-Za-z]{3,5}?"


def test_anchors_lookarounds():
    assert compile_to_pcre(r"(?<=foo)bar$") == r"(?<=foo)bar$"


def test_flags_prefix():
    out = compile_to_pcre("%flags i, m\nabc")
    assert out.startswith("(?im)")
    assert out.endswith("abc")
