"""
STRling Validator - JSON Schema Validation for Target Artifacts

This module provides validation functionality for STRling TargetArtifact objects
against their JSON Schema definitions (draft 2020-12). It ensures that compiled
patterns conform to the expected structure before emission.

The validator uses the jsonschema library to validate artifacts against schemas
located in the spec/schema directory. It provides detailed error messages when
validation fails, helping to catch structural issues early in the compilation
pipeline.
"""

from __future__ import annotations
from typing import Mapping, Any, Optional, TYPE_CHECKING
from pathlib import Path
import json

from jsonschema import Draft202012Validator

# Make a best-effort attempt to import `referencing.Registry` at runtime.
# Some environments (CI, static type checking) may not have `referencing`
# installed. We ensure `referencing_available` is always defined so static
# analyzers and linters don't flag an undefined name.
referencing_available: bool = False
if TYPE_CHECKING:
    # For type checkers only: expose the Registry type without requiring the
    # runtime dependency to be present. This import is not executed at
    # runtime because TYPE_CHECKING is False at runtime.
    from referencing import Registry  # pragma: no cover - type checking only
else:
    try:
        # runtime attempt to import referencing.Registry if available
        from referencing import Registry  # type: ignore

        referencing_available = True
    except Exception:  # pragma: no cover - optional runtime dep
        Registry = Any  # type: ignore

Schema = Mapping[str, Any]


def validate_artifact(
    artifact: Mapping[str, Any],
    schema_path: str,
    registry: Optional["Registry"] = None,
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

    if registry is not None and referencing_available:
        # Use the modern jsonschema API with referencing.Registry directly
        # This avoids the deprecated RefResolver class
        validator: Draft202012Validator = Draft202012Validator(
            schema, registry=registry
        )
    else:
        validator: Draft202012Validator = Draft202012Validator(schema)

    validator.validate(instance=artifact)
