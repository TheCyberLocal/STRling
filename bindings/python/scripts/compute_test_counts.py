#!/usr/bin/env python3
"""
Produce a per-file test counts markdown for the Python binding.

This script runs `pytest --collect-only -q` in the binding root to enumerate
test nodeids, groups known e2e tests into the same keys used by the Java and
JS outputs, and writes `../python-test-counts.md`.
"""
import os
import sys
import subprocess
from collections import defaultdict


script_dir = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(script_dir, '..'))
out = os.path.join(root, 'python-test-counts.md')

lines = ['# Python Test Counts (pytest)', '', '## Per-file counts', '']

print('Running pytest to collect test nodeids...', file=sys.stderr)
try:
    proc = subprocess.run([
        'pytest', '--collect-only', '-q'
    ], cwd=root, capture_output=True, text=True)
except FileNotFoundError:
    lines.append('Failed to invoke `pytest`. Ensure pytest is installed in this environment.')
    open(out, 'w', encoding='utf8').write('\n'.join(lines))
    print('Wrote', out)
    sys.exit(1)
except Exception as e:
    lines.append(f'Failed to run pytest: {e}')
    open(out, 'w', encoding='utf8').write('\n'.join(lines))
    print('Wrote', out)
    sys.exit(1)

raw = proc.stdout or proc.stderr or ''

# Try to extract nodeids. With -q pytest typically prints one nodeid per line
# like `tests/unit/test_foo.py::test_bar` or `tests/unit/test_foo.py::TestClass::test_bar`.
node_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

counts = defaultdict(int)

# Known e2e test filenames -> canonical keys to match Java/JS scripts
groups = {
    'test_e2e_combinatorial.py': 'e2e_combinatorial.test',
    'test_pcre2_emitter.py': 'pcre2_emitter.test',
    'test_cli_smoke.py': 'cli_smoke.test',
    # Ensure the schema validation tests are represented explicitly
    'test_schema_validation.py': 'schema_validation.test',
}

for ln in node_lines:
    # skip summary lines like 'collected 42 items' or other non-nodeid content
    if '::' in ln:
        node = ln
    elif ln.endswith('.py') and os.path.exists(os.path.join(root, ln)):
        node = ln
    else:
        # Not a nodeid; skip
        continue

    # Extract the file path before the first '::'
    file_part = node.split('::', 1)[0]
    # Some runners print absolute paths; normalize to basename
    base = os.path.basename(file_part)

    # Map known e2e filenames to grouped keys
    if base in groups:
        key = groups[base]
    else:
        # Derive a file-like key: remove leading 'test_' and trailing '.py'
        name = base
        if name.endswith('.py'):
            name = name[:-3]
        if name.startswith('test_') and len(name) > 5:
            name = name[5:]
        # Ensure we have a non-empty key
        if not name:
            key = base
        else:
            key = f"{name}.test"

    counts[key] += 1

# Write all per-file counts sorted alphabetically for stable output
for k in sorted(counts.keys()):
    lines.append(f"- `{k}`: {counts[k]} tests")

# totals (sum directly from counts)
total = sum(counts.values())
lines.insert(2, f"- **Total tests (sum):**: {total}")

open(out, 'w', encoding='utf8').write('\n'.join(lines))
print('Wrote', out)
