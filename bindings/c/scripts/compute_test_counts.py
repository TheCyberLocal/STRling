#!/usr/bin/env python3
"""
Compute test counts for C bindings by running test executables with XML output.
Maps test files like 'anchors_test.c' to 'anchors.test' in the output.
"""
import xml.etree.ElementTree as ET
import subprocess
import glob
import os
import re
import tempfile
from collections import defaultdict

# Find the C bindings directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
out = os.path.join(base_dir, 'c-test-counts.md')

# Find all test executables (excluding temporary phase/demo tests)
unit_tests = glob.glob(os.path.join(base_dir, 'tests/unit/*_test'))
e2e_tests = glob.glob(os.path.join(base_dir, 'tests/e2e/*_test'))
all_tests = sorted(unit_tests + e2e_tests)

print(f"Found {len(all_tests)} test executables")

# Collect test counts by running each test with XML output
test_counts = {}

for test_path in all_tests:
    if not os.path.exists(test_path):
        print(f"Warning: Test executable not found: {test_path}")
        continue
    
    # Extract test name from path: tests/unit/anchors_test -> anchors_test
    test_name = os.path.basename(test_path)
    
    # Skip if this is a temporary/scaffolding test
    if any(skip in test_name for skip in ['simple', 'phase3', 'phase4', 'demo', 'quantifier_alternation']):
        print(f"Skipping scaffolding test: {test_name}")
        continue
    
    try:
        # Run test with XML output and capture stdout
        env = os.environ.copy()
        env['CMOCKA_MESSAGE_OUTPUT'] = 'xml'
        
        result = subprocess.run(
            [test_path],
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        
        # Parse XML output from stdout
        if result.stdout.strip():
            try:
                root = ET.fromstring(result.stdout)
                # Count testcase elements in the XML
                test_count = len(root.findall('.//testcase'))
                
                # Map filename: anchors_test -> anchors.test
                display_name = test_name.replace('_test', '.test')
                test_counts[display_name] = test_count
                print(f"  {display_name}: {test_count} tests")
                
            except ET.ParseError as e:
                print(f"Warning: Failed to parse XML from {test_name}: {e}")
                test_counts[test_name.replace('_test', '.test')] = 0
        else:
            print(f"Warning: No XML output from {test_name}")
            test_counts[test_name.replace('_test', '.test')] = 0
            
    except subprocess.TimeoutExpired:
        print(f"Warning: Test {test_name} timed out")
        test_counts[test_name.replace('_test', '.test')] = 0
    except Exception as e:
        print(f"Warning: Failed to run {test_name}: {e}")
        test_counts[test_name.replace('_test', '.test')] = 0

# Calculate total
total = sum(test_counts.values())

# Generate markdown report
lines = [
    '# C Test Counts',
    '',
    f'- **Total tests (sum):**: {total}',
    '## Per-file counts',
    ''
]

# Sort and add each file's count
for test_file in sorted(test_counts.keys()):
    lines.append(f'- `{test_file}`: {test_counts[test_file]} tests')

# Write output
with open(out, 'w', encoding='utf8') as f:
    f.write('\n'.join(lines))

print(f'\nWrote {out}')
print(f'Total tests: {total}')