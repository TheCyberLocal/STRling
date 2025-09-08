from __future__ import annotations
from typing import Mapping, Any
from pathlib import Path
import json

# jsonschema is typed on modern versions
from jsonschema import validate

Schema = Mapping[str, Any]


def validate_artifact(artifact: Mapping[str, Any], schema_path: str) -> None:
    """
    Validate a TargetArtifact against a JSON Schema.
    Raises jsonschema.exceptions.ValidationError on failure.
    """
    schema_text = Path(schema_path).read_text(encoding="utf-8")
    schema: Schema = json.loads(schema_text)
    validate(instance=artifact, schema=schema)
