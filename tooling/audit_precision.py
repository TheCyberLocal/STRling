#!/usr/bin/env python3
import os
import subprocess
import re
import json
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SPEC_DIR = PROJECT_ROOT / "tests" / "spec"
BINDINGS_DIR = PROJECT_ROOT / "bindings"


# Baseline Metrics
def get_baseline_metrics():
    spec_files = list(SPEC_DIR.glob("*.json"))
    total_specs = len(spec_files)
    compiler_only = 0
    for spec in spec_files:
        try:
            with open(spec, "r", encoding="utf-8") as f:
                content = f.read()
                if '"input_ast"' in content:
                    compiler_only += 1
        except Exception:
            pass
    return total_specs, compiler_only


# Binding Configurations
BINDINGS = [
    {
        "name": "python",
        "command": ["pytest", "tests/unit/test_conformance.py"],
        "pattern": r"(\d+) passed",
    },
    {
        "name": "rust",
        "command": ["cargo", "test", "--test", "conformance"],
        "pattern": r"test result: ok\. (\d+) passed",
    },
    {
        "name": "go",
        "command": ["go", "test", "-v", "conformance_test.go"],
        "pattern": r"RUN\s+TestConformance/\S+",
        "count_occurrences": True,
    },
    {"name": "csharp", "command": ["dotnet", "test"], "pattern": r"Passed:\s+(\d+)"},
    {
        "name": "typescript",
        "command": ["npm", "test", "--", "conformance"],
        "pattern": r"Tests:\s+(\d+) passed",
    },
    {
        "name": "java",
        "command": ["mvn", "test", "-Dtest=ConformanceTests"],
        "pattern": r"Tests run: (\d+), Failures: 0",
    },
    {
        "name": "kotlin",
        "command": ["./gradlew", "test", "--tests", "strling.ConformanceTest"],
        "pattern": r"(\d+) tests completed",
    },
    {"name": "c", "command": ["make", "tests"], "pattern": r"Tests passed: (\d+)"},
    {"name": "cpp", "command": ["ctest"], "pattern": r"(\d+)% tests passed"},
    {
        "name": "ruby",
        "command": ["rake", "test"],
        "pattern": r"(\d+) runs, (\d+) assertions",
    },
    {
        "name": "php",
        "command": ["vendor/bin/phpunit", "tests/ConformanceTest.php"],
        "pattern": r"OK \((\d+) tests",
    },
    {
        "name": "perl",
        "command": ["prove", "t/conformance.t"],
        "pattern": r"Files=\d+, Tests=(\d+)",
    },
    {
        "name": "lua",
        "command": ["busted", "spec/strling_spec.lua"],
        "pattern": r"(\d+) successes",
    },
    {"name": "swift", "command": ["swift", "test"], "pattern": r"Executed (\d+) tests"},
    {
        "name": "dart",
        "command": ["dart", "test", "test/conformance_test.dart"],
        "pattern": r"All (\d+) tests passed",
    },
    {
        "name": "r",
        "command": ["Rscript", "-e", "devtools::test()"],
        "pattern": r"\[ FAIL \d+ \| WARN \d+ \| SKIP \d+ \| PASS (\d+) \]",
    },
]


def run_audit():
    print("Starting Precision Audit...")

    # 1. Establish Baseline
    total_specs, compiler_only = get_baseline_metrics()
    print(f"Baseline Metrics:")
    print(f"  Total Specs: {total_specs}")
    print(f"  Compiler-Only (AST): {compiler_only}")
    print("-" * 40)

    results = []

    # 2. Check Bindings
    binding_dirs = [d for d in BINDINGS_DIR.iterdir() if d.is_dir()]
    config_map = {b["name"]: b for b in BINDINGS}

    print(f"{'Binding':<15} | {'Count':<10} | {'Delta':<10} | {'Status':<20}")
    print("-" * 60)

    for b_dir in sorted(binding_dirs):
        name = b_dir.name

        if name not in config_map:
            print(f"{name:<15} | {'?':<10} | {'?':<10} | {'No Config':<20}")
            continue

        config = config_map[name]
        cmd = config["command"]
        pattern = config["pattern"]
        cwd = b_dir

        try:
            # Run the test command
            result = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )

            output = result.stdout + "\n" + result.stderr

            count = 0
            if config.get("count_occurrences"):
                matches = re.findall(pattern, output)
                count = len(matches)
            else:
                match = re.search(pattern, output)
                if match:
                    count = int(match.group(1))
                else:
                    count = -1

            delta = count - total_specs

            status = ""
            if count == total_specs:
                status = "✅ Perfect"
            elif count == -1:
                status = "⚠️ Parse Error"
            elif count < total_specs:
                if count >= compiler_only:
                    status = "⚠️ Minor Deficit"
                else:
                    status = "🔴 Defect"
            else:
                status = "🔵 Inflated"

            print(f"{name:<15} | {count:<10} | {delta:<10} | {status:<20}")

            results.append(
                {
                    "binding": name,
                    "count": count,
                    "delta": delta,
                    "status": status,
                    "raw_output_snippet": output[:200] if count == -1 else "",
                }
            )

        except subprocess.TimeoutExpired:
            print(f"{name:<15} | {'Timeout':<10} | {'?':<10} | {'🔴 Timeout':<20}")
            results.append(
                {
                    "binding": name,
                    "count": "Timeout",
                    "delta": "?",
                    "status": "🔴 Timeout",
                }
            )
        except Exception as e:
            print(f"{name:<15} | {'Error':<10} | {'?':<10} | {f'🔴 {str(e)[:15]}':<20}")
            results.append(
                {"binding": name, "count": "Error", "delta": "?", "status": "🔴 Error"}
            )

    # Generate Report
    report_path = PROJECT_ROOT / "docs" / "reports" / "coverage_precision.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        f.write("# Precision Audit & Coverage Justification\n\n")
        f.write(f"**Date:** 2025-11-23\n")
        f.write(f"**Baseline Target:** {total_specs}\n")
        f.write(f"**Compiler-Only Target:** {compiler_only}\n\n")
        f.write("| Binding | Count | Delta | Status | Justification/Remediation |\n")
        f.write("|---|---|---|---|---|\n")

        for r in results:
            justification = "TODO"
            if r["status"] == "✅ Perfect":
                justification = "Full compliance."
            elif r["count"] == -1:
                justification = "Could not parse test output. Check runner."

            f.write(
                f"| {r['binding']} | {r['count']} | {r['delta']} | {r['status']} | {justification} |\n"
            )

    print(f"\nReport generated at {report_path}")


if __name__ == "__main__":
    run_audit()
