import json
import os
import subprocess
import re
import sys
from typing import Optional, Tuple, List, Dict, Any

# Configuration
TOOLCHAIN_PATH = "toolchain.json"
REPORT_PATH = os.path.join("docs", "generated", "FINAL_AUDIT_REPORT.md")
STRLING_CLI = "./strling"


def print_instructional_failure():
    print("\n" + "=" * 60)
    print("🔴 OMEGA AUDIT FAILED")
    print("=" * 60)
    print("\nThe Golden Master validation has failed.")
    print("The Audit tool keeps output clean and does not display specific errors.\n")

    print("👉 ACTION REQUIRED:")
    print("To see the specific errors and debug your changes, you must run")
    print("the test command for the binding you are working on:\n")
    print("   ./strling test <language>  (e.g., ./strling test python)\n")
    print("=" * 60 + "\n")


# Regex patterns for detecting skipped tests
# These patterns should match actual skipped test indicators, not summary counts
SKIP_PATTERNS = [
    r"\s+skipped\b",  # whitespace + "skipped" + word boundary
    r"SKIPPED\b",
    r"\s+ignored\b",  # whitespace + "ignored" + word boundary
    r"\bpending\b",
    r"\bTODO\b",
    r"\[-\]",  # Some runners use [-] for skipped
    r"\bskip:",  # "skip:" at word boundary
    r"\bSkip:",
]

# Skip exclusion patterns (to avoid false positives from summary lines)
SKIP_EXCLUDE_PATTERNS = [
    r"\b0 ignored\b",
    r"\b0 skipped\b",
    r"skipped 0",
    r"Skipped:\s*0",
    r"> Task :.*SKIPPED",  # Gradle task skips (e.g., "> Task :checkKotlinGradlePluginConfigurationErrors SKIPPED")
    r"^=== RUN",  # Test run indicators should not be counted as skips (e.g., "=== RUN comments_are_ignored")
    r"\b0 pending\b",  # Busted summary line (e.g., "598 successes / 0 failures / 0 errors / 0 pending")
]

# Warning patterns for test/build output.
# Keep these scoped to actual diagnostic formats so test names like
# "ReDoS Risk Warning: Nested Quantifiers" do not count as build noise.
WARNING_PATTERNS = [
    r"^\s*warning\b",
    r"^\s*WARNING\b",
    r"^\s*Warning\b",
    r":\s*warning(?:\s+[A-Z]+\d+)?:",
    r"^\s*npm\s+WARN\b",
]

# Patterns that should NOT be counted as warnings (false positives)
# These include locale warnings and compiler warnings that aren't test failures
WARNING_EXCLUDE_PATTERNS = [
    r"locale",
    r"Setting locale failed",
    r"LANGUAGE",
    r"LC_ALL",
    r"\bwarnings\s*:\s*\[",
    r"\bno\s+warnings\b",
    # Rust/Cargo compiler warnings
    r"unused variable",
    r"unused import",
    r"never used",
    r"never read",
    r"unnecessary parentheses",
    r"generated \d+ warnings?\b",
    r"run `cargo fix",
    # GCC/Clang warnings
    r"-Wunused",
    r"-Wdeprecated",
    # General build warnings to ignore
    r"prerequisite",  # Perl prereq warnings
    # Node.js warnings
    r"localstorage-file",
]

# Semantic checks (filenames/patterns that must appear in output)
# Multiple patterns per check for different test runners
SEMANTIC_CHECKS = {
    "DupNames": [
        "test_semantic_duplicate_capture_group",
        "test_semantic_duplicates",  # Rust outputs this
        "semantic_duplicates",
        "duplicate_capture_group",
        "dup_names",
        "DupNames",
        "semantic_duplicates.json",  # For Go and other runners that output full filename
    ],
    "Ranges": [
        "test_semantic_ranges",
        "semantic_ranges",
        "Ranges",
        "semantic_ranges.json",  # For Go and other runners that output full filename
    ],
    # Essential 5 stdlib coverage. Bindings emit test names that vary per
    # runner, but the substring "email" reliably appears for any runner that
    # exercised the Essential helpers (e.g. test_email_valid, EmailValid,
    # essential_5/email, "Essential5.EmailValid", etc.).
    "Essential5": [
        "Essential5",
        "essential_5",
        "essential5",
        "essential-5",
        "test_email",
        "EmailValid",
        "email_valid",
        "email valid",
        "Essential.email",
        "essential::email",
    ],
}

