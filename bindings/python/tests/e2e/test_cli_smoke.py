"""Black-box smoke tests for the canonical Rust CLI transport."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest


TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parents[3]
KERNEL_MANIFEST = PROJECT_ROOT / "core" / "Cargo.toml"
PCRE2_PROFILE = "pcre2-10.43"
VALID_REGEX = "a(?<b>c)"


def cargo_executable() -> str:
    configured = os.environ.get("CARGO")
    discovered = shutil.which("cargo")
    conventional = (
        Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    )
    executable = (
        configured
        or discovered
        or (str(conventional) if conventional.is_file() else None)
    )
    if executable is None:
        pytest.fail("cargo is required for canonical CLI smoke tests")
    return executable


def run_cli(
    arguments: list[str], stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            cargo_executable(),
            "run",
            "--quiet",
            "--manifest-path",
            str(KERNEL_MANIFEST),
            "--bin",
            "strling-kernel",
            "--",
            *arguments,
        ],
        cwd=PROJECT_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def cli_directory() -> Iterator[Path]:
    path = PROJECT_ROOT / "core" / "target" / f"python-cli-smoke-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_file_import_emits_canonical_target_artifact(cli_directory: Path) -> None:
    source = cli_directory / "valid.regex"
    source.write_text(VALID_REGEX, encoding="utf-8")

    result = run_cli(
        [
            "import",
            "--input",
            str(source),
            "--target",
            PCRE2_PROFILE,
            "--output",
            "target_artifact",
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert result.stderr == ""
    response = json.loads(result.stdout)
    assert response["contract_version"] == "1.0.0"
    assert response["outcome"] == "succeeded"
    assert response["artifact"]["pattern"]["text"] == VALID_REGEX
    assert response["semantic_result"]["program"]["sources"][0]["provenance"] == {
        "kind": "imported"
    }


def test_stdin_import_matches_file_artifact() -> None:
    result = run_cli(
        [
            "import",
            "--input",
            "-",
            "--target",
            PCRE2_PROFILE,
            "--output",
            "target_artifact",
            "--format",
            "json",
        ],
        VALID_REGEX,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["artifact"]["pattern"]["text"] == VALID_REGEX


def test_check_returns_canonical_compile_result(cli_directory: Path) -> None:
    source = cli_directory / "valid.regex"
    source.write_text(VALID_REGEX, encoding="utf-8")

    result = run_cli(
        [
            "check",
            "--input",
            str(source),
            "--frontend",
            "regex",
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert result.stderr == ""
    response = json.loads(result.stdout)
    assert response["outcome"] == "succeeded"
    assert response["diagnostics"] == []


def test_parse_failure_is_structured_and_exits_two(cli_directory: Path) -> None:
    source = cli_directory / "invalid.regex"
    source.write_text("a(b", encoding="utf-8")

    result = run_cli(["import", "--input", str(source), "--format", "json"])

    assert result.returncode == 2
    assert result.stderr == ""
    response = json.loads(result.stdout)
    assert response["outcome"] == "failed"
    assert response["diagnostics"][0]["code"] == "STRL-FRONTEND-2012"


def test_retired_schema_flag_is_rejected_explicitly(cli_directory: Path) -> None:
    source = cli_directory / "valid.regex"
    source.write_text(VALID_REGEX, encoding="utf-8")

    result = run_cli(
        ["import", "--input", str(source), "--schema", "legacy.schema.json"]
    )

    assert result.returncode == 64
    assert result.stdout == ""
    assert "--schema is retired" in result.stderr


def test_missing_file_uses_stable_io_exit(cli_directory: Path) -> None:
    missing = cli_directory / "does-not-exist.regex"

    result = run_cli(["import", "--input", str(missing)])

    assert result.returncode == 74
    assert result.stdout == ""
    assert "cannot open source input" in result.stderr
