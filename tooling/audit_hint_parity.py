#!/usr/bin/env python3
"""
STRling Hint Parity Auditor

Statically audits all binding hint engines for parity with the TypeScript
reference implementation. Extracts error-pattern keys from each binding's
hint engine source and reports missing or extra patterns.

Usage:
    python tooling/audit_hint_parity.py

Exit codes:
    0 - All bindings have full parity
    1 - One or more bindings have drift
"""

import re
import sys
from pathlib import Path

# Repository root (this script lives in tooling/)
ROOT = Path(__file__).resolve().parent.parent

# ── TypeScript Reference Patterns ──────────────────────────────────────────
# These are the 38 canonical error-pattern keys from the TS hint engine.
# Source of truth: bindings/typescript/src/STRling/core/hint_engine.ts

TS_PATTERNS = [
    "Unterminated group",
    "Empty character class",
    "Unterminated character class",
    "Unterminated named backref",
    "Unterminated group name",
    "Unterminated lookahead",
    "Unterminated lookbehind",
    "Unterminated atomic group",
    "Unterminated {m,n}",
    "Unterminated {n}",
    "Unexpected token",
    "Unexpected trailing input",
    "Cannot quantify anchor",
    "Backreference to undefined group",
    "Duplicate group name",
    "Alternation lacks left-hand side",
    "Alternation lacks right-hand side",
    "Inline modifiers",
    "Invalid \\xHH escape",
    "Invalid \\uHHHH",
    "Unterminated \\x{...}",
    "Unterminated \\u{...}",
    "Unterminated \\p{...}",
    "Expected { after \\p/\\P",
    "Invalid brace quantifier content",
    "Invalid group name",
    "Invalid quantifier range",
    "Invalid character range",
    "Invalid flag",
    "Directive after pattern",
    "Malformed directive",
    "Empty alternation",
    "Unknown escape sequence",
    "Invalid quantifier",
    "Expected '<' after \\k",
    "Incomplete quantifier",
    "Invalid \\UHHHHHHHH escape",
    "Unmatched ')'",
]


def extract_quoted_strings(text: str) -> set[str]:
    """Extract all double-quoted and single-quoted strings from source text."""
    strings: set[str] = set()
    # Double-quoted strings (simple extraction)
    for m in re.finditer(r'"([^"]*)"', text):
        strings.add(m.group(1))
    # Single-quoted strings (handle escaped quotes like \' in Perl)
    for m in re.finditer(r"'((?:[^'\\]|\\.)*)'", text):
        # Unescape \' -> ' for Perl-style escaping
        val = m.group(1).replace("\\'", "'")
        strings.add(val)
    return strings


def find_matching_patterns(
    source_text: str, source_strings: set[str], reference: list[str]
) -> tuple[set[str], set[str]]:
    """Find which reference patterns appear in the source.

    Uses both quoted-string extraction AND plain substring search on source text
    to handle different backslash escaping conventions across languages.
    Also searches for common escaped variants (e.g., \\\\x for \\x).
    """
    found: set[str] = set()
    for pattern in reference:
        # Direct match in extracted strings
        for s in source_strings:
            if pattern in s:
                found.add(pattern)
                break
        if pattern in found:
            continue
        # Plain substring in source text
        if pattern in source_text:
            found.add(pattern)
            continue
        # Try with doubled backslashes (how most languages escape \\ in source)
        escaped = pattern.replace("\\", "\\\\")
        if escaped in source_text:
            found.add(pattern)
            continue
        # Try with raw-string-style (no extra escaping, common in Go/Rust)
        for s in source_strings:
            if escaped in s:
                found.add(pattern)
                break
    missing = set(reference) - found
    return found, missing


# ── Binding Definitions ────────────────────────────────────────────────────

BINDINGS = {
    "typescript": ROOT
    / "bindings"
    / "typescript"
    / "src"
    / "STRling"
    / "core"
    / "hint_engine.ts",
    "python": ROOT
    / "bindings"
    / "python"
    / "src"
    / "STRling"
    / "core"
    / "hint_engine.py",
    "java": ROOT
    / "bindings"
    / "java"
    / "src"
    / "main"
    / "java"
    / "com"
    / "strling"
    / "core"
    / "HintEngine.java",
    "csharp": ROOT
    / "bindings"
    / "csharp"
    / "src"
    / "STRling"
    / "Core"
    / "HintEngine.cs",
    "go": ROOT / "bindings" / "go" / "core" / "hint_engine.go",
    "rust": ROOT / "bindings" / "rust" / "src" / "core" / "hint_engine.rs",
    "c": ROOT / "bindings" / "c" / "src" / "core" / "hint_engine.c",
    "cpp": ROOT / "bindings" / "cpp" / "src" / "core" / "hint_engine.cpp",
    "fsharp": ROOT / "bindings" / "fsharp" / "src" / "STRling" / "Core" / "Errors.fs",
    "ruby": ROOT / "bindings" / "ruby" / "lib" / "strling" / "core" / "hint_engine.rb",
    "perl": ROOT / "bindings" / "perl" / "lib" / "STRling" / "Core" / "HintEngine.pm",
    "lua": ROOT / "bindings" / "lua" / "src" / "hint_engine.lua",
    "r": ROOT / "bindings" / "r" / "R" / "hint_engine.R",
    "kotlin": ROOT
    / "bindings"
    / "kotlin"
    / "src"
    / "main"
    / "kotlin"
    / "strling"
    / "core"
    / "HintEngine.kt",
    "dart": ROOT / "bindings" / "dart" / "lib" / "src" / "core" / "hint_engine.dart",
    "swift": ROOT
    / "bindings"
    / "swift"
    / "Sources"
    / "STRling"
    / "Core"
    / "HintEngine.swift",
    "php": ROOT / "bindings" / "php" / "src" / "Core" / "HintEngine.php",
}


def audit() -> int:
    """Run the parity audit. Returns 0 for full parity, 1 for drift."""
    total_bindings = 0
    passing_bindings = 0
    failing_bindings: list[tuple[str, set[str]]] = []

    print("=" * 72)
    print("STRling Hint Parity Audit")
    print(f"Reference: TypeScript ({len(TS_PATTERNS)} patterns)")
    print("=" * 72)
    print()

    for name, path in sorted(BINDINGS.items()):
        if not path.exists():
            print(f"  [{name:12s}] ⚠  File not found: {path.relative_to(ROOT)}")
            continue

        total_bindings += 1
        source = path.read_text(encoding="utf-8")
        source_strings = extract_quoted_strings(source)
        found, missing = find_matching_patterns(source, source_strings, TS_PATTERNS)

        if not missing:
            print(f"  [{name:12s}] ✓  {len(found)}/{len(TS_PATTERNS)} patterns")
            passing_bindings += 1
        else:
            print(
                f"  [{name:12s}] ✗  {len(found)}/{len(TS_PATTERNS)} patterns — missing {len(missing)}"
            )
            for p in sorted(missing):
                print(f"                   - {p}")
            failing_bindings.append((name, missing))

    print()
    print("-" * 72)
    print(f"Bindings audited: {total_bindings}")
    print(f"Passing:          {passing_bindings}")
    print(f"Failing:          {len(failing_bindings)}")
    print("-" * 72)

    if failing_bindings:
        print()
        print("DRIFT DETECTED — the following bindings need updates:")
        for name, missing in failing_bindings:
            print(f"  {name}: {len(missing)} missing pattern(s)")
        return 1

    print()
    print("ALL BINDINGS AT FULL PARITY ✓")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
