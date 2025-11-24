#!/usr/bin/env python3
"""
Lints the C++ binding's README.md to ensure that user-facing examples
do NOT contain forbidden raw pointer management tokens.

This is part of the acceptance criteria for Operation Fluent — the simply API
must hide all pointer semantics from the user.

Forbidden tokens:
  - std::unique_ptr
  - std::shared_ptr
  - std::make_shared
  - std::make_unique
  - new (as a keyword, not substring)

Exit code 0 if clean, 1 if violations found.
"""

import re
import sys
from pathlib import Path


def main():
    # Navigate to the C++ binding directory
    script_dir = Path(__file__).parent
    readme_path = script_dir.parent / "README.md"
    
    if not readme_path.exists():
        print(f"ERROR: README.md not found at {readme_path}", file=sys.stderr)
        return 1
    
    content = readme_path.read_text()
    
    # Define forbidden patterns
    forbidden_patterns = [
        r'\bstd::unique_ptr\b',
        r'\bstd::shared_ptr\b',
        r'\bstd::make_shared\b',
        r'\bstd::make_unique\b',
        r'\bnew\s+[\w:]+',  # "new SomeType" or "new std::string" but not "new" as part of a word
    ]
    
    violations = []
    
    # Extract code blocks to check
    in_code_block = False
    code_lines = []
    
    for line_num, line in enumerate(content.splitlines(), start=1):
        # Track code blocks (```cpp ... ``` or ``` ... ```)
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # Only check code blocks
        if in_code_block:
            for pattern in forbidden_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    violations.append({
                        'line': line_num,
                        'pattern': pattern,
                        'text': line.strip(),
                        'match': match.group(0)
                    })
    
    if violations:
        print("❌ VIOLATION: README.md contains forbidden pointer management tokens:", file=sys.stderr)
        print("", file=sys.stderr)
        for v in violations:
            print(f"  Line {v['line']}: Found '{v['match']}'", file=sys.stderr)
            print(f"    Pattern: {v['pattern']}", file=sys.stderr)
            print(f"    Content: {v['text']}", file=sys.stderr)
            print("", file=sys.stderr)
        print("The simply API must hide all raw pointer usage from users.", file=sys.stderr)
        return 1
    
    print("✅ PASS: README.md contains no forbidden pointer tokens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
