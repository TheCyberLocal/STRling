#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import glob, os, re
from collections import defaultdict

# Search for likely XML test report files under the C bindings directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
cands = []
# common patterns: surefire-style TEST-*.xml and CTestTestfile.xml produced by CTest
cands += glob.glob(os.path.join(base_dir, '**', 'TEST-*.xml'), recursive=True)
cands += glob.glob(os.path.join(base_dir, '**', 'CTestTestfile.xml'), recursive=True)
# fallback: any XML directly under a test-reports or build/test-reports directories
cands += glob.glob(os.path.join(base_dir, '**', 'test-reports', '*.xml'), recursive=True)
cands = sorted(set(cands))

out = os.path.join(base_dir, 'c-test-counts.md')

lines = ['# C Test Counts', '', '## Per-file counts', '']

raw = []
for f in cands:
    tests = 0
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        # prefer explicit attribute, else count <testcase> elements
        tests = int(root.attrib.get('tests') or root.attrib.get('test') or 0)
        if not tests:
            tests = len(root.findall('.//testcase'))
    except Exception:
        # best-effort fallback: zero if parsing fails
        tests = 0
    name = os.path.basename(f)
    # For CTestTestfile.xml use the parent directory as the test "name"
    if name == 'CTestTestfile.xml':
        name = os.path.basename(os.path.dirname(f))
    else:
        name = name.replace('TEST-', '').replace('.xml', '')
    raw.append((name, tests))

# Optional explicit grouping to mirror Java script e2e keys if C reports use similar names.
groups = {
    'e2e_combinatorial': 'e2e_combinatorial.test',
    'pcre2_emitter': 'pcre2_emitter.test',
    'cli_smoke': 'cli_smoke.test',
}

agg = {v: 0 for v in groups.values()}
others = []

for name, tests in raw:
    matched = False
    for prefix, outname in groups.items():
        if name == prefix or name.startswith(prefix + '_') or name.startswith(prefix + '-'):
            agg[outname] += tests
            matched = True
            break
    if not matched:
        others.append((name, tests))

def _camel_to_snake(s: str) -> str:
    # Insert underscores before capital letters (except at start) and normalize separators
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', s).replace('-', '_')
    s = re.sub(r'[^0-9a-zA-Z_]', '_', s)
    return s.lower()

file_agg = defaultdict(int)
for name, tests in others:
    # strip common suffixes and extension-like parts
    simple = name.split('.')[-1]
    simple = simple.split('$')[0]
    for suf in ('Test', 'Tests', 'TestCase', 'IT'):
        if simple.endswith(suf) and len(simple) > len(suf):
            simple = simple[:-len(suf)]
            break
    if not simple:
        key = name
    else:
        key = _camel_to_snake(simple) + '.test'
    file_agg[key] += tests

from collections import defaultdict as _defaultdict
combined = _defaultdict(int)
for k, v in agg.items():
    combined[k] += v
for k, v in file_agg.items():
    combined[k] += v

total = sum(combined.values())
lines.insert(2, f"- **Total tests (sum):**: {total}")

for k in sorted(combined.keys()):
    lines.append(f"- `{k}`: {combined[k]} tests")

open(out, 'w', encoding='utf8').write('\n'.join(lines))
print('Wrote', out)