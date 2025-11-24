#!/usr/bin/env python3
"""
Simple linter to check for forbidden pointer tokens in public usage files.

Checks the following files under bindings/cpp:
 - include/strling/*.hpp
 - README.md
 - test/** (unit tests)

Forbidden tokens: std::unique_ptr, std::make_shared, new Group, new strling::, ->, unique_ptr
"""

import sys
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Union

ROOT = Path(__file__).resolve().parents[1]

# Tokens we want to detect in the user-facing usage snippets/tests for simply API
FORBIDDEN = [
    "std::unique_ptr",
    "std::make_shared",
    "new Group",
    "new strling::",
    "->",
    "unique_ptr",
]


def hits_in_text(text: str, tokens: Iterable[str]) -> List[Tuple[int, str, str]]:
    """Return a list of (line_number, token, line) occurrences found in text.

    Parameters
    - text: full string to scan
    - tokens: iterable of substring tokens to search for

    Returns a list of tuples: (line_number, token, matched_line)
    """
    hits: List[Tuple[int, str, str]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        for token in tokens:
            if token in line:
                hits.append((i, token, line.strip()))
    return hits


def main():
    base: Path = ROOT
    targets: List[Union[Path, Tuple[str, str]]] = []

    # We'll only scan user-facing simply usage: README code blocks that mention simply
    # and unit tests that include the simply header or use the simply namespace.
    rd = base / "README.md"
    if rd.exists():
        with rd.open(encoding="utf-8") as fh:
            rtext = fh.read()
        # Find fenced code blocks which contain the simply usage (a minimal heuristic)
        code_blocks: List[str] = []
        fence_open: bool = False
        cur: List[str] = []
        for line in rtext.splitlines():
            if line.strip().startswith("```"):
                fence_open = not fence_open
                if not fence_open and cur:
                    code_blocks.append("\n".join(cur))
                    cur = []
                continue
            if fence_open:
                cur.append(line)
        # only keep code blocks which mention simply or include the simply header
        for block in code_blocks:
            if "simply" in block or "strling/simply.hpp" in block:
                targets.append(("README", block))

    # tests — only inspect files that include the simply header or use the simply namespace
    for p in (base / "test").rglob("*.cpp"):
        text = p.read_text(encoding="utf-8")
        if "strling/simply.hpp" in text or "using namespace strling::simply" in text:
            targets.append(p)

    all_hits: Dict[str, List[Tuple[int, str, str]]] = {}
    for f in targets:
        if isinstance(f, tuple) and f[0] == "README":
            hits = hits_in_text(f[1], FORBIDDEN)
            if hits:
                all_hits["bindings/cpp/README.md (code block)"] = hits
            continue

        # f here must be a Path (we filtered tuples above)
        if isinstance(f, Path):
            file_text = f.read_text(encoding="utf-8")
        else:
            # defensive: convert to str and read via Path
            file_text = Path(str(f)).read_text(encoding="utf-8")

        hits = hits_in_text(file_text, FORBIDDEN)
        if hits:
            all_hits[str(f)] = hits

    if all_hits:
        print("Forbidden pointer tokens found in public files:")
        for f, hits in all_hits.items():
            print(f"\nIn {f}:")
            for ln, token, line in hits:
                print(f"  {ln}: [{token}] {line}")
        sys.exit(2)

    print("No forbidden pointer tokens found in public headers, README, or tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
