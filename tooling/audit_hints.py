#!/usr/bin/env python3
"""
IEH Audit Script - Test STRling Parse Errors

This script takes an invalid STRling pattern as input and prints
the fully formatted STRlingParseError with hints.

Usage:
    python audit_hints.py "invalid_pattern"
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Tuple as _Tuple, Any, cast

# Make the local bindings/python/src available at runtime in a robust way.
# This helps running the script directly and is friendly to Pylance when the
# workspace is configured (see .vscode/settings.json which adds the same path
# to python.analysis.extraPaths for static analysis).
repo_root = Path(__file__).resolve().parents[1]
src_dir = repo_root / "bindings" / "python" / "src"
if src_dir.exists():
    sp = str(src_dir)
    if sp not in sys.path:
        sys.path.insert(0, sp)

if TYPE_CHECKING:
    # For static type checkers only - avoids runtime import failures in
    # environments where the bindings path isn't available.
    from STRling.core.nodes import Flags, Node  # type: ignore
    from STRling.core.errors import STRlingParseError  # type: ignore
    from typing import Callable

    # Tell the type checker the runtime `parse` callable signature. This
    # is a type-only declaration and won't affect runtime.
    parse: Callable[[str], _Tuple[Flags, Node]]  # type: ignore

try:  # prefer static import so type-checkers can resolve symbols
    from STRling.core.parser import parse  # type: ignore
    from STRling.core.errors import STRlingParseError  # type: ignore

    # Import the node types at runtime; we do this inside the try/except so
    # this script can still run in environments where the source path isn't
    # present and the dynamic loader is required.
    from STRling.core.nodes import Flags, Node  # type: ignore
except Exception:  # pragma: no cover - fallback for unusual environments
    # If static import fails at runtime, load modules dynamically from the
    # `bindings/python/src/STRling/core` path so the script can still run.
    import importlib.util as _importlib_util

    _parser_path = src_dir / "STRling" / "core" / "parser.py"
    _errors_path = src_dir / "STRling" / "core" / "errors.py"

    def _load_module(path: Path, name: str):
        spec = _importlib_util.spec_from_file_location(name, str(path))
        module = _importlib_util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(module)  # type: ignore
        return module

    parser_mod = _load_module(_parser_path, "STRling.core.parser")
    errors_mod = _load_module(_errors_path, "STRling.core.errors")

    parse = parser_mod.parse  # type: ignore
    STRlingParseError = errors_mod.STRlingParseError  # type: ignore


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
        # parse() returns (Flags, Node). Because the imported `parse` may be
        # dynamically loaded at runtime we help static analysis by casting
        # the return value to the expected tuple type.
        # Annotate the result variable so static analysis knows the exact
        # return structure from parse(): (Flags, Node). We use postponed
        # evaluation of annotations (PEP 563 / future import) so these
        # references don't need to be available at runtime, which keeps
        # this script robust in environments where the bindings path is
        # not present.
        result = parse(pattern)  # type: ignore[call-arg]
        # Use `Any` casts here to satisfy the language server when the
        # concrete binding types aren't resolvable in some editor setups.
        flags = cast(Any, result[0])
        ast = cast(Any, result[1])
        print("✓ Pattern parsed successfully (no error)")
        print(f"  Flags: {flags}")
        print(f"  AST: {ast}")
    except Exception as e:  # pragma: no cover - defensive runtime fallback
        # Print the string for any exception. We intentionally avoid
        # referencing the concrete exception class here to keep the
        # script robust in editor setups where the binding types are not
        # resolvable by the language server.
        ee: Exception = e
        print(str(ee))

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_hints.py <pattern>")
        print("Example: python audit_hints.py '(abc'")
        sys.exit(1)

    pattern = sys.argv[1]
    test_pattern(pattern)
