#!/usr/bin/env python3
"""
IEH Audit Script - Test STRling Parse Errors

This script takes an invalid STRling pattern as input and prints
the fully formatted STRlingParseError with hints.

Usage:
    python audit_hints.py "invalid_pattern"
"""

import sys
import os

# Add parent directory to path to import STRling module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bindings', 'python', 'src'))

from STRling.core.parser import parse
from STRling.core.errors import STRlingParseError


def test_pattern(pattern: str) -> None:
    """
    Test a pattern and print the formatted error if it fails.
    
    Parameters
    ----------
    pattern : str
        The STRling pattern to test
    """
    print(f"Testing pattern: {repr(pattern)}")
    print("-" * 60)
    
    try:
        flags, ast = parse(pattern)
        print("✓ Pattern parsed successfully (no error)")
        print(f"  Flags: {flags}")
        print(f"  AST: {ast}")
    except STRlingParseError as e:
        print(str(e))
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
    
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_hints.py <pattern>")
        print("Example: python audit_hints.py '(abc'")
        sys.exit(1)
    
    pattern = sys.argv[1]
    test_pattern(pattern)
