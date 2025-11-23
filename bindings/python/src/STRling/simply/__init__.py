"""
STRling Simply API - Main Entry Point

This module provides the complete public API for the STRling Simply interface,
which allows developers to build regex patterns using a fluent, chainable API.
It re-exports all constructors, lookarounds, character sets, static patterns,
and compilation utilities from their respective modules.

The Simply API is designed to be intuitive and self-documenting, replacing
cryptic regex syntax with readable function calls and method chains.
"""

from STRling.simply.pattern import Pattern, lit, STRlingError, repeat

# constructors
from STRling.simply.constructors import (
    any_of,
    may,
    merge,
    capture,
    group,
)

# lookarounds
from STRling.simply.lookarounds import (
    ahead,
    not_ahead,
    behind,
    not_behind,
    has,
    has_not,
)

# sets
from STRling.simply.sets import (
    between,
    not_between,
    in_chars,
    not_in_chars,
)

# static / predefined patterns
from STRling.simply.static import (
    alpha_num,
    not_alpha_num,
    special_char,
    not_special_char,
    letter,
    not_letter,
    upper,
    not_upper,
    lower,
    not_lower,
    hex_digit,
    not_hex_digit,
    digit,
    not_digit,
    whitespace,
    not_whitespace,
    newline,
    not_newline,
    tab,
    carriage,
    bound,
    not_bound,
    start,
    end,
)

# Public API surface exported by `STRling.simply`
__all__ = [
    # core
    "Pattern",
    "lit",
    "STRlingError",
    "repeat",
    # constructors
    "any_of",
    "may",
    "merge",
    "capture",
    "group",
    # lookarounds
    "ahead",
    "not_ahead",
    "behind",
    "not_behind",
    "has",
    "has_not",
    # sets
    "between",
    "not_between",
    "in_chars",
    "not_in_chars",
    # static
    "alpha_num",
    "not_alpha_num",
    "special_char",
    "not_special_char",
    "letter",
    "not_letter",
    "upper",
    "not_upper",
    "lower",
    "not_lower",
    "hex_digit",
    "not_hex_digit",
    "digit",
    "not_digit",
    "whitespace",
    "not_whitespace",
    "newline",
    "not_newline",
    "tab",
    "carriage",
    "bound",
    "not_bound",
    "start",
    "end",
]
