"""Fluent recipes that record only canonical Simply protocol operations."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple, Union

from STRling.interop import NativeClient
from STRling.simply.preview import (
    NativeSimplyPreviewTransport,
    SimplyAdapterResponse,
    SimplyCharacterSetMember,
    SimplyCompileProjection,
    SimplyPreviewBuilder,
    SimplyPreviewValue,
)


class STRlingError(ValueError):
    pass


class _RecordingContext:
    def __init__(self, builder: SimplyPreviewBuilder) -> None:
        self.builder = builder
        self.sequence = 0

    def next(self, prefix: str) -> str:
        self.sequence += 1
        return "{}-{}".format(prefix, self.sequence)


Recipe = Callable[[_RecordingContext], SimplyPreviewValue]


class Pattern:
    def __init__(
        self,
        recipe: Recipe,
        character_set_members: Optional[Sequence[SimplyCharacterSetMember]] = None,
    ) -> None:
        self._recipe = recipe
        self.character_set_members = (
            None
            if character_set_members is None
            else tuple(dict(member) for member in character_set_members)
        )

    def __call__(
        self, min_rep: Optional[int] = None, max_rep: Optional[int] = None
    ) -> "Pattern":
        if min_rep is None and max_rep is None:
            return self
        minimum = 0 if min_rep is None else min_rep
        if type(minimum) is not int or minimum < 0:
            raise STRlingError("repetition bounds must be non-negative integers")
        if max_rep is not None and (type(max_rep) is not int or max_rep < 0):
            raise STRlingError("repetition bounds must be non-negative integers")
        maximum = None if max_rep == 0 else (minimum if max_rep is None else max_rep)
        return Pattern(
            lambda context: context.builder.repeat(
                context.next("repeat"),
                self._record(context),
                minimum,
                maximum,
            )
        )

    def _record(self, context: _RecordingContext) -> SimplyPreviewValue:
        return self._recipe(context)

    def build_request(
        self,
        compile_projection: SimplyCompileProjection,
        identity_namespace: str = "python-simply",
        semantic_options: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        builder, root = self._build(identity_namespace, semantic_options)
        return builder.build_request(root, compile_projection)

    def compile(
        self,
        client: NativeClient,
        compile_projection: SimplyCompileProjection,
        target_profile: Optional[Mapping[str, Any]] = None,
        identity_namespace: str = "python-simply",
        semantic_options: Optional[Mapping[str, Any]] = None,
    ) -> SimplyAdapterResponse:
        builder, root = self._build(identity_namespace, semantic_options)
        return builder.compile(
            root,
            compile_projection,
            NativeSimplyPreviewTransport(client, target_profile),
        )

    def exec(self, _text_to_search: str, _target: str = "python") -> None:
        raise STRlingError(
            "Pattern.exec was retired: canonical adapters do not simulate runtime regex execution"
        )

    def __str__(self) -> str:
        raise STRlingError(
            "implicit regex rendering was retired: compile through the canonical adapter"
        )

    def _build(
        self,
        identity_namespace: str,
        semantic_options: Optional[Mapping[str, Any]],
    ) -> Tuple[SimplyPreviewBuilder, SimplyPreviewValue]:
        builder = SimplyPreviewBuilder(
            identity_namespace,
            "1.0-draft.1",
            semantic_options,
        )
        context = _RecordingContext(builder)
        return builder, self._record(context)


def create_pattern(
    recipe: Recipe,
    character_set_members: Optional[Sequence[SimplyCharacterSetMember]] = None,
) -> Pattern:
    return Pattern(recipe, character_set_members)


def coerce_pattern(value: Union[Pattern, str]) -> Pattern:
    if isinstance(value, str):
        return lit(value)
    if not isinstance(value, Pattern):
        raise STRlingError("expected a Pattern or literal string")
    return value


def lit(text: str) -> Pattern:
    if not isinstance(text, str):
        raise STRlingError("literal text must be a string")
    members = tuple({"kind": "literal", "value": value} for value in text)
    return create_pattern(
        lambda context: context.builder.literal(context.next("literal"), text),
        members,
    )


__all__ = ["Pattern", "STRlingError", "lit"]
