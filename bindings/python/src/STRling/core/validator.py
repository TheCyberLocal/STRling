from __future__ import annotations
from typing import Mapping, Any
from pathlib import Path
import json

from jsonschema import Draft202012Validator, RefResolver

try:
    # referencing>=0.36 exposes Registry at the top level
    from referencing import Registry  # type: ignore
except Exception:  # pragma: no cover – fallback if very old referencing
    Registry = None  # type: ignore[assignment]

Schema = Mapping[str, Any]


def validate_artifact(
    artifact: Mapping[str, Any],
    schema_path: str,
    registry: "Registry | None" = None,
) -> None:
    """Validate a TargetArtifact against a JSON Schema (draft 2020-12).

    Parameters
    ----------
    artifact : Mapping[str, Any]
        The concrete artifact to validate.
    schema_path : str
        Filesystem path to the JSON schema (can contain $ref).
    registry : referencing.Registry | None
        Optional pre-built referencing registry to resolve $ref / $dynamicRef.

    Raises
    ------
    jsonschema.exceptions.ValidationError
        If validation fails.
    """
    schema_text = Path(schema_path).read_text(encoding="utf-8")
    schema: Schema = json.loads(schema_text)

    if registry is not None:
        # Convert Registry to RefResolver for compatibility with jsonschema 4.x
        # Build a store dictionary from all resources in the registry
        store = {}
        for uri in registry.keys():
            resource = registry.get(uri)
            if resource is not None:
                store[uri] = resource.contents
        
        resolver = RefResolver(
            base_uri=schema.get("$id", ""),
            referrer=schema,
            store=store
        )
        validator = Draft202012Validator(schema, resolver=resolver)
    else:
        validator = Draft202012Validator(schema)

    validator.validate(instance=artifact)
