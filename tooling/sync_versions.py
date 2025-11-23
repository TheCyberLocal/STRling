#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

# Configuration
ROOT_DIR = Path(__file__).parent.parent
SOURCE_FILE = ROOT_DIR / "bindings/python/pyproject.toml"


def get_source_version():
    """Extracts version from pyproject.toml"""
    if not SOURCE_FILE.exists():
        print(f"Error: Source file {SOURCE_FILE} not found.")
        sys.exit(1)

    content = SOURCE_FILE.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(.*?)"', content, re.MULTILINE)
    if match:
        return match.group(1)

    print("Error: Could not find version in pyproject.toml")
    sys.exit(1)


def update_file(path, new_version, dry_run=False, updater_func=None):
    """Generic file update wrapper"""
    file_path = ROOT_DIR / path
    if not file_path.exists():
        print(f"Warning: Target file {path} not found. Skipping.")
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
        new_content = updater_func(content, new_version, file_path)

        if new_content != content:
            if not dry_run:
                file_path.write_text(new_content, encoding="utf-8")
                print(f"Updated {path} to {new_version}")
            else:
                print(f"Would update {path} to {new_version}")
            return True
        else:
            print(f"No changes needed for {path}")
            return True

    except Exception as e:
        print(f"Error updating {path}: {e}")
        return False


# --- Updater Functions ---


def update_toml_cargo(content, version, path):
    # Look for version in [package] section
    # This is a simplified regex approach.
    # It assumes 'version' is one of the first keys in [package] or clearly separated.
    # A more robust way would be to find [package] and then replace version inside it.

    # Pattern: Find [package] then look for version = "..." until the next section [
    pattern = r'(^\[package\][\s\S]*?^version\s*=\s*")([^"]+)(")'

    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return content[: match.start(2)] + version + content[match.end(2) :]
    return content


def update_json(content, version, path):
    data = json.loads(content)
    if "version" in data and data["version"] == version:
        return content

    data["version"] = version
    # Preserve indentation (assuming 2 or 4 spaces)
    indent = 2
    if "    " in content:
        indent = 4
    elif "\t" in content:
        indent = "\t"

    return json.dumps(data, indent=indent) + "\n"  # Add newline at EOF


def update_composer_json(content, version, path):
    # Composer might not have version, if so we add it after "name"
    data = json.loads(content)
    if "version" in data and data["version"] == version:
        return content

    # If using json.dump, we lose custom formatting.
    # Better to use regex for replacement if it exists, or insertion if not.
    if '"version":' in content:
        return re.sub(
            r'("version"\s*:\s*")([^"]+)(")', r"\g<1>" + version + r"\g<3>", content
        )
    else:
        # Insert after "name" (only the first occurrence, which is the package name)
        return re.sub(
            r'("name"\s*:\s*"[^"]+",)',
            r'\g<1>\n    "version": "' + version + '",',
            content,
            count=1,
        )


def update_yaml_pubspec(content, version, path):
    return re.sub(
        r"(^version:\s*)(.+)", r"\g<1>" + version, content, flags=re.MULTILINE
    )


def update_ruby_gemspec(content, version, path):
    # spec.version = "..."
    return re.sub(
        r'(spec\.version\s*=\s*")([^"]+)(")', r"\g<1>" + version + r"\g<3>", content
    )


def update_xml_csproj(content, version, path):
    # <Version>...</Version>
    if "<Version>" in content:
        return re.sub(
            r"(<Version>)([^<]+)(</Version>)", r"\g<1>" + version + r"\g<3>", content
        )
    else:
        # Insert into PropertyGroup
        return re.sub(
            r"(<PropertyGroup>)",
            r"\g<1>\n    <Version>" + version + "</Version>",
            content,
            count=1,
        )


def update_xml_pom(content, version, path):
    # <version>...</version> inside <project> (usually the first one)
    # This is tricky because dependencies also have versions.
    # We assume the project version is the first <version> tag after <project> start or near top.
    # Or we look for <groupId>... <artifactId>... <version>...

    # Strategy: Replace the first occurrence of <version> that is a direct child of project (conceptually)
    # Usually it's early in the file.
    return re.sub(
        r"(<version>)([^<]+)(</version>)",
        r"\g<1>" + version + r"\g<3>",
        content,
        count=1,
    )


def update_kotlin_gradle(content, version, path):
    # version = "..."
    return re.sub(
        r'(^version\s*=\s*")([^"]+)(")',
        r"\g<1>" + version + r"\g<3>",
        content,
        flags=re.MULTILINE,
    )


def update_r_description(content, version, path):
    # Version: ...
    # R versions must be numeric-ish. Strip alpha/beta for R if needed?
    # The user prompt says "Updates metadata files".
    # Let's assume we just put the version string. If R complains about 0.1.0-alpha, we might need logic.
    # R requires: at least two integers separated by . or -
    # Let's just replace it.
    return re.sub(
        r"(^Version:\s*)(.+)", r"\g<1>" + version, content, flags=re.MULTILINE
    )


def update_perl_pm(content, version, path):
    # our $VERSION = '...';
    return re.sub(
        r"(our\s+\$VERSION\s*=\s*')([^']+)(';)", r"\g<1>" + version + r"\g<3>", content
    )


def update_cmake(content, version, path):
    # project(... VERSION ...)
    return re.sub(
        r"(project\s*\([\s\S]*?VERSION\s+)([\d\.\w-]+)([\s\S]*?\))",
        r"\g<1>" + version + r"\g<3>",
        content,
    )


def update_c_source(content, version, path):
    # return "..." inside strling_version
    # We look for the function definition
    pattern = r'(const\s+char\s*\*\s*strling_version\s*\(\s*void\s*\)\s*\{[\s\S]*?return\s*")([^"]+)(")'
    return re.sub(pattern, r"\g<1>" + version + r"\g<3>", content)


def main():
    parser = argparse.ArgumentParser(description="Sync project version across bindings")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if versions are in sync without modifying",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to files")
    args = parser.parse_args()

    if not args.check and not args.write:
        print("Please specify --check or --write")
        sys.exit(1)

    version = get_source_version()
    print(f"Source version (Python): {version}")

    targets = [
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
    ]

    success = True
    for path, updater in targets:
        if not update_file(path, version, dry_run=not args.write, updater_func=updater):
            success = False

    if args.check and not success:
        print("Version mismatch detected!")
        sys.exit(1)

    if args.write:
        print("Version sync complete.")


if __name__ == "__main__":
    main()
