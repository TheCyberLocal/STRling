import json
import pytest
from pathlib import Path
from STRling.core.parser import from_json_fixture
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit

# Locate fixtures
# This file is in bindings/python/tests/unit/
# We want to go to tooling/js_to_json_ast/out/
# ../../../.. from tests/unit goes to bindings/python/tests/unit -> bindings/python/tests -> bindings/python -> bindings -> root
# Wait.
# bindings/python/tests/unit/test_conformance.py
# . parents[0] = unit
# . parents[1] = tests
# . parents[2] = python
# . parents[3] = bindings
# . parents[4] = STRling (root)
# So parents[4] is correct if we are in root/bindings/python/tests/unit
# Let's verify.
FIXTURES_DIR = Path(__file__).parents[4] / "tooling/js_to_json_ast/out"


def get_fixtures():
    if not FIXTURES_DIR.exists():
        return []
    return sorted(list(FIXTURES_DIR.rglob("*.json")))


@pytest.mark.parametrize("fixture_path", get_fixtures(), ids=lambda p: p.name)
def test_conformance(fixture_path):
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Skip if no expected pcre
    if "expected_codegen" not in data or "pcre" not in data["expected_codegen"]:
        pytest.skip("No expected PCRE output")

    expected_pcre = data["expected_codegen"]["pcre"]

    # Deserialize AST
    try:
        ast_root = from_json_fixture(data["input_ast"])
    except ValueError as e:
        pytest.fail(f"Deserialization failed: {e}")

    # Compile to IR
    compiler = Compiler()
    ir_root = compiler.compile(ast_root)

    # Emit
    flags = data.get("flags", {})
    emitted_pcre = emit(ir_root, flags)

    assert emitted_pcre == expected_pcre
