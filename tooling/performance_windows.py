"""Native Windows host controls for governed performance certification.

This module is deliberately standard-library-only and offline.  The controller
imports it to constrain its own process and invokes it as a fresh process for
each pre-measurement quiescence observation.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import platform
import re
import struct
import subprocess
import sys
import time
import uuid
from typing import Any, Mapping, Sequence


CONDITIONING_VERSION = "1.1.0"
POLICY_ID = "native-windows-fixed-frequency-quiescence-v2"
OBSERVATION_MILLISECONDS = 2_000
MAXIMUM_SELECTED_BUSY_BASIS_POINTS = 500
MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS = 100
MAXIMUM_SYSTEM_BUSY_BASIS_POINTS = 1_500

_PROCESSOR_PERFORMANCE_INFORMATION_CLASS = 8
_JOB_OBJECT_CPU_RATE_CONTROL_INFORMATION = 15
_JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x1
_CPU_SET_INFORMATION_TYPE = 0
_PROCESSOR_INFORMATION_LEVEL = 11
_PROCESSOR_POWER_SUBGROUP = "54533251-82be-4824-96c1-47b60b740d00"
_PROCESSOR_POWER_SETTINGS = {
    "minimum_processor_state_percent": "893dee8e-2bef-41e0-89c6-b55d0929964c",
    "maximum_processor_state_percent": "bc5038f7-23e0-4960-96da-33abaf5935ec",
    "processor_performance_boost_mode": "be337238-0d82-4146-a960-4f3749d470c7",
}
_REQUIRED_PROCESSOR_POWER_SETTINGS = {
    "minimum_processor_state_percent": 100,
    "maximum_processor_state_percent": 100,
    "processor_performance_boost_mode": 0,
}
_GUEST_MARKERS = (
    "virtual machine",
    "virtualbox",
    "vmware",
    "qemu",
    "kvm",
    "xen",
    "parallels",
    "bochs",
    "amazon ec2",
    "google compute engine",
    "openstack",
)


class WindowsQualificationError(RuntimeError):
    """A fail-closed native Windows qualification error."""


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _PROCESSOR_POWER_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Number", ctypes.c_ulong),
        ("MaxMhz", ctypes.c_ulong),
        ("CurrentMhz", ctypes.c_ulong),
        ("MhzLimit", ctypes.c_ulong),
        ("MaxIdleState", ctypes.c_ulong),
        ("CurrentIdleState", ctypes.c_ulong),
    ]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def document_fingerprint(value: Mapping[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return fingerprint(payload)


def _require_windows() -> None:
    if platform.system().lower() != "windows" or not sys.maxsize > 2**32:
        raise WindowsQualificationError(
            "native 64-bit Windows is required; WSL and compatibility processes are excluded"
        )


def _kernel32() -> Any:
    _require_windows()
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _raise_last_error(label: str) -> None:
    error = ctypes.get_last_error()
    raise WindowsQualificationError(f"{label} failed with Windows error {error}")


def parse_cpu_set_records(data: bytes) -> list[dict[str, object]]:
    """Parse variable-sized SYSTEM_CPU_SET_INFORMATION records."""

    records: list[dict[str, object]] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < 8:
            raise WindowsQualificationError("truncated CPU-set record header")
        size, record_type = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > len(data):
            raise WindowsQualificationError("invalid CPU-set record size")
        if record_type == _CPU_SET_INFORMATION_TYPE:
            if size < 32:
                raise WindowsQualificationError("truncated CPU-set information record")
            (
                cpu_set_id,
                group,
                logical_processor_index,
                core_index,
                last_level_cache_index,
                numa_node_index,
                efficiency_class,
                flags,
                scheduling_class,
                allocation_tag,
            ) = struct.unpack_from("<IHBBBBBBIQ", data, offset + 8)
            records.append(
                {
                    "cpu_set_id": cpu_set_id,
                    "processor_group": group,
                    "logical_processor_index": logical_processor_index,
                    "core_index": core_index,
                    "last_level_cache_index": last_level_cache_index,
                    "numa_node_index": numa_node_index,
                    "efficiency_class": efficiency_class,
                    "parked": bool(flags & 0x01),
                    "allocated": bool(flags & 0x02),
                    "allocated_to_target_process": bool(flags & 0x04),
                    "realtime": bool(flags & 0x08),
                    "scheduling_class": scheduling_class,
                    "allocation_tag": f"0x{allocation_tag:016x}",
                }
            )
        offset += size
    if offset != len(data) or not records:
        raise WindowsQualificationError("CPU-set enumeration was incomplete")
    return records


def enumerate_cpu_sets() -> list[dict[str, object]]:
    kernel32 = _kernel32()
    function = kernel32.GetSystemCpuSetInformation
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    function.restype = ctypes.c_int
    required = ctypes.c_ulong(0)
    function(None, 0, ctypes.byref(required), None, 0)
    if required.value == 0:
        _raise_last_error("GetSystemCpuSetInformation(size)")
    buffer = ctypes.create_string_buffer(required.value)
    if not function(buffer, required.value, ctypes.byref(required), None, 0):
        _raise_last_error("GetSystemCpuSetInformation")
    return parse_cpu_set_records(buffer.raw[: required.value])


def processor_group_counts() -> list[int]:
    kernel32 = _kernel32()
    kernel32.GetActiveProcessorGroupCount.argtypes = []
    kernel32.GetActiveProcessorGroupCount.restype = ctypes.c_ushort
    kernel32.GetActiveProcessorCount.argtypes = [ctypes.c_ushort]
    kernel32.GetActiveProcessorCount.restype = ctypes.c_ulong
    groups = int(kernel32.GetActiveProcessorGroupCount())
    if groups < 1:
        raise WindowsQualificationError("Windows reported no active processor groups")
    counts = [int(kernel32.GetActiveProcessorCount(index)) for index in range(groups)]
    if any(count < 1 for count in counts):
        raise WindowsQualificationError("Windows reported an empty processor group")
    return counts


def selected_cpu_set(
    selected_logical_cpu: int, cpu_sets: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    matches = [
        dict(row)
        for row in cpu_sets
        if row["processor_group"] == 0
        and row["logical_processor_index"] == selected_logical_cpu
    ]
    if len(matches) != 1:
        raise WindowsQualificationError(
            f"logical processor group 0:{selected_logical_cpu} did not map to one CPU set"
        )
    observed = matches[0]
    selected = {
        key: observed[key]
        for key in (
            "cpu_set_id",
            "processor_group",
            "logical_processor_index",
            "core_index",
            "last_level_cache_index",
            "numa_node_index",
            "efficiency_class",
            "scheduling_class",
        )
    }
    siblings = sorted(
        int(row["logical_processor_index"])
        for row in cpu_sets
        if row["processor_group"] == selected["processor_group"]
        and row["core_index"] == selected["core_index"]
    )
    selected["thread_siblings"] = siblings
    selected["physical_core_identity"] = (
        f"group-{selected['processor_group']}/core-{selected['core_index']}"
        f"/efficiency-{selected['efficiency_class']}"
    )
    return selected


def _current_process_handle() -> int:
    kernel32 = _kernel32()
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    return int(kernel32.GetCurrentProcess())


def process_affinity() -> dict[str, object]:
    kernel32 = _kernel32()
    function = kernel32.GetProcessAffinityMask
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    function.restype = ctypes.c_int
    process_mask = ctypes.c_size_t(0)
    system_mask = ctypes.c_size_t(0)
    if not function(
        _current_process_handle(),
        ctypes.byref(process_mask),
        ctypes.byref(system_mask),
    ):
        _raise_last_error("GetProcessAffinityMask")
    effective = [
        index
        for index in range(ctypes.sizeof(ctypes.c_size_t) * 8)
        if process_mask.value & (1 << index)
    ]
    return {
        "processor_group": 0,
        "effective_logical_processors": effective,
        "process_affinity_mask": f"0x{process_mask.value:016x}",
        "system_affinity_mask": f"0x{system_mask.value:016x}",
    }


def process_default_cpu_set_ids() -> list[int]:
    kernel32 = _kernel32()
    function = kernel32.GetProcessDefaultCpuSets
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    function.restype = ctypes.c_int
    required = ctypes.c_ulong(0)
    if not function(_current_process_handle(), None, 0, ctypes.byref(required)):
        error = ctypes.get_last_error()
        if error != 122:  # ERROR_INSUFFICIENT_BUFFER
            _raise_last_error("GetProcessDefaultCpuSets(size)")
    if required.value == 0:
        return []
    values = (ctypes.c_ulong * required.value)()
    if not function(
        _current_process_handle(), values, required.value, ctypes.byref(required)
    ):
        _raise_last_error("GetProcessDefaultCpuSets")
    return [int(values[index]) for index in range(required.value)]


def enforce_current_process_placement(selected_logical_cpu: int) -> dict[str, object]:
    """Apply and then authenticate Windows hard affinity and CPU-set controls."""

    _require_windows()
    counts = processor_group_counts()
    if len(counts) != 1:
        raise WindowsQualificationError(
            "the governed Windows path currently requires one processor group"
        )
    if selected_logical_cpu < 0 or selected_logical_cpu >= counts[0]:
        raise WindowsQualificationError(
            f"logical processor {selected_logical_cpu} is outside processor group 0"
        )
    cpu_sets = enumerate_cpu_sets()
    selected = selected_cpu_set(selected_logical_cpu, cpu_sets)
    kernel32 = _kernel32()
    set_affinity = kernel32.SetProcessAffinityMask
    set_affinity.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    set_affinity.restype = ctypes.c_int
    mask = 1 << selected_logical_cpu
    if not set_affinity(_current_process_handle(), mask):
        _raise_last_error("SetProcessAffinityMask")
    set_cpu_sets = kernel32.SetProcessDefaultCpuSets
    set_cpu_sets.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_ulong,
    ]
    set_cpu_sets.restype = ctypes.c_int
    cpu_set_ids = (ctypes.c_ulong * 1)(int(selected["cpu_set_id"]))
    if not set_cpu_sets(_current_process_handle(), cpu_set_ids, 1):
        _raise_last_error("SetProcessDefaultCpuSets")
    affinity = process_affinity()
    defaults = process_default_cpu_set_ids()
    if affinity["effective_logical_processors"] != [selected_logical_cpu]:
        raise WindowsQualificationError("Windows process affinity did not remain exact")
    if defaults != [selected["cpu_set_id"]]:
        raise WindowsQualificationError(
            "Windows process CPU-set assignment did not remain exact"
        )
    return {
        **affinity,
        "process_default_cpu_set_ids": defaults,
        "selected_cpu_set": selected,
    }


def cpu_quota_state() -> dict[str, object]:
    kernel32 = _kernel32()
    in_job = ctypes.c_int(0)
    is_in_job = kernel32.IsProcessInJob
    is_in_job.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    is_in_job.restype = ctypes.c_int
    if not is_in_job(_current_process_handle(), None, ctypes.byref(in_job)):
        _raise_last_error("IsProcessInJob")
    if not in_job.value:
        return {
            "in_job": False,
            "control_flags": 0,
            "rate_control_enabled": False,
            "effective_cpu_quota": "unlimited",
        }
    values = (ctypes.c_ulong * 2)()
    returned = ctypes.c_ulong(0)
    query = kernel32.QueryInformationJobObject
    query.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    query.restype = ctypes.c_int
    if not query(
        None,
        _JOB_OBJECT_CPU_RATE_CONTROL_INFORMATION,
        values,
        ctypes.sizeof(values),
        ctypes.byref(returned),
    ):
        _raise_last_error("QueryInformationJobObject(CPU rate)")
    flags = int(values[0])
    enabled = bool(flags & _JOB_OBJECT_CPU_RATE_CONTROL_ENABLE)
    return {
        "in_job": True,
        "control_flags": flags,
        "rate_control_enabled": enabled,
        "effective_cpu_quota": "limited" if enabled else "unlimited",
    }


def timer_information() -> dict[str, object]:
    kernel32 = _kernel32()
    frequency = ctypes.c_longlong(0)
    function = kernel32.QueryPerformanceFrequency
    function.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(frequency)) or frequency.value <= 0:
        _raise_last_error("QueryPerformanceFrequency")
    clock = time.get_clock_info("perf_counter")
    return {
        "source": "QueryPerformanceCounter",
        "frequency_hz": int(frequency.value),
        "python_implementation": clock.implementation,
        "python_resolution_nanoseconds": max(1, round(clock.resolution * 1e9)),
        "monotonic": bool(clock.monotonic),
        "adjustable": bool(clock.adjustable),
    }


def memory_bytes() -> int:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    state = MEMORYSTATUSEX()
    state.dwLength = ctypes.sizeof(state)
    kernel32 = _kernel32()
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        _raise_last_error("GlobalMemoryStatusEx")
    if state.ullTotalPhys <= 0:
        raise WindowsQualificationError("physical memory identity is unavailable")
    return int(state.ullTotalPhys)


def _registry_value(path: str, name: str) -> object:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError as error:
        raise WindowsQualificationError(
            f"registry identity {path}/{name}: {error}"
        ) from error
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (str, int)):
        return value
    return str(value)


def os_identity() -> dict[str, object]:
    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    return {
        "product_name": _registry_value(path, "ProductName"),
        "display_version": _registry_value(path, "DisplayVersion"),
        "edition_id": _registry_value(path, "EditionID"),
        "installation_type": _registry_value(path, "InstallationType"),
        "current_build": _registry_value(path, "CurrentBuildNumber"),
        "ubr": _registry_value(path, "UBR"),
        "build_lab_ex": _registry_value(path, "BuildLabEx"),
        "native_version": platform.version(),
        "machine": platform.machine().lower(),
    }


def firmware_identity() -> dict[str, object]:
    path = r"HARDWARE\DESCRIPTION\System\BIOS"
    fields = {
        "system_manufacturer": "SystemManufacturer",
        "system_product_name": "SystemProductName",
        "system_version": "SystemVersion",
        "baseboard_manufacturer": "BaseBoardManufacturer",
        "baseboard_product": "BaseBoardProduct",
        "bios_vendor": "BIOSVendor",
        "bios_version": "BIOSVersion",
    }
    return {key: _registry_value(path, value) for key, value in fields.items()}


def processor_registry_identity() -> dict[str, object]:
    path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    fields = {
        "identifier": "Identifier",
        "model_name": "ProcessorNameString",
        "vendor_id": "VendorIdentifier",
        "nominal_mhz": "~MHz",
        "microcode_update_revision": "Update Revision",
        "microcode_update_status": "Update Status",
    }
    return {key: _registry_value(path, value) for key, value in fields.items()}


def guest_indicators(identity: Mapping[str, object]) -> list[str]:
    indicators = []
    for key, value in identity.items():
        normalized = str(value).lower()
        for marker in _GUEST_MARKERS:
            if marker in normalized:
                indicators.append(f"{key}:{marker}")
    return sorted(set(indicators))


def _guid(value: str) -> _GUID:
    return _GUID.from_buffer_copy(uuid.UUID(value).bytes_le)


def processor_power_setting(active_scheme_guid: str, setting_guid: str) -> int:
    powrprof = ctypes.WinDLL("PowrProf.dll", use_last_error=True)
    function = powrprof.PowerReadACValueIndex
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_GUID),
        ctypes.POINTER(_GUID),
        ctypes.POINTER(_GUID),
        ctypes.POINTER(ctypes.c_ulong),
    ]
    function.restype = ctypes.c_ulong
    scheme = _guid(active_scheme_guid)
    subgroup = _guid(_PROCESSOR_POWER_SUBGROUP)
    setting = _guid(setting_guid)
    value = ctypes.c_ulong(0)
    status = int(
        function(
            None,
            ctypes.byref(scheme),
            ctypes.byref(subgroup),
            ctypes.byref(setting),
            ctypes.byref(value),
        )
    )
    if status != 0:
        raise WindowsQualificationError(
            f"PowerReadACValueIndex failed for {setting_guid} with status {status}"
        )
    return int(value.value)


def selected_processor_frequency(
    logical_processor_count: int, selected_logical_cpu: int
) -> dict[str, int]:
    if not 0 <= selected_logical_cpu < logical_processor_count:
        raise WindowsQualificationError("selected processor frequency index is invalid")
    records_type = _PROCESSOR_POWER_INFORMATION * logical_processor_count
    records = records_type()
    powrprof = ctypes.WinDLL("PowrProf.dll", use_last_error=True)
    function = powrprof.CallNtPowerInformation
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    function.restype = ctypes.c_long
    status = int(
        function(
            _PROCESSOR_INFORMATION_LEVEL,
            None,
            0,
            ctypes.byref(records),
            ctypes.sizeof(records),
        )
    )
    if status != 0:
        raise WindowsQualificationError(
            f"CallNtPowerInformation failed with NTSTATUS 0x{status & 0xFFFFFFFF:08x}"
        )
    selected = records[selected_logical_cpu]
    return {
        "processor_number": int(selected.Number),
        "maximum_mhz": int(selected.MaxMhz),
        "current_mhz": int(selected.CurrentMhz),
        "mhz_limit": int(selected.MhzLimit),
    }


def validate_performance_power_policy(power: Mapping[str, object]) -> None:
    settings = power.get("processor_settings")
    if settings != _REQUIRED_PROCESSOR_POWER_SETTINGS:
        raise WindowsQualificationError(
            "governed Windows calibration requires processor min/max 100% "
            "with performance boost disabled"
        )
    frequency = power.get("selected_processor_frequency")
    if not isinstance(frequency, Mapping):
        raise WindowsQualificationError("selected processor frequency is unavailable")
    maximum = frequency.get("maximum_mhz")
    if (
        not isinstance(maximum, int)
        or maximum <= 0
        or frequency.get("processor_number") is None
        or frequency.get("current_mhz") != maximum
        or frequency.get("mhz_limit") != maximum
    ):
        raise WindowsQualificationError(
            "selected processor is not at its authenticated non-boosted frequency"
        )


def power_information(
    logical_processor_count: int, selected_logical_cpu: int
) -> dict[str, object]:
    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    state = SYSTEM_POWER_STATUS()
    kernel32 = _kernel32()
    kernel32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
    kernel32.GetSystemPowerStatus.restype = ctypes.c_int
    if not kernel32.GetSystemPowerStatus(ctypes.byref(state)):
        _raise_last_error("GetSystemPowerStatus")
    if state.ACLineStatus not in {0, 1}:
        raise WindowsQualificationError("Windows power source is unknown")
    try:
        completed = subprocess.run(
            ["powercfg.exe", "/getactivescheme"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise WindowsQualificationError(
            f"active Windows power scheme: {error}"
        ) from error
    match = re.search(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        completed.stdout,
    )
    if match is None:
        raise WindowsQualificationError(
            "active Windows power scheme GUID is unavailable"
        )
    name_match = re.search(r"\(([^()]*)\)\s*$", completed.stdout.strip())
    active_scheme_guid = match.group(1).lower()
    power: dict[str, object] = {
        "source": "ac" if state.ACLineStatus == 1 else "battery",
        "battery_saver": bool(state.SystemStatusFlag),
        "active_scheme_guid": active_scheme_guid,
        "active_scheme_name": name_match.group(1) if name_match else "unknown",
        "processor_settings": {
            name: processor_power_setting(active_scheme_guid, setting_guid)
            for name, setting_guid in _PROCESSOR_POWER_SETTINGS.items()
        },
        "selected_processor_frequency": selected_processor_frequency(
            logical_processor_count, selected_logical_cpu
        ),
    }
    validate_performance_power_policy(power)
    return power


class _PROCESSOR_PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("IdleTime", ctypes.c_longlong),
        ("KernelTime", ctypes.c_longlong),
        ("UserTime", ctypes.c_longlong),
        ("DpcTime", ctypes.c_longlong),
        ("InterruptTime", ctypes.c_longlong),
        ("InterruptCount", ctypes.c_ulong),
    ]


def processor_performance_counters(count: int) -> list[dict[str, int]]:
    if count < 1:
        raise WindowsQualificationError("processor counter count must be positive")
    values = (_PROCESSOR_PERFORMANCE_INFORMATION * count)()
    returned = ctypes.c_ulong(0)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    function = ntdll.NtQuerySystemInformation
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    function.restype = ctypes.c_long
    status = int(
        function(
            _PROCESSOR_PERFORMANCE_INFORMATION_CLASS,
            values,
            ctypes.sizeof(values),
            ctypes.byref(returned),
        )
    )
    if status != 0 or returned.value < ctypes.sizeof(values):
        raise WindowsQualificationError(
            f"NtQuerySystemInformation(processor performance) failed with NTSTATUS 0x{status & 0xFFFFFFFF:08x}"
        )
    return [
        {
            "idle": int(row.IdleTime),
            "kernel": int(row.KernelTime),
            "user": int(row.UserTime),
            "dpc": int(row.DpcTime),
            "interrupt": int(row.InterruptTime),
            "interrupt_count": int(row.InterruptCount),
        }
        for row in values
    ]


def quiescence_rates(
    before: Sequence[Mapping[str, int]],
    after: Sequence[Mapping[str, int]],
    selected_logical_cpu: int,
) -> dict[str, int]:
    if len(before) != len(after) or not 0 <= selected_logical_cpu < len(before):
        raise WindowsQualificationError("processor counter denominator changed")

    def deltas(index: int) -> tuple[int, int, int]:
        start = before[index]
        end = after[index]
        idle = end["idle"] - start["idle"]
        kernel = end["kernel"] - start["kernel"]
        user = end["user"] - start["user"]
        total = kernel + user
        busy = total - idle
        interrupt = (end["dpc"] - start["dpc"]) + (
            end["interrupt"] - start["interrupt"]
        )
        if min(idle, kernel, user, total, busy, interrupt) < 0 or total <= 0:
            raise WindowsQualificationError("processor performance counters regressed")
        return total, busy, interrupt

    selected_total, selected_busy, selected_interrupt = deltas(selected_logical_cpu)
    system = [deltas(index) for index in range(len(before))]
    system_total = sum(row[0] for row in system)
    system_busy = sum(row[1] for row in system)
    return {
        "selected_busy_basis_points": round(selected_busy * 10_000 / selected_total),
        "selected_interrupt_basis_points": round(
            selected_interrupt * 10_000 / selected_total
        ),
        "system_busy_basis_points": round(system_busy * 10_000 / system_total),
        "selected_interrupt_count_delta": (
            after[selected_logical_cpu]["interrupt_count"]
            - before[selected_logical_cpu]["interrupt_count"]
        ),
    }


def evaluate_quiescence(observation: Mapping[str, int]) -> list[str]:
    failures = []
    for field, maximum in (
        ("selected_busy_basis_points", MAXIMUM_SELECTED_BUSY_BASIS_POINTS),
        ("selected_interrupt_basis_points", MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS),
        ("system_busy_basis_points", MAXIMUM_SYSTEM_BUSY_BASIS_POINTS),
    ):
        if observation[field] > maximum:
            failures.append(f"{field}>{maximum}")
    return failures


def execution_resource(selected_logical_cpu: int) -> dict[str, object]:
    placement = enforce_current_process_placement(selected_logical_cpu)
    quota = cpu_quota_state()
    if quota["effective_cpu_quota"] != "unlimited":
        raise WindowsQualificationError("the current Windows job imposes a CPU quota")
    timer = timer_information()
    selected = placement["selected_cpu_set"]
    return {
        "platform": "windows",
        "placement_mechanism": "process-affinity-and-cpu-sets",
        "processor_group": placement["processor_group"],
        "selected_logical_processor": selected_logical_cpu,
        "selected_cpu_set_id": selected["cpu_set_id"],
        "process_affinity_mask": placement["process_affinity_mask"],
        "system_affinity_mask": placement["system_affinity_mask"],
        "effective_cpu_affinity": placement["effective_logical_processors"],
        "process_default_cpu_set_ids": placement["process_default_cpu_set_ids"],
        "cpu_quota": quota,
        "timer": timer,
        "processor_topology": selected,
    }


def stable_platform_probe(selected_logical_cpu: int) -> dict[str, object]:
    cpu_sets = enumerate_cpu_sets()
    selected = selected_cpu_set(selected_logical_cpu, cpu_sets)
    groups = processor_group_counts()
    topology_cpu_sets = [
        {
            key: row[key]
            for key in (
                "cpu_set_id",
                "processor_group",
                "logical_processor_index",
                "core_index",
                "last_level_cache_index",
                "numa_node_index",
                "efficiency_class",
                "scheduling_class",
            )
        }
        for row in cpu_sets
    ]
    firmware = firmware_identity()
    indicators = guest_indicators(firmware)
    if indicators:
        raise WindowsQualificationError(
            "firmware identifies a virtual guest: " + ", ".join(indicators)
        )
    power = power_information(sum(groups), selected_logical_cpu)
    if power["source"] != "ac" or power["battery_saver"]:
        raise WindowsQualificationError(
            "governed Windows calibration requires AC power with battery saver disabled"
        )
    resource = execution_resource(selected_logical_cpu)
    return {
        "os": os_identity(),
        "firmware": firmware,
        "processor_registry": processor_registry_identity(),
        "processor_group_counts": groups,
        "logical_processor_count": sum(groups),
        "physical_core_count": len(
            {(row["processor_group"], row["core_index"]) for row in cpu_sets}
        ),
        "host_cpu_sets": topology_cpu_sets,
        "selected_cpu_set": selected,
        "memory_bytes": memory_bytes(),
        "power": power,
        "execution_resource": resource,
        "guest_indicators": indicators,
    }


def conditioning_report(
    selected_logical_cpu: int, expected_host_attestation: str
) -> dict[str, object]:
    stable = stable_platform_probe(selected_logical_cpu)
    count = int(stable["logical_processor_count"])
    before = processor_performance_counters(count)
    started = time.perf_counter_ns()
    time.sleep(OBSERVATION_MILLISECONDS / 1_000)
    elapsed = time.perf_counter_ns() - started
    after = processor_performance_counters(count)
    observation = quiescence_rates(before, after, selected_logical_cpu)
    failures = evaluate_quiescence(observation)
    identity = {
        "policy_id": POLICY_ID,
        "selected_logical_cpu": selected_logical_cpu,
        "execution_resource": stable["execution_resource"],
        "power": stable["power"],
        "limits": {
            "observation_milliseconds": OBSERVATION_MILLISECONDS,
            "maximum_selected_busy_basis_points": MAXIMUM_SELECTED_BUSY_BASIS_POINTS,
            "maximum_selected_interrupt_basis_points": MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS,
            "maximum_system_busy_basis_points": MAXIMUM_SYSTEM_BUSY_BASIS_POINTS,
        },
    }
    report: dict[str, object] = {
        "conditioning_version": CONDITIONING_VERSION,
        "status": "passed" if not failures else "rejected",
        "policy_id": POLICY_ID,
        "host_attestation_fingerprint": expected_host_attestation,
        "selected_logical_cpu": selected_logical_cpu,
        "conditioning_identity": identity,
        "conditioning_identity_fingerprint": fingerprint(identity),
        "observation": {
            **observation,
            "elapsed_nanoseconds": elapsed,
            "failures": failures,
        },
        "report_fingerprint": "0" * 64,
    }
    report["report_fingerprint"] = document_fingerprint(report, "report_fingerprint")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe or condition a native Windows performance host"
    )
    parser.add_argument("command", choices=("probe", "condition"))
    parser.add_argument("--selected-logical-cpu", required=True, type=int)
    parser.add_argument("--expected-host-attestation")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "probe":
            result = stable_platform_probe(arguments.selected_logical_cpu)
        else:
            if not arguments.expected_host_attestation:
                raise WindowsQualificationError(
                    "conditioning requires --expected-host-attestation"
                )
            result = conditioning_report(
                arguments.selected_logical_cpu,
                arguments.expected_host_attestation,
            )
        print(json.dumps(result, sort_keys=True) if arguments.json else result)
        return 0 if result.get("status", "passed") == "passed" else 2
    except WindowsQualificationError as error:
        print(
            json.dumps({"status": "unavailable", "reason": str(error)}, sort_keys=True)
            if arguments.json
            else str(error),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
