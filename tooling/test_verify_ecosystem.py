import importlib.util
import os
from pathlib import Path

import pytest

_CANDIDATE_MODULE_REL_PATHS = [
    os.path.join("..", "verify_ecosystem.py"),
    os.path.join("..", "scripts", "verify_ecosystem.py"),
]

# Only include module files that actually exist on disk. Some checkouts may not have
# a top-level `verify_ecosystem.py` but will have the `scripts/verify_ecosystem.py`.
MODULE_REL_PATHS = []
for p in _CANDIDATE_MODULE_REL_PATHS:
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), p))
    if os.path.exists(abs_path):
        MODULE_REL_PATHS.append(p)


def _load_module_from_relpath(relpath: str):
    """Load the verify_ecosystem module from a file relative to this test file.

    Raises ImportError if the spec or its loader can't be created so mypy/pylance
    won't be reporting Optional[...] usage later on.
    """
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, relpath))
    spec = importlib.util.spec_from_file_location("verify_ecosystem", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from path: {path!r}")
    mod = importlib.util.module_from_spec(spec)
    # At runtime loader is expected to implement exec_module
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_parse_pytest_counts(module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    out = """
    ========================= test session starts ==========================
    collected 3 items

    tests/test_core.py ..s                                         [100%]

    ======================= 2 passed, 1 skipped in 0.12s ======================
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 2
    assert failed in (0, None) or failed == 0
    assert skipped == 1


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_parse_cargo_counts(module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    out = """
    running 2 tests

    test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 1
    assert failed == 1
    assert skipped == 0


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_parse_gradle_counts(module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    out = """
    Test run finished after 0.123 s
    [       3 tests found, 3 succeeded, 0 failed ]
    Tests: 3 passed, 0 failed, 0 skipped
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 3
    assert failed == 0
    assert skipped == 0


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_choose_command_package_json(tmp_path: Path, module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    d: Path = tmp_path / "fakebind"
    d.mkdir()
    (d / "package.json").write_text('{"name":"test","scripts":{"test":"echo ok"}}')
    # choose_command expects a binding_dir path; emulate by calling choose_command on unknown binding but pointing at d
    cmd = mod.choose_command("unknown", str(d))
    assert cmd[0] in ("npm", "true")


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_map_status_various(module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    # Crash
    assert mod.map_status_from_result(None, None, False) == "💥 CRASH"
    # rc 0 with no failed
    assert mod.map_status_from_result(0, 0, True) == "✅"
    # rc 1 with failed > 0
    assert mod.map_status_from_result(1, 5, True) == "❌"


@pytest.mark.parametrize("module_relpath", MODULE_REL_PATHS)
def test_generate_report_summary(module_relpath: str):
    mod = _load_module_from_relpath(module_relpath)
    # Create two dummy results
    r1 = mod.BindingResult(
        binding="python",
        status="✅",
        passed=5,
        failed=0,
        skipped=1,
        duration=0.12,
        exit_code=0,
        stdout="ok",
        stderr="",
    )
    r2 = mod.BindingResult(
        binding="rust",
        status="❌",
        passed=3,
        failed=2,
        skipped=0,
        duration=1.23,
        exit_code=1,
        stdout="out",
        stderr="err",
    )
    md = mod.generate_report([r1, r2], generated_at=None)
    assert "Global STRling Test Report" in md
    assert "Python" in md and "Rust" in md
    assert "Total Tests" in md
