#!/usr/bin/env python3
"""Sync project version numbers across language bindings.

This script is used by maintainers to keep a single Source-Of-Truth
version (in `bindings/python/pyproject.toml`) synchronized with
language-specific metadata files across the repo.

The module is written to be importable and testable; functions raise
exceptions instead of calling sys.exit() directly so callers (or tests)
can decide how to handle errors.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
SOURCE_FILE: Path = ROOT_DIR / "bindings/python/pyproject.toml"


def get_source_version() -> str:
    """Return the version found in the Python binding `pyproject.toml`.

    Raises:
        FileNotFoundError: if `pyproject.toml` does not exist.
        ValueError: if no version line is found.
    """
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Source file {SOURCE_FILE} not found.")

    content: str = SOURCE_FILE.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(.*?)"', content, re.MULTILINE)
    if match:
        return match.group(1)

    raise ValueError("Could not find version in pyproject.toml")


def update_file(
    path: str,
    new_version: str,
    dry_run: bool = False,
    updater_func: Optional[Callable[[str, str, Path], str]] = None,
) -> bool:
    """Read a target file, run an updater func on its contents and write back.

    Returns True if file was present and processed (even if no change),
    False if file was missing or if an error occurred.
    """
    file_path: Path = ROOT_DIR / path
    if not file_path.exists():
        logger.warning("Target file %s not found. Skipping.", path)
        return False

    if updater_func is None:
        raise ValueError("updater_func must be provided")

    try:
        content: str = file_path.read_text(encoding="utf-8")
        new_content: str = updater_func(content, new_version, file_path)

        if new_content != content:
            if not dry_run:
                file_path.write_text(new_content, encoding="utf-8")
                logger.info("Updated %s to %s", path, new_version)
            else:
                logger.info("Would update %s to %s", path, new_version)
        else:
            logger.debug("No changes needed for %s", path)

        return True
    except Exception:
        logger.exception("Error updating %s", path)
        return False


# --- Updater Functions ---


def update_toml_cargo(content: str, version: str, path: Path) -> str:
    # Update the version inside [package] section in a Cargo.toml
    pattern = re.compile(
        r'(^\[package\][\s\S]*?^version\s*=\s*")([^\"]+)(")',
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if match:
        return content[: match.start(2)] + version + content[match.end(2) :]
    return content


def update_json(content: str, version: str, path: Path) -> str:
    data = json.loads(content)
    if data.get("version") == version:
        return content

    data["version"] = version

    # Try to detect indentation from the existing file (fallback to 2)
    indent = 2
    m = re.search(r"\n(\s+)\"[^\"]+\":", content)
    if m:
        indent = len(m.group(1))

    return json.dumps(data, indent=indent, ensure_ascii=False) + "\n"


def update_composer_json(content: str, version: str, path: Path) -> str:
    # Use JSON parsing to handle both replacement and insertion robustly.
    # Composer files are valid JSON; json.loads/json.dumps will correctly
    # handle both updating an existing "version" key and inserting one when
    # missing. We try to detect indentation to preserve formatting.
    data = json.loads(content)
    if data.get("version") == version:
        return content

    data["version"] = version

    # Detect indentation similar to update_json
    indent = 2
    m = re.search(r"\n(\s+)\"[^\"]+\":", content)
    if m:
        indent = len(m.group(1))

    return json.dumps(data, indent=indent, ensure_ascii=False) + "\n"


def update_yaml_pubspec(content: str, version: str, path: Path) -> str:
    return re.sub(
        r"(^version:\s*)(.+)",
        lambda m: m.group(1) + version,
        content,
        flags=re.MULTILINE,
    )


def update_ruby_gemspec(content: str, version: str, path: Path) -> str:
    # Use callable replacement to avoid ambiguous group concatenation
    return re.sub(
        r'(spec\.version\s*=\s*")([^\"]+)(")',
        lambda m: m.group(1) + version + m.group(3),
        content,
    )


def update_xml_csproj(content: str, version: str, path: Path) -> str:
    if "<Version>" in content:
        return re.sub(
            r"(<Version>)([^<]+)(</Version>)",
            lambda m: m.group(1) + version + m.group(3),
            content,
        )

    # Insert a Version element into the first PropertyGroup if missing
    return re.sub(
        r"(<PropertyGroup>)",
        lambda m: m.group(1) + "\n    <Version>" + version + "</Version>",
        content,
        count=1,
    )


def update_xml_pom(content: str, version: str, path: Path) -> str:
    # Replace the first project-level <version>...</version> occurrence.
    return re.sub(
        r"(<version>)([^<]+)(</version>)",
        lambda m: m.group(1) + version + m.group(3),
        content,
        count=1,
    )


def update_kotlin_gradle(content: str, version: str, path: Path) -> str:
    return re.sub(
        r'(^version\s*=\s*")([^\"]+)(")',
        lambda m: m.group(1) + version + m.group(3),
        content,
        flags=re.MULTILINE,
    )


def update_r_description(content: str, version: str, path: Path) -> str:
    return re.sub(
        r"(^Version:\s*)(.+)",
        lambda m: m.group(1) + version,
        content,
        flags=re.MULTILINE,
    )


def update_perl_pm(content: str, version: str, path: Path) -> str:
    return re.sub(
        r"(our\s+\$VERSION\s*=\s*')([^']+)(';)",
        lambda m: m.group(1) + version + m.group(3),
        content,
    )


def update_cmake(content: str, version: str, path: Path) -> str:
    return re.sub(
        r"(project\s*\([\s\S]*?VERSION\s+)([\d\.\w-]+)([\s\S]*?\))",
        lambda m: m.group(1) + version + m.group(3),
        content,
    )


def update_c_source(content: str, version: str, path: Path) -> str:
    pattern = re.compile(
        r'(const\s+char\s*\*\s*strling_version\s*\(\s*void\s*\)\s*\{[\s\S]*?return\s*")([^\"]+)(\")',
        re.DOTALL,
    )
    # callable replacement is safest
    return pattern.sub(lambda m: m.group(1) + version + m.group(3), content)


def update_lua_rockspec(content: str, version: str, path: Path) -> str:
    rockspec_version = version if "-" in version else (version + "-1")
    return re.sub(
        r'(^version\s*=\s*")([^\"]+)(")',
        lambda m: m.group(1) + rockspec_version + m.group(3),
        content,
        flags=re.MULTILINE,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync project version across bindings")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if versions are in sync without modifying",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to files")
    args = parser.parse_args(argv)

    if not args.check and not args.write:
        parser.print_usage()
        return 1

    try:
        version = get_source_version()
    except Exception as exc:
        logger.exception("Failed to determine source version: %s", exc)
        return 2

    logger.info("Source version (Python): %s", version)

    targets: List[Tuple[str, Callable[[str, str, Path], str]]] = [
        ("bindings/rust/Cargo.toml", update_toml_cargo),
        ("bindings/typescript/package.json", update_json),
        ("bindings/php/composer.json", update_composer_json),
        ("bindings/ruby/strling.gemspec", update_ruby_gemspec),
        ("bindings/dart/pubspec.yaml", update_yaml_pubspec),
        ("bindings/csharp/src/STRling/STRling.csproj", update_xml_csproj),
        ("bindings/fsharp/src/STRling/STRling.fsproj", update_xml_csproj),
        ("bindings/java/pom.xml", update_xml_pom),
        ("bindings/kotlin/build.gradle.kts", update_kotlin_gradle),
        ("bindings/r/DESCRIPTION", update_r_description),
        ("bindings/perl/lib/STRling.pm", update_perl_pm),
        ("bindings/cpp/CMakeLists.txt", update_cmake),
        ("bindings/c/src/strling.c", update_c_source),
        ("bindings/lua/strling-scm-1.rockspec", update_lua_rockspec),
    ]

    success = True
    for path, updater in targets:
        if not update_file(path, version, dry_run=not args.write, updater_func=updater):
            success = False

    if args.check and not success:
        logger.error("Version mismatch detected!")
        return 3

    if args.write:
        logger.info("Version sync complete.")

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
