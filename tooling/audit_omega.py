import json
import subprocess
import re
from typing import Optional, Tuple, List, Dict, Any

# Configuration
TOOLCHAIN_PATH = "toolchain.json"
REPORT_PATH = "FINAL_AUDIT_REPORT.md"
STRLING_CLI = "./strling"

# Regex patterns
SKIP_PATTERNS = [
    r"skipped",
    r"SKIPPED",
    r"ignored",
    r"pending",
    r"TODO",
    r"\[-\]",  # Some runners use [-] for skipped
]

# Warning patterns for test/build output
# Exclude common false positives like locale warnings
WARNING_PATTERNS = [
    r"warning:",
    r"WARNING:",
    r"Warning:",
]

# Patterns that should NOT be counted as warnings (false positives)
WARNING_EXCLUDE_PATTERNS = [
    r"locale",
    r"Setting locale failed",
    r"LANGUAGE",
    r"LC_ALL",
]

# Semantic checks (filenames/patterns that must appear in output)
# Multiple patterns per check for different test runners
SEMANTIC_CHECKS = {
    "DupNames": [
        "test_semantic_duplicate_capture_group",
        "semantic_duplicates",
        "duplicate_capture_group",
        "dup_names",
        "DupNames",
    ],
    "Ranges": [
        "test_semantic_ranges",
        "semantic_ranges",
        "Ranges",
    ],
}


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

    for pattern in SKIP_PATTERNS:
        skips += len(re.findall(pattern, combined))

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

        # Verdict
        verdict = "🟢 CERTIFIED"
        if test_res.returncode != 0:
            verdict = "🔴 FAIL (Exit Code)"
        elif skips > 0:
            verdict = "🔴 FAIL (Skips)"
        elif warn_count > 0:
            verdict = "🔴 FAIL (Warnings)"
        elif not dup_names_verified or not ranges_verified:
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
        patterns = [
            r"(\d+) tests passed",
            r"====\s+(\d+)\s+passed",
            r"Tests:\s+(\d+)\s+passed",
            r"test result: ok\. (\d+) passed",
            r"Tests run:\s+(\d+), Failures: 0",
            r"Files=\d+, Tests=(\d+)",
            r"OK \((\d+) tests?",
            r"Tests: (\d+)",
            r"\[ FAIL 0 \| WARN 0 \| SKIP 0 \| PASS (\d+) \]",
            r"\+(\d+): All tests passed",
            r"(\d+)/\d+ tests passed",
            r"Passed:\s+(\d+)",
            r"(\d+)% tests passed, \d+ tests failed out of (\d+)",
        ]

        for pat in patterns:
            match = re.search(pat, combined)
            if match:
                test_count = match.group(1)
                break

        # Special handling for Go: count "ok" lines
        if test_count == "Unknown":
            go_ok_count = len(re.findall(r"^ok\s+", combined, re.MULTILINE))
            if go_ok_count > 0:
                test_count = f"{go_ok_count} pkgs"

        results.append(
            {
                "binding": lang,
                "build": "✅",
                "tests": test_count,
                "skips": "✅" if skips == 0 else f"❌ ({skips} Skip)",
                "warnings": "✅" if warn_count == 0 else f"❌ ({warn_count} Warn)",
                "dup_names": "✅ Verified" if dup_names_verified else "❓ Missing",
                "ranges": "✅ Verified" if ranges_verified else "❓ Missing",
                "verdict": verdict,
            }
        )

    # 3. Report Generation
    print(">> Step 3: Generating Report")

    with open(REPORT_PATH, "w") as f:
        f.write("# Final Audit Report\n\n")
        f.write(
            "| Binding | Build | Tests | Zero Skips | Zero Warnings | Semantic: DupNames | Semantic: Ranges | Verdict |\n"
        )
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")

        for r in results:
            f.write(
                f"| {r['binding']} | {r['build']} | {r['tests']} | {r['skips']} | {r['warnings']} | {r['dup_names']} | {r['ranges']} | {r['verdict']} |\n"
            )

    print(f">> Audit Complete. Report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
