#!/usr/bin/env python3
"""
STRling CLI Server - JSON-RPC Interface for Parser Diagnostics

This module provides a command-line interface for obtaining structured
diagnostics from the STRling parser. It serves as the binding-agnostic
communication layer between the LSP server and the Python core logic.

The CLI emits JSON-formatted diagnostics that can be consumed by any LSP
implementation, ensuring compatibility with the future Rust core and
multi-language roadmap.

Usage:
    python -m STRling.cli_server --diagnostics <filepath>
    python -m STRling.cli_server --diagnostics-stdin

Output Format:
    {
        "success": true/false,
        "diagnostics": [
            {
                "range": {
                    "start": {"line": 0, "character": 5},
                    "end": {"line": 0, "character": 6}
                },
                "severity": 1,
                "message": "Error message with hint",
                "source": "STRling",
                "code": "error_code"
            }
        ],
        "version": "1.0.0"
    }
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List

from .core.parser import parse
from .core.errors import STRlingParseError


def diagnose_file(filepath: str) -> Dict[str, Any]:
    """
    Diagnose a STRling pattern file and return structured diagnostics.

    Parameters
    ----------
    filepath : str
        Path to the STRling pattern file to analyze

    Returns
    -------
    dict
        A dictionary containing:
        - success: Whether the parse was successful
        - diagnostics: List of diagnostic objects (empty if success)
        - version: CLI protocol version
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return {
                "success": False,
                "diagnostics": [
                    {
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 0},
                        },
                        "severity": 1,
                        "message": f"File not found: {filepath}",
                        "source": "STRling",
                        "code": "file_not_found",
                    }
                ],
                "version": "1.0.0",
            }

        content = path.read_text(encoding="utf-8")
        return diagnose_content(content)

    except Exception as e:
        return {
            "success": False,
            "diagnostics": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 0},
                    },
                    "severity": 1,
                    "message": f"Error reading file: {str(e)}",
                    "source": "STRling",
                    "code": "read_error",
                }
            ],
            "version": "1.0.0",
        }


def diagnose_content(content: str) -> Dict[str, Any]:
    """
    Diagnose STRling pattern content and return structured diagnostics.

    Parameters
    ----------
    content : str
        The STRling pattern content to analyze

    Returns
    -------
    dict
        A dictionary containing:
        - success: Whether the parse was successful
        - diagnostics: List of diagnostic objects (empty if success)
        - version: CLI protocol version
    """
    diagnostics: List[Dict[str, Any]] = []

    try:
        # Attempt to parse the content
        parse(content)
        return {"success": True, "diagnostics": [], "version": "1.0.0"}

    except STRlingParseError as e:
        # Convert the parse error to LSP diagnostic format
        diagnostics.append(e.to_lsp_diagnostic())
        return {"success": False, "diagnostics": diagnostics, "version": "1.0.0"}

    except Exception as e:
        # Catch any unexpected errors
        diagnostics.append(
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 0},
                },
                "severity": 1,
                "message": f"Unexpected error: {str(e)}",
                "source": "STRling",
                "code": "internal_error",
            }
        )
        return {"success": False, "diagnostics": diagnostics, "version": "1.0.0"}


def main() -> int:
    """Main entry point for the CLI server."""
    parser = argparse.ArgumentParser(
        description="STRling CLI Server - JSON Diagnostics Interface"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--diagnostics",
        metavar="FILE",
        help="Analyze a STRling pattern file and output JSON diagnostics",
    )
    group.add_argument(
        "--diagnostics-stdin",
        action="store_true",
        help="Read pattern from stdin and output JSON diagnostics",
    )
    group.add_argument(
        "--version", action="store_true", help="Print version information"
    )

    args = parser.parse_args()

    if args.version:
        print(
            json.dumps(
                {
                    "version": "1.0.0",
                    "name": "STRling CLI Server",
                    "protocol": "json-rpc",
                }
            )
        )
        return 0

    if args.diagnostics:
        result = diagnose_file(args.diagnostics)
    elif args.diagnostics_stdin:
        content = sys.stdin.read()
        result = diagnose_content(content)
    else:
        parser.print_help()
        return 1

    # Output JSON result
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
