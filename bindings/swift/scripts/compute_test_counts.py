#!/usr/bin/env python3
"""
Produce a per-file test counts markdown for the Swift binding.

This script walks the Tests/ directory to find all .swift test files,
counts test functions using the standard Swift XCTest convention (func test...()),
maps Swift file names to the standardized .test format, and writes
`../swift-test-counts.md`.
"""
import os
import re
from collections import defaultdict

script_dir = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(script_dir, '..'))
tests_dir = os.path.join(root, 'Tests')
out = os.path.join(root, 'swift-test-counts.md')

# Filename mapping from PascalCase Swift files to standardized .test format
# Note: Pcre2EmitterTests doesn't exist; the actual file is E2EPCRE2EmitterTests
filename_mapping = {
    'AnchorsTests.swift': 'anchors.test',
    'CharClassesTests.swift': 'char_classes.test',
    'CliSmokeTests.swift': 'cli_smoke.test',
    'E2ECombinatorialTests.swift': 'e2e_combinatorial.test',
    'E2EPCRE2EmitterTests.swift': 'pcre2_emitter.test',
    'EmitterEdgesTests.swift': 'emitter_edges.test',
    'ErrorFormattingTests.swift': 'error_formatting.test',
    'ErrorsTests.swift': 'errors.test',
    'FlagsAndFreeSpacingTests.swift': 'flags_and_free_spacing.test',
    'GroupsBackrefsLookaroundsTests.swift': 'groups_backrefs_lookarounds.test',
    'IEHAuditGapsTests.swift': 'ieh_audit_gaps.test',
    'IRCompilerTests.swift': 'ir_compiler.test',
    'LiteralsAndEscapesTests.swift': 'literals_and_escapes.test',
    'ParserErrorsTests.swift': 'parser_errors.test',
    'QuantifiersTests.swift': 'quantifiers.test',
    'SchemaValidationTests.swift': 'schema_validation.test',
    'SimplyAPITests.swift': 'simply_api.test',
}

# Regular expression to find Swift test functions
# Matches: func testSomething()
test_function_pattern = re.compile(r"^\s*func\s+(test\w+)\s*\(")

counts = defaultdict(int)

# Walk the Tests directory to find all .swift files
for dirpath, dirnames, filenames in os.walk(tests_dir):
    for filename in filenames:
        if not filename.endswith('.swift'):
            continue
        
        # Check if this file is in our mapping (only count spec-related tests)
        if filename not in filename_mapping:
            continue
        
        filepath = os.path.join(dirpath, filename)
        standardized_name = filename_mapping[filename]
        
        # Count test functions in this file
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if test_function_pattern.match(line):
                    counts[standardized_name] += 1

# Build the markdown output
lines = ['# Swift Test Counts', '']

# Calculate total
total = sum(counts.values())
lines.append(f"- **Total tests (sum):**: {total}")
lines.append('')
lines.append('## Per-file counts')
lines.append('')

# Sort by standardized name alphabetically
for name in sorted(counts.keys()):
    lines.append(f"- `{name}`: {counts[name]} tests")

# Write output
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'Wrote {out}')
print(f'Total tests: {total}')
