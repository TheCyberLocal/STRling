#!/usr/bin/env python3
"""
parse_strl.py — Thin CLI wrapper over the unified language-intelligence core.

Module Pedagogy:
================
This script is the single command-line surface for analyzing STRling DSL
files. After the consolidation of the previous CLI server shadow, all
parsing, validation, and emission flows go through the same Python core
that the LSP server consumes (see
``bindings/python/src/STRling/core/intelligence.py``). This file owns
*only* CLI argument parsing, file/stdin I/O, and JSON output formatting.

The output JSON contract and exit codes are stable and asserted by the
end-to-end smoke tests
(``bindings/python/tests/e2e/test_cli_smoke.py``):

* Success without ``--emit``  → empty stdout, exit ``0``.
* Success with ``--emit``     → ``{"artifact": ..., "emitted": ...}`` on
  stdout, exit ``0``.
* Schema validation failure   → ``{"validation_error": ..., "artifact": ...}``,
  exit ``3``.
* Parse failure               → ``{"error": {"message": ..., "pos": ...}}``,
  exit ``2``.
* Missing input file          → uncaught ``FileNotFoundError`` propagates
  to stderr with no stdout, non-zero exit (mirrors prior behaviour).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Make the in-tree Python binding importable when running this script
# directly from the repository checkout. Production installs already have
# ``STRling`` on ``sys.path`` so this insert is a no-op for them.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PY_SRC = _REPO_ROOT / "bindings" / "python" / "src"
if _PY_SRC.is_dir() and str(_PY_SRC) not in sys.path:
    sys.path.insert(0, str(_PY_SRC))

from STRling.core.errors import STRlingParseError  # noqa: E402
from STRling.core.parser import parse, parse_to_artifact  # noqa: E402
from STRling.core.validator import validate_artifact  # noqa: E402


def _emit_pcre2(src: str) -> str:
    """Compile ``src`` and serialize via the PCRE2 emitter.

    Compiler and emitter are imported lazily so the parse-only path does
    not pay for them. Returns the emitted regex string.
    """
    from STRling.core.compiler import Compiler
    from STRling.emitters import pcre2 as pcre2_emitter

    flags, ast = parse(src)
    ir_root = Compiler().compile(ast)
    flags_dict = flags.to_dict() if hasattr(flags, "to_dict") else None
    return pcre2_emitter.emit(ir_root, flags_dict)


def main() -> None:
    """Entry point for ``python3 tooling/parse_strl.py``."""
    ap = argparse.ArgumentParser(description="STRling Parser & Emitter")
    ap.add_argument("input", help=".strl file path or '-' for stdin")
    ap.add_argument("--schema", help="Path to base.schema.json for validation")
    ap.add_argument(
        "--emit", choices=["pcre2"], help="Emit target regex for the given engine"
    )
    args = ap.parse_args()

    src = (
        sys.stdin.read()
        if args.input == "-"
        else Path(args.input).read_text(encoding="utf-8")
    )

    # --- Parse stage ----------------------------------------------------- #
    try:
        artifact: Dict[str, Any] = parse_to_artifact(src)
    except STRlingParseError as e:
        # Preserve the historical error envelope so existing smoke tests
        # and downstream consumers continue to parse the response.
        print(
            json.dumps(
                {"error": {"message": e.message, "pos": e.pos}},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(2)

    # --- Optional schema validation -------------------------------------- #
    if args.schema:
        try:
            validate_artifact(artifact, args.schema)
        except Exception as e:
            print(
                json.dumps(
                    {"validation_error": str(e), "artifact": artifact},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            sys.exit(3)

    # --- Optional regex emission ----------------------------------------- #
    if args.emit:
        if args.emit == "pcre2":
            emitted: Any = _emit_pcre2(src)
        else:  # pragma: no cover - argparse choices keeps this unreachable
            emitted = f"Emitter '{args.emit}' not implemented."

        print(
            json.dumps(
                {"artifact": artifact, "emitted": emitted},
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
