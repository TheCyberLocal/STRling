import importlib.util
import os


def load_module():
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, "..", "verify_ecosystem.py"))
    spec = importlib.util.spec_from_file_location("verify_ecosystem", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_pytest_counts():
    mod = load_module()
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


def test_parse_cargo_counts():
    mod = load_module()
    out = """
    running 2 tests

    test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 1
    assert failed == 1
    assert skipped == 0


def test_parse_gradle_counts():
    mod = load_module()
    out = """
    Test run finished after 0.123 s
    [       3 tests found, 3 succeeded, 0 failed ]
    Tests: 3 passed, 0 failed, 0 skipped
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 3
    assert failed == 0
    assert skipped == 0


def test_choose_command_package_json(tmp_path):
    mod = load_module()
    d = tmp_path / "fakebind"
    d.mkdir()
    (d / "package.json").write_text('{"name":"test","scripts":{"test":"echo ok"}}')
    # choose_command expects a binding_dir path; emulate by calling choose_command on unknown binding but pointing at d
    cmd = mod.choose_command("unknown", str(d))
    assert cmd[0] in ("npm", "true")


def test_map_status_various():
    mod = load_module()
    # Crash
    assert mod.map_status_from_result(None, None, False) == "💥 CRASH"
    # rc 0 with no failed
    assert mod.map_status_from_result(0, 0, True) == "✅"
    # rc 1 with failed > 0
    assert mod.map_status_from_result(1, 5, True) == "❌"


def test_generate_report_summary():
    mod = load_module()
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


import importlib.util
import os


def load_module():
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, "..", "scripts", "verify_ecosystem.py"))
    spec = importlib.util.spec_from_file_location("verify_ecosystem", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_pytest_counts():
    mod = load_module()
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


def test_parse_cargo_counts():
    mod = load_module()
    out = """
    running 2 tests

    test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 1
    assert failed == 1
    assert skipped == 0


def test_parse_gradle_counts():
    mod = load_module()
    out = """
    Test run finished after 0.123 s
    [       3 tests found, 3 succeeded, 0 failed ]
    Tests: 3 passed, 0 failed, 0 skipped
    """
    passed, failed, skipped = mod.parse_counts_from_text(out)
    assert passed == 3
    assert failed == 0
    assert skipped == 0


def test_choose_command_package_json(tmp_path):
    mod = load_module()
    d = tmp_path / "fakebind"
    d.mkdir()
    (d / "package.json").write_text('{"name":"test","scripts":{"test":"echo ok"}}')
    # choose_command expects a binding_dir path; emulate by calling choose_command on unknown binding but pointing at d
    cmd = mod.choose_command("unknown", str(d))
    assert cmd[0] in ("npm", "true")


def test_map_status_various():
    mod = load_module()
    # Crash
    assert mod.map_status_from_result(None, None, False) == "💥 CRASH"
    # rc 0 with no failed
    assert mod.map_status_from_result(0, 0, True) == "✅"
    # rc 1 with failed > 0
    assert mod.map_status_from_result(1, 5, True) == "❌"


def test_generate_report_summary():
    mod = load_module()
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
