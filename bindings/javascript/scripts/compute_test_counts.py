#!/usr/bin/env python3
"""
Parse a Jest JSON results file and produce a per-file test counts markdown,
mirroring the Java `compute_test_counts.py` behavior.

Writes output to `../js-test-counts.md`.
"""
import json
import os
import sys
import subprocess

script_dir = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(script_dir, '..'))
out = os.path.join(root, 'js-test-counts.md')

lines = ['# JS Test Counts (jest)', '', '## Per-file counts', '']

# If the jest JSON results file doesn't exist, try to run the test script
# to produce it automatically (so users don't have to generate it manually).
# Always run the test runner and parse JSON from its output so counts are
# always up-to-date. We avoid reading a previously-written JSON file.
print('Running Jest to collect latest test results...', file=sys.stderr)
try:
    # Prefer npx to invoke local jest binary; fall back to npm test if npx isn't available.
    proc = subprocess.run([
        'npx', 'jest', '--json', '--colors=false'
    ], cwd=root, capture_output=True, text=True)
except FileNotFoundError:
    # npx not available; try npm test which forwards args to jest
    try:
        proc = subprocess.run([
            'npm', 'test', '--', '--json', '--colors=false'
        ], cwd=root, capture_output=True, text=True)
    except Exception as e:
        print('Failed to invoke test runner:', e, file=sys.stderr)
        lines.append('Failed to run tests to produce JSON results. Ensure dependencies are installed and run `npm test -- --json` manually.')
        open(out, 'w', encoding='utf8').write('\n'.join(lines))
        print('Wrote', out)
        sys.exit(1)
except Exception as e:
    print('Failed to invoke npx/jest:', e, file=sys.stderr)
    lines.append('Failed to run tests to produce JSON results. Ensure dependencies are installed and run `npm test -- --json` manually.')
    open(out, 'w', encoding='utf8').write('\n'.join(lines))
    print('Wrote', out)
    sys.exit(1)

# Capture stdout (preferred) or stderr if stdout is empty. npm may write to stderr.
raw = proc.stdout or proc.stderr or ''

# Try to find JSON object within the raw output in case there are logs.
start = raw.find('{')
end = raw.rfind('}')
if start == -1 or end == -1 or end <= start:
    print('Could not find JSON output from jest. Full output below for debugging:', file=sys.stderr)
    print(raw, file=sys.stderr)
    lines.append('Test run did not produce JSON output. Run `npm test -- --json` manually to diagnose.')
    open(out, 'w', encoding='utf8').write('\n'.join(lines))
    print('Wrote', out)
    sys.exit(1)

json_text = raw[start:end+1]
try:
    data = json.loads(json_text)
except Exception as e:
    print('Failed to parse JSON output from jest:', e, file=sys.stderr)
    print('Raw JSON snippet:', file=sys.stderr)
    print(json_text, file=sys.stderr)
    lines.append('Failed to parse JSON output from test runner. Run tests manually to inspect output.')
    open(out, 'w', encoding='utf8').write('\n'.join(lines))
    print('Wrote', out)
    sys.exit(1)

test_results = data.get('testResults') or []

# Collect per-file counts into a list, then sort alphabetically for deterministic output
entries = []
for tr in test_results:
    # test file name
    name = tr.get('name') or tr.get('testFilePath') or ''
    name = os.path.basename(name)
    # try to strip common test extensions to match Java script naming style
    for ext in ('.test.js', '.spec.js', '.test.mjs', '.spec.mjs', '.mjs', '.js', '.ts', '.tsx'):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break

    # determine counts: prefer explicit totals, else sum categories, else fallback to assertions
    count = 0 # Default to 0

    # Attempt 1: Try to get count from explicit total first
    if 'numTotalTests' in tr:
        try:
            count = int(tr.get('numTotalTests', 0))
        except Exception:
            count = 0 # Reset on error

    # Attempt 2: If total is 0 (or missing), try to count assertionResults.
    # This is often the most reliable count for individual tests.
    if count == 0:
        try:
            ar = tr.get('assertionResults') or []
            count = len(ar)
        except Exception:
            count = 0 # Reset on error

    # Attempt 3: If assertionResults is also 0, try summing the keys as a last resort
    if count == 0:
        try:
            keys = ('numPassingTests', 'numFailingTests', 'numPendingTests', 'numTodoTests')
            count = sum(int(tr.get(k, 0)) for k in keys)
        except Exception:
            count = 0 # Give up, count is 0

    entries.append((name, count))

# Sort entries by filename (case-insensitive)
entries.sort(key=lambda x: x[0].lower())

# Append sorted per-file lines
for name, count in entries:
    lines.append(f"- `{name}`: {count} tests")

# totals (compute from entries for reliability)
try:
    total = sum(count for _, count in entries)
except Exception:
    total = 0
lines.insert(2, f"- **Total tests (sum):**: {total}")

open(out, 'w', encoding='utf8').write('\n'.join(lines))
print('Wrote', out)
