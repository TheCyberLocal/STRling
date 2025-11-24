#!/usr/bin/env python3
"""
Unified test orchestration for all STRling language bindings.

Creates TEST_REPORT.md at repo root summarizing per-binding test results.

Usage: python tooling/scripts/verify_ecosystem.py [--report-path PATH] [--dry-run] [--timeout SECONDS]

This script is intentionally conservative: it will not install dependencies by default.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict


def _find_repo_root(start: Optional[str] = None) -> str:
    # Walk upward from start until we find a directory that looks like the repo root
    # (it should contain the `bindings/` directory). Fallback to two levels up.
    start = start or os.path.dirname(__file__)
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "bindings")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur or parent == "":
            # fallback
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cur = parent


ROOT = _find_repo_root()
TEST_REPORT_PATH_DEFAULT = os.path.join(ROOT, "TEST_REPORT.md")

# Map structure: binding-dir -> command list
BINDING_CONFIG: Dict[str, List[str]] = {
    # Reference Implementations
    "python": ["pytest"],
    "javascript": ["npm", "test"],
    "typescript": ["npm", "test"],
    # Systems
    "rust": ["cargo", "test"],
    "c": ["make", "test"],
    "cpp": ["ctest"],
    "go": ["go", "test", "./..."],
    "swift": ["swift", "test"],
    # JVM & .NET
    "java": ["./gradlew", "test"],
    "kotlin": ["./gradlew", "test"],
    "csharp": ["dotnet", "test"],
    "fsharp": ["dotnet", "test"],
    # Scripting
    "ruby": ["bundle", "exec", "rake", "test"],
    "perl": ["prove", "-r", "t/"],
    "php": ["composer", "test"],
    "r": ["Rscript", "-e", "testthat::test_dir('tests')"],
    "lua": ["busted"],
    "dart": ["dart", "test"],
}


@dataclass
class BindingResult:
    binding: str
    status: str
    passed: Optional[int]
    failed: Optional[int]
    skipped: Optional[int]
    duration: float
    exit_code: Optional[int]
    stdout: str
    stderr: str


def find_binding_dir(binding: str) -> Optional[str]:
    path = os.path.join(ROOT, "bindings", binding)
    return path if os.path.isdir(path) else None


def choose_command(binding: str, binding_dir: str) -> List[str]:
    # Use static registry by default, but perform small heuristics
    if binding == "javascript" and not os.path.isdir(binding_dir):
        # Many repos use `typescript` instead of `javascript` — try that overlay
        alt = os.path.join(ROOT, "bindings", "typescript")
        if os.path.isdir(alt):
            binding_dir = alt

    if binding in BINDING_CONFIG:
        return list(BINDING_CONFIG[binding])

    # fallback: try to detect common manifests
    if os.path.exists(os.path.join(binding_dir, "package.json")):
        return ["npm", "test"]
    if os.path.exists(os.path.join(binding_dir, "pyproject.toml")) or os.path.exists(
        os.path.join(binding_dir, "pytest.ini")
    ):
        return ["pytest"]
    if os.path.exists(os.path.join(binding_dir, "Cargo.toml")):
        return ["cargo", "test"]
    return ["true"]


def run_command(
    cmd: List[str], cwd: Optional[str], timeout: Optional[int]
) -> Tuple[Optional[int], str, str, float]:
    start = time.perf_counter()
    try:
        # Use shutil.which to ensure the command is available; if not, we'll capture error
        if shutil.which(cmd[0]) is None and not cmd[0].startswith("./"):
            raise FileNotFoundError(f"Command not found: {cmd[0]}")

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        rc = proc.returncode
        stdout = proc.stdout.decode(errors="replace")
        stderr = proc.stderr.decode(errors="replace")
    except FileNotFoundError as e:
        rc = None
        stdout = ""
        stderr = str(e)
    except subprocess.TimeoutExpired as e:
        rc = None
        stdout = e.stdout.decode(errors="replace") if e.stdout else ""
        stderr = f"Timeout after {timeout}s"
    except Exception as e:
        rc = None
        stdout = ""
        stderr = str(e)
    end = time.perf_counter()
    return rc, stdout, stderr, end - start


def parse_counts_from_text(
    text: str,
) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    # Generic patterns used by pytest, cargo, gradle, go, etc.
    # Examples matched: '14 passed', '2 failed', '3 skipped', 'X passed, Y failed, Z skipped'
    passed = failed = skipped = None

    # Combined pattern: e.g., 'X passed, Y failed, Z skipped'
    combo = re.search(
        r"(?P<passed>\d+)\s+passed.*?(?P<failed>\d+)\s+failed.*?(?P<skipped>\d+)\s+skipped",
        text,
        re.I | re.S,
    )
    if combo:
        passed = int(combo.group("passed"))
        failed = int(combo.group("failed"))
        skipped = int(combo.group("skipped"))
        return passed, failed, skipped

    # Another combined style: 'Tests: X passed, Y failed, Z skipped' or 'Tests: X failed, Y passed, Z skipped'
    combo2 = re.search(
        r"Tests?:\s*(?P<a>\d+)\s+passed.*?(?P<b>\d+)\s+failed.*?(?P<c>\d+)\s+skipped",
        text,
        re.I | re.S,
    )
    if combo2:
        return int(combo2.group("a")), int(combo2.group("b")), int(combo2.group("c"))

    # cargo 'test result: ok. 0 passed; 0 failed; 0 ignored;'
    cargo = re.search(
        r"test result:\s*(?P<result>ok|FAILED).*?(?P<passed>\d+)\s+passed;.*?(?P<failed>\d+)\s+failed;.*?(?P<skipped>\d+)\s+(?:ignored|skipped);",
        text,
        re.I | re.S,
    )
    if cargo:
        passed = int(cargo.group("passed"))
        failed = int(cargo.group("failed"))
        skipped = int(cargo.group("skipped"))
        return passed, failed, skipped

    # single patterns
    m_passed = re.search(r"(\d+)\s+passed", text, re.I)
    if m_passed:
        passed = int(m_passed.group(1))

    m_failed = re.search(r"(\d+)\s+failed", text, re.I)
    if m_failed:
        failed = int(m_failed.group(1))

    m_skipped = re.search(r"(\d+)\s+skipped", text, re.I)
    if m_skipped:
        skipped = int(m_skipped.group(1))

    # gradle 'Tests: 3 passed, 1 failed, 0 skipped' or '0 failures'
    gradle_totals = re.search(r"(\d+)\s+failed\s+tests?", text, re.I)
    if gradle_totals and failed is None:
        failed = int(gradle_totals.group(1))

    # TAP-like 'ok' lines -> count of 'ok' and 'not ok'
    if passed is None or failed is None:
        ok_count = len(re.findall(r"^ok\b", text, re.M))
        not_ok = len(re.findall(r"^not ok\b", text, re.M))
        if ok_count and (passed is None):
            passed = ok_count
        if not_ok and (failed is None):
            failed = not_ok

    return passed, failed, skipped


def map_status_from_result(
    rc: Optional[int], failed: Optional[int], parsed_some: bool
) -> str:
    # Exit codes 0 and 1 are considered normal for test frameworks – 1 may indicate failures but not a crash
    if rc is None:
        return "💥 CRASH"
    if rc not in (0, 1):
        return "💥 CRASH"
    # rc 0/1
    # If parsed counts and failed > 0 -> failing
    if parsed_some and failed and failed > 0:
        return "❌"
    # If rc == 0 and nothing failed -> pass
    if rc == 0:
        return "✅"
    # rc == 1 but no failed count -> conservative fail symbol
    if rc == 1:
        return "❌"
    return "❓"


def generate_report(
    results: List[BindingResult], generated_at: Optional[datetime] = None
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    rows = []
    for r in results:
        passed = r.passed if r.passed is not None else 0
        failed = r.failed if r.failed is not None else 0
        skipped = r.skipped if r.skipped is not None else 0

        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        total_tests += passed + failed + skipped

        rows.append(
            (
                r.binding.capitalize(),
                r.status,
                passed,
                failed,
                skipped,
                f"{r.duration:.2f}s",
            )
        )

    global_health = 0.0
    total_count = total_passed + total_failed
    if total_count > 0:
        global_health = float(total_passed) / total_count * 100.0

    overall_status = "✅" if total_failed == 0 else "❌"

    lines = []
    lines.append("# Global STRling Test Report")
    lines.append(f"**Generated:** {generated_at.isoformat()}")
    lines.append(f"**Status:** {overall_status}")
    lines.append("")
    lines.append("| Binding | Status | Passed | Failed | Skipped | Duration |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for name, status, passed, failed, skipped, duration in rows:
        lines.append(
            f"| {name} | {status} | {passed} | {failed} | {skipped} | {duration} |"
        )

    lines.append("")
    lines.append(
        f"**Total Tests:** {total_tests} | **Global Health:** {global_health:.1f}%"
    )
    lines.append("")
    lines.append("---")
    lines.append("## Details")
    lines.append("")
    for r in results:
        if r.status in ("💥 CRASH", "❌"):
            lines.append(f"### {r.binding.capitalize()} — {r.status}")
            lines.append(f"- Exit code: {r.exit_code}")
            lines.append(f"- Duration: {r.duration:.2f}s")
            lines.append("\n<details>\n<summary>stdout</summary>\n\n```")
            lines.append(r.stdout or "(no stdout)")
            lines.append("```\n</details>\n")
            lines.append("\n<details>\n<summary>stderr</summary>\n\n```")
            lines.append(r.stderr or "(no stderr)")
            lines.append("```\n</details>\n")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-path", default=TEST_REPORT_PATH_DEFAULT)
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout (s) per test command"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect bindings and commands but don't execute them",
    )
    parser.add_argument(
        "--bindings",
        nargs="*",
        help="Optional list of specific binding names to run (default: all in registry)",
    )
    args = parser.parse_args(argv)

    target_bindings = args.bindings or list(BINDING_CONFIG.keys())

    results: List[BindingResult] = []

    for binding in sorted(set(target_bindings)):
        bdir = find_binding_dir(binding)
        if bdir is None:
            results.append(
                BindingResult(
                    binding=binding,
                    status="⚠️ MISSING",
                    passed=0,
                    failed=0,
                    skipped=0,
                    duration=0.0,
                    exit_code=None,
                    stdout="",
                    stderr="",
                )
            )
            continue

        cmd = choose_command(binding, bdir)
        if args.dry_run:
            results.append(
                BindingResult(
                    binding=binding,
                    status="⚠️ DRY-RUN",
                    passed=0,
                    failed=0,
                    skipped=0,
                    duration=0.0,
                    exit_code=0,
                    stdout="",
                    stderr=f"DRY-RUN: would run: {shlex.join(cmd)} in {bdir}",
                )
            )
            continue

        rc, stdout, stderr, duration = run_command(cmd, cwd=bdir, timeout=args.timeout)
        passed, failed, skipped = parse_counts_from_text(stdout + "\n" + stderr)
        parsed_some = any(x is not None for x in (passed, failed, skipped))
        status = map_status_from_result(rc, failed, parsed_some)

        r = BindingResult(
            binding=binding,
            status=status,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            exit_code=rc,
            stdout=stdout,
            stderr=stderr,
        )
        results.append(r)

    report_md = generate_report(results)
    with open(args.report_path, "w", encoding="utf-8") as fh:
        fh.write(report_md)

    print(f"Wrote test report to {args.report_path}")

    # Exit with non-zero if any crash occurred
    if any(r.status == "💥 CRASH" for r in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
