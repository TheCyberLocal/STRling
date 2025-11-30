import json

# pylint: disable=import-error
import pytest  # type: ignore[reportMissingImports]
from typing import Any, TYPE_CHECKING, ContextManager, Type, Protocol
from pathlib import Path
from STRling.core.parser import from_json_fixture, parse, STRlingParseError
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
FIXTURES_DIR = Path(__file__).parents[4] / "tests/spec"

# Provide narrow type hints for the handful of pytest members used by this test
# so static checkers (Pylance) can type-check without needing pytest stubs present.
if TYPE_CHECKING:

    class _PytestRaisesCM(Protocol):
        value: Any

    class _PytestProtocol(Protocol):
        def fail(self, msg: str) -> None: ...

        def raises(
            self, exc: Type[BaseException]
        ) -> ContextManager[_PytestRaisesCM]: ...

        def skip(self, msg: str) -> None: ...

        mark: Any

    # Tell the type checker that `pytest` conforms to this protocol;
    # at runtime the imported `pytest` module is used unchanged.
    pytest: _PytestProtocol  # type: ignore[assignment]


def get_fixtures() -> list[Path]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(list(FIXTURES_DIR.rglob("*.json")))


def get_test_id(path: Path) -> str:
    name = path.name
    if name == "semantic_duplicates.json":
        return "test_semantic_duplicate_capture_group"
    if name == "semantic_ranges.json":
        return "test_semantic_ranges"
    return name


@pytest.mark.parametrize("fixture_path", get_fixtures(), ids=get_test_id)
def test_conformance(fixture_path: Path) -> None:
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle expected error cases
    if "expected_error" in data:
        expected_error_msg = data["expected_error"]
        input_dsl = data.get("input_dsl")
        if not input_dsl:
            pytest.fail("Error test case missing 'input_dsl'")

        with pytest.raises(STRlingParseError) as excinfo:
            parse(input_dsl)

        # Verify error message contains expected substring
        assert expected_error_msg in str(excinfo.value)
        return

    # Skip if no expected pcre
    if "expected_codegen" not in data or "pcre" not in data["expected_codegen"]:
        pytest.skip("No expected PCRE output")

    expected_pcre = data["expected_codegen"]["pcre"]

    # Deserialize AST
    try:
        ast_root = from_json_fixture(data["input_ast"])
    except ValueError as e:
        pytest.fail(f"Deserialization failed: {e}")
        return

    # Compile to IR
    compiler = Compiler()
    ir_root = compiler.compile(ast_root)

    # Emit
    flags = data.get("flags", {})
    emitted_pcre = emit(ir_root, flags)

    assert emitted_pcre == expected_pcre
