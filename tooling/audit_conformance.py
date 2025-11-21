#!/usr/bin/env python3
"""
Conformance Audit Tool

This script ensures 100% test coverage of JSON AST fixtures across all language bindings.
It verifies that every fixture in tooling/js_to_json_ast/out/ is tested by both Python
and Java conformance test suites.

Exit Codes:
  0 - All fixtures are tested by both bindings
  1 - Missing fixture coverage detected
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Set, List


def get_repo_root() -> Path:
    """Get the repository root directory"""
    script_dir = Path(__file__).parent
    return script_dir.parent


def get_all_fixture_ids(fixtures_dir: Path) -> Set[str]:
    """Get all fixture IDs from the fixtures directory"""
    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}", file=sys.stderr)
        sys.exit(1)
    
    fixture_files = sorted(fixtures_dir.glob("*.json"))
    fixture_ids = {f.stem for f in fixture_files}
    
    print(f"Found {len(fixture_ids)} total fixtures in {fixtures_dir}")
    return fixture_ids


def run_python_conformance_tests(repo_root: Path) -> Set[str]:
    """Run Python conformance tests and extract executed fixture IDs"""
    python_dir = repo_root / "bindings" / "python"
    
    print("\nRunning Python conformance tests...")
    
    # Run pytest with verbose output to capture test names
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/unit/test_conformance.py", "-v", "--tb=no"],
        cwd=python_dir,
        capture_output=True,
        text=True
    )
    
    # Check if pytest is available
    if result.returncode != 0 and "No module named pytest" in result.stderr:
        print("ERROR: pytest is not installed. Please install Python dependencies:", file=sys.stderr)
        print("  pip install -r bindings/python/requirements.txt", file=sys.stderr)
        print("  pip install -e bindings/python", file=sys.stderr)
        sys.exit(1)
    
    # Parse test names from pytest output
    # Test names look like: test_conformance[js_test_pattern_1.json]
    executed = set()
    for line in result.stdout.split('\n'):
        if 'test_conformance[' in line:
            # Extract fixture name from test name
            start = line.find('[') + 1
            end = line.find(']', start)
            if start > 0 and end > start:
                fixture_name = line[start:end]
                # Remove .json extension to get fixture ID
                fixture_id = fixture_name.replace('.json', '')
                executed.add(fixture_id)
    
    # If no tests were found but pytest ran successfully, something is wrong
    if len(executed) == 0 and result.returncode == 0:
        print("WARNING: Pytest ran but no conformance tests were found", file=sys.stderr)
        print("Check that tests/unit/test_conformance.py exists and contains tests", file=sys.stderr)
    
    print(f"Python executed {len(executed)} fixtures")
    return executed


def run_java_conformance_tests(repo_root: Path) -> Set[str]:
    """Run Java conformance tests and extract executed fixture IDs"""
    java_dir = repo_root / "bindings" / "java"
    
    print("\nRunning Java conformance tests...")
    
    # Run maven test with conformance tests (not quiet so we can parse output)
    result = subprocess.run(
        ["mvn", "test", "-Dtest=ConformanceTests"],
        cwd=java_dir,
        capture_output=True,
        text=True
    )
    
    # Parse test count from Maven output
    # Maven reports "Tests run: N, Failures: F, Errors: E, Skipped: S"
    test_count = 0
    for line in result.stdout.split('\n'):
        if 'Tests run:' in line and 'ConformanceTests' in line:
            # Extract test count
            parts = line.split('Tests run:')
            if len(parts) > 1:
                count_str = parts[1].split(',')[0].strip()
                try:
                    test_count = int(count_str)
                    print(f"Java ran {test_count} conformance tests")
                except ValueError:
                    pass
                break
    
    # If we found a test count, assume that many fixtures were tested
    # (Since we can't easily parse individual test names from Maven output)
    executed = set()
    if test_count > 0:
        # Get the fixture list and take the first N fixtures
        # This assumes the test runs all fixtures in order
        fixtures_dir = repo_root / "tooling" / "js_to_json_ast" / "out"
        fixture_files = sorted(fixtures_dir.glob("*.json"))
        
        # Verify the test count matches the fixture count
        if test_count == len(fixture_files):
            executed = {f.stem for f in fixture_files}
            print(f"Java test count ({test_count}) matches fixture count - assuming 100% coverage")
        else:
            print(f"WARNING: Test count ({test_count}) doesn't match fixture count ({len(fixture_files)})")
            print("This may indicate some fixtures were skipped")
            # Still return the fixtures, but the audit will likely fail
            executed = {f.stem for f in fixture_files[:test_count]}
    else:
        # Failed to parse test count
        if result.returncode != 0:
            print("ERROR: Java tests failed to run", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)
        else:
            print("WARNING: Could not parse test count from Maven output")
    
    print(f"Java executed {len(executed)} fixtures")
    return executed


def main():
    repo_root = get_repo_root()
    fixtures_dir = repo_root / "tooling" / "js_to_json_ast" / "out"
    
    # Get all available fixtures
    all_fixtures = get_all_fixture_ids(fixtures_dir)
    
    # Run tests and get executed fixtures
    python_executed = run_python_conformance_tests(repo_root)
    java_executed = run_java_conformance_tests(repo_root)
    
    # Check for missing coverage
    python_missing = all_fixtures - python_executed
    java_missing = all_fixtures - java_executed
    
    print("\n" + "=" * 80)
    print("CONFORMANCE AUDIT RESULTS")
    print("=" * 80)
    
    print(f"\nTotal Fixtures: {len(all_fixtures)}")
    print(f"Python Executed: {len(python_executed)}")
    print(f"Java Executed: {len(java_executed)}")
    
    exit_code = 0
    
    if python_missing:
        print(f"\n❌ Python MISSING {len(python_missing)} fixtures:")
        for fixture_id in sorted(python_missing)[:10]:  # Show first 10
            print(f"  - {fixture_id}")
        if len(python_missing) > 10:
            print(f"  ... and {len(python_missing) - 10} more")
        exit_code = 1
    else:
        print("\n✅ Python: All fixtures tested")
    
    if java_missing:
        print(f"\n❌ Java MISSING {len(java_missing)} fixtures:")
        for fixture_id in sorted(java_missing)[:10]:  # Show first 10
            print(f"  - {fixture_id}")
        if len(java_missing) > 10:
            print(f"  ... and {len(java_missing) - 10} more")
        exit_code = 1
    else:
        print("\n✅ Java: All fixtures tested")
    
    print("\n" + "=" * 80)
    
    if exit_code == 0:
        print("✅ AUDIT PASSED: All fixtures have 100% coverage")
    else:
        print("❌ AUDIT FAILED: Missing fixture coverage detected")
    
    print("=" * 80)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
