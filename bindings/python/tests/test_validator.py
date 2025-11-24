import json
import tempfile
from pathlib import Path
import pytest
from jsonschema import ValidationError

from STRling.core.validator import validate_artifact


def test_validate_artifact_pass():
    artifact = {"foo": "bar"}
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string"}},
        "required": ["foo"],
    }

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        f.write(json.dumps(schema))
        schema_path = f.name

    # should not raise
    validate_artifact(artifact, schema_path)


def test_validate_artifact_fails():
    artifact = {}
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string"}},
        "required": ["foo"],
    }

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        f.write(json.dumps(schema))
        schema_path = f.name

    with pytest.raises(ValidationError):
        validate_artifact(artifact, schema_path)
