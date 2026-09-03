#!/usr/bin/env python3
"""Materialize and verify the release Lua rockspec from its governed template."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "bindings/lua/strling-template.rockspec"
SOURCE_VERSION_PATH = ROOT / "governance/release-policy.json"
VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]*\Z")


class RockspecError(ValueError):
    """Raised when release rockspec materialization is not trustworthy."""


def normalize_lua_rockspec_version(version: str) -> str:
    """Append the LuaRocks revision unless the version already contains one."""
    if "-" not in version:
        return version + "-1"
    base, prerelease = version.split("-", 1)
    if prerelease.isdigit() or re.search(r"-\d+$", prerelease):
        return f"{base}-{prerelease}"
    return f"{base}-{prerelease}-1"


def source_version(path: Path = SOURCE_VERSION_PATH) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        version = data["product"]["repository_projection"]["version"]
    except (KeyError, TypeError) as exc:
        raise RockspecError(f"missing product repository projection in {path}") from exc
    if not isinstance(version, str):
        raise RockspecError(f"invalid product repository projection in {path}")
    return version


def validate_version(version: str) -> str:
    if not VERSION_PATTERN.fullmatch(version):
        raise RockspecError(f"invalid release version: {version!r}")
    return version


def rockspec_name(version: str) -> str:
    return (
        f"strling-{normalize_lua_rockspec_version(validate_version(version))}.rockspec"
    )


def render_rockspec(template: str, version: str) -> str:
    version = validate_version(version)
    rockspec_version = normalize_lua_rockspec_version(version)
    rendered, version_count = re.subn(
        r'(^version\s*=\s*)"VERSION-1"',
        lambda match: f'{match.group(1)}"{rockspec_version}"',
        template,
        flags=re.MULTILINE,
    )
    rendered, tag_count = re.subn(
        r'(tag\s*=\s*)"vVERSION"',
        lambda match: f'{match.group(1)}"v{version}"',
        rendered,
    )
    if version_count != 1 or tag_count != 1 or "VERSION" in rendered:
        raise RockspecError(
            "template must contain exactly one VERSION-1 field and one vVERSION tag"
        )
    return rendered


def materialize(
    version: str, output_dir: Path, template_path: Path = TEMPLATE_PATH
) -> Path:
    if not output_dir.is_dir():
        raise RockspecError(f"output directory does not exist: {output_dir}")
    output = output_dir / rockspec_name(version)
    rendered = render_rockspec(template_path.read_text(encoding="utf-8"), version)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    return output.resolve()


def verify_rockspec(
    version: str, path: Path, template_path: Path = TEMPLATE_PATH
) -> None:
    expected_name = rockspec_name(version)
    if path.name != expected_name:
        raise RockspecError(
            f"rockspec filename mismatch: expected {expected_name}, found {path.name}"
        )
    expected = render_rockspec(template_path.read_text(encoding="utf-8"), version)
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RockspecError(f"cannot read {path}: {exc}") from exc
    if actual != expected:
        raise RockspecError(
            f"rockspec content does not match canonical producer: {path}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("materialize", "verify", "check-template", "name")
    )
    version = parser.add_mutually_exclusive_group()
    version.add_argument("--version")
    version.add_argument("--version-from-source", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--print-path-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        version = args.version or source_version()
        output: Path | None = None
        if args.operation == "materialize":
            if args.output_dir is None:
                raise RockspecError("materialize requires --output-dir")
            output = materialize(version, args.output_dir, args.template)
        elif args.operation == "verify":
            if args.path is None:
                raise RockspecError("verify requires --path")
            verify_rockspec(version, args.path, args.template)
            output = args.path.resolve()
        elif args.operation == "check-template":
            render_rockspec(args.template.read_text(encoding="utf-8"), version)
        else:
            output = Path(rockspec_name(version))
    except (OSError, RockspecError, json.JSONDecodeError) as exc:
        print(f"LUA_ROCKSPEC_RESULT status=failed reason={exc}", file=sys.stderr)
        return 1

    if args.print_path_only:
        if output is None:
            print(
                "--print-path-only requires materialize, verify, or name",
                file=sys.stderr,
            )
            return 2
        print(output)
    elif args.json_output:
        print(
            json.dumps(
                {
                    "operation": args.operation,
                    "output": str(output) if output else None,
                    "status": "passed",
                    "version": version,
                },
                sort_keys=True,
            )
        )
    else:
        suffix = f" output={output}" if output else ""
        print(f"LUA_ROCKSPEC_RESULT status=passed version={version}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
