#!/usr/bin/env python3
"""Reproduce the Swift package-resource copy of C compatibility fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "bindings/c/tests/fixtures"
DESTINATION = ROOT / "bindings/swift/Tests/STRlingConformanceTests/Resources"


def json_files(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    return {path.name: path for path in sorted(directory.glob("*.json"))}


def projection_findings(source: Path, destination: Path) -> list[str]:
    sources = json_files(source)
    outputs = json_files(destination)
    if not sources:
        return [f"no source JSON fixtures found in {source}"]
    if not destination.is_dir():
        return [f"expected output directory is missing: {destination}"]

    findings: list[str] = []
    for name in sorted(sources.keys() - outputs.keys()):
        findings.append(f"missing output: {name}")
    for name in sorted(outputs.keys() - sources.keys()):
        findings.append(f"unexpected output: {name}")
    for name in sorted(sources.keys() & outputs.keys()):
        if sources[name].read_bytes() != outputs[name].read_bytes():
            findings.append(f"stale output: {name}")
    return findings


def write_projection(source: Path, destination: Path) -> None:
    sources = json_files(source)
    if not sources:
        raise FileNotFoundError(f"no source JSON fixtures found in {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for output in json_files(destination).values():
        if output.name not in sources:
            output.unlink()
    for name, source_path in sources.items():
        (destination / name).write_bytes(source_path.read_bytes())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize the Swift compatibility fixture projection."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.write:
        try:
            write_projection(SOURCE, DESTINATION)
        except OSError as exc:
            print(f"fixture projection failed: {exc}", file=sys.stderr)
            return 2
        print(f"synchronized {len(json_files(SOURCE))} fixture files")
        return 0

    findings = projection_findings(SOURCE, DESTINATION)
    if findings:
        for finding in findings:
            print(f"fixture projection: {finding}", file=sys.stderr)
        return 1
    print(f"verified {len(json_files(SOURCE))} fixture files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