# Test count patterns (Generic to Specific)
TEST_PATTERNS = [
    r"(\d+) tests passed",
    r"====\s+(\d+)\s+passed",
    r"Tests:\s+(\d+)\s+passed",
    r"Tests:\s+(\d+) passed,\s+\d+ total",  # Jest
    r"Executed (\d+) tests, with 0 failures",  # XCTest (Swift)
    r"\[STRling Audit\] Tests: (\d+), Skipped: \d+",  # Kotlin (Strict)
    r"test result: ok\. (\d+) passed",
    r"Tests run:\s+(\d+), Failures: 0",
    r"Files=\d+, Tests=(\d+)",
    r"OK \((\d+) tests?[,\)]",
    r"^Tests:\s*(\d+)",
    r"\[\s*FAIL\s*\d+\s*\|\s*WARN\s*\d+\s*\|\s*SKIP\s*\d+\s*\|\s*PASS\s*(\d+)\s*\]",  # R (Strict)
    r"^(\d+) successes / \d+ failures / \d+ errors",  # Lua (Strict)
    r"(\d+) runs, \d+ assertions",  # Ruby
    r"\+(\d+): All tests passed",
    r"(\d+)/\d+ tests passed",
    r"Passed:\s+(\d+)",
]


def load_toolchain():
    with open(TOOLCHAIN_PATH, "r") as f:
        return json.load(f)


def run_command(cmd: str) -> Optional[subprocess.CompletedProcess[str]]:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result
    except Exception:
        return None


def analyze_output(stdout: str, stderr: str) -> Tuple[int, int]:
    skips = 0
    warnings = 0

    combined = stdout + "\n" + stderr
    lines = combined.split("\n")

    # Count skips per line, excluding false positives like "0 ignored"
    for line in lines:
        has_skip = False
        for pattern in SKIP_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                has_skip = True
                break

        if has_skip:
            # Check if this skip should be excluded (e.g., "0 ignored" summary)
            is_excluded = False
            for exclude_pattern in SKIP_EXCLUDE_PATTERNS:
                if re.search(exclude_pattern, line, re.IGNORECASE):
                    is_excluded = True
                    break
            if not is_excluded:
                skips += 1

    # Count warnings per line, excluding false positives
    for line in lines:
        has_warning = False
        for pattern in WARNING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                has_warning = True
                break

        if has_warning:
            # Check if this warning should be excluded (e.g., locale warnings)
            is_excluded = False
            for exclude_pattern in WARNING_EXCLUDE_PATTERNS:
                if re.search(exclude_pattern, line, re.IGNORECASE):
                    is_excluded = True
                    break
            if not is_excluded:
                warnings += 1

    return skips, warnings


def check_semantic(stdout: str, stderr: str, check_key: str) -> bool:
    # Check if the specific test file or case was mentioned in the output
    # This assumes runners print test names.
    combined = stdout + "\n" + stderr

    targets = SEMANTIC_CHECKS.get(check_key, [])
    if not targets:
        return False

    # Check if any of the target patterns are found in the output
    for target in targets:
        if target in combined:
            return True
    return False


