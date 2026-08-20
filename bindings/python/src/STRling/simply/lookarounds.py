"""Lookaround conveniences expressed only as Simply protocol recipes."""

from __future__ import annotations

from typing import Union

from STRling.simply.pattern import Pattern, coerce_pattern, create_pattern

PatternLike = Union[Pattern, str]


def _look(value: PatternLike, direction: str, polarity: str) -> Pattern:
    pattern = coerce_pattern(value)
    return create_pattern(
        lambda context: context.builder.lookaround(
            context.next("lookaround"),
            direction,
            polarity,
            pattern._record(context),
        )
    )


def ahead(pattern: PatternLike) -> Pattern:
    return _look(pattern, "ahead", "positive")


def not_ahead(pattern: PatternLike) -> Pattern:
    return _look(pattern, "ahead", "negative")


def behind(pattern: PatternLike) -> Pattern:
    return _look(pattern, "behind", "positive")


def not_behind(pattern: PatternLike) -> Pattern:
    return _look(pattern, "behind", "negative")


def _contains(pattern: PatternLike, polarity: str) -> Pattern:
    value = coerce_pattern(pattern)

    def recipe(context):
        wildcard = context.builder.wildcard(context.next("wildcard"))
        repeated = context.builder.repeat(context.next("repeat"), wildcard, 0, None)
        sequence = context.builder.sequence(
            context.next("sequence"), [repeated, value._record(context)]
        )
        return context.builder.lookaround(
            context.next("lookaround"), "ahead", polarity, sequence
        )

    return create_pattern(recipe)


def has(pattern: PatternLike) -> Pattern:
    return _contains(pattern, "positive")


def has_not(pattern: PatternLike) -> Pattern:
    return _contains(pattern, "negative")


__all__ = ["ahead", "behind", "has", "has_not", "not_ahead", "not_behind"]
