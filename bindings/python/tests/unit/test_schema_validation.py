from __future__ import annotations

from typing import Any
import json
import pathlib

import pytest

from STRling.core.parser import parse_to_artifact as p2a

BASE = (
    pathlib.Path(__file__).resolve().parents[4] / "spec" / "schema" / "base.schema.json"
)

# Optional dependency: import if available, else skip these tests
try:
    import jsonschema as _jsonschema  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dep
    _jsonschema = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(_jsonschema is None, reason="jsonschema not installed")


def _load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "src",
    [
        r"abc",
        r"(?<n>\d+)-\k<n>",
        r"[A-Za-z0-9_]+",
        r"^foo$",
        r"(?=bar)baz",
        r"(?<=foo)bar",
    ],
)
def test_artifact_validates_against_base_schema(src: str) -> None:
    schema = _load_json(BASE)
    art = p2a(src)
    assert _jsonschema is not None
    _jsonschema.validate(art, schema)  # type: ignore[union-attr]
    assert art["version"] == "1.0.0"
