from __future__ import annotations

import copy
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path

from tooling.performance_resource_certification import _windows_host_attestation
from tooling.performance_windows import (
    MAXIMUM_SELECTED_BUSY_BASIS_POINTS,
    MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS,
    MAXIMUM_SYSTEM_BUSY_BASIS_POINTS,
    WindowsQualificationError,
    evaluate_quiescence,
    guest_indicators,
    parse_cpu_set_records,
    quiescence_rates,
    selected_cpu_set,
    selected_cpu_set_allocation_state,
    validate_process_power_policy,
    validate_performance_power_policy,
)


ROOT = Path(__file__).resolve().parents[2]


def _counter(
    *, idle: int, kernel: int, user: int, dpc: int = 0, interrupt: int = 0
) -> dict[str, int]:
    return {
        "idle": idle,
        "kernel": kernel,
        "user": user,
        "dpc": dpc,
        "interrupt": interrupt,
        "interrupt_count": 0,
    }


class NativeWindowsPerformanceEnvironmentTests(unittest.TestCase):
    def test_cpu_set_records_authenticate_group_core_and_class(self) -> None:
        record = struct.pack(
            "<IIIHBBBBBBIQ",
            32,
            0,
            276,
            0,
            20,
            20,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        parsed = parse_cpu_set_records(record)
        self.assertEqual(parsed[0]["cpu_set_id"], 276)
        self.assertEqual(parsed[0]["processor_group"], 0)
        self.assertEqual(parsed[0]["logical_processor_index"], 20)
        self.assertEqual(parsed[0]["core_index"], 20)
        self.assertEqual(parsed[0]["efficiency_class"], 0)
        selected = selected_cpu_set(20, parsed)
        self.assertEqual(selected["thread_siblings"], [20])
        self.assertEqual(
            selected["physical_core_identity"], "group-0/core-20/efficiency-0"
        )

    def test_cpu_set_parser_and_selection_fail_closed(self) -> None:
        with self.assertRaises(WindowsQualificationError):
            parse_cpu_set_records(b"\x20\x00")
        record = struct.pack(
            "<IIIHBBBBBBIQ",
            32,
            0,
            256,
            0,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
        )
        with self.assertRaises(WindowsQualificationError):
            selected_cpu_set(20, parse_cpu_set_records(record))

    def test_cpu_set_allocation_state_accepts_supported_native_controls(self) -> None:
        def record(flags: int) -> bytes:
            return struct.pack(
                "<IIIHBBBBBBIQ",
                32,
                0,
                276,
                0,
                20,
                20,
                0,
                0,
                0,
                flags,
                0,
                0xA11C,
            )

        ordinary = selected_cpu_set_allocation_state(
            20, parse_cpu_set_records(record(0x00))
        )
        self.assertEqual(
            ordinary,
            {
                "allocated": False,
                "allocated_to_target_process": False,
                "realtime": False,
                "allocation_tag": "0x000000000000a11c",
            },
        )
        reservation = selected_cpu_set_allocation_state(
            20, parse_cpu_set_records(record(0x06))
        )
        self.assertEqual(
            reservation,
            {
                "allocated": True,
                "allocated_to_target_process": True,
                "realtime": False,
                "allocation_tag": "0x000000000000a11c",
            },
        )
        selected_cpu_set_allocation_state(20, parse_cpu_set_records(record(0x07)))
        for flags in (0x02, 0x04):
            with (
                self.subTest(flags=flags),
                self.assertRaises(WindowsQualificationError),
            ):
                selected_cpu_set_allocation_state(
                    20, parse_cpu_set_records(record(flags))
                )

    def test_guest_firmware_indicators_fail_closed(self) -> None:
        self.assertEqual(
            guest_indicators(
                {"manufacturer": "VMware, Inc.", "product": "Virtual Machine"}
            ),
            ["manufacturer:vmware", "product:virtual machine"],
        )
        self.assertEqual(
            guest_indicators({"manufacturer": "Notebook", "product": "X370SNx1"}),
            [],
        )

    def test_quiescence_limits_pass_at_boundary_and_reject_one_over(self) -> None:
        at_boundary = {
            "selected_busy_basis_points": MAXIMUM_SELECTED_BUSY_BASIS_POINTS,
            "selected_interrupt_basis_points": (
                MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS
            ),
            "system_busy_basis_points": MAXIMUM_SYSTEM_BUSY_BASIS_POINTS,
        }
        self.assertEqual(evaluate_quiescence(at_boundary), [])
        for field in at_boundary:
            noisy = dict(at_boundary)
            noisy[field] += 1
            self.assertEqual(len(evaluate_quiescence(noisy)), 1, field)

    def test_quiescence_rates_use_selected_and_whole_host_denominators(self) -> None:
        before = [
            _counter(idle=0, kernel=0, user=0),
            _counter(idle=0, kernel=0, user=0),
        ]
        after = [
            _counter(idle=9_000, kernel=9_500, user=500),
            _counter(idle=9_600, kernel=9_700, user=300, dpc=25, interrupt=25),
        ]
        rates = quiescence_rates(before, after, 1)
        self.assertEqual(rates["selected_busy_basis_points"], 400)
        self.assertEqual(rates["selected_interrupt_basis_points"], 50)
        self.assertEqual(rates["system_busy_basis_points"], 700)
        self.assertEqual(evaluate_quiescence(rates), [])

    def test_fixed_frequency_power_policy_fails_closed(self) -> None:
        power = {
            "processor_settings": {
                "minimum_processor_state_percent": 100,
                "maximum_processor_state_percent": 100,
                "processor_performance_boost_mode": 0,
            },
            "selected_processor_frequency": {
                "processor_number": 20,
                "maximum_mhz": 2200,
                "current_mhz": 2200,
                "mhz_limit": 2200,
            },
        }
        validate_performance_power_policy(power)
        for field, value in (
            ("minimum_processor_state_percent", 99),
            ("maximum_processor_state_percent", 99),
            ("processor_performance_boost_mode", 1),
        ):
            changed = json.loads(json.dumps(power))
            changed["processor_settings"][field] = value
            with self.assertRaises(WindowsQualificationError):
                validate_performance_power_policy(changed)
        changed = json.loads(json.dumps(power))
        changed["selected_processor_frequency"]["current_mhz"] = 2199
        with self.assertRaises(WindowsQualificationError):
            validate_performance_power_policy(changed)

    def test_process_power_policy_requires_explicit_high_qos(self) -> None:
        policy = {
            "api": "SetProcessInformation(ProcessPowerThrottling)",
            "version": 1,
            "control_mask": 1,
            "state_mask": 0,
            "execution_speed_policy": "high-qos",
            "enforcement_result": "success",
        }
        validate_process_power_policy(policy)
        for field, value in (
            ("control_mask", 0),
            ("state_mask", 1),
            ("execution_speed_policy", "eco-qos"),
            ("enforcement_result", "failed"),
        ):
            changed = dict(policy)
            changed[field] = value
            with self.assertRaises(WindowsQualificationError):
                validate_process_power_policy(changed)

    def test_supported_controls_attestation_is_schema_valid(self) -> None:
        baseline = json.loads(
            (
                ROOT / "tests/certification/performance-resource/1.0/baseline.json"
            ).read_text(encoding="utf-8")
        )
        environment = baseline["environment"]
        historical = environment["host_attestation"]
        host_processor = historical["host_processor"]
        historical_evidence = historical["reservation_evidence"]
        execution = copy.deepcopy(environment["execution_resource"])
        allocation_state = {
            "allocated": False,
            "allocated_to_target_process": False,
            "realtime": False,
            "allocation_tag": "0x0000000000000000",
        }
        execution["placement_mechanism"] = (
            "process-affinity-cpu-sets-supported-controls"
        )
        execution["cpu_set_allocation_state"] = allocation_state
        probe = {
            "os": {
                "product_name": "Windows 11 Pro",
                "display_version": "25H2",
                "current_build": "26200",
                "ubr": 9168,
                "native_version": "10.0.26200.9168",
            },
            "processor_registry": {
                "identifier": host_processor["processor_identifier"],
                "vendor_id": host_processor["vendor_id"],
                "microcode_update_revision": host_processor["microcode"],
                "model_name": host_processor["model_name"],
            },
            "execution_resource": execution,
            "selected_cpu_set": historical_evidence["selected_cpu_topology"],
            "host_cpu_sets": historical_evidence["host_topology"],
            "processor_group_counts": historical_evidence["processor_group_counts"],
            "logical_processor_count": host_processor["logical_cpu_count"],
            "physical_core_count": host_processor["physical_core_count"],
            "power": historical_evidence["power"],
            "firmware": historical_evidence["firmware"],
            "guest_indicators": [],
        }
        attestation = _windows_host_attestation(
            probe, selected_logical_cpu=20, root=ROOT
        )
        self.assertEqual(
            attestation["reservation"]["mechanism"],
            "native-windows-supported-controls",
        )
        self.assertFalse(attestation["reservation"]["exclusive"])
        self.assertFalse(attestation["reservation"]["unrelated_workloads_excluded"])
        self.assertEqual(
            attestation["reservation_evidence"]["cpu_set_allocation_state"],
            allocation_state,
        )

    @unittest.skipUnless(sys.platform == "win32", "native Windows-only integration")
    def test_live_native_probe_and_attestation_are_self_consistent(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tooling.performance_windows",
                "probe",
                "--selected-logical-cpu",
                "20",
                "--json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            unavailable = json.loads(completed.stderr)
            self.assertEqual(unavailable["status"], "unavailable")
            self.assertIn("selected Windows CPU set", unavailable["reason"])
            return
        probe = json.loads(completed.stdout)
        execution = probe["execution_resource"]
        self.assertEqual(execution["effective_cpu_affinity"], [20])
        self.assertEqual(execution["processor_group"], 0)
        self.assertEqual(
            execution["process_power_policy"],
            {
                "api": "SetProcessInformation(ProcessPowerThrottling)",
                "version": 1,
                "control_mask": 1,
                "state_mask": 0,
                "execution_speed_policy": "high-qos",
                "enforcement_result": "success",
            },
        )
        self.assertEqual(execution["cpu_quota"]["effective_cpu_quota"], "unlimited")
        self.assertEqual(probe["power"]["source"], "ac")
        self.assertEqual(
            probe["power"]["processor_settings"],
            {
                "minimum_processor_state_percent": 100,
                "maximum_processor_state_percent": 100,
                "processor_performance_boost_mode": 0,
            },
        )
        self.assertEqual(
            probe["power"]["selected_processor_frequency"]["current_mhz"],
            probe["power"]["selected_processor_frequency"]["maximum_mhz"],
        )
        self.assertEqual(probe["guest_indicators"], [])
        attestation = _windows_host_attestation(
            probe, selected_logical_cpu=20, root=ROOT
        )
        self.assertEqual(attestation["environment_kind"], "native-windows-bare-metal")
        self.assertFalse(attestation["reservation"]["exclusive"])
        self.assertFalse(attestation["reservation"]["unrelated_workloads_excluded"])
        self.assertTrue(attestation["reservation"]["quiescence_required"])


if __name__ == "__main__":
    unittest.main()
