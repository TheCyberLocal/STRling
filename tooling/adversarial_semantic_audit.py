#!/usr/bin/env python3
"""Empirical adversarial evidence through the canonical CLI and governed engines.

No observation in this module defines language meaning. Strict execution is a
deliberately separate, non-mandatory operation until equivalence is corrected.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import tempfile
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling import shared_cross_engine_corpus as shared
from tooling.contract_validation import ContractSuite, load_json
from tooling.ecmascript_runtime_certification import run_harness as node_harness
from tooling.python_re_runtime_certification import run_harness as python_harness
from tooling.pcre2_feature_probe import (
    Engine,
    MatchLimits,
    file_digest,
    profile_configuration,
)

ROOT = shared.ROOT
DIRECTORY = ROOT / "tests/conformance/adversarial/1.0"
CORPUS = DIRECTORY / "corpus.json"
EVIDENCE = DIRECTORY / "evidence.json"
DIGEST = shared.canonical_digest
PROFILES = shared.EXPECTED_PROFILE_IDS
LINES = {
    "LF": "\n",
    "VT": "\v",
    "FF": "\f",
    "CR": "\r",
    "CRLF": "\r\n",
    "NEL": "\x85",
    "LS": "\u2028",
    "PS": "\u2029",
}
EDGE_POINTS = {0x130, 0x131, 0x17F, 0x212A, 0x3C2}


@lru_cache(maxsize=1)
def contracts() -> ContractSuite:
    return ContractSuite()


def validate_corpus(corpus: dict | None = None) -> dict:
    value = load_json(CORPUS) if corpus is None else corpus
    schema = load_json(DIRECTORY / "corpus.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    subjects = {s["id"]: s for s in value["subjects"]}
    cases = {c["id"]: c for c in value["cases"]}
    if len(subjects) != len(value["subjects"]) or len(cases) != len(value["cases"]):
        raise ValueError("duplicate corpus identity")
    used = set()
    for case in cases.values():
        if set(case["subjects"]) - subjects.keys():
            raise ValueError("unknown subject")
        used.update(case["subjects"])
        for tag in case["tags"]:
            if not tag.startswith("line-matrix:"):
                continue
            context = tag.split(":")[1]
            for name, terminator in LINES.items():
                expected = {
                    "bare": terminator,
                    "start": "x" + terminator + "a",
                    "end": "a" + terminator + "x",
                    "final": "a" + terminator,
                }[context]
                if not any(
                    subjects[s]["value"] == expected
                    and "line:" + name in subjects[s]["tags"]
                    for s in case["subjects"]
                ):
                    raise ValueError(
                        f"{case['id']}: missing real {name}/{context} subject"
                    )
    if used != subjects.keys():
        raise ValueError("unexecuted subjects cannot satisfy coverage")
    mandatory = {
        "wildcard-excluding-lines",
        "unicode-word-class",
        "line-start",
        "line-end",
        "before-final-line-terminator",
    }
    if mandatory - cases.keys():
        raise ValueError("missing semantic case")
    for case_id, context in (
        ("wildcard-excluding-lines", "bare"),
        ("line-start", "start"),
        ("line-end", "end"),
        ("before-final-line-terminator", "final"),
    ):
        if "line-matrix:" + context not in cases[case_id]["tags"]:
            raise ValueError("missing line coverage obligation")
    for case_id in ("unicode-word-class", "word-boundary"):
        actual = [subjects[s] for s in cases[case_id]["subjects"]]
        import unicodedata

        for category in ("Mn", "Pc", "Lo", "Nl", "Nd", "No"):
            if not any(
                unicodedata.category(s["value"]) == category
                and "category:" + category in s["tags"]
                for s in actual
            ):
                raise ValueError("missing Unicode category probe")
    folding = [c for c in cases.values() if "case-fold" in c["tags"]]
    for point in EDGE_POINTS:
        if not any(chr(point) in c["source"] for c in folding) or not any(
            subjects[s]["value"] == chr(point) for c in folding for s in c["subjects"]
        ):
            raise ValueError("missing bidirectional case-fold edge")
    for tag in (
        "capture:nonparticipating",
        "capture:reset-in-repetition",
        "capture:negative-lookaround",
        "capture:alternation",
    ):
        if not any(tag in c["tags"] for c in cases.values()):
            raise ValueError("missing capture algorithm probe")
    for case_id in (
        "wildcard-excluding-lines",
        "wildcard-including-lines",
        "negated-character-set",
        "ascii-character-set",
    ):
        lengths = {
            len(subjects[s]["value"].encode("utf-8"))
            for s in cases[case_id]["subjects"]
            if len(subjects[s]["value"]) == 1
        }
        if not {1, 2, 3} <= lengths:
            raise ValueError("missing bytes/scalar probes")
    return value


def compile_case(
    binary: Path, case: dict, profile: str, *, artifact: bool = True
) -> dict:
    command = [
        str(binary),
        "compile",
        "--input",
        "-",
        "--target",
        shared._profile_path(profile).stem,
        "--source-id",
        "src:adversarial." + case["id"],
    ]
    for output in ["semantic", "analysis", "portability"] + (
        ["target_artifact"] if artifact else []
    ):
        command += ["--output", output]
    completed = subprocess.run(
        command,
        input=case["source"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        timeout=30,
        check=False,
    )
    result = json.loads(completed.stdout) if completed.stdout else None
    if result is not None:
        contracts().validate("compile-result.schema.json", result)
    return {
        "exit_code": completed.returncode,
        "stdout": result,
        "stdout_empty": not completed.stdout,
        "stderr": completed.stderr,
    }


def validate_semantic_probe(case: dict, program: dict) -> None:
    def walk(value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    nodes = list(walk(program["root"]))
    kinds = {n.get("kind") for n in nodes}
    for tag in case["tags"]:
        if (
            tag.startswith("capture:")
            and not {
                "capture",
                "repeat"
                if "repetition" in tag or "nonparticipating" in tag
                else "backreference",
            }
            <= kinds
        ):
            raise ValueError("capture tag is not backed by semantic structure")
        if tag == "capture:nonparticipating" and not any(
            n.get("kind") == "repeat" and n.get("min") == 0 for n in nodes
        ):
            raise ValueError(
                "nonparticipating probe must contain optional capture path"
            )
        if tag == "capture:reset-in-repetition" and "alternation" not in kinds:
            raise ValueError("reset probe must have a nonparticipating alternative")
    if case["id"] == "wildcard-excluding-lines" and not any(
        n.get("kind") == "wildcard" and n.get("line_terminators") == "exclude"
        for n in nodes
    ):
        raise ValueError("wildcard probe lost its semantic construct")
    if case["id"] == "unicode-word-class" and not any(
        n.get("name") == "word" and n.get("domain") == "unicode" for n in nodes
    ):
        raise ValueError("Unicode word probe lost its semantic construct")


def normalize_match(match: dict | None, subject: str, profile: str) -> dict:
    """Compare first-search spans and capture participation in UTF-8 coordinates.

    Keep bytes values as hex, including partial scalars; decoding to text would
    either hide the defect or crash on the evidence that matters most.
    """
    if match is None or match.get("span") is None:
        return {"matched": False, "span_utf8": None, "captures": []}
    is_bytes = profile.endswith("-bytes")

    def offset(n: int) -> int:
        if is_bytes or profile.startswith("profile:pcre2/"):
            return n
        if profile.startswith("profile:ecmascript/"):
            return shared._utf16_to_utf8(subject, n)
        return shared._scalar_to_utf8(subject, n)

    def span(raw: list | None) -> list | None:
        return None if raw is None else [offset(raw[0]), offset(raw[1])]

    captures = []
    for capture in match.get("captures", []):
        if capture["index"] == 0:
            continue
        raw_value = capture.get("value")
        captures.append(
            {
                "slot": capture["index"],
                "span_utf8": span(capture.get("span")),
                "value_utf8_hex": raw_value
                if is_bytes or raw_value is None
                else raw_value.encode("utf-8").hex(),
            }
        )
    return {"matched": True, "span_utf8": span(match["span"]), "captures": captures}


def requirements_probe(result: dict) -> dict:
    artifact = result["artifact"]
    pattern = artifact["pattern"]["text"]
    # Bounded lexical inventory, not a regex parser: all authored probe source
    # is structural and contains no literal assertion-shaped text.
    constructs = {}
    for marker, capability in (
        ("(?=", "assertions.lookahead"),
        ("(?!", "assertions.lookahead"),
        ("(?<=", "assertions.lookbehind.fixed_length"),
        ("(?<!", "assertions.lookbehind.fixed_length"),
    ):
        if marker in pattern:
            constructs[marker] = capability
    declared = {r["capability_id"] for r in artifact["requirements"]}
    profile = load_json(shared._profile_path(artifact["target_profile"]["profile_id"]))
    support = {c["capability_id"]: c for c in profile["capabilities"]}
    missing = sorted(set(constructs.values()) - declared)
    return {
        "semantic_requirements": result["analysis"]["feature_requirements"],
        "emitted_constructs": constructs,
        "artifact_requirements": artifact["requirements"],
        "missing_requirements": missing,
        "profile_support": {c: support.get(c) for c in missing},
    }


def governed_runtimes() -> tuple[dict, dict]:
    pcre_paths, node, python = shared._runtime_paths()
    paths = {"node": node, "python": python, **pcre_paths}
    expected = {
        "node": shared.EXPECTED_NODE_EXECUTABLE_SHA256,
        "python": shared.EXPECTED_PYTHON_EXECUTABLE_SHA256,
        **{v: item["sha256"] for v, item in shared.EXPECTED_PCRE2_LIBRARIES.items()},
    }
    for key, path in paths.items():
        if file_digest(path) != expected[key]:
            raise ValueError(f"{key}: governed executable/library fingerprint mismatch")
    node_identity = node_harness(node, {"protocol_version": "1.0.0", "cases": []})[
        "runtime"
    ]
    python_identity = python_harness(
        python, {"protocol_version": "1.0.0", "cases": []}
    )["runtime"]
    if (
        node_identity["node"] != shared.EXPECTED_NODE
        or node_identity["v8"] != shared.EXPECTED_V8
        or python_identity["version"] != shared.EXPECTED_VERSION
    ):
        raise ValueError("governed runtime version mismatch")
    identities = {
        "node": {**node_identity, "sha256": expected["node"]},
        "python": {**python_identity, "sha256": expected["python"]},
    }
    for version, path in pcre_paths.items():
        identity = Engine(path).version()
        if identity.split()[0] != version:
            raise ValueError("PCRE2 version mismatch")
        identities[version] = {"version": identity, "sha256": expected[version]}
    return paths, identities


def execute_artifact(
    artifact: dict, subjects: list[str], paths: dict
) -> tuple[dict, list]:
    profile = artifact["target_profile"]["profile_id"]
    pattern = artifact["pattern"]
    request = {
        "id": "adversarial",
        "source": pattern["text"],
        "flags": pattern.get("flags", []),
        "subjects": subjects,
    }
    if profile.startswith("profile:pcre2/"):
        version = profile.rsplit("/", 1)[1]
        raw = Engine(paths[version]).run_detailed_case(
            pattern["text"],
            [{"subject": s} for s in subjects],
            profile_configuration(load_json(shared._profile_path(profile))),
            MatchLimits(match=100_000, depth=10_000, heap_kib=64 * 1024),
        )
        if raw["compile"] != "ok":
            return raw, []
        for item in raw["matches"]:
            if item["outcome"] not in {"match", "no_match"}:
                raise ValueError(f"PCRE2 execution incomplete: {item['outcome']}")
        matches = raw["matches"]
    else:
        if profile.startswith("profile:python-re/"):
            request["pattern_kind"] = "bytes" if profile.endswith("-bytes") else "str"
            if request["pattern_kind"] == "bytes":
                request["subjects"] = [s.encode("utf-8").hex() for s in subjects]
            response = python_harness(
                paths["python"], {"protocol_version": "1.0.0", "cases": [request]}
            )
        else:
            request["capture_names"] = {}
            response = node_harness(
                paths["node"], {"protocol_version": "1.0.0", "cases": [request]}
            )
        if len(response["cases"]) != 1 or response["cases"][0]["id"] != request["id"]:
            raise ValueError("runtime response identity differs")
        raw = response["cases"][0]
        status = (
            raw["compile"]
            if isinstance(raw["compile"], str)
            else raw["compile"]["status"]
        )
        if status != "ok":
            return raw, []
        if [r["subject"] for r in raw["observations"]] != request["subjects"]:
            raise ValueError("runtime subject denominator differs")
        matches = [
            r["matches"][0] if r["matches"] else None for r in raw["observations"]
        ]
    if len(matches) != len(subjects):
        raise ValueError("runtime observation denominator differs")
    return raw, [normalize_match(m, s, profile) for m, s in zip(matches, subjects)]


def findings_for(rows: list[dict]) -> list[dict]:
    findings = []
    groups: dict[tuple, list] = {}
    for row in rows:
        case_id, profile = row["case_id"], row["profile"]["profile_id"]
        if row["compile"]["stdout"] is None:
            findings.append(
                {
                    "id": f"diagnostic/{case_id}/{profile}",
                    "case_id": case_id,
                    "classification": "DIAGNOSTIC_DELIVERY_DEFECT",
                    "profiles": [profile],
                }
            )
        if row.get("target_compile") == "error":
            findings.append(
                {
                    "id": f"target-compile/{case_id}/{profile}",
                    "case_id": case_id,
                    "classification": "TARGET_COMPILE_FAILURE",
                    "profiles": [profile],
                }
            )
        for requirement in row.get("requirements_probe", {}).get(
            "missing_requirements", []
        ):
            findings.append(
                {
                    "id": f"requirement/{case_id}/{profile}/{requirement}",
                    "case_id": case_id,
                    "classification": "REQUIREMENT_UNSOUNDNESS",
                    "profiles": [profile],
                    "missing_requirement": requirement,
                }
            )
        for observation in row.get("observations", []):
            groups.setdefault((case_id, observation["subject_id"]), []).append(
                (profile, observation["result"])
            )
    for (case_id, subject_id), values in sorted(groups.items()):
        if len({DIGEST(result) for _, result in values}) > 1:
            findings.append(
                {
                    "id": f"semantic/{case_id}/{subject_id}",
                    "case_id": case_id,
                    "subject_id": subject_id,
                    "classification": "SEMANTIC_DIVERGENCE",
                    "profiles": [p for p, _ in values],
                    "results": dict(values),
                }
            )
    return sorted(findings, key=lambda item: item["id"])


def quantifier_boundary(binary: Path, paths: dict) -> list[dict]:
    """Bounded bisection for the exact one-literal program, not general limits."""
    boundaries = []
    for profile in PROFILES:
        if not profile.startswith("profile:pcre2/"):
            continue
        accepted, rejected = 1, 65535
        probes = []
        for count in [accepted, rejected]:
            probes.append(_quantifier_probe(binary, paths, profile, count))
        if [p["target_compile"] for p in probes] != ["ok", "error"]:
            raise ValueError("quantifier boundary endpoints changed; investigate")
        while rejected - accepted > 1:
            count = (accepted + rejected) // 2
            probe = _quantifier_probe(binary, paths, profile, count)
            probes.append(probe)
            if probe["target_compile"] == "ok":
                accepted = count
            else:
                rejected = count
        boundaries.append(
            {
                "profile_id": profile,
                "largest_accepted": accepted,
                "smallest_rejected": rejected,
                "probes": probes,
            }
        )
    return boundaries


def _quantifier_probe(binary: Path, paths: dict, profile: str, count: int) -> dict:
    case = {
        "id": f"quantifier-boundary-{count}",
        "source": f'semantic strling 1.0; case sensitive; pattern repeat from 1 to {count} using greedy {{ text "a"; }}',
    }
    compiled = compile_case(binary, case, profile)
    artifact = compiled["stdout"]["artifact"]
    raw, _ = execute_artifact(artifact, [], paths)
    return {
        "case_id": case["id"],
        "source": case["source"],
        "count": count,
        "artifact": artifact,
        "artifact_sha256": DIGEST(artifact),
        "portability_status": compiled["stdout"]["portability"]["status"],
        "target_compile": raw["compile"],
        "raw": raw,
    }


def execute(corpus: dict, binary: Path, paths: dict) -> list[dict]:
    subjects = {s["id"]: s for s in corpus["subjects"]}
    rows = []
    for case in corpus["cases"]:
        for profile in PROFILES:
            profile_data = load_json(shared._profile_path(profile))
            reference = {
                "profile_id": profile,
                "profile_version": profile_data["profile_version"],
                "sha256": DIGEST(profile_data),
            }
            compiled = compile_case(binary, case, profile)
            result = compiled["stdout"]
            row = {
                "case_id": case["id"],
                "source_sha256": DIGEST(case["source"]),
                "profile": reference,
                "runtime_key": "node"
                if "ecmascript" in profile
                else "python"
                if "python-re" in profile
                else profile.rsplit("/", 1)[1],
                "compile": compiled,
                "observations": [],
            }
            if result is None:
                if compiled["exit_code"] != 70:
                    raise ValueError(
                        f"unexpected compiler transport failure: {compiled}"
                    )
                row["pre_emission"] = compile_case(
                    binary, case, profile, artifact=False
                )
                pre = row["pre_emission"]["stdout"]
                if pre is None or pre["outcome"] != "succeeded":
                    raise ValueError("diagnostic probe fails before emission")
                probe = subprocess.run(
                    [str(binary.parent / "examples/adversarial_emission_probe")],
                    input=json.dumps(
                        {
                            "program": pre["semantic_result"]["program"],
                            "profile": profile_data,
                        }
                    ),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                    check=True,
                )
                row["direct_serializer"] = json.loads(probe.stdout)
                if not row["direct_serializer"].get("diagnostics"):
                    raise ValueError(
                        "serialization failure lacks direct diagnostic evidence"
                    )
                rows.append(row)
                continue
            if result.get("semantic_result", {}).get("status") != "complete":
                raise ValueError(
                    f"invalid semantic probe {case['id']}: {result['diagnostics']}"
                )
            validate_semantic_probe(case, result["semantic_result"]["program"])
            artifact = result.get("artifact")
            if artifact is None:
                if result.get("portability", {}).get("status") != "unsupported":
                    raise ValueError("unexplained missing artifact")
                row["disposition"] = "EXPECTED_PROFILE_DIFFERENCE"
            else:
                if artifact["target_profile"] != reference:
                    raise ValueError("kernel profile differs from governed registry")
                row["artifact_sha256"] = DIGEST(artifact)
                row["requirements_probe"] = requirements_probe(result)
                raw, normalized = execute_artifact(
                    artifact, [subjects[s]["value"] for s in case["subjects"]], paths
                )
                row["raw"] = raw
                status = (
                    raw["compile"]
                    if isinstance(raw["compile"], str)
                    else raw["compile"]["status"]
                )
                row["target_compile"] = "ok" if status == "ok" else "error"
                row["observations"] = [
                    {
                        "subject_id": sid,
                        "subject_sha256": DIGEST(subjects[sid]),
                        "value_utf8_hex": subjects[sid]["value"].encode("utf-8").hex(),
                        "result": observation,
                    }
                    for sid, observation in zip(case["subjects"], normalized)
                ]
            rows.append(row)
    return rows


def validate_evidence(evidence: dict, corpus: dict) -> None:
    Draft202012Validator(load_json(DIRECTORY / "evidence.schema.json")).validate(
        evidence
    )
    unsigned = {k: v for k, v in evidence.items() if k != "result_sha256"}
    if evidence["result_sha256"] != DIGEST(unsigned):
        raise ValueError("evidence fingerprint differs")
    if evidence["corpus_sha256"] != DIGEST(corpus):
        raise ValueError("evidence corpus differs")
    expected_hashes = {
        "node": shared.EXPECTED_NODE_EXECUTABLE_SHA256,
        "python": shared.EXPECTED_PYTHON_EXECUTABLE_SHA256,
        **{v: data["sha256"] for v, data in shared.EXPECTED_PCRE2_LIBRARIES.items()},
    }
    if any(
        evidence["runtimes"][key]["sha256"] != digest
        for key, digest in expected_hashes.items()
    ):
        raise ValueError("preserved runtime identity differs from governed pin")
    expected = {(c["id"], p) for c in corpus["cases"] for p in PROFILES}
    actual = [(r["case_id"], r["profile"]["profile_id"]) for r in evidence["rows"]]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("evidence application denominator differs")
    subjects = {s["id"]: s for s in corpus["subjects"]}
    cases = {c["id"]: c for c in corpus["cases"]}
    for row in evidence["rows"]:
        case = cases[row["case_id"]]
        if row["source_sha256"] != DIGEST(case["source"]):
            raise ValueError("evidence source differs")
        profile = load_json(shared._profile_path(row["profile"]["profile_id"]))
        if row["profile"]["sha256"] != DIGEST(profile):
            raise ValueError("evidence profile differs")
        result = row["compile"]["stdout"]
        if result:
            contracts().validate("compile-result.schema.json", result)
            validate_semantic_probe(case, result["semantic_result"]["program"])
            if result.get("artifact") and row["artifact_sha256"] != DIGEST(
                result["artifact"]
            ):
                raise ValueError("evidence artifact differs")
            if result.get("artifact") and row[
                "requirements_probe"
            ] != requirements_probe(result):
                raise ValueError("requirement inventory differs from artifact")
        else:
            direct = row["direct_serializer"]["diagnostics"]
            if (
                row["compile"]["exit_code"] != 70
                or not row["compile"]["stdout_empty"]
                or not direct
            ):
                raise ValueError("incomplete diagnostic delivery evidence")
            for diagnostic in direct:
                contracts().validate("diagnostic.schema.json", diagnostic)
        if row.get("target_compile") == "ok":
            if [o["subject_id"] for o in row["observations"]] != case["subjects"]:
                raise ValueError("evidence subject denominator differs")
            raw = row["raw"]
            raw_matches = raw.get("matches")
            if raw_matches is None:
                raw_matches = [
                    o["matches"][0] if o["matches"] else None
                    for o in raw["observations"]
                ]
            rebuilt = [
                normalize_match(m, subjects[s]["value"], row["profile"]["profile_id"])
                for m, s in zip(raw_matches, case["subjects"])
            ]
            if len(raw_matches) != len(case["subjects"]) or rebuilt != [
                o["result"] for o in row["observations"]
            ]:
                raise ValueError(
                    "normalized observations differ from raw engine evidence"
                )
        for observation in row["observations"]:
            subject = subjects[observation["subject_id"]]
            if (
                observation["subject_sha256"] != DIGEST(subject)
                or observation["value_utf8_hex"]
                != subject["value"].encode("utf-8").hex()
            ):
                raise ValueError("evidence subject differs")
    if evidence["findings"] != findings_for(evidence["rows"]):
        raise ValueError("evidence findings differ from observations")
    if evidence["run_id"] != DIGEST(
        {"corpus": DIGEST(corpus), "rows": evidence["rows"]}
    ):
        raise ValueError("run identity differs")
    for boundary in evidence["quantifier_boundaries"]:
        by_count = {p["count"]: p for p in boundary["probes"]}
        low, high = boundary["largest_accepted"], boundary["smallest_rejected"]
        if (
            high != low + 1
            or by_count[low]["target_compile"] != "ok"
            or by_count[high]["target_compile"] != "error"
        ):
            raise ValueError(
                "quantifier boundary lacks adjacent accepted/rejected evidence"
            )
        for probe in by_count.values():
            if probe["artifact_sha256"] != DIGEST(probe["artifact"]):
                raise ValueError("quantifier boundary artifact differs")


def observation_path(case_id: str) -> str:
    # Case-fold probes deliberately differ only by Unicode/ASCII letter case.
    # Their files must remain distinct on case-insensitive host filesystems.
    return f"observations/{case_id.lower()}-{DIGEST(case_id)[:12]}.json"


def load_evidence(path: Path = EVIDENCE) -> dict:
    evidence = load_json(path)
    Draft202012Validator(load_json(DIRECTORY / "evidence.schema.json")).validate(
        evidence
    )
    # Legacy envelopes remain readable so the first sharded run can compare
    # its findings with the preceding repository-owned observation.
    if "rows" in evidence:
        return evidence
    rows = []
    seen = set()
    for reference in evidence.pop("case_observations"):
        case_id = reference["case_id"]
        relative = observation_path(case_id)
        if (
            not re.fullmatch(r"[A-Za-z0-9-]+", case_id)
            or reference["path"] != relative
            or relative in seen
        ):
            raise ValueError("invalid or duplicate observation shard identity")
        seen.add(relative)
        shard = load_json(path.parent / relative)
        if DIGEST(shard) != reference["sha256"]:
            raise ValueError("observation shard fingerprint differs")
        if set(shard) != {"case_id", "rows"} or shard["case_id"] != case_id:
            raise ValueError("observation shard case differs")
        if any(row["case_id"] != case_id for row in shard["rows"]):
            raise ValueError("observation shard row case differs")
        rows.extend(shard["rows"])
    present = {
        p.relative_to(path.parent).as_posix()
        for p in (path.parent / "observations").glob("*.json")
    }
    if seen != present:
        raise ValueError("unreferenced observation shard")
    evidence["rows"] = rows
    return evidence


def write_evidence(evidence: dict, path: Path = EVIDENCE) -> None:
    index = {key: value for key, value in evidence.items() if key != "rows"}
    index["case_observations"] = []
    (path.parent / "observations").mkdir(exist_ok=True)
    grouped = {}
    for row in evidence["rows"]:
        grouped.setdefault(row["case_id"], []).append(row)
    for case_id, rows in grouped.items():
        shard = {"case_id": case_id, "rows": rows}
        relative = observation_path(case_id)
        (path.parent / relative).write_text(
            json.dumps(shard, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        index["case_observations"].append(
            {"case_id": case_id, "path": relative, "sha256": DIGEST(shard)}
        )
    path.write_text(
        json.dumps(index, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def source_identity() -> dict:
    paths = sorted(
        set(ROOT.glob("core/src/**/*.rs"))
        | {
            ROOT / "core/cli/strling-kernel.rs",
            ROOT / "core/examples/adversarial_emission_probe.rs",
            ROOT / "core/internal/Cargo.toml",
            Path(__file__).resolve(),
            ROOT / "tooling/node_regexp_harness.mjs",
            ROOT / "tooling/python_re_harness.py",
            ROOT / "tooling/pcre2_feature_probe.py",
        }
    )
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(
            p.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        for p in paths
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Execute exact engines; every finding makes the command non-green",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Preserve a new empirical observation run, never normative expectations",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Offline corpus and preserved evidence integrity only",
    )
    args = parser.parse_args()
    if args.check and (args.strict or args.write):
        parser.error("--check cannot replace strict execution or evidence generation")
    corpus = validate_corpus()
    if args.check:
        validate_evidence(load_evidence(), corpus)
        print(
            "Adversarial corpus and preserved evidence integrity: passed (not an equivalence claim)"
        )
        return 0
    try:
        paths, runtimes = governed_runtimes()
        subprocess.run(
            [
                "cargo",
                "build",
                "--manifest-path",
                "core/internal/Cargo.toml",
                "--bin",
                "strling-kernel",
                "--example",
                "adversarial_emission_probe",
                "--locked",
                "--quiet",
            ],
            cwd=ROOT,
            check=True,
            timeout=600,
        )
        binary = (
            Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "core/internal/target"))
            / "debug/strling-kernel"
        )
        # One byte-identical copy avoids repeatedly loading large binaries over
        # a mounted workspace filesystem; compilation still uses current source.
        with tempfile.TemporaryDirectory(prefix="strling-adversarial-") as scratch:
            copied = Path(scratch) / "strling-kernel"
            shutil.copy2(binary, copied)
            (copied.parent / "examples").mkdir()
            probe = binary.parent / "examples/adversarial_emission_probe"
            shutil.copy2(probe, copied.parent / "examples" / probe.name)
            if file_digest(binary) != file_digest(copied):
                raise ValueError("kernel transport copy differs")
            rows = execute(corpus, copied, paths)
            if rows != execute(corpus, copied, paths):
                raise ValueError("independent real-engine runs are not deterministic")
            boundary = quantifier_boundary(copied, paths)
            if boundary != quantifier_boundary(copied, paths):
                raise ValueError(
                    "quantifier boundary observations are not deterministic"
                )
        findings = findings_for(rows)
        previous = load_evidence() if EVIDENCE.exists() else None
        known_ids = {f["id"] for f in previous["findings"]} if previous else set()
        observed_ids = {f["id"] for f in findings}
        evidence = {
            "schema_version": "1.0.0",
            "authority": corpus["authority"],
            "source_sha": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "source_files": source_identity(),
            "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_id": DIGEST({"corpus": DIGEST(corpus), "rows": rows}),
            "repeat_runs": 2,
            "corpus_sha256": DIGEST(corpus),
            "runtimes": runtimes,
            "rows": rows,
            "quantifier_boundaries": boundary,
            "findings": findings,
        }
        evidence["result_sha256"] = DIGEST(evidence)
        validate_evidence(evidence, corpus)
        if args.write:
            write_evidence(evidence)
        print(
            "AUDIT DIVERGENCE SUITE: "
            + ("FAILED AS EXPECTED" if findings else "UNEXPECTEDLY GREEN — INVESTIGATE")
        )
        print(
            f"known findings reproduced: {len(observed_ids & known_ids)}; unexpected findings: {len(observed_ids - known_ids)}; unreproduced baseline findings: {len(known_ids - observed_ids)}; observed findings: {len(findings)}"
        )
        return 1 if findings else 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "ENVIRONMENT_BLOCKED", "message": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
