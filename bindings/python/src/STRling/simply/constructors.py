"""Composite conveniences expressed only as Simply protocol recipes."""

from __future__ import annotations

from typing import Sequence, Union

from STRling.simply.pattern import Pattern, coerce_pattern, create_pattern

PatternLike = Union[Pattern, str]


def _values(patterns: Sequence[PatternLike]) -> Sequence[Pattern]:
    return tuple(coerce_pattern(pattern) for pattern in patterns)


def _body(patterns: Sequence[PatternLike]) -> Pattern:
    prepared = _values(patterns)
    if len(prepared) == 1:
        return prepared[0]
    return create_pattern(
        lambda context: context.builder.sequence(
            context.next("sequence"),
            [pattern._record(context) for pattern in prepared],
        )
    )


def any_of(*patterns: PatternLike) -> Pattern:
    prepared = _values(patterns)
    return create_pattern(
        lambda context: context.builder.alternation(
            context.next("alternation"),
            [pattern._record(context) for pattern in prepared],
        )
    )


def may(*patterns: PatternLike) -> Pattern:
    return _body(patterns)(0, 1)


def merge(*patterns: PatternLike) -> Pattern:
    return _body(patterns)


def capture(*patterns: PatternLike) -> Pattern:
    value = _body(patterns)

    def recipe(context):
        capture_key = context.next("capture")
        return context.builder.capture(
            context.next("capture-step"), capture_key, value._record(context)
        )

    return create_pattern(recipe)


def group(name: str, *patterns: PatternLike) -> Pattern:
    value = _body(patterns)
    return create_pattern(
        lambda context: context.builder.capture(
            context.next("capture-step"),
            context.next("capture"),
            value._record(context),
            name,
        )
    )


__all__ = ["any_of", "capture", "group", "may", "merge"]
