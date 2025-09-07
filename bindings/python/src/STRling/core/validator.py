
from __future__ import annotations
from typing import Dict, Any
import json, os
from pathlib import Path

def validate_artifact(artifact: Dict[str, Any], schema_path: str) -> None:
    """
    Validate a TargetArtifact against a JSON schema.
    Raises jsonschema.exceptions.ValidationError on failure.
    """
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise RuntimeError("jsonschema is required for validation but not installed") from e
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=artifact, schema=schema)
