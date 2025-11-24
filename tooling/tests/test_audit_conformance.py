import sys
from pathlib import Path

import pytest

from tooling import audit_conformance as ac


class _FakeResult:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_run_python_conformance_tests_parses_and_prints(tmp_path, monkeypatch, capsys):
    # Create the minimal bindings/python directory so the function can build paths
    repo_root = tmp_path / "repo"
    python_dir = repo_root / "bindings" / "python"
    python_dir.mkdir(parents=True)

    # Prepare fake pytest output containing a test name with a fixture
    fake_stdout = (
        "test_conformance[js_test_pattern_1.json] PASSED\n"
        "test_conformance[js_test_pattern_2.json] PASSED\n"
    )

    def fake_run(*args, **kwargs):
        return _FakeResult(stdout=fake_stdout, stderr="", returncode=0)

    monkeypatch.setattr(ac.subprocess, "run", fake_run)

    executed = ac.run_python_conformance_tests(repo_root)

    captured = capsys.readouterr()
    assert "Python (pytest stdout)" in captured.out
    assert "js_test_pattern_1.json" in captured.out
    assert executed == {"js_test_pattern_1", "js_test_pattern_2"}


def test_run_java_conformance_tests_parses_and_prints(tmp_path, monkeypatch, capsys):
    # repo layout: bindings/java and tooling/js_to_json_ast/out with fixtures
    repo_root = tmp_path / "repo"
    java_dir = repo_root / "bindings" / "java"
    fixtures_dir = repo_root / "tooling" / "js_to_json_ast" / "out"
    java_dir.mkdir(parents=True)
    fixtures_dir.mkdir(parents=True)

    # create three fixture files
    for name in ("a.json", "b.json", "c.json"):
        (fixtures_dir / name).write_text("{}")

    # Simulate maven printing a tests-run line for 3 tests
    fake_stdout = "[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0"

    def fake_run(*args, **kwargs):
        return _FakeResult(stdout=fake_stdout, stderr="", returncode=0)

    monkeypatch.setattr(ac.subprocess, "run", fake_run)

    executed = ac.run_java_conformance_tests(repo_root)

    captured = capsys.readouterr()
    assert "Java (maven stdout)" in captured.out
    assert "Tests run: 3" in captured.out
    assert executed == {"a", "b", "c"}
