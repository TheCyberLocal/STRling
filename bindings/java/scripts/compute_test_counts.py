#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import glob, os
import re
from collections import defaultdict

# Directory containing surefire XML reports
indir = os.path.join(os.path.dirname(__file__), '..', 'target', 'surefire-reports')
indir = os.path.abspath(indir)
out = os.path.join(os.path.dirname(__file__), '..', 'java-test-counts.md')
files = sorted(glob.glob(os.path.join(indir, 'TEST-*.xml')))

lines = ['# Java Test Counts (surefire)', '', '## Per-file counts', '']

# Collect raw counts per surefire file
raw = []
for f in files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        tests = int(root.attrib.get('tests') or root.attrib.get('test') or 0)
    except Exception:
        tests = 0
    name = os.path.basename(f).replace('TEST-', '').replace('.xml', '')
    raw.append((name, tests))

# Map/aggregate certain Java test class prefixes into JS-style e2e filenames
# This ensures the Java computed counts use the same three e2e keys as the
# JavaScript `compute_test_counts.py` output: `e2e_combinatorial.test`,
# `pcre2_emitter.test` and `cli_smoke.test`.
groups = {
    'com.strling.tests.e2e.E2ECombinatorialTest': 'e2e_combinatorial.test',
    'com.strling.tests.e2e.PCRE2EmitterTest': 'pcre2_emitter.test',
    'com.strling.tests.e2e.CliSmokeTest': 'cli_smoke.test',
}

# Initialize aggregation dict and a list for uncategorized entries
agg = {v: 0 for v in groups.values()}
others = []

for name, tests in raw:
    matched = False
    for prefix, outname in groups.items():
        # Match prefix or nested inner classes that start with the prefix
        if name == prefix or name.startswith(prefix + '$'):
            agg[outname] += tests
            matched = True
            break
    if not matched:
        others.append((name, tests))

# Write grouped entries first (so e2e summaries mirror JS output)
for k in ('e2e_combinatorial.test', 'pcre2_emitter.test', 'cli_smoke.test'):
    lines.append(f"- `{k}`: {agg.get(k, 0)} tests")

# Aggregate remaining Java class-based names into file-like keys so the
# Java output mirrors the JS output's per-file grouping. We take the
# simple class name, strip common test suffixes, convert CamelCase to
# snake_case and append `.test`.
def _camel_to_snake(s: str) -> str:
    # Insert underscores before capital letters (except at start)
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

file_agg = defaultdict(int)
for name, tests in others:
    simple = name.split('.')[-1]
    # Handle nested inner classes like Outer$Inner
    simple = simple.split('$')[0]
    # Strip common test suffixes
    for suf in ('Test', 'Tests', 'TestCase', 'IT'):
        if simple.endswith(suf) and len(simple) > len(suf):
            simple = simple[:-len(suf)]
            break
    if not simple:
        key = name
    else:
        key = _camel_to_snake(simple) + '.test'
    file_agg[key] += tests

# Write aggregated per-file counts sorted for stable output
for k in sorted(file_agg.keys()):
    lines.append(f"- `{k}`: {file_agg[k]} tests")

# totals
try:
    total = sum(int(l.split(': ')[1].split()[0]) for l in lines if l.startswith('- `'))
except Exception:
    total = 0
lines.insert(2, f"- **Total tests (sum):**: {total}")

open(out, 'w', encoding='utf8').write('\n'.join(lines))
print('Wrote', out)
