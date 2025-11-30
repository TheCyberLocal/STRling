#!/usr/bin/env python3
import json
import sys

REPORT_PATH = "FINAL_AUDIT_REPORT.md"

if len(sys.argv) < 2:
    print("Usage: audit_omega_simulate.py <data.json>")
    sys.exit(2)

with open(sys.argv[1], 'r') as f:
    results = json.load(f)

# Keep ordering stable
bindings_order = [r['binding'] for r in results]

with open(REPORT_PATH, 'w') as f:
    f.write('# Final Audit Report\n\n')
    f.write('| Binding | Build | Tests | Zero Skips | Zero Warnings | Semantic: DupNames | Semantic: Ranges | Verdict |\n')
    f.write('| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n')

    for r in results:
        f.write(f"| {r['binding']} | {r.get('build', '❌')} | {r.get('tests', 'Unknown')} | {r.get('skips', 'N/A')} | {r.get('warnings', 'N/A')} | {r.get('dup_names', '❓ Missing')} | {r.get('ranges', '❓ Missing')} | {r.get('verdict', '🔴 FAIL')} |\n")

print(f"Wrote {REPORT_PATH} with {len(results)} entries")
