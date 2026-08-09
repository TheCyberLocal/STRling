#!/usr/bin/env python3
"""Validate tracked repository artifacts against the STRling hygiene policy."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "governance" / "repository-hygiene.json"
BINARY_SIGNATURES = (
    b"\x7fELF",
    b"PK\x03\x04",
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"%PDF-",
    b"\x1f\x8b",
)


class HygieneConfigurationError(ValueError):
    """Raised when the hygiene policy or tracked inventory is invalid."""


@dataclass(frozen=True)
class Entry:
    path: str
    mode: str


@dataclass(frozen=True, order=True)
class Finding:
    rule: str
    path: str
    message: str


def matches(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise HygieneConfigurationError(f"{field} must be a list of strings")
    return list(value)


def load_policy(
    path: Path = POLICY_PATH,
    root: Path = ROOT,
) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise HygieneConfigurationError(f"cannot read hygiene policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise HygieneConfigurationError("unsupported hygiene policy schema")

    required = (
        "prohibited_patterns",
        "allowed_intentional_artifacts",
        "generated_paths",
        "binary_allowlist",
        "text_policy",
        "private_key_markers",
        "credential_marker_exclusions",
        "executable_allowlist",
        "case_collision_waivers",
    )
    missing = [field for field in required if field not in policy]
    if missing:
        raise HygieneConfigurationError(
            f"hygiene policy is missing required field '{missing[0]}'"
        )
    if policy.get("scope") != "tracked_files":
        raise HygieneConfigurationError("hygiene scope must be tracked_files")
    if not isinstance(policy.get("maximum_file_size_bytes"), int):
        raise HygieneConfigurationError("maximum_file_size_bytes must be an integer")

    prohibited = policy["prohibited_patterns"]
    if not isinstance(prohibited, list):
        raise HygieneConfigurationError("prohibited_patterns must be a list")
    rule_ids: set[str] = set()
    for raw_rule in prohibited:
        if not isinstance(raw_rule, dict) or not isinstance(raw_rule.get("id"), str):
            raise HygieneConfigurationError("each prohibited rule must have an id")
        rule_id = raw_rule["id"]
        if rule_id in rule_ids:
            raise HygieneConfigurationError(f"duplicate prohibited rule '{rule_id}'")
        rule_ids.add(rule_id)
        _string_list(raw_rule.get("patterns"), f"{rule_id}.patterns")

    allowed = policy["allowed_intentional_artifacts"]
    if not isinstance(allowed, list):
        raise HygieneConfigurationError("allowed_intentional_artifacts must be a list")
    for raw_allowed in allowed:
        if not isinstance(raw_allowed, dict):
            raise HygieneConfigurationError(
                "intentional artifact entries must be objects"
            )
        allowed_path = raw_allowed.get("path")
        allowed_rule = raw_allowed.get("rule")
        rationale = raw_allowed.get("rationale")
        if not all(
            isinstance(value, str) and value
            for value in (allowed_path, allowed_rule, rationale)
        ):
            raise HygieneConfigurationError(
                "intentional artifact entries require path, rule, and rationale"
            )
        if allowed_rule not in rule_ids:
            raise HygieneConfigurationError(
                f"intentional artifact references unknown rule '{allowed_rule}'"
            )

    binaries = policy["binary_allowlist"]
    if not isinstance(binaries, list):
        raise HygieneConfigurationError("binary_allowlist must be a list")
    binary_paths: set[str] = set()
    for raw_binary in binaries:
        if not isinstance(raw_binary, dict):
            raise HygieneConfigurationError("binary allowlist entries must be objects")
        binary_path = raw_binary.get("path")
        digest = raw_binary.get("sha256")
        rationale = raw_binary.get("rationale")
        if not isinstance(binary_path, str) or not binary_path:
            raise HygieneConfigurationError("binary allowlist path must be a string")
        if binary_path in binary_paths:
            raise HygieneConfigurationError(
                f"duplicate binary allowlist path '{binary_path}'"
            )
        binary_paths.add(binary_path)
        if not isinstance(digest, str) or len(digest) != 64:
            raise HygieneConfigurationError(
                f"binary allowlist path '{binary_path}' needs a SHA-256 digest"
            )
        if not isinstance(rationale, str) or not rationale:
            raise HygieneConfigurationError(
                f"binary allowlist path '{binary_path}' needs a rationale"
            )

    text_policy = policy["text_policy"]
    if not isinstance(text_policy, dict):
        raise HygieneConfigurationError("text_policy must be an object")
    for field in (
        "extensions",
        "special_files",
        "excluded_paths",
        "crlf_paths",
    ):
        _string_list(text_policy.get(field), f"text_policy.{field}")

    _string_list(policy["private_key_markers"], "private_key_markers")
    credential_exclusions = policy["credential_marker_exclusions"]
    if not isinstance(credential_exclusions, list):
        raise HygieneConfigurationError("credential_marker_exclusions must be a list")
    for exclusion in credential_exclusions:
        if not isinstance(exclusion, dict) or not all(
            isinstance(exclusion.get(field), str) and exclusion.get(field)
            for field in ("path", "rationale")
        ):
            raise HygieneConfigurationError(
                "credential marker exclusions require path and rationale"
            )
    _string_list(policy["executable_allowlist"], "executable_allowlist")

    waivers = policy["case_collision_waivers"]
    if not isinstance(waivers, list):
        raise HygieneConfigurationError("case_collision_waivers must be a list")
    for raw_waiver in waivers:
        if not isinstance(raw_waiver, dict):
            raise HygieneConfigurationError("case collision waivers must be objects")
        waiver = raw_waiver.get("waiver")
        paths = _string_list(raw_waiver.get("paths"), "case collision waiver paths")
        if not isinstance(waiver, str) or not waiver or len(paths) < 2:
            raise HygieneConfigurationError(
                "case collision waivers require an id and at least two paths"
            )
        waiver_file = root / "governance" / "waivers" / f"{waiver}.yaml"
        if not waiver_file.is_file():
            raise HygieneConfigurationError(
                f"case collision waiver '{waiver}' has no governed waiver file"
            )
    return policy


def tracked_entries(root: Path = ROOT) -> list[Entry]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--stage", "-z"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise HygieneConfigurationError(
            f"cannot inventory tracked files: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise HygieneConfigurationError(f"git tracked-file inventory failed: {detail}")

    entries: list[Entry] = []
    for record in completed.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, _object_id, stage = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise HygieneConfigurationError(
                "git returned an invalid tracked-file record"
            ) from exc
        if stage != "0":
            raise HygieneConfigurationError(
                f"tracked path '{path}' has an unresolved index stage"
            )
        entries.append(Entry(path, mode))
    return sorted(entries, key=lambda entry: entry.path)


def _is_binary(data: bytes) -> bool:
    if any(data.startswith(signature) for signature in BINARY_SIGNATURES):
        return True
    if b"\0" in data[:8192]:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _trailing_whitespace_line(data: bytes) -> int | None:
    for line_number, line in enumerate(data.splitlines(keepends=True), start=1):
        if line.endswith(b"\r\n"):
            content = line[:-2]
        elif line.endswith((b"\n", b"\r")):
            content = line[:-1]
        else:
            content = line
        if content.endswith((b" ", b"\t")):
            return line_number
    return None


def _text_governed(path: str, text_policy: Mapping[str, object]) -> bool:
    excluded = _string_list(text_policy["excluded_paths"], "text excluded paths")
    if matches(path, excluded):
        return False
    extensions = set(_string_list(text_policy["extensions"], "text extensions"))
    special_files = set(_string_list(text_policy["special_files"], "special files"))
    return Path(path).suffix.lower() in extensions or Path(path).name in special_files


def scan(
    policy: Mapping[str, object],
    entries: Sequence[Entry],
    root: Path = ROOT,
) -> list[Finding]:
    findings: list[Finding] = []
    inventory = {entry.path: entry for entry in entries}
    allowed_rules = {
        (str(item["path"]), str(item["rule"]))
        for item in policy["allowed_intentional_artifacts"]  # type: ignore[index]
    }
    binary_allowlist = {
        str(item["path"]): item
        for item in policy["binary_allowlist"]  # type: ignore[index]
    }
    binary_paths = set(binary_allowlist)
    maximum_size = int(policy["maximum_file_size_bytes"])
    text_policy = policy["text_policy"]
    assert isinstance(text_policy, dict)
    executable_allowlist = set(
        _string_list(policy["executable_allowlist"], "executable allowlist")
    )
    marker_exclusions = {
        str(item["path"])
        for item in policy["credential_marker_exclusions"]  # type: ignore[index]
    }
    markers = _string_list(policy["private_key_markers"], "private key markers")

    prohibited = policy["prohibited_patterns"]
    assert isinstance(prohibited, list)
    for entry in entries:
        path = entry.path
        file_path = root / path
        for raw_rule in prohibited:
            assert isinstance(raw_rule, dict)
            rule_id = str(raw_rule["id"])
            patterns = _string_list(raw_rule["patterns"], f"{rule_id}.patterns")
            if (
                matches(path, patterns)
                and (path, rule_id) not in allowed_rules
                and path not in binary_paths
            ):
                findings.append(
                    Finding(rule_id, path, "tracked path matches a prohibited pattern")
                )

        if not file_path.is_file():
            findings.append(
                Finding(
                    "tracked-file-present",
                    path,
                    "tracked path is missing or not a regular file",
                )
            )
            continue
        data = file_path.read_bytes()
        if len(data) > maximum_size:
            findings.append(
                Finding(
                    "maximum-file-size",
                    path,
                    f"{len(data)} bytes exceeds the {maximum_size}-byte limit",
                )
            )

        binary = _is_binary(data)
        allowed_binary = binary_allowlist.get(path)
        if allowed_binary is not None:
            digest = hashlib.sha256(data).hexdigest()
            if digest != allowed_binary["sha256"]:
                findings.append(
                    Finding(
                        "binary-integrity",
                        path,
                        "SHA-256 does not match the exact binary allowlist",
                    )
                )
        elif binary:
            findings.append(
                Finding(
                    "unexpected-binary",
                    path,
                    "binary content is not present in the exact binary allowlist",
                )
            )

        if not binary and path not in marker_exclusions:
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                decoded = ""
            for marker in markers:
                if marker in decoded:
                    findings.append(
                        Finding(
                            "private-key-marker",
                            path,
                            f"tracked text contains credential marker '{marker}'",
                        )
                    )
                    break

        if not binary and _text_governed(path, text_policy):
            if text_policy.get("encoding") == "utf-8":
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    findings.append(
                        Finding(
                            "text-encoding", path, "governed text is not valid UTF-8"
                        )
                    )
                    continue

            crlf_paths = _string_list(text_policy["crlf_paths"], "CRLF paths")
            bare_carriage_return = b"\r" in data.replace(b"\r\n", b"")
            if matches(path, crlf_paths):
                if b"\n" in data.replace(b"\r\n", b"") or bare_carriage_return:
                    findings.append(
                        Finding(
                            "line-endings",
                            path,
                            "governed text must use CRLF line endings",
                        )
                    )
            elif b"\r\n" in data or bare_carriage_return:
                findings.append(
                    Finding(
                        "line-endings", path, "governed text must use LF line endings"
                    )
                )

            trailing_line = _trailing_whitespace_line(data)
            if text_policy.get("forbid_trailing_whitespace") and trailing_line:
                findings.append(
                    Finding(
                        "trailing-whitespace",
                        path,
                        f"trailing whitespace begins at line {trailing_line}",
                    )
                )
            if text_policy.get("require_final_newline") and data:
                expected = b"\r\n" if matches(path, crlf_paths) else b"\n"
                if not data.endswith(expected):
                    findings.append(
                        Finding(
                            "final-newline",
                            path,
                            "governed text lacks its final newline",
                        )
                    )

        executable = entry.mode == "100755"
        expected_executable = path in executable_allowlist
        if executable and not expected_executable:
            findings.append(
                Finding(
                    "executable-mode", path, "tracked executable bit is not allowlisted"
                )
            )
        elif expected_executable and not executable:
            findings.append(
                Finding(
                    "executable-mode", path, "allowlisted executable lacks mode 100755"
                )
            )

    for expected_path in sorted(binary_paths | executable_allowlist):
        if expected_path not in inventory:
            findings.append(
                Finding(
                    "allowlist-target",
                    expected_path,
                    "policy allowlist references a path that is not tracked",
                )
            )

    waived_collisions = {
        frozenset(_string_list(item["paths"], "case waiver paths"))
        for item in policy["case_collision_waivers"]  # type: ignore[index]
    }
    by_casefold: dict[str, set[str]] = {}
    for path in inventory:
        by_casefold.setdefault(path.casefold(), set()).add(path)
    for paths in by_casefold.values():
        if len(paths) > 1 and frozenset(paths) not in waived_collisions:
            joined = ", ".join(sorted(paths))
            findings.append(
                Finding(
                    "case-collision", joined, "tracked paths collide case-insensitively"
                )
            )

    return sorted(set(findings))


def normalize_text(
    policy: Mapping[str, object],
    entries: Sequence[Entry],
    root: Path = ROOT,
) -> list[str]:
    """Mechanically normalize governed text without touching serializer-owned paths."""

    text_policy = policy["text_policy"]
    assert isinstance(text_policy, dict)
    crlf_paths = _string_list(text_policy["crlf_paths"], "CRLF paths")
    changed: list[str] = []
    for entry in entries:
        if not _text_governed(entry.path, text_policy):
            continue
        file_path = root / entry.path
        if not file_path.is_file():
            continue
        data = file_path.read_bytes()
        if _is_binary(data):
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        if text_policy.get("forbid_trailing_whitespace"):
            normalized = "\n".join(
                line.rstrip(" \t") for line in normalized.split("\n")
            )
        if text_policy.get("require_final_newline") and normalized:
            if not normalized.endswith("\n"):
                normalized += "\n"
        if matches(entry.path, crlf_paths):
            normalized = normalized.replace("\n", "\r\n")
        encoded = normalized.encode("utf-8")
        if encoded != data:
            file_path.write_bytes(encoded)
            changed.append(entry.path)
    return changed


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit one structured result document",
    )
    parser.add_argument(
        "--normalize-text",
        action="store_true",
        help="mechanically normalize governed text before validation",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        policy = load_policy()
        entries = tracked_entries()
        normalized_paths = (
            normalize_text(policy, entries) if args.normalize_text else []
        )
        findings = scan(policy, entries)
    except HygieneConfigurationError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "configuration_error",
                        "exit_code": 2,
                        "error": str(exc),
                        "findings": [],
                    },
                    sort_keys=True,
                )
            )
        else:
            print(
                f"HYGIENE_RESULT status=configuration_error error={exc}",
                file=sys.stderr,
            )
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "status": "failed" if findings else "passed",
                    "exit_code": 1 if findings else 0,
                    "tracked_files": len(entries),
                    "findings": [asdict(finding) for finding in findings],
                    "normalized_files": normalized_paths,
                },
                sort_keys=True,
            )
        )
    else:
        if normalized_paths:
            print(f"HYGIENE_NORMALIZE status=passed files={len(normalized_paths)}")
        for finding in findings:
            print(
                "HYGIENE_RESULT "
                f"status=failed rule={finding.rule} path={finding.path} "
                f"message={finding.message}"
            )
        print(
            "HYGIENE_SUMMARY "
            f"status={'failed' if findings else 'passed'} "
            f"tracked_files={len(entries)} findings={len(findings)}"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
