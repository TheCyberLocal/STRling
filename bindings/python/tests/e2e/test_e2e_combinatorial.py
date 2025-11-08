"""
Test Design — e2e/test_e2e_combinatorial.py

## Purpose
This test suite provides systematic combinatorial E2E validation to ensure that
different STRling features work correctly when combined. It follows a risk-based,
tiered approach to manage test complexity while achieving comprehensive coverage.

## Description
Unlike unit tests that test individual features in isolation, this suite tests
feature interactions using two strategies:

1. **Tier 1 (Pairwise)**: Tests all N=2 combinations of core features
2. **Tier 2 (Strategic Triplets)**: Tests N=3 combinations of high-risk features

The tests verify that the full compile pipeline (parse -> compile -> emit)
correctly handles feature interactions.

## Scope
-   **In scope:**
    -   Pairwise (N=2) combinations of all core features
    -   Strategic triplet (N=3) combinations of high-risk features
    -   End-to-end validation from DSL to PCRE2 output
    -   Detection of interaction bugs between features

-   **Out of scope:**
    -   Exhaustive N³ or higher combinations
    -   Runtime behavior validation (covered by conformance tests)
    -   Individual feature testing (covered by unit tests)
"""

import pytest
from STRling.core.parser import parse
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit as emit_pcre2


# --- Helper Function ------------------------------------------------------------


def compile_to_pcre(src: str) -> str:
    """A helper to run the full DSL -> PCRE2 string pipeline."""
    flags, ast = parse(src)
    ir_root = Compiler().compile(ast)
    return emit_pcre2(ir_root, flags)


# --- Tier 1: Pairwise Combinatorial Tests (N=2) --------------------------------


