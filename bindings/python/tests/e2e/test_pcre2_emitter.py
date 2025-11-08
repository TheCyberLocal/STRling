"""
Test Design — e2e/test_pcre2_emitter.py

## Purpose
This test suite provides end-to-end (E2E) validation of the entire STRling
compiler pipeline, from a source DSL string to the final PCRE2 regex string.
It serves as a high-level integration test to ensure that the parser,
compiler, and emitter work together correctly to produce valid output for a
set of canonical "golden" patterns.

## Description
Unlike the unit tests which inspect individual components, this E2E suite
treats the compiler as a black box. It provides a STRling DSL string as
input and asserts that the final emitted string is exactly as expected for
the PCRE2 target. These tests are designed to catch regressions and verify the
correct integration of all core components, including the handling of
PCRE2-specific extension features like atomic groups.

## Scope
-   **In scope:**
    -   The final string output of the full `parse -> compile -> emit`
        pipeline for a curated list of representative patterns.

    -   Verification that the emitted string is syntactically correct for
        the PCRE2 engine.
    -   End-to-end testing of PCRE2-supported extension features (e.g.,
        atomic groups, possessive quantifiers).
    -   Verification that flags are correctly translated into the `(?imsux)`
        prefix in the final string.
-   **Out of scope:**
    -   Exhaustive testing of every possible DSL feature (this is the role
        of the unit tests).
    -   The runtime behavior of the generated regex string in a live PCRE2
        engine (this is the purpose of the Sprint 7 conformance suite).

    -   Detailed validation of the intermediate AST or IR structures.

"""

import re
import pytest

from STRling.core.parser import parse, ParseError
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit as emit_pcre2

# --- Test Suite Setup -----------------------------------------------------------


def compile_to_pcre(src: str) -> str:
    """A helper to run the full DSL -> PCRE2 string pipeline."""
    flags, ast = parse(src)
    ir_root = Compiler().compile(ast)
    return emit_pcre2(ir_root, flags)


# --- Test Suite -----------------------------------------------------------------


class TestCategoryACoreLanguageFeatures:
    """
    Covers end-to-end compilation of canonical "golden" patterns for core
    DSL features.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            # A.1: Complex pattern with named groups, classes, quantifiers, and flags
            (
                "%flags x\n(?<area>\\d{3}) - (?<exchange>\\d{3}) - (?<line>\\d{4})",
                r"(?x)(?<area>\d{3})-(?<exchange>\d{3})-(?<line>\d{4})",
            ),
            # A.2: Alternation requiring automatic grouping for precedence
            ("start(?:a|b|c)end", r"start(?:a|b|c)end"),
            # A.3: Lookarounds and anchors
            ("(?<=^foo)\\w+", r"(?<=^foo)\w+"),
            # A.4: Unicode properties with the unicode flag
            ("%flags u\n\\p{L}+", r"(?u)\p{L}+"),
            # A.5: Backreferences and lazy quantifiers
            ("<(?<tag>\\w+)>.*?</\\k<tag>>", r"<(?<tag>\w+)>.*?</\k<tag>>"),
        ],
        ids=[
            "golden_phone_number",
            "golden_alternation_precedence",
            "golden_lookaround_anchor",
            "golden_unicode_property",
            "golden_backreference_lazy_quant",
        ],
    )
    def test_golden_patterns(self, input_dsl: str, expected_regex: str):
        """
        Tests that representative DSL patterns compile to the correct PCRE2 string.
        """
        assert compile_to_pcre(input_dsl) == expected_regex


class TestCategoryBEmitterSpecificSyntax:
    """
    Covers emitter-specific syntax generation, like flags and escaping.
    """

    def test_all_flags_are_generated_correctly(self):
        """
        Tests that all supported flags are correctly prepended to the pattern.
        """
        # Note: The 'a' is needed to create a non-empty pattern
        assert compile_to_pcre("%flags imsux\na") == "(?imsux)a"

    def test_all_metacharacters_are_escaped(self):
        """
        Tests that all regex metacharacters are correctly escaped when used as
        literals.
        """
        # To test literal metacharacters, escape them in the DSL source
        metachars_dsl = r"\.\^\$\|\(\)\?\*\+\{\}\[\]\\"
        metachars_literal = ".^$|()?*+{}[]\\"
        escaped_metachars = re.escape(metachars_literal)
        assert compile_to_pcre(metachars_dsl) == escaped_metachars


class TestCategoryCExtensionFeatures:
    """
    Covers end-to-end compilation of PCRE2-specific extension features.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_regex",
        [
            (r"(?>a+)", r"(?>a+)"),
            (r"a*+", r"a*+"),
            (r"\Astart\z", r"\Astart\z"),
        ],
        ids=["atomic_group", "possessive_quantifier", "absolute_anchors"],
    )
    def test_pcre2_extensions(self, input_dsl: str, expected_regex: str):
        """
        Tests that DSL constructs corresponding to PCRE2 extensions are emitted
        correctly.
        """
        assert compile_to_pcre(input_dsl) == expected_regex


class TestCategoryDErrorHandling:
    """
    Covers how errors from the pipeline are propagated.
    """

    def test_parse_error_propagates_through_pipeline(self):
        """
        Tests that an invalid DSL string raises a ParseError when the full
        compilation is attempted.
        """
        with pytest.raises(ParseError, match="Unterminated group"):
            compile_to_pcre("a(b")
