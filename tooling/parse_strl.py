#!/usr/bin/env python3
import sys, json, argparse
from pathlib import Path

from core.parser import parse_to_artifact, parse, ParseError
from core.validator import validate_artifact

def main():
    ap = argparse.ArgumentParser(description="STRling Parser & Emitter (Sprint 3+4)")
    ap.add_argument("input", help=".strl file path or '-' for stdin")
    ap.add_argument("--schema", help="Path to base.schema.json for validation")
    ap.add_argument("--emit", choices=["pcre2"], help="Emit target regex for the given engine")
    args = ap.parse_args()

    src = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")

    try:
        artifact = parse_to_artifact(src)
    except ParseError as e:
        print(json.dumps({"error": {"message": e.message, "pos": e.pos}}, ensure_ascii=False, indent=2))
        sys.exit(2)

    if args.schema:
        try:
            validate_artifact(artifact, args.schema)
        except Exception as e:
            print(json.dumps({"validation_error": str(e), "artifact": artifact}, ensure_ascii=False, indent=2))
            sys.exit(3)

    if args.emit:
        from core.compiler import Compiler
        from emitters import pcre2 as pcre2_emitter
        flags, ast = parse(src)
        ir_root = Compiler().compile(ast)
        if args.emit == "pcre2":
            emitted = pcre2_emitter.emit(ir_root, flags.to_dict())
        print(json.dumps({"artifact": artifact, "emitted": emitted}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(artifact, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()