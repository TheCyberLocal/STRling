
#!/usr/bin/env python3
import sys, json, argparse
from core.parser import parse_to_artifact, ParseError
from core.validator import validate_artifact
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="STRling Sprint 3 Parser")
    ap.add_argument("input", help=".strl file path or '-' for stdin")
    ap.add_argument("--schema", help="Path to base.schema.json for validation")
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

    print(json.dumps(artifact, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