class TestTier1PairwiseCombinations:
    """
    Tests all pairwise (N=2) combinations of core STRling features.
    """

    # Flags + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Flags + Literals
            ("%flags i\nhello", r"(?i)hello"),
            ("%flags x\na b c", r"(?x)abc"),
            # Flags + Character Classes
            ("%flags i\n[a-z]+", r"(?i)[a-z]+"),
            ("%flags u\n\\p{L}+", r"(?u)\p{L}+"),
            # Flags + Anchors
            ("%flags m\n^start", r"(?m)^start"),
            ("%flags m\nend$", r"(?m)end$"),
            # Flags + Quantifiers
            ("%flags s\na*", r"(?s)a*"),
            ("%flags x\na{2,5}", r"(?x)a{2,5}"),
            # Flags + Groups
            ("%flags i\n(hello)", r"(?i)(hello)"),
            ("%flags x\n(?<name>\\d+)", r"(?x)(?<name>\d+)"),
            # Flags + Lookarounds
            ("%flags i\n(?=test)", r"(?i)(?=test)"),
            ("%flags m\n(?<=^foo)", r"(?m)(?<=^foo)"),
            # Flags + Alternation
            ("%flags i\na|b|c", r"(?i)a|b|c"),
            ("%flags x\nfoo | bar", r"(?x)foo|bar"),
            # Flags + Backreferences
            ("%flags i\n(\\w+)\\s+\\1", r"(?i)(\w+)\s+\1"),
        ],
        ids=[
            "flags_literals_case_insensitive",
            "flags_literals_free_spacing",
            "flags_charclass_case_insensitive",
            "flags_charclass_unicode",
            "flags_anchor_multiline_start",
            "flags_anchor_multiline_end",
            "flags_quantifier_dotall",
            "flags_quantifier_free_spacing",
            "flags_group_case_insensitive",
            "flags_group_named_free_spacing",
            "flags_lookahead_case_insensitive",
            "flags_lookbehind_multiline",
            "flags_alternation_case_insensitive",
            "flags_alternation_free_spacing",
            "flags_backref_case_insensitive",
        ],
    )
    def test_flags_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests flags combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Literals + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Literals + Character Classes
            ("abc[xyz]", r"abc[xyz]"),
            ("\\d\\d\\d-[0-9]", r"\d\d\d-[0-9]"),
            # Literals + Anchors
            ("^hello", r"^hello"),
            ("world$", r"world$"),
            ("\\bhello\\b", r"\bhello\b"),
            # Literals + Quantifiers
            ("a+bc", r"a+bc"),
            ("test\\d{3}", r"test\d{3}"),
            # Literals + Groups
            ("hello(world)", r"hello(world)"),
            ("test(?:group)", r"test(?:group)"),
            # Literals + Lookarounds
            ("hello(?=world)", r"hello(?=world)"),
            ("(?<=test)result", r"(?<=test)result"),
            # Literals + Alternation
            ("hello|world", r"hello|world"),
            ("a|b|c", r"a|b|c"),
            # Literals + Backreferences
            ("(\\w+)=\\1", r"(\w+)=\1"),
        ],
        ids=[
            "literals_charclass",
            "literals_charclass_mixed",
            "literals_anchor_start",
            "literals_anchor_end",
            "literals_anchor_word_boundary",
            "literals_quantifier_plus",
            "literals_quantifier_brace",
            "literals_group_capturing",
            "literals_group_noncapturing",
            "literals_lookahead",
            "literals_lookbehind",
            "literals_alternation_words",
            "literals_alternation_chars",
            "literals_backref",
        ],
    )
    def test_literals_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests literals combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Character Classes + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Character Classes + Anchors
            ("^[a-z]+", r"^[a-z]+"),
            ("[0-9]+$", r"[0-9]+$"),
            # Character Classes + Quantifiers
            ("[a-z]*", r"[a-z]*"),
            ("[0-9]{2,4}", r"[0-9]{2,4}"),
            ("\\w+?", r"\w+?"),
            # Character Classes + Groups
            ("([a-z]+)", r"([a-z]+)"),
            ("(?:[0-9]+)", r"(?:[0-9]+)"),
            # Character Classes + Lookarounds
            ("(?=[a-z])", r"(?=[a-z])"),
            ("(?<=\\d)", r"(?<=\d)"),
            # Character Classes + Alternation
            ("[a-z]|[0-9]", r"[a-z]|[0-9]"),
            ("\\w|\\s", r"\w|\s"),
            # Character Classes + Backreferences
            ("([a-z])\\1", r"([a-z])\1"),
        ],
        ids=[
            "charclass_anchor_start",
            "charclass_anchor_end",
            "charclass_quantifier_star",
            "charclass_quantifier_brace",
            "charclass_quantifier_lazy",
            "charclass_group_capturing",
            "charclass_group_noncapturing",
            "charclass_lookahead",
            "charclass_lookbehind",
            "charclass_alternation_classes",
            "charclass_alternation_shorthands",
            "charclass_backref",
        ],
    )
    def test_charclasses_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests character classes combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Anchors + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Anchors + Quantifiers
            ("^a+", r"^a+"),
            ("\\b\\w+", r"\b\w+"),
            # Anchors + Groups
            ("^(test)", r"^(test)"),
            ("(start)$", r"(start)$"),
            # Anchors + Lookarounds
            ("^(?=test)", r"^(?=test)"),
            ("(?<=^foo)", r"(?<=^foo)"),
            # Anchors + Alternation
            ("^a|b$", r"^a|b$"),
            # Anchors + Backreferences
            ("^(\\w+)\\s+\\1$", r"^(\w+)\s+\1$"),
        ],
        ids=[
            "anchor_quantifier_start",
            "anchor_quantifier_boundary",
            "anchor_group_start",
            "anchor_group_end",
            "anchor_lookahead",
            "anchor_lookbehind",
            "anchor_alternation",
            "anchor_backref",
        ],
    )
    def test_anchors_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests anchors combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Quantifiers + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Quantifiers + Groups
            ("(abc)+", r"(abc)+"),
            ("(?:test)*", r"(?:test)*"),
            ("(?<name>\\d)+", r"(?<name>\d)+"),
            # Quantifiers + Lookarounds
            ("(?=a)+", r"(?:(?=a))+"),
            ("test(?<=\\d)*", r"test(?:(?<=\d))*"),
            # Quantifiers + Alternation
            ("(a|b)+", r"(a|b)+"),
            ("(?:foo|bar)*", r"(?:foo|bar)*"),
            # Quantifiers + Backreferences
            ("(\\w)\\1+", r"(\w)\1+"),
            ("(\\d+)-\\1{2}", r"(\d+)-\1{2}"),
        ],
        ids=[
            "quantifier_group_capturing",
            "quantifier_group_noncapturing",
            "quantifier_group_named",
            "quantifier_lookahead",
            "quantifier_lookbehind",
            "quantifier_alternation_group",
            "quantifier_alternation_noncapturing",
            "quantifier_backref_repeated",
            "quantifier_backref_specific",
        ],
    )
    def test_quantifiers_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests quantifiers combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Groups + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Groups + Lookarounds
            ("((?=test)abc)", r"((?=test)abc)"),
            ("(?:(?<=\\d)result)", r"(?:(?<=\d)result)"),
            # Groups + Alternation
            ("(a|b|c)", r"(a|b|c)"),
            ("(?:foo|bar)", r"(?:foo|bar)"),
            # Groups + Backreferences
            ("(\\w+)\\s+\\1", r"(\w+)\s+\1"),
            ("(?<tag>\\w+)\\k<tag>", r"(?<tag>\w+)\k<tag>"),
        ],
        ids=[
            "group_lookahead_inside",
            "group_lookbehind_inside",
            "group_alternation_capturing",
            "group_alternation_noncapturing",
            "group_backref_numbered",
            "group_backref_named",
        ],
    )
    def test_groups_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests groups combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Lookarounds + Other Features
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Lookarounds + Alternation
            ("(?=a|b)", r"(?=a|b)"),
            ("(?<=foo|bar)", r"(?<=foo|bar)"),
            # Lookarounds + Backreferences
            ("(\\w+)(?=\\1)", r"(\w+)(?=\1)"),
        ],
        ids=[
            "lookahead_alternation",
            "lookbehind_alternation",
            "lookahead_backref",
        ],
    )
    def test_lookarounds_combined_with_other_features(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests lookarounds combined with each other core feature."""
        assert compile_to_pcre(input_dsl) == expected_regex

    # Alternation + Backreferences
    
    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            ("(a)\\1|(b)\\2", r"(a)\1|(b)\2"),
        ],
        ids=[
            "alternation_backref",
        ],
    )
    def test_alternation_combined_with_backreferences(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests alternation combined with backreferences."""
        assert compile_to_pcre(input_dsl) == expected_regex


# --- Tier 2: Strategic Triplet Tests (N=3) -------------------------------------


class TestTier2StrategicTriplets:
    """
    Tests strategic triplet (N=3) combinations of high-risk features where
    bugs are most likely to hide: Flags, Groups, Quantifiers, Lookarounds,
    and Alternation.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Flags + Groups + Quantifiers
            ("%flags i\n(hello)+", r"(?i)(hello)+"),
            ("%flags x\n(?:a b)+", r"(?x)(?:ab)+"),
            ("%flags i\n(?<name>\\w)+", r"(?i)(?<name>\w)+"),
            # Flags + Groups + Lookarounds
            ("%flags i\n((?=test)result)", r"(?i)((?=test)result)"),
            ("%flags m\n(?:(?<=^)start)", r"(?m)(?:(?<=^)start)"),
            # Flags + Quantifiers + Lookarounds
            ("%flags i\n(?=test)+", r"(?i)(?:(?=test))+"),
            ("%flags s\n.*(?<=end)", r"(?s).*(?<=end)"),
            # Flags + Alternation + Groups
            ("%flags i\n(a|b|c)", r"(?i)(a|b|c)"),
            ("%flags x\n(?:foo | bar | baz)", r"(?x)(?:foo|bar|baz)"),
            # Groups + Quantifiers + Lookarounds
            ("((?=\\d)\\w)+", r"((?=\d)\w)+"),
            ("(?:(?<=test)\\w+)*", r"(?:(?<=test)\w+)*"),
            # Groups + Quantifiers + Alternation
            ("(a|b)+", r"(a|b)+"),
            ("(?:foo|bar){2,5}", r"(?:foo|bar){2,5}"),
            # Quantifiers + Lookarounds + Alternation
            ("(?=a|b)+", r"(?:(?=a|b))+"),
            ("(foo|bar)(?<=test)*", r"(foo|bar)(?:(?<=test))*"),
        ],
        ids=[
            "flags_groups_quantifiers_case",
            "flags_groups_quantifiers_spacing",
            "flags_groups_quantifiers_named",
            "flags_groups_lookahead",
            "flags_groups_lookbehind",
            "flags_quantifiers_lookahead",
            "flags_quantifiers_lookbehind",
            "flags_alternation_groups_case",
            "flags_alternation_groups_spacing",
            "groups_quantifiers_lookahead",
            "groups_quantifiers_lookbehind",
            "groups_quantifiers_alternation",
            "groups_quantifiers_alternation_brace",
            "quantifiers_lookahead_alternation",
            "quantifiers_lookbehind_alternation",
        ],
    )
    def test_strategic_triplet_combinations(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests strategic triplets of high-risk feature interactions."""
        assert compile_to_pcre(input_dsl) == expected_regex


# --- Complex Nested Feature Tests -----------------------------------------------


class TestComplexNestedFeatures:
    """
    Tests complex nested combinations that are especially prone to bugs.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # Deeply nested groups with quantifiers
            ("((a+)+)+", r"((a+)+)+"),
            # Multiple lookarounds in sequence
            ("(?=test)(?!fail)result", r"(?=test)(?!fail)result"),
            # Nested alternation with groups
            ("(a|(b|c))", r"(a|(b|c))"),
            # Quantified lookaround with backreference
            ("(\\w)(?=\\1)+", r"(\w)(?:(?=\1))+"),
            # Complex free spacing with all features
            (
                "%flags x\n(?<tag> \\w+ ) \\s* = \\s* (?<value> [^>]+ ) \\k<tag>",
                r"(?x)(?<tag>\w+)\s*=\s*(?<value>[^>]+)\k<tag>",
            ),
            # Atomic group with quantifiers
            ("(?>a+)b", r"(?>a+)b"),
            # Possessive quantifiers in groups
            ("(a*+)b", r"(a*+)b"),
        ],
        ids=[
            "deeply_nested_quantifiers",
            "multiple_lookarounds",
            "nested_alternation",
            "quantified_lookaround_backref",
            "complex_free_spacing",
            "atomic_group_quantifier",
            "possessive_in_group",
        ],
    )
    def test_complex_nested_combinations(
        self, input_dsl: str, expected_regex: str
    ):
        """Tests complex nested feature combinations."""
        assert compile_to_pcre(input_dsl) == expected_regex
