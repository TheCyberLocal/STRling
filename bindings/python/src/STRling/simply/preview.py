"""Host-neutral Simply request recording with canonical native execution."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence

from STRling.interop import NativeClient

SIMPLY_PREVIEW_PROTOCOL_VERSION = "1.1.0"
SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION = "1.0.0"
SIMPLY_PREVIEW_PROTOCOL_VERSIONS = (
    SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION,
    SIMPLY_PREVIEW_PROTOCOL_VERSION,
)
SIMPLY_PREVIEW_STATUS = "preview"

SimplyBuilderRequest = Dict[str, Any]
SimplyAdapterResponse = Dict[str, Any]
SimplyCompileProjection = Mapping[str, Any]
SimplyCharacterSetMember = Mapping[str, Any]


@dataclass(frozen=True)
class SimplyPreviewValue:
    step_id: str
    _owner: object = field(repr=False, compare=False)


class SimplyPreviewTransport(Protocol):
    def execute(self, request: SimplyBuilderRequest) -> SimplyAdapterResponse: ...


class SimplyPreviewError(ValueError):
    def __init__(self, errors: Sequence[Mapping[str, str]]) -> None:
        self.errors = tuple(deepcopy(list(errors)))
        super().__init__("{} Simply construction error(s)".format(len(self.errors)))


class SimplyPreviewTransportError(RuntimeError):
    pass


class NativeSimplyPreviewTransport:
    def __init__(
        self,
        client: NativeClient,
        target_profile: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._client = client
        self._target_profile = (
            None if target_profile is None else deepcopy(dict(target_profile))
        )

    def execute(self, request: SimplyBuilderRequest) -> SimplyAdapterResponse:
        response = self._client.simply_compile(request, self._target_profile)
        return _decode_response(response, request.get("protocol_version"))


class SimplyPreviewBuilder:
    def __init__(
        self,
        identity_namespace: str,
        specification_version: str = "1.0-draft.1",
        semantic_options: Optional[Mapping[str, Any]] = None,
        protocol_version: str = SIMPLY_PREVIEW_PROTOCOL_VERSION,
    ) -> None:
        if protocol_version not in SIMPLY_PREVIEW_PROTOCOL_VERSIONS:
            raise SimplyPreviewTransportError(
                "unsupported Simply Preview protocol {}".format(protocol_version)
            )
        self._owner = object()
        self._identity_namespace = identity_namespace
        self._specification_version = specification_version
        self._protocol_version = protocol_version
        self._semantic_options = deepcopy(
            semantic_options
            if semantic_options is not None
            else default_simply_semantic_options()
        )
        self._steps = []  # type: list[dict[str, Any]]

    def empty(self, step_id: str) -> SimplyPreviewValue:
        return self._append(step_id, "empty", {})

    def literal(self, step_id: str, text: str) -> SimplyPreviewValue:
        return self._append(step_id, "literal", {"text": text})

    def wildcard(
        self, step_id: str, line_terminators: Optional[str] = None
    ) -> SimplyPreviewValue:
        arguments = (
            {} if line_terminators is None else {"line_terminators": line_terminators}
        )
        return self._append(step_id, "wildcard", arguments)

    def character_set(
        self,
        step_id: str,
        members: Sequence[SimplyCharacterSetMember],
        negated: bool = False,
    ) -> SimplyPreviewValue:
        return self._append(
            step_id,
            "character_set",
            {"negated": negated, "members": deepcopy(list(members))},
        )

    def sequence(
        self, step_id: str, values: Sequence[SimplyPreviewValue]
    ) -> SimplyPreviewValue:
        return self._append(
            step_id,
            "sequence",
            {"values": [self._value_step(value) for value in values]},
        )

    def alternation(
        self, step_id: str, values: Sequence[SimplyPreviewValue]
    ) -> SimplyPreviewValue:
        return self._append(
            step_id,
            "alternation",
            {"values": [self._value_step(value) for value in values]},
        )

    def group(self, step_id: str, value: SimplyPreviewValue) -> SimplyPreviewValue:
        return self._append(step_id, "group", {"value": self._value_step(value)})

    def capture(
        self,
        step_id: str,
        capture_key: str,
        value: SimplyPreviewValue,
        name: Optional[str] = None,
    ) -> SimplyPreviewValue:
        arguments = {
            "value": self._value_step(value),
            "capture_key": capture_key,
        }
        if name is not None:
            arguments["name"] = name
        return self._append(step_id, "capture", arguments)

    def backreference(self, step_id: str, capture_key: str) -> SimplyPreviewValue:
        return self._append(step_id, "backreference", {"capture_key": capture_key})

    def position(self, step_id: str, position: str) -> SimplyPreviewValue:
        return self._append(step_id, "position", {"position": position})

    def lookaround(
        self,
        step_id: str,
        direction: str,
        polarity: str,
        value: SimplyPreviewValue,
    ) -> SimplyPreviewValue:
        return self._append(
            step_id,
            "lookaround",
            {
                "value": self._value_step(value),
                "direction": direction,
                "polarity": polarity,
            },
        )

    def atomic(self, step_id: str, value: SimplyPreviewValue) -> SimplyPreviewValue:
        return self._append(step_id, "atomic", {"value": self._value_step(value)})

    def repeat(
        self,
        step_id: str,
        value: SimplyPreviewValue,
        min_count: int,
        max_count: Optional[int],
        mode: str = "greedy",
    ) -> SimplyPreviewValue:
        return self._append(
            step_id,
            "repeat",
            {
                "value": self._value_step(value),
                "min": min_count,
                "max": max_count,
                "mode": mode,
            },
        )

    def import_node(
        self,
        step_id: str,
        node: Mapping[str, Any],
        sources: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> SimplyPreviewValue:
        arguments = {"node": deepcopy(dict(node))}
        if sources is not None:
            arguments["sources"] = deepcopy(list(sources))
        return self._append(step_id, "import_node", arguments)

    def import_program(
        self, step_id: str, program: Mapping[str, Any]
    ) -> SimplyPreviewValue:
        return self._append(
            step_id, "import_program", {"program": deepcopy(dict(program))}
        )

    def stdlib_helper(
        self,
        step_id: str,
        helper_id: str,
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> SimplyPreviewValue:
        if self._protocol_version != SIMPLY_PREVIEW_PROTOCOL_VERSION:
            raise SimplyPreviewTransportError(
                "stdlib_helper requires Simply Preview protocol 1.1.0"
            )
        return self._append(
            step_id,
            "stdlib_helper",
            {
                "helper_id": helper_id,
                "parameters": deepcopy(dict(parameters or {})),
            },
        )

    def build_request(
        self,
        root: SimplyPreviewValue,
        compile_projection: SimplyCompileProjection,
    ) -> SimplyBuilderRequest:
        return deepcopy(
            {
                "protocol_version": self._protocol_version,
                "contract_version": "1.0.0",
                "specification_version": self._specification_version,
                "identity_namespace": self._identity_namespace,
                "semantic_options": self._semantic_options,
                "steps": self._steps,
                "root_step_id": self._value_step(root),
                "compile": dict(compile_projection),
            }
        )

    def compile(
        self,
        root: SimplyPreviewValue,
        compile_projection: SimplyCompileProjection,
        transport: SimplyPreviewTransport,
    ) -> SimplyAdapterResponse:
        response = transport.execute(self.build_request(root, compile_projection))
        if response["status"] == "failure":
            raise SimplyPreviewError(response["errors"])
        return response

    def _append(
        self, step_id: str, operation: str, arguments: Mapping[str, Any]
    ) -> SimplyPreviewValue:
        self._steps.append(
            {
                "step_id": step_id,
                "operation": operation,
                "arguments": deepcopy(dict(arguments)),
            }
        )
        return SimplyPreviewValue(step_id=step_id, _owner=self._owner)

    def _value_step(self, value: SimplyPreviewValue) -> str:
        if not isinstance(value, SimplyPreviewValue) or value._owner is not self._owner:
            raise SimplyPreviewTransportError(
                "Simply values belong to exactly one Preview builder"
            )
        return value.step_id


def default_simply_semantic_options() -> Dict[str, str]:
    return {
        "case_matching": "sensitive",
        "text_model": "unicode_scalar_values",
        "builtin_character_domain": "unicode",
        "wildcard_line_terminators": "exclude",
    }


def serialize_simply_builder_request(request: SimplyBuilderRequest) -> str:
    return json.dumps(request, ensure_ascii=False, separators=(",", ":"))


def _decode_response(
    value: object, expected_protocol_version: object
) -> SimplyAdapterResponse:
    if not isinstance(value, dict):
        raise SimplyPreviewTransportError("Simply transport response must be an object")
    if (
        expected_protocol_version not in SIMPLY_PREVIEW_PROTOCOL_VERSIONS
        or value.get("protocol_version") != expected_protocol_version
        or value.get("status") not in ("success", "failure")
    ):
        raise SimplyPreviewTransportError(
            "Simply transport response has an unsupported protocol or status"
        )
    if value["status"] == "failure":
        if not isinstance(value.get("errors"), list):
            raise SimplyPreviewTransportError(
                "Simply failure response must contain errors"
            )
        return deepcopy(value)
    if not isinstance(value.get("compile_request"), dict) or not isinstance(
        value.get("compile_result"), dict
    ):
        raise SimplyPreviewTransportError(
            "Simply success response must contain canonical request and result objects"
        )
    return deepcopy(value)


__all__ = [
    "SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION",
    "SIMPLY_PREVIEW_PROTOCOL_VERSION",
    "SIMPLY_PREVIEW_PROTOCOL_VERSIONS",
    "SIMPLY_PREVIEW_STATUS",
    "NativeSimplyPreviewTransport",
    "SimplyAdapterResponse",
    "SimplyBuilderRequest",
    "SimplyCharacterSetMember",
    "SimplyCompileProjection",
    "SimplyPreviewBuilder",
    "SimplyPreviewError",
    "SimplyPreviewTransport",
    "SimplyPreviewTransportError",
    "SimplyPreviewValue",
    "default_simply_semantic_options",
    "serialize_simply_builder_request",
]
