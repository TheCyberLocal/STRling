from __future__ import annotations
from typing import Mapping, Any
from pathlib import Path
import json

from jsonschema import Draft202012Validator

try:
    # referencing>=0.30 for modern jsonschema
    from referencing import Registry
    HAVE_REFERENCING = True
except ImportError:  # pragma: no cover
    HAVE_REFERENCING = False
    Registry = None  # type: ignore[assignment,misc]

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

    if registry is not None and HAVE_REFERENCING:
        # Use the modern jsonschema API with referencing.Registry directly
        # This avoids the deprecated RefResolver class
        validator = Draft202012Validator(schema, registry=registry)
    else:
        validator = Draft202012Validator(schema)
    
    validator.validate(instance=artifact)