def main():
    print(">> Starting Operation Omega: Final Ecosystem Coherency Audit")

    # 1. Environment Sterilization
    print(">> Step 1: Environment Sterilization (Global Clean)")
    run_command(f"{STRLING_CLI} clean all")

    toolchain = load_toolchain()
    bindings = toolchain.get("bindings", {})

    results: List[Dict[str, Any]] = []

    # 2. The Grand Execution
    print(">> Step 2: The Grand Execution")

    for lang in bindings:
        print(f">> Processing {lang}...")

        # Setup (to ensure clean build)
        # We run setup to install deps/configure
        setup_res = run_command(f"{STRLING_CLI} setup {lang}")
        if setup_res is None or setup_res.returncode != 0:
            print(f"!! Setup failed for {lang}")
            if setup_res:
                print(f"STDOUT: {setup_res.stdout}")
                print(f"STDERR: {setup_res.stderr}")
            results.append(
                {
                    "binding": lang,
                    "build": "❌ Fail (Setup)",
                    "tests": 0,
                    "skips": "N/A",
                    "warnings": "N/A",
                    "dup_names": "N/A",
                    "ranges": "N/A",
                    "verdict": "🔴 FAIL",
                }
            )
            continue

        # Build (if applicable)
        # Check if 'build' command exists in toolchain for this language
        # We can't easily check the json here without reloading or passing it down.
        # But we have 'bindings' dict.
        binding_def = bindings.get(lang, {})
        if "build" in binding_def and binding_def["build"]:
            print(f">> Building {lang}...")
            build_res = run_command(f"{STRLING_CLI} build {lang}")
            if build_res is None or build_res.returncode != 0:
                print(f"!! Build failed for {lang}")
                results.append(
                    {
                        "binding": lang,
                        "build": "❌ Fail (Build)",
                        "tests": 0,
                        "skips": "N/A",
                        "warnings": "N/A",
                        "dup_names": "N/A",
                        "ranges": "N/A",
                        "verdict": "🔴 FAIL",
                    }
                )
                continue

        # Test
        test_res = run_command(f"{STRLING_CLI} test {lang}")
        # duration = time.time() - start_time

        if test_res is None:
            print(f"!! Test execution failed for {lang}")
            results.append(
                {
                    "binding": lang,
                    "build": "✅",
                    "tests": 0,
                    "skips": "N/A",
                    "warnings": "N/A",
                    "dup_names": "N/A",
                    "ranges": "N/A",
                    "verdict": "🔴 FAIL (Exec)",
                }
            )
            continue

        # Analyze
        skips, warn_count = analyze_output(test_res.stdout, test_res.stderr)

        # Semantic Checks
        dup_names_verified = check_semantic(
            test_res.stdout, test_res.stderr, "DupNames"
        )
        ranges_verified = check_semantic(test_res.stdout, test_res.stderr, "Ranges")
        essential5_verified = check_semantic(
            test_res.stdout, test_res.stderr, "Essential5"
        )

        # Verdict
        verdict = "🟢 CERTIFIED"
        if test_res.returncode != 0:
            verdict = "🔴 FAIL (Exit Code)"
        elif skips > 0:
            verdict = "🔴 FAIL (Skips)"
        elif warn_count > 0:
            verdict = "🔴 FAIL (Warnings)"
        elif not dup_names_verified or not ranges_verified or not essential5_verified:
            verdict = "🔴 FAIL (Semantic)"

        # Count tests
        test_count = "Unknown"
        # Regex patterns for different runners
        # 1. Generic "X tests passed"
        # 2. Pytest: "==== 714 passed in 0.45s ===="
        # 3. Jest: "Tests:       20 passed, 20 total"
        # 4. Cargo (Rust): "test result: ok. 578 passed"
        # 5. Maven (Java): "Tests run: 20, Failures: 0"
        # 6. TAP (Perl): "Files=X, Tests=Y"
        # 7. PHPUnit: "OK (X tests, Y assertions)" or "Tests: X"
        # 8. R testthat: "[ FAIL 0 | WARN 0 | SKIP 0 | PASS X ]"
        # 9. Dart: "+X: All tests passed!" or "X/Y tests passed"
        # 10. .NET (dotnet test): "Passed:  X"
        # 11. CTest: "100% tests passed"
        # 12. Go: count "ok" lines
        combined = test_res.stdout + "\n" + test_res.stderr

        for pat in TEST_PATTERNS:
            match = re.search(pat, combined)
            if match:
                test_count = match.group(1)
                break

        # Special handling for CTest: "100% tests passed, 0 tests failed out of X"
        if test_count == "Unknown":
            ctest_match = re.search(
                r"\d+% tests passed, \d+ tests failed out of (\d+)", combined
            )
            if ctest_match:
                test_count = ctest_match.group(1)

        # Special handling for XCTest (Swift): "Executed N tests"
        # We take the maximum value found to capture the "All tests" aggregate
        xctest_matches = re.findall(r"Executed (\d+) tests", combined)
        if xctest_matches:
            counts = [int(c) for c in xctest_matches]
            max_count = max(counts)
            if test_count == "Unknown" or (
                test_count.isdigit() and int(test_count) < max_count
            ):
                test_count = str(max_count)

        # Special handling for Go: count "ok" lines
        if test_count == "Unknown":
            go_ok_count = len(re.findall(r"^ok\s+", combined, re.MULTILINE))
            if go_ok_count > 0:
                test_count = f"{go_ok_count} pkgs"

        # Fallback: Count "=== RUN" lines
        if test_count == "Unknown":
            run_count = len(re.findall(r"=== RUN", combined))
            if run_count > 0:
                test_count = run_count

        results.append(
            {
                "binding": lang,
                "build": "✅",
                "tests": test_count,
                "skips": "✅" if skips == 0 else f"❌ ({skips} Skip)",
                "warnings": "✅" if warn_count == 0 else f"❌ ({warn_count} Warn)",
                "dup_names": "✅ Verified" if dup_names_verified else "❓ Missing",
                "ranges": "✅ Verified" if ranges_verified else "❓ Missing",
                "essential5": "✅ Verified" if essential5_verified else "❓ Missing",
                "verdict": verdict,
            }
        )

    # 3. Report Generation
    print(">> Step 3: Generating Report")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    with open(REPORT_PATH, "w") as f:
        f.write("# Final Audit Report\n\n")
        f.write(
            "| Binding | Build | Tests | Zero Skips | Zero Warnings | Semantic: DupNames | Semantic: Ranges | Stdlib: Essential5 | Verdict |\n"
        )
        f.write(
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        )

        for r in results:
            f.write(
                f"| {r['binding']} | {r['build']} | {r['tests']} | {r['skips']} | {r['warnings']} | {r['dup_names']} | {r['ranges']} | {r.get('essential5', 'N/A')} | {r['verdict']} |\n"
            )

    print(f">> Audit Complete. Report saved to {REPORT_PATH}")

    # Check for failures
    certification_passed = True
    for r in results:
        if r["verdict"] != "🟢 CERTIFIED":
            certification_passed = False
            break

    if not certification_passed:
        print_instructional_failure()
        sys.exit(1)


if __name__ == "__main__":
    main()
