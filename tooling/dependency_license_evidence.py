"""Generate hash-bound license evidence when registry metadata is incomplete."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
DART_LOCK = ROOT / "bindings/dart/pubspec.lock"
PYTHON_LOCK = ROOT / "bindings/python/requirements.lock.txt"
LUA_LOCK = ROOT / "bindings/lua/luarocks.lock"
CPAN_LOCK = ROOT / "bindings/perl/cpanfile.snapshot"
OUTPUT = ROOT / "governance/dependency-license-evidence.json"
USER_AGENT = "strling-license-evidence/1"


class LicenseEvidenceError(RuntimeError):
    """License evidence could not be authenticated or classified."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: Mapping[str, Any]) -> str:
    normalized = {key: item for key, item in value.items() if key != "fingerprint"}
    return f"sha256:{hashlib.sha256(_canonical(normalized)).hexdigest()}"


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise LicenseEvidenceError(f"cannot retrieve {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LicenseEvidenceError(f"{url} did not return a JSON object")
    return payload


def _get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise LicenseEvidenceError(f"cannot retrieve {url}: {exc}") from exc


def _license_expression(text: str) -> str:
    normalized = " ".join(text.replace("\r", "\n").split()).lower()
    if (
        "redistribution and use in source and binary forms" in normalized
        and "neither the name" in normalized
        and "this software is provided" in normalized
    ):
        return "BSD-3-Clause"
    if (
        "redistribution and use in source and binary forms" in normalized
        and "this software is provided" in normalized
    ):
        return "BSD-2-Clause"
    if (
        "permission is hereby granted, free of charge" in normalized
        and 'the software is provided "as is"' in normalized
    ):
        return "MIT"
    if "apache license version 2.0, january 2004" in normalized:
        return "Apache-2.0"
    if (
        "same terms as the perl 5 programming language system itself" in normalized
        and "gnu general public license" in normalized
        and "either version 1, or (at your option) any later version" in normalized
        and 'the "artistic license"' in normalized
    ):
        return "Artistic-1.0-Perl OR GPL-1.0-or-later"
    raise LicenseEvidenceError("license text does not match a governed classifier")


def _archive_license(archive: bytes) -> tuple[str, str, str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            candidates = []
            for member in bundle.getmembers():
                path = PurePosixPath(member.name)
                if (
                    member.isfile()
                    and not path.is_absolute()
                    and ".." not in path.parts
                    and path.name.upper() in {"LICENSE", "LICENSE.TXT", "LICENSE.MD"}
                ):
                    candidates.append(member)
            candidates.sort(
                key=lambda item: (len(PurePosixPath(item.name).parts), item.name)
            )
            if not candidates:
                raise LicenseEvidenceError(
                    "package archive has no top-level license file"
                )
            selected = candidates[0]
            extracted = bundle.extractfile(selected)
            if extracted is None:
                raise LicenseEvidenceError("package license file cannot be read")
            raw = extracted.read(1_048_577)
    except (tarfile.TarError, OSError) as exc:
        raise LicenseEvidenceError(f"cannot inspect package archive: {exc}") from exc
    if len(raw) > 1_048_576:
        raise LicenseEvidenceError("package license file exceeds the evidence limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LicenseEvidenceError("package license file is not UTF-8") from exc
    return selected.name, hashlib.sha256(raw).hexdigest(), _license_expression(text)


def _archive_json(archive: bytes, filename: str) -> dict[str, Any]:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            candidates = [
                member
                for member in bundle.getmembers()
                if member.isfile()
                and not PurePosixPath(member.name).is_absolute()
                and ".." not in PurePosixPath(member.name).parts
                and PurePosixPath(member.name).name == filename
                and len(PurePosixPath(member.name).parts) == 2
            ]
            if len(candidates) != 1:
                raise LicenseEvidenceError(
                    f"package archive does not contain one top-level {filename}"
                )
            extracted = bundle.extractfile(candidates[0])
            if extracted is None:
                raise LicenseEvidenceError(f"package {filename} cannot be read")
            payload = json.load(extracted)
    except (tarfile.TarError, OSError, json.JSONDecodeError) as exc:
        raise LicenseEvidenceError(f"cannot inspect package {filename}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LicenseEvidenceError(f"package {filename} is not a JSON object")
    return payload


def _lua_entries() -> list[dict[str, str]]:
    try:
        lock_text = LUA_LOCK.read_text(encoding="utf-8")
    except OSError as exc:
        raise LicenseEvidenceError(f"cannot read {LUA_LOCK}: {exc}") from exc
    locked = re.findall(
        r'^\s*\["([A-Za-z0-9._-]+)"\]\s*=\s*"([0-9][A-Za-z0-9._-]*)"\s*,?\s*$',
        lock_text,
        re.MULTILINE,
    )
    if locked != [("lua-cjson", "2.1.0.10-1")]:
        raise LicenseEvidenceError(
            "LuaRocks lock does not contain the exact governed graph"
        )
    package_name, version = locked[0]
    rockspec_url = (
        f"https://luarocks.org/manifests/openresty/{package_name}-{version}.rockspec"
    )
    rockspec = _get_bytes(rockspec_url)
    try:
        rockspec_text = rockspec.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LicenseEvidenceError("LuaRocks rockspec is not UTF-8") from exc
    if (
        f'version = "{version}"' not in rockspec_text
        or 'url = "git+https://github.com/openresty/lua-cjson"' not in rockspec_text
        or 'tag = "2.1.0.10"' not in rockspec_text
        or 'license = "MIT"' not in rockspec_text
        or '"lua >= 5.1"' not in rockspec_text
    ):
        raise LicenseEvidenceError(
            "LuaRocks rockspec identity or dependency graph drifted"
        )
    tag_url = "https://api.github.com/repos/openresty/lua-cjson/git/ref/tags/2.1.0.10"
    tag = _get_json(tag_url)
    tag_object = tag.get("object")
    if (
        tag.get("ref") != "refs/tags/2.1.0.10"
        or not isinstance(tag_object, dict)
        or tag_object.get("type") != "commit"
        or not isinstance(tag_object.get("sha"), str)
        or re.fullmatch(r"[0-9a-f]{40}", str(tag_object["sha"])) is None
    ):
        raise LicenseEvidenceError("lua-cjson tag is not an exact commit reference")
    source_commit = str(tag_object["sha"])
    archive_url = (
        f"https://github.com/openresty/lua-cjson/archive/{source_commit}.tar.gz"
    )
    archive = _get_bytes(archive_url)
    license_path, license_sha256, expression = _archive_license(archive)
    if expression != "MIT":
        raise LicenseEvidenceError("lua-cjson source license is not MIT")
    return [
        {
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "archive_url": archive_url,
            "ecosystem": "luarocks",
            "license": expression,
            "license_path": license_path,
            "license_sha256": license_sha256,
            "package": package_name,
            "registry_metadata_url": rockspec_url,
            "rockspec_sha256": hashlib.sha256(rockspec).hexdigest(),
            "source_commit": source_commit,
            "version": version,
        }
    ]


def _cpan_entries() -> list[dict[str, str]]:
    try:
        snapshot = CPAN_LOCK.read_text(encoding="utf-8")
    except OSError as exc:
        raise LicenseEvidenceError(f"cannot read {CPAN_LOCK}: {exc}") from exc
    if not snapshot.startswith(
        "# carton snapshot format: version 1.0\nDISTRIBUTIONS\n"
    ):
        raise LicenseEvidenceError("Carton snapshot format is not version 1.0")
    records = re.findall(
        r"(?m)^  ([A-Za-z0-9._-]+)\n    pathname: ([A-Z0-9]/[A-Z0-9]{2}/[A-Z0-9._-]+/[A-Za-z0-9._-]+\.tar\.gz)$",
        snapshot,
    )
    expected = {
        "Capture-Tiny-0.50": "D/DA/DAGOLDEN/Capture-Tiny-0.50.tar.gz",
        "FFI-CheckLib-0.31": "P/PL/PLICEASE/FFI-CheckLib-0.31.tar.gz",
        "FFI-Platypus-2.11": "P/PL/PLICEASE/FFI-Platypus-2.11.tar.gz",
        "File-Which-1.27": "P/PL/PLICEASE/File-Which-1.27.tar.gz",
    }
    if dict(records) != expected:
        raise LicenseEvidenceError("Carton snapshot distribution graph drifted")
    entries: list[dict[str, str]] = []
    license_names = {
        "apache_2_0": "Apache-2.0",
        "perl_5": "Artistic-1.0-Perl OR GPL-1.0-or-later",
    }
    for distribution_identity, pathname in sorted(records):
        matched = re.fullmatch(r"(.+)-([0-9][A-Za-z0-9._]*)", distribution_identity)
        if matched is None:
            raise LicenseEvidenceError(
                f"cannot parse CPAN identity {distribution_identity}"
            )
        package_name, version = matched.groups()
        archive_url = f"https://cpan.metacpan.org/authors/id/{pathname}"
        archive = _get_bytes(archive_url)
        metadata = _archive_json(archive, "META.json")
        raw_licenses = metadata.get("license")
        if (
            metadata.get("name") != package_name
            or str(metadata.get("version")) != version
            or not isinstance(raw_licenses, list)
            or len(raw_licenses) != 1
            or raw_licenses[0] not in license_names
        ):
            raise LicenseEvidenceError(
                f"CPAN archive metadata does not match {package_name}@{version}"
            )
        license_path, license_sha256, expression = _archive_license(archive)
        if expression != license_names[raw_licenses[0]]:
            raise LicenseEvidenceError(
                f"CPAN metadata and license text disagree for {package_name}@{version}"
            )
        entries.append(
            {
                "archive_sha256": hashlib.sha256(archive).hexdigest(),
                "archive_url": archive_url,
                "ecosystem": "cpan",
                "license": expression,
                "license_path": license_path,
                "license_sha256": license_sha256,
                "package": package_name,
                "registry_metadata_url": f"{archive_url}#META.json",
                "version": version,
            }
        )
    return entries


def _dart_entries() -> list[dict[str, str]]:
    try:
        lock = yaml.safe_load(DART_LOCK.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise LicenseEvidenceError(f"cannot parse {DART_LOCK}: {exc}") from exc
    packages = lock.get("packages") if isinstance(lock, dict) else None
    if not isinstance(packages, dict) or not packages:
        raise LicenseEvidenceError("Dart lock omitted its package inventory")
    entries: list[dict[str, str]] = []
    for package_name, package in sorted(packages.items()):
        if not isinstance(package_name, str) or not isinstance(package, dict):
            raise LicenseEvidenceError("Dart lock contains a malformed package")
        if package.get("source") != "hosted":
            raise LicenseEvidenceError(
                f"Dart package {package_name} is not registry-hosted"
            )
        version = package.get("version")
        description = package.get("description")
        if not isinstance(version, str) or not isinstance(description, dict):
            raise LicenseEvidenceError(f"Dart package {package_name} lacks identity")
        expected_sha256 = description.get("sha256")
        registry = description.get("url")
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or registry != "https://pub.dev"
        ):
            raise LicenseEvidenceError(
                f"Dart package {package_name} lacks pub.dev integrity"
            )
        encoded_name = urllib.parse.quote(package_name, safe="")
        encoded_version = urllib.parse.quote(version, safe="")
        api_url = (
            f"https://pub.dev/api/packages/{encoded_name}/versions/{encoded_version}"
        )
        metadata = _get_json(api_url)
        archive_url = metadata.get("archive_url")
        archive_sha256 = metadata.get("archive_sha256")
        pubspec = metadata.get("pubspec")
        if (
            metadata.get("version") != version
            or not isinstance(pubspec, dict)
            or pubspec.get("name") != package_name
            or archive_sha256 != expected_sha256
            or not isinstance(archive_url, str)
            or not archive_url.startswith("https://pub.dev/api/archives/")
        ):
            raise LicenseEvidenceError(
                f"pub.dev metadata does not match {package_name}@{version}"
            )
        archive = _get_bytes(archive_url)
        actual_sha256 = hashlib.sha256(archive).hexdigest()
        if actual_sha256 != expected_sha256:
            raise LicenseEvidenceError(
                f"pub.dev archive hash mismatch for {package_name}@{version}"
            )
        license_path, license_sha256, expression = _archive_license(archive)
        entries.append(
            {
                "archive_sha256": actual_sha256,
                "archive_url": archive_url,
                "ecosystem": "dart-pub",
                "license": expression,
                "license_path": license_path,
                "license_sha256": license_sha256,
                "package": package_name,
                "registry_metadata_url": api_url,
                "version": version,
            }
        )
    return entries


def _python_lock_records() -> dict[tuple[str, str], set[str]]:
    try:
        lines = PYTHON_LOCK.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise LicenseEvidenceError(f"cannot read {PYTHON_LOCK}: {exc}") from exc
    records: dict[tuple[str, str], set[str]] = {}
    current: tuple[str, str] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "--hash=")):
            requirement = stripped.removesuffix("\\").strip()
            if "==" in requirement:
                name, version = requirement.split("==", 1)
                if name and version:
                    current = (name.lower().replace("_", "-"), version)
                    records[current] = set()
                    continue
            current = None
        if current is not None and stripped.startswith("--hash=sha256:"):
            digest = stripped.removesuffix("\\").split(":", 1)[1].strip()
            if len(digest) == 64:
                records[current].add(digest)
    return records


def _python_entries() -> list[dict[str, str]]:
    records = _python_lock_records()
    entries: list[dict[str, str]] = []
    for package_name in ("colorama",):
        identities = [identity for identity in records if identity[0] == package_name]
        if len(identities) != 1:
            raise LicenseEvidenceError(
                f"Python lock does not contain one exact {package_name} identity"
            )
        identity = identities[0]
        _, version = identity
        api_url = f"https://pypi.org/pypi/{package_name}/{urllib.parse.quote(version, safe='')}/json"
        metadata = _get_json(api_url)
        info = metadata.get("info")
        files = metadata.get("urls")
        if (
            not isinstance(info, dict)
            or info.get("name", "").lower() != package_name
            or info.get("version") != version
            or not isinstance(files, list)
        ):
            raise LicenseEvidenceError(
                f"PyPI metadata does not match {package_name}@{version}"
            )
        candidates = []
        for file in files:
            digests = file.get("digests") if isinstance(file, dict) else None
            digest = digests.get("sha256") if isinstance(digests, dict) else None
            url = file.get("url") if isinstance(file, dict) else None
            if (
                file.get("packagetype") == "sdist"
                and isinstance(digest, str)
                and digest in records[identity]
                and isinstance(url, str)
                and url.startswith("https://files.pythonhosted.org/")
            ):
                candidates.append((url, digest))
        if len(candidates) != 1:
            raise LicenseEvidenceError(
                f"PyPI has no unique hash-pinned sdist for {package_name}@{version}"
            )
        archive_url, expected_sha256 = candidates[0]
        archive = _get_bytes(archive_url)
        actual_sha256 = hashlib.sha256(archive).hexdigest()
        if actual_sha256 != expected_sha256:
            raise LicenseEvidenceError(
                f"PyPI archive hash mismatch for {package_name}@{version}"
            )
        license_path, license_sha256, expression = _archive_license(archive)
        entries.append(
            {
                "archive_sha256": actual_sha256,
                "archive_url": archive_url,
                "ecosystem": "python",
                "license": expression,
                "license_path": license_path,
                "license_sha256": license_sha256,
                "package": package_name,
                "registry_metadata_url": api_url,
                "version": version,
            }
        )
    return entries


def build_evidence() -> dict[str, Any]:
    value: dict[str, Any] = {
        "document_kind": "dependency-license-evidence",
        "schema_version": "1.0.0",
        "sources": [
            "bindings/dart/pubspec.lock",
            "bindings/lua/luarocks.lock",
            "bindings/perl/cpanfile.snapshot",
            "bindings/python/requirements.lock.txt",
        ],
        "entries": sorted(
            [*_dart_entries(), *_lua_entries(), *_cpan_entries(), *_python_entries()],
            key=lambda item: (item["ecosystem"], item["package"], item["version"]),
        ),
    }
    value["fingerprint"] = _fingerprint(value)
    return value


def synchronize(*, write: bool) -> dict[str, object]:
    expected = build_evidence()
    actual = None
    if OUTPUT.is_file():
        try:
            actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            actual = None
    matches = actual == expected
    if write and not matches:
        OUTPUT.write_text(
            json.dumps(expected, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        matches = True
    return {
        "status": "passed" if matches else "failed",
        "entries": len(expected["entries"]),
        "fingerprint": expected["fingerprint"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = synchronize(write=args.write)
    except LicenseEvidenceError as exc:
        result = {"status": "failed", "error": str(exc)}
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
