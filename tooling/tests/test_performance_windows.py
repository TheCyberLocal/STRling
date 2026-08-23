from __future__ import annotations

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
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        probe = json.loads(completed.stdout)
        execution = probe["execution_resource"]
        self.assertEqual(execution["effective_cpu_affinity"], [20])
        self.assertEqual(execution["processor_group"], 0)
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
        self.assertTrue(attestation["reservation"]["quiescence_required"])


if __name__ == "__main__":
    unittest.main()
