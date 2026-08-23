#!/usr/bin/env python3
"""Attest and condition a dedicated bare-metal Linux performance resource."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


ATTESTATION_ENV = "STRLING_PERFORMANCE_HOST_ATTESTATION"
SELECTED_CPU_ENV = "STRLING_PERFORMANCE_SELECTED_LOGICAL_CPU"
EXPECTED_ATTESTATION_ENV = "STRLING_PERFORMANCE_EXPECTED_HOST_ATTESTATION"


class QualificationError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def document_fingerprint(document: dict[str, Any], field: str) -> str:
    payload = dict(document)
    payload.pop(field, None)
    return fingerprint(payload)


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def required_text(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise QualificationError(f"{path}: {error}") from error
    if not value:
        raise QualificationError(f"{path} is empty")
    return value


def optional_text(path: Path, default: str = "unknown") -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return default
    return value or default


def parse_cpu_set(value: str) -> list[int]:
    cpus: list[int] = []
    for part in value.split(","):
        bounds = part.split("-")
        if len(bounds) not in {1, 2}:
            raise QualificationError(f"invalid CPU set {value}")
        try:
            start = int(bounds[0])
            end = int(bounds[-1])
        except ValueError as error:
            raise QualificationError(f"invalid CPU set {value}") from error
        if start < 0 or end < start:
            raise QualificationError(f"invalid CPU set {value}")
        cpus.extend(range(start, end + 1))
    return sorted(set(cpus))


def command_line_cpu_set(name: str) -> list[int]:
    prefix = f"{name}="
    token = next(
        (
            value
            for value in required_text(Path("/proc/cmdline")).split()
            if value.startswith(prefix)
        ),
        None,
    )
    if token is None:
        raise QualificationError(f"kernel command line lacks {name}")
    parts = [
        part
        for part in token[len(prefix) :].split(",")
        if part not in {"domain", "managed_irq", "nohz"}
    ]
    if not parts:
        raise QualificationError(f"kernel command line {name} has no CPU set")
    return parse_cpu_set(",".join(parts))


def cpuinfo(selected: int) -> dict[str, str]:
    for block in required_text(Path("/proc/cpuinfo")).split("\n\n"):
        fields = {
            key.strip(): value.strip()
            for line in block.splitlines()
            if ":" in line
            for key, value in [line.split(":", 1)]
        }
        if fields.get("processor") != str(selected):
            continue
        mapping = {
            "vendor_id": "vendor_id",
            "family": "cpu family",
            "model": "model",
            "stepping": "stepping",
            "microcode": "microcode",
            "model_name": "model name",
        }
        result = {
            name: fields.get(source, "unknown") for name, source in mapping.items()
        }
        if any(value == "unknown" for value in result.values()):
            break
        return result
    raise QualificationError(f"CPU identity is incomplete for logical CPU {selected}")


def cpu_topology(cpu: int) -> dict[str, Any]:
    root = Path(f"/sys/devices/system/cpu/cpu{cpu}")
    topology = root / "topology"
    return {
        "logical_cpu": cpu,
        "online": optional_text(root / "online", "1") == "1",
        "package_id": required_text(topology / "physical_package_id"),
        "die_id": optional_text(topology / "die_id"),
        "core_id": required_text(topology / "core_id"),
        "core_type": optional_text(topology / "core_type"),
        "thread_siblings": required_text(topology / "thread_siblings_list"),
    }


def all_cpu_topology() -> list[dict[str, Any]]:
    rows = []
    for path in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
        match = re.fullmatch(r"cpu(\d+)", path.name)
        if match:
            rows.append(cpu_topology(int(match.group(1))))
    rows.sort(key=lambda row: row["logical_cpu"])
    if not rows:
        raise QualificationError("host CPU topology is unavailable")
    return rows


def cgroup_identity(selected: int) -> dict[str, Any]:
    cgroup_path = next(
        (
            line[3:] or "/"
            for line in required_text(Path("/proc/self/cgroup")).splitlines()
            if line.startswith("0::")
        ),
        None,
    )
    if cgroup_path is None or not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise QualificationError("unified cgroup v2 is required")
    cgroup_root = Path("/sys/fs/cgroup").resolve()
    root = (cgroup_root / cgroup_path.lstrip("/")).resolve()
    if root != cgroup_root and cgroup_root not in root.parents:
        raise QualificationError("cgroup path escaped its mount")
    cpuset = required_text(root / "cpuset.cpus.effective")
    if parse_cpu_set(cpuset) != [selected]:
        raise QualificationError(f"cgroup cpuset {cpuset} is not CPU {selected}")
    cpu_max = " ".join(required_text(root / "cpu.max").split())
    if not cpu_max.startswith("max "):
        raise QualificationError(f"CPU quota is not unlimited: {cpu_max}")
    return {
        "cgroup_path": cgroup_path,
        "cgroup_cpuset_effective": cpuset,
        "cgroup_cpu_max": cpu_max,
    }


def process_ancestors() -> set[int]:
    ancestors = set()
    process_id = os.getpid()
    while process_id > 0 and process_id not in ancestors:
        ancestors.add(process_id)
        try:
            value = (Path("/proc") / str(process_id) / "stat").read_text(
                encoding="utf-8"
            )
            closing = value.rfind(") ")
            fields = value[closing + 2 :].split() if closing >= 0 else []
            process_id = int(fields[1])
        except (OSError, ValueError, IndexError) as error:
            raise QualificationError(
                f"cannot authenticate process ancestry: {error}"
            ) from error
    return ancestors


def unrelated_schedulable_tasks(selected: int) -> list[dict[str, Any]]:
    allowed = process_ancestors()
    rows = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit() or int(path.name) in allowed:
            continue
        try:
            status = (path / "status").read_text(encoding="utf-8")
        except OSError as error:
            raise QualificationError(
                f"cannot inspect {path}/status: {error}"
            ) from error
        affinity_match = re.search(r"^Cpus_allowed_list:\s*(.+)$", status, re.MULTILINE)
        name_match = re.search(r"^Name:\s*(.+)$", status, re.MULTILINE)
        if affinity_match and selected in parse_cpu_set(
            affinity_match.group(1).strip()
        ):
            rows.append(
                {
                    "pid": int(path.name),
                    "name": name_match.group(1).strip() if name_match else "unknown",
                }
            )
    rows.sort(key=lambda row: row["pid"])
    return rows


def thermal_throttle_counts(selected: int) -> dict[str, int]:
    root = Path(f"/sys/devices/system/cpu/cpu{selected}/thermal_throttle")
    paths = sorted(root.glob("*throttle_count"))
    if not paths:
        raise QualificationError("hardware thermal-throttle counters are unavailable")
    result = {path.name: int(required_text(path)) for path in paths}
    if any(result.values()):
        raise QualificationError(f"thermal throttling was observed: {result}")
    return result


def isolation_evidence(selected: int) -> dict[str, Any]:
    if (
        Path("/sys/hypervisor/type").exists()
        or "hypervisor" in required_text(Path("/proc/cpuinfo")).split()
    ):
        raise QualificationError("bare-metal attestation rejects a hypervisor guest")
    isolated = parse_cpu_set(required_text(Path("/sys/devices/system/cpu/isolated")))
    nohz_full = parse_cpu_set(required_text(Path("/sys/devices/system/cpu/nohz_full")))
    isolcpus = command_line_cpu_set("isolcpus")
    rcu_nocbs = command_line_cpu_set("rcu_nocbs")
    irq_affinity = command_line_cpu_set("irqaffinity")
    if not all(
        selected in values for values in (isolated, nohz_full, isolcpus, rcu_nocbs)
    ):
        raise QualificationError("selected CPU lacks complete kernel isolation")
    if selected in irq_affinity:
        raise QualificationError("selected CPU is present in housekeeping IRQ affinity")
    governor_path = Path(
        f"/sys/devices/system/cpu/cpu{selected}/cpufreq/scaling_governor"
    )
    governor = required_text(governor_path)
    if governor != "performance":
        raise QualificationError(f"CPU governor is not performance: {governor}")
    preference_path = governor_path.parent / "energy_performance_preference"
    preference = required_text(preference_path)
    if preference != "performance":
        raise QualificationError(
            f"energy performance preference is not performance: {preference}"
        )
    unrelated = unrelated_schedulable_tasks(selected)
    if unrelated:
        raise QualificationError(
            f"unrelated tasks can execute on CPU {selected}: {unrelated}"
        )
    return {
        **cgroup_identity(selected),
        "isolated_cpus": isolated,
        "nohz_full_cpus": nohz_full,
        "isolcpus": isolcpus,
        "rcu_nocbs": rcu_nocbs,
        "irq_affinity": irq_affinity,
        "governor": governor,
        "energy_performance_preference": preference,
        "thermal_throttle_counts": thermal_throttle_counts(selected),
        "unrelated_schedulable_tasks": unrelated,
    }


def os_identity() -> str:
    values = {}
    for line in required_text(Path("/etc/os-release")).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return f"{values.get('PRETTY_NAME', 'unknown-linux')} | kernel {platform.release()}"


def build_attestation(selected: int, conditioner: Path) -> dict[str, Any]:
    if os.sched_getaffinity(0) != {selected}:
        raise QualificationError(
            f"process affinity {sorted(os.sched_getaffinity(0))} is not CPU {selected}"
        )
    selected_topology = cpu_topology(selected)
    online_cpus = parse_cpu_set(required_text(Path("/sys/devices/system/cpu/online")))
    online_siblings = sorted(
        set(parse_cpu_set(selected_topology["thread_siblings"])) & set(online_cpus)
    )
    if selected not in online_cpus or online_siblings != [selected]:
        raise QualificationError(
            "measured physical core must have only the selected hardware thread online"
        )
    topology = all_cpu_topology()
    processor = cpuinfo(selected)
    processor["logical_cpu_count"] = len(topology)
    processor["topology_sha256"] = fingerprint(topology)
    isolation = isolation_evidence(selected)
    clocksource = required_text(
        Path("/sys/devices/system/clocksource/clocksource0/current_clocksource")
    )
    evidence = {
        "selected_cpu_topology": selected_topology,
        "host_topology": topology,
        "online_cpus": online_cpus,
        **isolation,
        "clocksource": clocksource,
    }
    if evidence["clocksource"] != "tsc":
        raise QualificationError(
            f"bare-metal clocksource is not tsc: {evidence['clocksource']}"
        )
    host_id = hashlib.sha256(
        required_text(Path("/etc/machine-id")).encode("utf-8")
    ).hexdigest()
    attestation: dict[str, Any] = {
        "schema_version": "1.0.0",
        "attestation_kind": "strling-performance-host-reservation",
        "environment_kind": "dedicated-bare-metal",
        "host_id_sha256": host_id,
        "host_os": os_identity(),
        "host_kernel_or_hypervisor": platform.release(),
        "host_processor": processor,
        "reservation": {
            "mechanism": "bare-metal-cpuset-isolation",
            "reservation_id": f"bare-metal-{host_id[:16]}-cpu-{selected}",
            "host_logical_processors": [selected],
            "host_physical_core_identity": (
                f"package-{selected_topology['package_id']}/"
                f"die-{selected_topology['die_id']}/core-{selected_topology['core_id']}"
            ),
            "cpu_quota": "unlimited",
            "exclusive": True,
            "housekeeping_excluded": True,
            "unrelated_workloads_excluded": True,
            "evidence_sha256": fingerprint(evidence),
        },
        "reservation_evidence": evidence,
        "conditioning": {
            "policy_id": "bare-metal-isolation-power-thermal-v1",
            "executable_path": str(conditioner),
            "executable_sha256": file_fingerprint(conditioner),
        },
        "attestation_fingerprint": "0" * 64,
    }
    attestation["attestation_fingerprint"] = document_fingerprint(
        attestation, "attestation_fingerprint"
    )
    return attestation


def write_attestation(path: Path, attestation: dict[str, Any]) -> None:
    if os.geteuid() != 0:
        raise QualificationError("attestation output requires root")
    if not path.is_absolute() or path.is_symlink():
        raise QualificationError("attestation output must be an absolute non-symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as output:
        json.dump(attestation, output, indent=4, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.chmod(temporary, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.replace(temporary, path)


def condition() -> dict[str, Any]:
    try:
        selected = int(os.environ[SELECTED_CPU_ENV])
        attestation_path = Path(os.environ[ATTESTATION_ENV])
        expected_fingerprint = os.environ[EXPECTED_ATTESTATION_ENV]
    except (KeyError, ValueError) as error:
        raise QualificationError(
            f"conditioning environment is incomplete: {error}"
        ) from error
    attestation = json.loads(required_text(attestation_path))
    if (
        attestation.get("attestation_fingerprint")
        != document_fingerprint(attestation, "attestation_fingerprint")
        or attestation["attestation_fingerprint"] != expected_fingerprint
    ):
        raise QualificationError("host attestation fingerprint changed")
    observed = build_attestation(selected, Path(__file__).resolve())
    if observed != attestation:
        raise QualificationError("host reservation or conditioning state changed")
    report: dict[str, Any] = {
        "conditioning_version": "1.0.0",
        "status": "passed",
        "policy_id": attestation["conditioning"]["policy_id"],
        "host_attestation_fingerprint": expected_fingerprint,
        "selected_logical_cpu": selected,
        "thermal_state": "nominal",
        "power_state": "governed",
        "unrelated_workloads_excluded": True,
        "report_fingerprint": "0" * 64,
    }
    report["report_fingerprint"] = document_fingerprint(report, "report_fingerprint")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    attest = subparsers.add_parser("attest")
    attest.add_argument("--selected-logical-cpu", type=int, required=True)
    attest.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "attest":
            conditioner = Path(__file__).resolve()
            attestation = build_attestation(arguments.selected_logical_cpu, conditioner)
            write_attestation(arguments.output, attestation)
            result: dict[str, Any] = {
                "status": "passed",
                "attestation_path": str(arguments.output),
                "attestation_fingerprint": attestation["attestation_fingerprint"],
            }
        elif arguments.json:
            result = condition()
        else:
            parser.error("use attest or --json")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        OSError,
        QualificationError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        print(json.dumps({"status": "failed", "message": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
