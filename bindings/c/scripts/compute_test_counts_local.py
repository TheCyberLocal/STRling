#!/usr/bin/env python3
"""
Local helper to compute C test counts by scanning .c test sources.
This mirrors the intended behavior for `compute_test_counts.py` but works from
source files (counts TestCase entries) so it doesn't require running built
executables.
"""
import os
import glob
import re

script_dir = os.path.dirname(__file__)
base_dir = os.path.abspath(os.path.join(script_dir, '..'))
out = os.path.join(base_dir, 'c-test-counts.md')

unit_tests = glob.glob(os.path.join(base_dir, 'tests', 'unit', '*_test.c'))
e2e_tests = glob.glob(os.path.join(base_dir, 'tests', 'e2e', '*_test.c'))
all_tests = sorted(unit_tests + e2e_tests)

print(f"Found {len(all_tests)} C test source files")

id_entry_re = re.compile(r'^\s*\{\s*"[^"]+"\s*,', re.MULTILINE)
header_count_re = re.compile(r'\((\d+)\s+Tests?\)')

test_counts = {}
for test_path in all_tests:
    filename = os.path.basename(test_path)
    # Skip obvious scaffolding/test-harness files if any
    if any(skip in filename for skip in ['simple', 'phase3', 'phase4', 'demo', 'quantifier_alternation']):
        print(f"Skipping scaffolding source: {filename}")
        continue
    try:
        with open(test_path, 'r', encoding='utf8') as fh:
            src = fh.read()
        matches = id_entry_re.findall(src)
        count = len(matches)
        if count == 0:
            m = header_count_re.search(src)
            if m:
                try:
                    count = int(m.group(1))
                except Exception:
                    count = 0
        display_name = filename.replace('_test.c', '.test').replace('.c', '.test')
        test_counts[display_name] = count
        print(f"  {display_name}: {count} tests")
    except Exception as e:
        print(f"Warning: Failed to inspect {filename}: {e}")
        test_counts[filename.replace('_test.c', '.test')] = 0

# Generate markdown
lines = ['# C Test Counts', '', f'- **Total tests (sum):**: {sum(test_counts.values())}', '## Per-file counts', '']
for test_file in sorted(test_counts.keys()):
    lines.append(f'- `{test_file}`: {test_counts[test_file]} tests')

with open(out, 'w', encoding='utf8') as f:
    f.write('\n'.join(lines))

print('Wrote', out)
