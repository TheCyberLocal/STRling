"""Canonical compile-request conveniences over a supplied native client."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from STRling.interop import NativeClient


class Compiler:
    def __init__(self, client: NativeClient) -> None:
        self._client = client

    def compile(
        self,
        request: Mapping[str, Any],
        target_profile: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        return self._client.compile(request, target_profile)

    def check(
        self,
        request: Mapping[str, Any],
        target_profile: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        return self.compile(request, target_profile)


def parse(
    client: NativeClient,
    source: str,
    options: Optional[Mapping[str, Any]] = None,
) -> Any:
    prepared = dict(options or {})
    return client.compile(
        source_compile_request(source, prepared, ("semantic",)),
        prepared.get("target_profile"),
    )


def parse_to_artifact(
    client: NativeClient,
    source: str,
    options: Mapping[str, Any],
) -> Any:
    prepared = dict(options)
    target_profile = prepared.get("target_profile")
    target_reference = prepared.get("target_profile_reference")
    if not isinstance(target_profile, Mapping) or not isinstance(
        target_reference, Mapping
    ):
        raise TypeError(
            "parse_to_artifact requires an exact target profile and reference"
        )
    return client.compile(
        source_compile_request(
            source,
            prepared,
            ("semantic", "portability", "target_artifact"),
        ),
        target_profile,
    )


def source_compile_request(
    source: str,
    options: Optional[Mapping[str, Any]] = None,
    fallback_outputs: Sequence[str] = ("semantic", "analysis"),
) -> dict[str, Any]:
    prepared = dict(options or {})
    specification_version = str(prepared.get("specification_version", "1.0-draft.1"))
    frontend_id = str(prepared.get("frontend_id", "semantic_strling"))
    request = {
        "contract_version": "1.0.0",
        "specification_version": specification_version,
        "input": {
            "kind": "source",
            "document": {
                "contract_version": "1.0.0",
                "source_id": str(prepared.get("source_id", "src:python.adapter")),
                "specification_version": specification_version,
                "frontend": {
                    "id": frontend_id,
                    "dialect_version": str(
                        prepared.get("frontend_version", specification_version)
                    ),
                },
                "content": {
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": str(
                        prepared.get(
                            "media_type",
                            "text/x-regex"
                            if frontend_id == "legacy_regex"
                            else "text/strling",
                        )
                    ),
                    "text": source,
                },
                "provenance": {"kind": "authored"},
            },
        },
        "requested_outputs": list(prepared.get("requested_outputs", fallback_outputs)),
        "compiler_options": dict(
            prepared.get(
                "compiler_options",
                {
                    "partial_semantics": "forbid",
                    "diagnostic_policy": {"minimum_severity": "hint"},
                },
            )
        ),
    }
    target_reference = prepared.get("target_profile_reference")
    if isinstance(target_reference, Mapping):
        request["target_profile"] = dict(target_reference)
    return request


__all__ = [
    "Compiler",
    "parse",
    "parse_to_artifact",
    "source_compile_request",
]
