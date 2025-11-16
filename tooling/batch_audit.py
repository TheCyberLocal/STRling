#!/usr/bin/env python3
"""
Batch IEH Audit Script - Test Multiple Error Cases

This script tests multiple error cases and generates a comprehensive report.
"""

import sys
import os

# Add parent directory to path to import STRling module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bindings', 'python', 'src'))

from STRling.core.parser import parse
from STRling.core.errors import STRlingParseError


def test_pattern(pattern: str) -> dict:
    """
    Test a pattern and return error details.
    
    Returns
    -------
    dict
        Dictionary with keys: 'pattern', 'error_msg', 'hint', 'formatted'
    """
    try:
        flags, ast = parse(pattern)
        return {
            'pattern': pattern,
            'error_msg': None,
            'hint': None,
            'formatted': 'Pattern parsed successfully (no error)'
        }
    except STRlingParseError as e:
        return {
            'pattern': pattern,
            'error_msg': e.message,
            'hint': e.hint,
            'formatted': str(e)
        }
    except Exception as e:
        return {
            'pattern': pattern,
            'error_msg': f'{type(e).__name__}: {e}',
            'hint': None,
            'formatted': f'Unexpected error: {type(e).__name__}: {e}'
        }


# Comprehensive error test cases
ERROR_CASES = {
    "Groups and Lookarounds": [
        ("(a|b", "Unclosed Group"),
        ("(?<name>a", "Unclosed Named Group"),
        ("(?<1a>)", "Invalid Group Name (starts with digit)"),
        ("(?<>)", "Empty Group Name"),
        ("(?<name-bad>)", "Invalid Group Name (hyphen)"),
        ("(?:abc", "Unclosed Non-Capturing Group"),
        ("(?>abc", "Unclosed Atomic Group"),
        ("(?=abc", "Unclosed Lookahead"),
        ("(?!abc", "Unclosed Negative Lookahead"),
        ("(?<=abc", "Unclosed Lookbehind"),
        ("(?<!abc", "Unclosed Negative Lookbehind"),
        ("(?<name>a)(?<name>b)", "Duplicate Group Name"),
        ("abc)", "Unmatched Closing Paren"),
        ("(?i)", "Inline Modifier (not supported)"),
    ],
    
    "Quantifiers": [
        ("*", "Quantifier at Start"),
        ("+", "Plus at Start"),
        ("?", "Question at Start"),
        ("{5}", "Brace Quant at Start"),
        ("a{5,2}", "Inverted Range"),
        ("a{", "Incomplete Brace Quant (no digits)"),
        ("a{5", "Incomplete Brace Quant (no close)"),
        ("a{5,", "Incomplete Brace Quant (comma no close)"),
        ("a{foo}", "Non-Digit in Brace Quant"),
        ("^*", "Quantified Anchor (start)"),
        ("$+", "Quantified Anchor (end)"),
        ("\\b?", "Quantified Word Boundary"),
    ],
    
    "Character Classes": [
        ("[abc", "Unclosed Char Class"),
        ("[", "Empty Unclosed Char Class"),
        ("[z-a]", "Invalid Range (z-a)"),
        ("[9-0]", "Invalid Range (9-0)"),
        ("[]", "Empty Char Class (if this even errors)"),
        ("[a-]", "Incomplete Range (trailing dash)"),
        ("[-a]", "Leading Dash"),
        ("[^]", "Empty Negated Class (if errors)"),
    ],
    
    "Anchors and Escapes": [
        ("a^b", "Misplaced Anchor (caret in middle)"),
        ("a$b", "Misplaced Anchor (dollar in middle)"),
        ("\\z", "Unknown Escape (lowercase z)"),
        ("\\q", "Unknown Escape (q)"),
        ("\\xGG", "Invalid Hex Escape"),
        ("\\x", "Incomplete Hex Escape"),
        ("\\x{", "Incomplete Hex Brace"),
        ("\\x{GG}", "Invalid Hex in Brace"),
        ("\\uGGGG", "Invalid Unicode 4-digit"),
        ("\\u", "Incomplete Unicode"),
        ("\\u{", "Incomplete Unicode Brace"),
        ("\\UGGGGGGGG", "Invalid Unicode 8-digit"),
        ("\\p", "Incomplete Unicode Property (no brace)"),
        ("\\p{", "Incomplete Unicode Property (no close)"),
        ("\\p{Foo", "Unterminated Unicode Property"),
        ("\\P{Bar", "Unterminated Unicode Property (P)"),
    ],
    
    "Backreferences": [
        ("\\1", "Backref to Undefined Group (no groups)"),
        ("(a)\\2", "Backref to Undefined Group (only 1 group)"),
        ("\\k<name>", "Named Backref to Undefined Group"),
        ("\\k", "Incomplete Named Backref (no <)"),
        ("\\k<", "Incomplete Named Backref (no >)"),
        ("\\k<foo", "Unterminated Named Backref"),
    ],
    
    "Alternation": [
        ("|abc", "Alternation Lacks Left-Hand Side"),
        ("abc|", "Alternation Lacks Right-Hand Side"),
        ("a||b", "Empty Alternation Branch"),
    ],
    
    "Directives and Flags": [
        ("%flags foo", "Invalid Flag Letter"),
        ("abc%flags i", "Flag After Pattern"),
    ],
}


def main():
    """Run all error tests and print results."""
    print("=" * 80)
    print("IEH AUDIT - COMPREHENSIVE ERROR TESTING")
    print("=" * 80)
    print()
    
    total_tests = 0
    
    for category, cases in ERROR_CASES.items():
        print(f"\n{'=' * 80}")
        print(f"CATEGORY: {category}")
        print(f"{'=' * 80}\n")
        
        for pattern, description in cases:
            total_tests += 1
            print(f"[{total_tests}] {description}")
            print(f"    Pattern: {repr(pattern)}")
            print(f"    {'-' * 70}")
            
            result = test_pattern(pattern)
            
            if result['error_msg']:
                print(f"    Error: {result['error_msg']}")
                if result['hint']:
                    print(f"    Hint: {result['hint'][:80]}...")
                else:
                    print(f"    Hint: None")
            else:
                print(f"    ✓ No error (unexpected!)")
            
            print()
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL TESTS RUN: {total_tests}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
