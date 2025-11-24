#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING
import importlib

# Make local `bindings/python/src` importable at runtime when this script
# is executed from the repository workspace. This helps running the script
# directly (and often helps IDEs/static analyzers discover the package).
_repo_root = Path(__file__).resolve().parents[1]
_py_src = _repo_root / "bindings" / "python" / "src"
if str(_py_src) not in sys.path:
    sys.path.insert(0, str(_py_src))

# Load core modules dynamically at runtime to avoid static import errors
# in editors that don't include the local package path.
parse_to_artifact: Any = None
parse: Any = None
ParseError: Any = Exception
validate_artifact: Any = None
try:
    _mod_parser = importlib.import_module("STRling.core.parser")
    parse_to_artifact = getattr(_mod_parser, "parse_to_artifact")
    parse = getattr(_mod_parser, "parse")
    ParseError = getattr(_mod_parser, "ParseError")
    _mod_validator = importlib.import_module("STRling.core.validator")
    validate_artifact = getattr(_mod_validator, "validate_artifact")
except Exception:
    # leave placeholders in place if imports fail at runtime
    pass

if TYPE_CHECKING:
    # Avoid importing `STRling.core` directly in editors where the package
    # path is not configured. Provide Any-typed aliases so type checkers
    # won't raise missing-import diagnostics and we avoid unused-import
    # warnings from linters.
    _parser: Any = None
    _validator: Any = None


def main():
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

    # parse_to_artifact may be typed only for static checkers; guard at runtime.
    try:
        artifact: Dict[str, Any] = parse_to_artifact(src)  # type: ignore
    except ParseError as e:  # type: ignore[arg-type]
        # ParseError expected to have .message and .pos attributes per spec.
        message = getattr(e, "message", str(e))
        pos = getattr(e, "pos", None)
        print(
            json.dumps(
                {"error": {"message": message, "pos": pos}},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(2)

    if args.schema:
        try:
            validate_artifact(artifact, args.schema)  # type: ignore
        except Exception as e:
            print(
                json.dumps(
                    {"validation_error": str(e), "artifact": artifact},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            sys.exit(3)

    if args.emit:
        # Import compiler and emitters lazily; include type-ignore for runtime
        try:
            from STRling.core.compiler import Compiler  # type: ignore
            from STRling.emitters import pcre2 as pcre2_emitter  # type: ignore
        except Exception:
            Compiler = None  # type: ignore
            pcre2_emitter = None  # type: ignore

        flags: Any = None
        ast: Any = None
        if parse is not None:
            flags, ast = parse(src)  # type: ignore

        ir_root: Any = None
        if Compiler is not None and ast is not None:
            ir_root = Compiler().compile(ast)  # type: ignore

        emitted: Any = None
        if args.emit == "pcre2":
            if pcre2_emitter is not None and flags is not None and ir_root is not None:
                # flags expected to have a `to_dict()` method.
                flags_dict = getattr(flags, "to_dict", lambda: None)()
                emitted = pcre2_emitter.emit(ir_root, flags_dict)  # type: ignore
            else:
                emitted = "Emitter 'pcre2' not available in this environment."
        else:
            emitted = f"Emitter '{args.emit}' not implemented."

        print(
            json.dumps(
                {"artifact": artifact, "emitted": emitted}, ensure_ascii=False, indent=2
            )
        )


if __name__ == "__main__":
    main()
