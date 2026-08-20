"""Character-set conveniences expressed as canonical Simply set members."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence, Union

from STRling.simply.pattern import (
    Pattern,
    STRlingError,
    coerce_pattern,
    create_pattern,
)

PatternLike = Union[Pattern, str]


def character_set(
    members: Sequence[Mapping[str, object]], negated: bool = False
) -> Pattern:
    copied = tuple(dict(member) for member in members)
    return create_pattern(
        lambda context: context.builder.character_set(
            context.next("character-set"), copied, negated
        ),
        copied,
    )


def between(
    start: Union[str, int],
    end: Union[str, int],
    min_rep: Optional[int] = None,
    max_rep: Optional[int] = None,
) -> Pattern:
    pattern = character_set(({"kind": "range", "start": str(start), "end": str(end)},))
    return pattern if min_rep is None else pattern(min_rep, max_rep)


def not_between(
    start: Union[str, int],
    end: Union[str, int],
    min_rep: Optional[int] = None,
    max_rep: Optional[int] = None,
) -> Pattern:
    pattern = character_set(
        ({"kind": "range", "start": str(start), "end": str(end)},), True
    )
    return pattern if min_rep is None else pattern(min_rep, max_rep)


def in_chars(*patterns: PatternLike) -> Pattern:
    return _combined_set(patterns, False)


def not_in_chars(*patterns: PatternLike) -> Pattern:
    return _combined_set(patterns, True)


def _combined_set(patterns: Sequence[PatternLike], negated: bool) -> Pattern:
    members = []
    for value in (coerce_pattern(pattern) for pattern in patterns):
        if value.character_set_members is None:
            raise STRlingError(
                "character-set composition accepts only literals and character-set patterns"
            )
        members.extend(value.character_set_members)
    return character_set(members, negated)


__all__ = [
    "between",
    "character_set",
    "in_chars",
    "not_between",
    "not_in_chars",
]
