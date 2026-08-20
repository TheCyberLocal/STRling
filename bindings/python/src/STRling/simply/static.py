"""Legacy ergonomic names mapped to canonical Simply protocol operations."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence, Tuple

from STRling.simply.pattern import Pattern, create_pattern
from STRling.simply.sets import character_set


def _repeated(
    pattern: Pattern,
    min_rep: Optional[int],
    max_rep: Optional[int],
) -> Pattern:
    return pattern if min_rep is None else pattern(min_rep, max_rep)


def _ranges(
    values: Sequence[Tuple[str, str]],
    negated: bool,
    min_rep: Optional[int],
    max_rep: Optional[int],
) -> Pattern:
    return _repeated(
        character_set(
            tuple(
                {"kind": "range", "start": start, "end": end} for start, end in values
            ),
            negated,
        ),
        min_rep,
        max_rep,
    )


def _builtin(
    name: str,
    negated: bool,
    min_rep: Optional[int],
    max_rep: Optional[int],
) -> Pattern:
    return _repeated(
        character_set(
            (
                {
                    "kind": "builtin",
                    "name": name,
                    "domain": "unicode",
                    "negated": negated,
                },
            )
        ),
        min_rep,
        max_rep,
    )


def alpha_num(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "Z"), ("a", "z"), ("0", "9")), False, min_rep, max_rep)


def not_alpha_num(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _ranges((("A", "Z"), ("a", "z"), ("0", "9")), True, min_rep, max_rep)


_ASCII_PUNCTUATION = tuple(
    {"kind": "literal", "value": value}
    for value in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)


def special_char(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _repeated(character_set(_ASCII_PUNCTUATION), min_rep, max_rep)


def not_special_char(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _repeated(character_set(_ASCII_PUNCTUATION, True), min_rep, max_rep)


def letter(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "Z"), ("a", "z")), False, min_rep, max_rep)


def not_letter(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "Z"), ("a", "z")), True, min_rep, max_rep)


def upper(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "Z"),), False, min_rep, max_rep)


def not_upper(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "Z"),), True, min_rep, max_rep)


def lower(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("a", "z"),), False, min_rep, max_rep)


def not_lower(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("a", "z"),), True, min_rep, max_rep)


def hex_digit(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _ranges((("A", "F"), ("a", "f"), ("0", "9")), False, min_rep, max_rep)


def not_hex_digit(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _ranges((("A", "F"), ("a", "f"), ("0", "9")), True, min_rep, max_rep)


def digit(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _builtin("digit", False, min_rep, max_rep)


def not_digit(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _builtin("digit", True, min_rep, max_rep)


def whitespace(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _builtin("whitespace", False, min_rep, max_rep)


def not_whitespace(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _builtin("whitespace", True, min_rep, max_rep)


def _literal_set(
    value: str,
    negated: bool,
    min_rep: Optional[int],
    max_rep: Optional[int],
) -> Pattern:
    return _repeated(
        character_set(({"kind": "literal", "value": value},), negated),
        min_rep,
        max_rep,
    )


def newline(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _literal_set("\n", False, min_rep, max_rep)


def not_newline(
    min_rep: Optional[int] = None, max_rep: Optional[int] = None
) -> Pattern:
    return _literal_set("\n", True, min_rep, max_rep)


def tab(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _literal_set("\t", False, min_rep, max_rep)


def carriage(min_rep: Optional[int] = None, max_rep: Optional[int] = None) -> Pattern:
    return _literal_set("\r", False, min_rep, max_rep)


def _position(value: str) -> Pattern:
    return create_pattern(
        lambda context: context.builder.position(context.next("position"), value)
    )


def bound(_min_rep: Optional[int] = None, _max_rep: Optional[int] = None) -> Pattern:
    return _position("word_boundary")


def not_bound(
    _min_rep: Optional[int] = None, _max_rep: Optional[int] = None
) -> Pattern:
    return _position("not_word_boundary")


def start() -> Pattern:
    return _position("input_start")


def end() -> Pattern:
    return _position("input_end")


def email() -> Pattern:
    return _stdlib("stdlib.email", {})


def url() -> Pattern:
    return _stdlib("stdlib.url", {})


def uuid(version: Optional[int] = None) -> Pattern:
    return _stdlib("stdlib.uuid", {"version": version})


def ip(version: Optional[int] = None) -> Pattern:
    return _stdlib("stdlib.ip", {"version": version})


def date_time() -> Pattern:
    return _stdlib("stdlib.date_time", {})


def _stdlib(helper_id: str, parameters: Mapping[str, object]) -> Pattern:
    return create_pattern(
        lambda context: context.builder.stdlib_helper(
            context.next("stdlib-helper"), helper_id, parameters
        )
    )


__all__ = [
    "alpha_num",
    "bound",
    "carriage",
    "date_time",
    "digit",
    "email",
    "end",
    "hex_digit",
    "ip",
    "letter",
    "lower",
    "newline",
    "not_alpha_num",
    "not_bound",
    "not_digit",
    "not_hex_digit",
    "not_letter",
    "not_lower",
    "not_newline",
    "not_special_char",
    "not_upper",
    "not_whitespace",
    "special_char",
    "start",
    "tab",
    "upper",
    "url",
    "uuid",
    "whitespace",
]
