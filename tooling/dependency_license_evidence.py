"""Generate hash-bound license evidence when registry metadata is incomplete."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
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
            "bindings/python/requirements.lock.txt",
        ],
        "entries": sorted(
            [*_dart_entries(), *_python_entries()],
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
