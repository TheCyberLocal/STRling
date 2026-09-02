from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator

from tooling.performance_resource_certification import (
    FIXTURE_IDS,
    MEASUREMENT_CONDITIONING_MAX_ATTEMPTS,
    MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS,
    OPERATION_IDS,
    PERFORMANCE_OPERATION_IDS,
    RESOURCE_OPERATION_IDS,
    PerformanceExecutionLedger,
    PerformanceResourceError,
    _artifact_fingerprints_match,
    _artifact_identity_check,
    _artifact_source_changes,
    _canonical_build_root,
    _enforce_governed_cpu_affinity,
    _external_workload_isolation_check,
    _git_invocation,
    _load_host_attestation,
    _measurement_conditioning_check,
    _resolved_command,
    _resolved_environment,
    _runner_resource_matches,
    _should_delegate_windows_full,
    _windows_native_worktree,
    _windows_external_workloads,
    _write_json,
    calibrate_baseline,
    certification_measurement_status,
    conditioning_identities_match,
    conditioning_snapshots_compatible,
    compare_hard_metric,
    create_active_contract,
    derived_relative_budget_basis_points,
    document_fingerprint,
    environment_fingerprint,
    environment_identity_fingerprint,
    environment_mismatches,
    environments_compatible,
    load_json,
    main as performance_main,
    performance_measurement_keys,
    planned_environment_rollover_manifest,
    refresh_resource_identities,
    sample_statistics,
    validate_baseline,
    validate_evidence,
    validate_environment_rollover,
    validate_fixture_manifest,
    validate_manifest,
    validate_repository_contract,
    validate_resource_inventory,
)
from tooling.structured_operation_execution import load_artifact


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "governance/schemas/performance-resource-certification.schema.json"
MANIFEST_PATH = ROOT / "tests/certification/performance-resource/1.0/manifest.json"
FIXTURE_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/fixture-manifest.json"
)
INVENTORY_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/resource-limits.json"
)
EVIDENCE_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/valid-evidence.json"
)
BASELINE_PATH = ROOT / "tests/certification/performance-resource/1.0/baseline.json"


class PerformanceResourceCertificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.manifest = load_json(MANIFEST_PATH)
        cls.fixtures = load_json(FIXTURE_PATH)
        cls.inventory = load_json(INVENTORY_PATH)
        cls.evidence = load_json(EVIDENCE_PATH)

    def test_schema_and_repository_contract_validate(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        validate_fixture_manifest(self.fixtures)
        validate_resource_inventory(self.inventory)
        validate_manifest(
            self.manifest,
            fixtures=self.fixtures,
            inventory=self.inventory,
        )
        validate_evidence(self.evidence, manifest=self.manifest)
        result = validate_repository_contract()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["operation_count"], 22)
        self.assertEqual(result["fixture_count"], 12)
        self.assertEqual(result["resource_declaration_count"], 56)

    def test_resource_identity_refresh_does_not_recalibrate_measurements(self) -> None:
        stale = copy.deepcopy(self.inventory)
        stale["families"][6]["test_sources"][0]["sha256"] = "0" * 64
        baseline = load_json(BASELINE_PATH)
        manifest, inventory, refreshed_baseline, evidence = refresh_resource_identities(
            self.manifest, stale, baseline, self.evidence
        )
        self.assertEqual(baseline["measurements"], refreshed_baseline["measurements"])
        validate_resource_inventory(inventory)
        validate_baseline(refreshed_baseline, manifest=manifest)
        validate_evidence(evidence, manifest=manifest)

    @patch.dict("os.environ", {}, clear=True)
    @patch(
        "tooling.performance_resource_certification.platform.release",
        return_value="5.15.0-microsoft-standard-WSL2",
    )
    @patch(
        "tooling.performance_resource_certification.platform.system",
        return_value="Linux",
    )
    def test_windows_full_delegation_is_exact_and_nonrecursive(
        self, _system: object, _release: object
    ) -> None:
        self.assertTrue(_should_delegate_windows_full(["--profile", "full", "--json"]))
        self.assertTrue(
            _should_delegate_windows_full(
                [
                    "--profile",
                    "full",
                    "--json",
                    "--execution-directory",
                    "/mnt/c/execution",
                    "--certification-invocation-id",
                    "1" * 32,
                    "--certification-profile",
                    "release",
                    "--expected-source-sha",
                    "2" * 40,
                    "--producer-id",
                    "performance_resource_full_certification@repository",
                ]
            )
        )
        self.assertFalse(
            _should_delegate_windows_full(["--profile", "pull-request", "--json"])
        )
        with patch.dict("os.environ", {"STRLING_PERFORMANCE_NATIVE_CHILD": "1"}):
            self.assertFalse(
                _should_delegate_windows_full(["--profile", "full", "--json"])
            )

    def test_execution_ledger_distinguishes_zero_consumed_and_indeterminate(
        self,
    ) -> None:
        directory = (
            ROOT / "target/codex-tools/performance-ledger-tests" / uuid.uuid4().hex
        )
        directory.mkdir(parents=True)
        try:
            ledger = PerformanceExecutionLedger(
                directory,
                producer_id="performance_resource_full_certification@repository",
                operation_id="certification.performance-resource-full",
                source_sha="1" * 40,
                invocation_id="2" * 32,
                certification_profile="release",
                producer_profile="full",
            )
            progress = load_artifact(directory / "progress.json")
            self.assertEqual("zero", progress["sample_consumption"]["state"])
            self.assertEqual(
                0,
                progress["sample_consumption"]["authenticated_sample_count"],
            )

            key = ("latency:fixture", "fixture:tiny")
            ledger.start_coordinate(key)
            progress = load_artifact(directory / "progress.json")
            self.assertEqual("indeterminate", progress["sample_consumption"]["state"])
            self.assertIsNone(
                progress["sample_consumption"]["authenticated_sample_count"]
            )
            ledger.complete_coordinate(key, [10, 11, 12])
            progress = load_artifact(directory / "progress.json")
            self.assertEqual("consumed", progress["sample_consumption"]["state"])
            self.assertEqual(
                3,
                progress["sample_consumption"]["authenticated_sample_count"],
            )
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_execution_ledger_incomplete_artifact_preserves_sample_boundary(
        self,
    ) -> None:
        for sampled in (False, True):
            with self.subTest(sampled=sampled):
                directory = (
                    ROOT
                    / "target/codex-tools/performance-ledger-tests"
                    / uuid.uuid4().hex
                )
                directory.mkdir(parents=True)
                try:
                    ledger = PerformanceExecutionLedger(
                        directory,
                        producer_id=(
                            "performance_resource_full_certification@repository"
                        ),
                        operation_id="certification.performance-resource-full",
                        source_sha="1" * 40,
                        invocation_id="2" * 32,
                        certification_profile="release",
                        producer_profile="full",
                    )
                    if sampled:
                        ledger.start_coordinate(("latency:fixture", "fixture:tiny"))
                    self.assertEqual(
                        3,
                        ledger.write_incomplete(
                            code="controlled-error", message="controlled failure"
                        ),
                    )
                    result = load_artifact(directory / "result.json")
                    expected_state = "indeterminate" if sampled else "zero"
                    self.assertEqual(
                        expected_state, result["sample_consumption"]["state"]
                    )
                    self.assertEqual("incomplete", result["terminal_status"])
                    self.assertEqual(3, result["process_exit_code"])
                finally:
                    shutil.rmtree(directory, ignore_errors=True)

    @patch(
        "tooling.performance_resource_certification.certify",
        side_effect=PerformanceResourceError(
            "controlled-producer-error", "controlled producer failure"
        ),
    )
    @patch(
        "tooling.performance_resource_certification._git_identity",
        return_value=("1" * 40, False),
    )
    @patch(
        "tooling.performance_resource_certification.platform.system",
        return_value="Windows",
    )
    def test_governed_main_exception_writes_bound_incomplete_artifact(
        self, _system: object, _identity: object, _certify: object
    ) -> None:
        directory = (
            ROOT / "target/codex-tools/performance-ledger-tests" / uuid.uuid4().hex
        )
        directory.mkdir(parents=True)
        try:
            exit_code = performance_main(
                [
                    "--profile",
                    "full",
                    "--json",
                    "--execution-directory",
                    str(directory),
                    "--certification-invocation-id",
                    "2" * 32,
                    "--certification-profile",
                    "release",
                    "--expected-source-sha",
                    "1" * 40,
                    "--producer-id",
                    "performance_resource_full_certification@repository",
                ]
            )
            self.assertEqual(3, exit_code)
            result = load_artifact(directory / "result.json")
            self.assertEqual("incomplete", result["terminal_status"])
            self.assertEqual("zero", result["sample_consumption"]["state"])
            self.assertEqual(
                "controlled-producer-error", result["integrity_error"]["code"]
            )
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    @patch("tooling.performance_resource_certification._git_identity")
    @patch("tooling.performance_resource_certification.subprocess.run")
    def test_windows_delegation_selects_exact_clean_native_worktree(
        self, run: Mock, identity: Mock
    ) -> None:
        root = Path("/tmp/linked-worktree")
        native = Path("/mnt/c/repository")
        run.return_value = Mock(
            stdout=(
                "worktree /mnt/c/repository\n"
                "HEAD abcdef\n"
                "branch refs/heads/architecture/v4\n\n"
                "worktree /tmp/linked-worktree\n"
                "HEAD abcdef\n"
                "detached\n"
            )
        )
        identity.side_effect = [("abcdef", False), ("abcdef", False)]

        self.assertEqual(_windows_native_worktree(root), native)

    @patch("tooling.performance_resource_certification._git_identity")
    @patch("tooling.performance_resource_certification.subprocess.run")
    def test_windows_delegation_rejects_stale_or_dirty_native_worktree(
        self, run: Mock, identity: Mock
    ) -> None:
        root = Path("/tmp/linked-worktree")
        run.return_value = Mock(
            stdout=(
                "worktree /mnt/c/repository\n"
                "HEAD stale\n"
                "branch refs/heads/architecture/v4\n"
            )
        )
        identity.side_effect = [("abcdef", False), ("stale", False)]

        with self.assertRaisesRegex(
            PerformanceResourceError, "exactly one clean native worktree"
        ):
            _windows_native_worktree(root)

    @patch.dict(
        "os.environ",
        {
            "STRLING_PERFORMANCE_CARGO": "C:/exact/cargo.exe",
            "STRLING_PERFORMANCE_RUSTC": "C:/exact/rustc.exe",
        },
        clear=True,
    )
    def test_exact_toolchain_override_removes_rustup_selector(self) -> None:
        self.assertEqual(
            _resolved_command(["cargo", "+1.75.0", "build"]),
            ["C:/exact/cargo.exe", "build"],
        )
        self.assertEqual(
            _resolved_command(["rustc", "+1.75.0", "-vV"]),
            ["C:/exact/rustc.exe", "-vV"],
        )
        self.assertEqual(
            _resolved_environment(["cargo", "+1.75.0", "build"])["RUSTC"],
            "C:/exact/rustc.exe",
        )
        self.assertNotIn("RUSTC", _resolved_environment(["rustc", "-vV"]))

    @patch.dict(
        "os.environ",
        {
            "RUSTFLAGS": "-C target-cpu=native",
            "CARGO_ENCODED_RUSTFLAGS": "-C\x1ftarget-cpu=native",
        },
        clear=True,
    )
    @patch(
        "tooling.performance_resource_certification.platform.system",
        return_value="Windows",
    )
    def test_performance_build_environment_is_checkout_independent(
        self, _system: object
    ) -> None:
        root = ROOT / "temporary-checkout"
        environment = _resolved_environment(["cargo", "build"], root=root)
        self.assertNotIn("RUSTFLAGS", environment)
        self.assertEqual(environment["CARGO_INCREMENTAL"], "0")
        self.assertEqual(
            environment["CARGO_ENCODED_RUSTFLAGS"].split("\x1f"),
            [
                f"--remap-path-prefix={root.absolute()}=C:/strling-source",
                "-C",
                "link-arg=/Brepro",
                "-C",
                "link-arg=/PDBALTPATH:%_PDB%",
            ],
        )

    @patch("tooling.performance_resource_certification.Path.exists", return_value=False)
    @patch("tooling.performance_resource_certification.subprocess.run")
    @patch(
        "tooling.performance_resource_certification.platform.system",
        return_value="Windows",
    )
    def test_windows_build_root_uses_and_releases_fixed_drive(
        self, _system: object, run: Mock, _exists: Mock
    ) -> None:
        run.return_value = Mock(returncode=0, stdout="", stderr="")
        root = ROOT / "temporary-checkout"
        with _canonical_build_root(root) as build_root:
            self.assertEqual(build_root, Path("P:/"))
        self.assertEqual(
            [entry.args[0] for entry in run.call_args_list],
            [
                ["subst", "P:", str(root.resolve())],
                ["subst", "P:", "/D"],
            ],
        )

    @patch(
        "tooling.performance_resource_certification._conditioning_snapshot",
        return_value={
            "conditioning_identity_fingerprint": "a" * 64,
            "snapshot_fingerprint": "b" * 64,
            "quiescence_observation": {"failures": []},
        },
    )
    def test_each_measurement_gets_authenticated_conditioning(
        self, conditioning: Mock
    ) -> None:
        result = _measurement_conditioning_check(
            ("latency:kernel-request", "fixture:simply-tiny"), environment={}
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["id"],
            "environment:measurement-conditioning/latency:kernel-request/fixture:simply-tiny",
        )
        self.assertEqual(conditioning.call_count, 1)

    @patch(
        "tooling.performance_resource_certification._conditioning_snapshot",
        side_effect=[
            PerformanceResourceError("conditioning", "host busy"),
            {
                "conditioning_identity_fingerprint": "a" * 64,
                "snapshot_fingerprint": "b" * 64,
                "quiescence_observation": {"failures": []},
            },
        ],
    )
    @patch("tooling.performance_resource_certification.time.sleep")
    def test_measurement_conditioning_acquires_quiet_without_weakening_thresholds(
        self, sleep: Mock, conditioning: Mock
    ) -> None:
        result = _measurement_conditioning_check(
            ("latency:kernel-request", "fixture:simply-tiny"), environment={}
        )
        self.assertEqual(result["status"], "passed")
        details = cast(dict[str, object], result["details"])
        self.assertEqual(details["attempt"], 2)
        self.assertEqual(
            details["maximum_attempts"],
            MEASUREMENT_CONDITIONING_MAX_ATTEMPTS,
        )
        self.assertEqual(
            details["retry_delay_seconds"],
            MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS,
        )
        self.assertEqual(conditioning.call_count, 2)
        sleep.assert_called_once_with(MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS)

    @patch(
        "tooling.performance_resource_certification._conditioning_snapshot",
        side_effect=PerformanceResourceError("conditioning", "host busy"),
    )
    @patch("tooling.performance_resource_certification.time.sleep")
    def test_measurement_conditioning_exhausts_exact_attempt_denominator(
        self, sleep: Mock, conditioning: Mock
    ) -> None:
        result = _measurement_conditioning_check(
            ("latency:kernel-request", "fixture:simply-tiny"), environment={}
        )
        self.assertEqual(result["status"], "unavailable")
        details = cast(dict[str, object], result["details"])
        self.assertEqual(
            len(cast(list[object], details["rejected_attempts"])),
            MEASUREMENT_CONDITIONING_MAX_ATTEMPTS,
        )
        self.assertEqual(conditioning.call_count, MEASUREMENT_CONDITIONING_MAX_ATTEMPTS)
        self.assertEqual(sleep.call_count, MEASUREMENT_CONDITIONING_MAX_ATTEMPTS - 1)

    @patch(
        "tooling.performance_resource_certification.platform.system",
        return_value="Windows",
    )
    @patch("tooling.performance_resource_certification.subprocess.run")
    def test_windows_external_workload_scan_names_heavyweight_processes(
        self, run: Mock, _system: object
    ) -> None:
        run.return_value = Mock(
            returncode=0,
            stdout=(
                '"ProcessId","Name"\n'
                '"40624","fortress"\n'
                '"44784","cargo"\n'
                '"123","python"\n'
            ),
            stderr="",
        )

        self.assertEqual(
            _windows_external_workloads(),
            [
                {"name": "cargo", "process_id": 44784},
                {"name": "fortress", "process_id": 40624},
            ],
        )

    @patch(
        "tooling.performance_resource_certification._windows_external_workloads",
        return_value=[{"name": "fortress", "process_id": 40624}],
    )
    def test_external_workload_isolation_fails_closed(self, _scan: Mock) -> None:
        result = _external_workload_isolation_check(
            ("latency:cli-startup", "fixture:simply-tiny"),
            phase="post-measurement",
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["id"],
            "environment:external-workload-isolation/post-measurement/"
            "latency:cli-startup/fixture:simply-tiny",
        )
        self.assertEqual(
            cast(dict[str, object], result["details"])["observed_workloads"],
            [{"name": "fortress", "process_id": 40624}],
        )

    @patch(
        "tooling.performance_resource_certification._windows_external_workloads",
        side_effect=PerformanceResourceError(
            "external-workload-scan", "process inventory unavailable"
        ),
    )
    def test_external_workload_isolation_rejects_unprovable_state(
        self, _scan: Mock
    ) -> None:
        result = _external_workload_isolation_check(
            ("latency:cli-startup", "fixture:simply-tiny"),
            phase="pre-measurement",
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            cast(dict[str, object], result["details"])["code"],
            "external-workload-scan",
        )

    def test_native_git_translates_wsl_linked_worktree_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").write_text(
                "gitdir: /mnt/c/repository/.git/worktrees/source\n",
                encoding="utf-8",
            )
            with patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Windows",
            ):
                command = _git_invocation(root, "rev-parse", "HEAD")
        self.assertEqual(
            command,
            [
                "git",
                "--git-dir",
                "C:/repository/.git/worktrees/source",
                "--work-tree",
                str(root),
                "rev-parse",
                "HEAD",
            ],
        )

    def test_denominators_and_profile_partition_are_exact(self) -> None:
        self.assertEqual(
            [row["id"] for row in self.manifest["operations"]], OPERATION_IDS
        )
        self.assertEqual([row["id"] for row in self.fixtures["fixtures"]], FIXTURE_IDS)
        partitions = {row["id"]: row for row in self.manifest["profile_partitions"]}
        self.assertEqual(partitions["local"]["operation_ids"], [])
        self.assertEqual(
            partitions["pull-request"]["operation_ids"], RESOURCE_OPERATION_IDS
        )
        self.assertEqual(partitions["full"]["operation_ids"], OPERATION_IDS)
        self.assertTrue(
            all(
                row["state"] == "active"
                for row in self.manifest["operations"]
                if row["id"] in PERFORMANCE_OPERATION_IDS
            )
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["cpu_affinity_policy"],
            "single-fixed-logical-cpu",
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["selected_logical_cpu"], 20
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["host_reservation_policy"],
            "authenticated-native-placement-or-host-pinned-reservation",
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["execution_resource_policy"],
            "platform-native-single-cpu-effective",
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["cpu_quota_policy"], "unlimited"
        )
        self.assertEqual(
            self.manifest["measurement_policy"]["conditioning_policy"],
            "authenticated-identical-before-each-repetition",
        )
        self.assertTrue(
            all(
                row["state"] == "active"
                for row in self.manifest["operations"]
                if row["id"] in RESOURCE_OPERATION_IDS
            )
        )

    def test_fixture_classes_and_resource_sources_are_complete(self) -> None:
        self.assertEqual(
            {row["class"] for row in self.fixtures["fixtures"]},
            {"tiny", "common", "large", "pathological"},
        )
        self.assertEqual(len(self.inventory["families"]), 9)
        self.assertEqual(
            sum(
                len(source["declarations"])
                for family in self.inventory["families"]
                for source in family["sources"]
            ),
            56,
        )
        test_paths = {
            source["path"]
            for family in self.inventory["families"]
            for source in family["test_sources"]
        }
        self.assertEqual(len(test_paths), 19)

    def test_robust_statistics_use_locked_nearest_rank_method(self) -> None:
        samples = list(range(1, 65))
        self.assertEqual(
            sample_statistics(samples),
            {
                "sample_count": 64,
                "median": 32,
                "p95": 61,
                "mad": 16,
                "minimum": 1,
                "maximum": 64,
            },
        )

    def test_budget_derivation_rejects_unstable_baselines(self) -> None:
        self.assertEqual(
            derived_relative_budget_basis_points(median=1000, mad=10), 1000
        )
        self.assertEqual(
            derived_relative_budget_basis_points(median=1000, mad=40), 2400
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            derived_relative_budget_basis_points(median=1000, mad=100)
        self.assertEqual(raised.exception.code, "unstable-baseline")

    def test_controlled_regression_boundaries_fail_closed(self) -> None:
        inside = compare_hard_metric(
            baseline_median=1000,
            observed_median=1099,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        exact = compare_hard_metric(
            baseline_median=1000,
            observed_median=1100,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        relative_over = compare_hard_metric(
            baseline_median=1000,
            observed_median=1101,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        absolute_over = compare_hard_metric(
            baseline_median=1000,
            observed_median=1501,
            relative_regression_basis_points=10000,
            absolute_ceiling=1500,
        )
        self.assertEqual(inside["status"], "passed")
        self.assertEqual(exact["status"], "passed")
        self.assertEqual(relative_over["status"], "failed")
        self.assertFalse(relative_over["relative_passed"])
        self.assertEqual(absolute_over["status"], "failed")
        self.assertFalse(absolute_over["absolute_passed"])

    def test_informational_trends_are_reported_without_blocking(self) -> None:
        self.assertEqual(
            certification_measurement_status(
                enforcement="hard", comparison_status="failed"
            ),
            "failed",
        )
        self.assertEqual(
            certification_measurement_status(
                enforcement="informational", comparison_status="failed"
            ),
            "passed",
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            certification_measurement_status(
                enforcement="unknown", comparison_status="failed"
            )
        self.assertEqual(raised.exception.code, "measurement-enforcement")

    def test_environment_compatibility_is_exact_and_fail_closed(self) -> None:
        environment = self._environment()
        self.assertTrue(
            environments_compatible(environment, copy.deepcopy(environment))
        )
        for field, changed in (
            ("os_version", "different"),
            ("cpu_model", "different"),
            ("logical_cpu_count", 99),
            ("rustc_version", "rustc 9.9.9"),
            ("feature_set", ["different"]),
            ("selected_logical_cpu", 21),
            ("effective_cpu_affinity", [21]),
            ("effective_cpuset", "21"),
        ):
            observed = copy.deepcopy(environment)
            observed[field] = changed
            self.assertFalse(environments_compatible(environment, observed), field)

    def test_environment_mismatches_name_exact_leaf_coordinates(self) -> None:
        baseline = {
            "cpu": {"model": "example", "topology": [0, 1]},
            "timer": "qpc",
        }
        observed = {
            "cpu": {"model": "different", "topology": [0, 2]},
            "extra": True,
        }
        self.assertEqual(
            environment_mismatches(baseline, observed),
            [
                {
                    "coordinate": "cpu.model",
                    "baseline": "example",
                    "observed": "different",
                },
                {
                    "coordinate": "cpu.topology",
                    "baseline": [0, 1],
                    "observed": [0, 2],
                },
                {"coordinate": "extra", "baseline": None, "observed": True},
                {"coordinate": "timer", "baseline": "qpc", "observed": None},
            ],
        )

    def test_windows_job_ancestry_is_diagnostic_when_quota_is_unlimited(self) -> None:
        baseline = load_json(BASELINE_PATH)["environment"]
        observed = copy.deepcopy(baseline)
        observed["execution_resource"]["cpu_quota"]["in_job"] = False
        attestation = observed["host_attestation"]
        evidence = attestation["reservation_evidence"]
        evidence["cpu_quota"]["in_job"] = False
        attestation["reservation"]["evidence_sha256"] = document_fingerprint(
            evidence, "not-present"
        )
        attestation["attestation_fingerprint"] = document_fingerprint(
            attestation, "attestation_fingerprint"
        )
        observed["host_attestation_fingerprint"] = attestation[
            "attestation_fingerprint"
        ]

        self.assertNotEqual(
            environment_fingerprint(baseline), environment_fingerprint(observed)
        )
        self.assertEqual(
            environment_identity_fingerprint(baseline),
            environment_identity_fingerprint(observed),
        )
        self.assertTrue(environments_compatible(baseline, observed))

        observed["execution_resource"]["cpu_quota"]["control_flags"] = 1
        self.assertFalse(environments_compatible(baseline, observed))

    def test_windows_conditioning_compatibility_uses_effective_controls(self) -> None:
        baseline = load_json(BASELINE_PATH)["conditioning_repetitions"][0]
        observed = copy.deepcopy(baseline)
        observed["host_attestation_fingerprint"] = "f" * 64
        observed["conditioning_identity_fingerprint"] = "e" * 64
        observed["quiescence_observation"]["selected_busy_basis_points"] = 1
        observed["snapshot_fingerprint"] = "d" * 64
        self.assertTrue(conditioning_snapshots_compatible(baseline, observed))

        observed["cpu_quota"] = "limited"
        self.assertFalse(conditioning_snapshots_compatible(baseline, observed))

    def test_windows_runner_power_policy_must_match_exactly(self) -> None:
        power_policy = {
            "api": "SetProcessInformation(ProcessPowerThrottling)",
            "version": 1,
            "control_mask": 1,
            "state_mask": 0,
            "execution_speed_policy": "high-qos",
            "enforcement_result": "success",
        }
        execution = {
            "platform": "windows",
            "placement_mechanism": "process-affinity-cpu-sets-supported-controls",
            "processor_group": 0,
            "selected_logical_processor": 20,
            "selected_cpu_set_id": 276,
            "cpu_set_allocation_state": {
                "allocated": False,
                "allocated_to_target_process": False,
                "realtime": False,
                "allocation_tag": "0x0000000000000000",
            },
            "processor_topology": {"core_index": 20, "efficiency_class": 0},
            "timer": {"source": "QueryPerformanceCounter", "frequency_hz": 10_000_000},
            "process_power_policy": power_policy,
        }
        result = {
            "platform": "windows",
            "placement_mechanism": "process-affinity-cpu-sets-supported-controls",
            "processor_group": 0,
            "selected_cpu_set_id": 276,
            "cpu_set_allocation_state": copy.deepcopy(
                execution["cpu_set_allocation_state"]
            ),
            "selected_logical_cpu": 20,
            "effective_cpu_affinity": [20],
            "effective_cpuset": "group-0:logical-20:cpu-set-276:core-20:efficiency-0",
            "cpu_quota": "unlimited",
            "timer_source": "QueryPerformanceCounter:10000000",
            "process_power_policy": power_policy,
            "observed_processor_groups": [0],
            "observed_logical_processors": [20],
        }
        self.assertTrue(
            _runner_resource_matches(
                result, selected_logical_cpu=20, execution_resource=execution
            )
        )
        changed = copy.deepcopy(result)
        changed["process_power_policy"]["state_mask"] = 1
        self.assertFalse(
            _runner_resource_matches(
                changed, selected_logical_cpu=20, execution_resource=execution
            )
        )
        changed = copy.deepcopy(result)
        changed["cpu_set_allocation_state"]["allocation_tag"] = "0x0000000000000001"
        self.assertFalse(
            _runner_resource_matches(
                changed, selected_logical_cpu=20, execution_resource=execution
            )
        )

    def test_full_artifact_identity_is_exact_and_fail_closed(self) -> None:
        expected = self._artifact_fingerprints()
        self.assertTrue(_artifact_fingerprints_match(expected, copy.deepcopy(expected)))
        changed = copy.deepcopy(expected)
        changed["runner"]["sha256"] = "f" * 64
        self.assertFalse(_artifact_fingerprints_match(expected, changed))
        missing = copy.deepcopy(expected)
        missing.pop("interop")
        self.assertFalse(_artifact_fingerprints_match(expected, missing))

    def test_full_artifact_identity_accepts_only_source_bound_candidate_drift(
        self,
    ) -> None:
        expected = self._artifact_fingerprints()
        observed = copy.deepcopy(expected)
        observed["runner"]["sha256"] = "f" * 64
        commits = {
            "baseline_source_commit": "1" * 40,
            "candidate_source_commit": "2" * 40,
        }

        accepted, details = _artifact_identity_check(
            expected,
            observed,
            **commits,
            source_changes={"runner": ["core/src/semantic/mod.rs"]},
        )
        self.assertTrue(accepted)
        self.assertEqual(
            "candidate-source-bound",
            cast(dict[str, Any], details["artifacts"])["runner"]["status"],
        )

        rejected, details = _artifact_identity_check(
            expected,
            observed,
            **commits,
            source_changes={"runner": []},
        )
        self.assertFalse(rejected)
        self.assertEqual(
            "unexplained-artifact-drift",
            cast(dict[str, Any], details["artifacts"])["runner"]["status"],
        )

        missing = copy.deepcopy(observed)
        missing.pop("interop")
        rejected, details = _artifact_identity_check(
            expected,
            missing,
            **commits,
            source_changes={"runner": ["core/src/semantic/mod.rs"]},
        )
        self.assertFalse(rejected)
        self.assertFalse(details["complete_artifact_set"])

    def test_artifact_source_changes_require_ancestor_and_exact_closure(
        self,
    ) -> None:
        completed = Mock(returncode=0, stdout="core/src/semantic/mod.rs\n", stderr="")

        def successful_git(command: list[str], **_kwargs: object) -> Mock:
            if "merge-base" in command:
                return Mock(returncode=0, stdout="", stderr="")
            return completed

        with (
            patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Linux",
            ),
            patch(
                "tooling.performance_resource_certification.subprocess.run",
                side_effect=successful_git,
            ) as runner,
        ):
            changes = _artifact_source_changes(
                baseline_source_commit="1" * 40,
                candidate_source_commit="2" * 40,
            )
        self.assertEqual(
            {"core/src/semantic/mod.rs"},
            {path for paths in changes.values() for path in paths},
        )
        self.assertIn("merge-base", runner.call_args_list[0].args[0])
        for call in runner.call_args_list[1:]:
            self.assertIn("--no-renames", call.args[0])
            self.assertIn("core/src", call.args[0])

        with (
            patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Linux",
            ),
            patch(
                "tooling.performance_resource_certification.subprocess.run",
                return_value=Mock(returncode=1, stdout="", stderr=""),
            ),
        ):
            with self.assertRaises(PerformanceResourceError) as raised:
                _artifact_source_changes(
                    baseline_source_commit="1" * 40,
                    candidate_source_commit="2" * 40,
                )
        self.assertEqual("artifact-source-ancestry", raised.exception.code)

    def test_conditioning_identity_is_exact_while_raw_noise_is_observed(self) -> None:
        first = {
            "conditioning_identity_fingerprint": "1" * 64,
            "snapshot_fingerprint": "2" * 64,
            "quiescence_observation": {"selected_busy_basis_points": 10},
        }
        second = {
            "conditioning_identity_fingerprint": "1" * 64,
            "snapshot_fingerprint": "3" * 64,
            "quiescence_observation": {"selected_busy_basis_points": 20},
        }
        self.assertTrue(conditioning_identities_match([first, second]))
        second["conditioning_identity_fingerprint"] = "4" * 64
        self.assertFalse(conditioning_identities_match([first, second]))

    def test_guest_generated_hypervisor_attestation_is_rejected(self) -> None:
        attestation = copy.deepcopy(self._environment()["host_attestation"])
        attestation["environment_kind"] = "hypervisor-host-pinned"
        attestation["reservation"]["mechanism"] = "hypervisor-host-pinned"
        attestation["attestation_fingerprint"] = document_fingerprint(
            attestation, "attestation_fingerprint"
        )
        with (
            patch.dict(
                "tooling.performance_resource_certification.os.environ",
                {"STRLING_PERFORMANCE_HOST_ATTESTATION": "/synthetic/attestation"},
            ),
            patch(
                "tooling.performance_resource_certification._verify_external_file",
                return_value=Path("/synthetic/attestation"),
            ),
            patch(
                "tooling.performance_resource_certification.load_json",
                return_value=attestation,
            ),
            patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Linux",
            ),
        ):
            with self.assertRaises(PerformanceResourceError) as raised:
                _load_host_attestation(require_root_owned=False)
        self.assertEqual(raised.exception.code, "unsupported-host-attestation")

    def test_single_cpu_affinity_is_enforced_and_fail_closed(self) -> None:
        with (
            patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Linux",
            ),
            patch(
                "tooling.performance_resource_certification.os.sched_getaffinity",
                side_effect=[{0, 20, 30}, {20}],
                create=True,
            ),
            patch(
                "tooling.performance_resource_certification.os.sched_setaffinity",
                create=True,
            ) as setter,
        ):
            self.assertEqual(_enforce_governed_cpu_affinity(self.manifest), [20])
            setter.assert_called_once_with(0, {20})

        with (
            patch(
                "tooling.performance_resource_certification.platform.system",
                return_value="Linux",
            ),
            patch(
                "tooling.performance_resource_certification.os.sched_getaffinity",
                return_value={0, 1},
                create=True,
            ),
        ):
            with self.assertRaises(PerformanceResourceError) as raised:
                _enforce_governed_cpu_affinity(self.manifest)
            self.assertEqual(raised.exception.code, "affinity-unavailable")

    def test_active_baseline_authenticates_samples_stats_budget_and_update(
        self,
    ) -> None:
        active_manifest, baseline = self._active_contract()
        Draft202012Validator(self.schema).validate(baseline)
        validate_manifest(
            active_manifest,
            fixtures=self.fixtures,
            inventory=self.inventory,
        )
        validate_baseline(baseline, manifest=active_manifest, synthetic=True)

        mutations: list[tuple[str, Any]] = [
            ("environment_fingerprint", "0" * 64),
            ("update_command", "silent update is forbidden"),
        ]
        for field, value in mutations:
            changed = copy.deepcopy(baseline)
            changed[field] = value
            changed["baseline_fingerprint"] = document_fingerprint(
                changed, "baseline_fingerprint"
            )
            with self.assertRaises(PerformanceResourceError):
                validate_baseline(changed, manifest=active_manifest, synthetic=True)

        stale_samples = copy.deepcopy(baseline)
        stale_samples["measurements"][0]["repetitions"][0] = [
            value + 100_000
            for value in stale_samples["measurements"][0]["repetitions"][0]
        ]
        stale_samples["baseline_fingerprint"] = document_fingerprint(
            stale_samples, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(stale_samples, manifest=active_manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "batch-normalization")

        weakened_budget = copy.deepcopy(baseline)
        weakened_budget["measurements"][0]["budget"][
            "relative_regression_basis_points"
        ] = 4000
        weakened_budget["baseline_fingerprint"] = document_fingerprint(
            weakened_budget, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(weakened_budget, manifest=active_manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "budget-derivation")

        changed_batch = copy.deepcopy(baseline)
        changed_batch["measurements"][0]["batch_iterations"] += 1
        changed_batch["baseline_fingerprint"] = document_fingerprint(
            changed_batch, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(changed_batch, manifest=active_manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "batch-normalization")

        short_batch = copy.deepcopy(baseline)
        short_batch["measurements"][0]["batch_duration_repetitions"] = [
            [100 for _ in repetition]
            for repetition in short_batch["measurements"][0]["repetitions"]
        ]
        short_batch["measurements"][0]["repetitions"] = [
            [6 for _ in repetition]
            for repetition in short_batch["measurements"][0]["repetitions"]
        ]
        short_batch["measurements"][0]["samples"] = [6] * 5
        short_batch["measurements"][0]["statistics"] = sample_statistics([6] * 5)
        short_batch["measurements"][0]["budget"]["relative_regression_basis_points"] = (
            1000
        )
        short_batch["baseline_fingerprint"] = document_fingerprint(
            short_batch, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(short_batch, manifest=active_manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "batch-duration-minimum")
        self.assertIn("batch_iterations=16", str(raised.exception))
        self.assertIn(
            "repetition_medians=[100, 100, 100, 100, 100]",
            str(raised.exception),
        )

        conditioning_drift = copy.deepcopy(baseline)
        conditioning_drift["conditioning_repetitions"][-1]["policy_id"] = (
            "different-conditioning"
        )
        conditioning_drift["conditioning_repetitions"][-1]["snapshot_fingerprint"] = (
            document_fingerprint(
                conditioning_drift["conditioning_repetitions"][-1],
                "snapshot_fingerprint",
            )
        )
        conditioning_drift["baseline_fingerprint"] = document_fingerprint(
            conditioning_drift, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(
                conditioning_drift, manifest=active_manifest, synthetic=True
            )
        self.assertEqual(raised.exception.code, "conditioning-drift")

    def test_calibration_executes_five_complete_repetitions(self) -> None:
        calls: dict[tuple[str, str | None], int] = {}
        operations = {row["id"]: row for row in self.manifest["operations"]}

        observed_batches: dict[tuple[str, str | None], list[int | None]] = {}

        def measure(key: tuple[str, str | None], **kwargs: object) -> dict[str, Any]:
            repetition = calls.get(key, 0)
            calls[key] = repetition + 1
            base = 100_000 + (list(calls).index(key) * 10_000) + repetition
            if operations[key[0]]["measurement_kind"] == "latency":
                observed_batches.setdefault(key, []).append(
                    kwargs.get("batch_iterations")
                )
                batch = 16
                normalized = [base + (index % 3) for index in range(64)]
                return {
                    "samples": normalized,
                    "batch_iterations": batch,
                    "batch_duration_samples": [value * batch for value in normalized],
                }
            return {
                "samples": [base],
                "batch_iterations": 1,
                "batch_duration_samples": None,
            }

        environment = self._environment()
        conditioning = self._conditioning_snapshot(environment)
        with (
            patch(
                "tooling.performance_resource_certification._measure_key",
                side_effect=measure,
            ),
            patch(
                "tooling.performance_resource_certification._conditioning_snapshot",
                return_value=conditioning,
            ) as condition,
        ):
            active_manifest, baseline = calibrate_baseline(
                self.manifest,
                self.fixtures,
                artifacts={},
                artifact_fingerprints=self._artifact_fingerprints(),
                environment=environment,
                source_commit="2" * 40,
                rationale=(
                    "Synthetic orchestration proof for all governed repetitions."
                ),
            )

        expected_keys = performance_measurement_keys(self.manifest)
        self.assertEqual(set(calls), set(expected_keys))
        self.assertTrue(all(count == 5 for count in calls.values()))
        self.assertTrue(
            all(
                values == [None, 16, 16, 16, 16] for values in observed_batches.values()
            )
        )
        self.assertEqual(len(baseline["measurements"]), len(expected_keys))
        self.assertEqual(condition.call_count, 5)
        self.assertEqual(baseline["conditioning_repetitions"], [conditioning] * 5)
        validate_baseline(baseline, manifest=active_manifest, synthetic=True)

    def test_governed_writer_is_atomic_and_confined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            governed = (
                root / "tests/certification/performance-resource/1.0/baseline.json"
            )
            _write_json(governed, {"status": "passed"}, root=root)
            self.assertEqual(load_json(governed), {"status": "passed"})
            self.assertTrue(governed.read_bytes().endswith(b"\n"))
            self.assertEqual(list(governed.parent.glob("*.tmp")), [])

            with self.assertRaises(PerformanceResourceError) as raised:
                _write_json(root / "outside.json", {"status": "failed"}, root=root)
            self.assertEqual(raised.exception.code, "write-boundary")

    def test_controlled_manifest_mutations_fail_closed(self) -> None:
        removed = copy.deepcopy(self.manifest)
        removed["operations"].pop()
        removed["manifest_fingerprint"] = document_fingerprint(
            removed, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(removed, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "operation-denominator")

        partially_deactivated = copy.deepcopy(self.manifest)
        partially_deactivated["operations"][0]["state"] = "planned"
        partially_deactivated["operations"][0]["budget"] = {
            "state": "planned",
            "relative_regression_basis_points": None,
            "absolute_ceiling": None,
            "rationale": "Controlled partial activation must fail closed.",
        }
        partially_deactivated["manifest_fingerprint"] = document_fingerprint(
            partially_deactivated, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(
                partially_deactivated,
                fixtures=self.fixtures,
                inventory=self.inventory,
            )
        self.assertEqual(raised.exception.code, "partial-activation")

        shrunk = copy.deepcopy(self.manifest)
        shrunk["profile_partitions"][1]["operation_ids"].pop()
        shrunk["manifest_fingerprint"] = document_fingerprint(
            shrunk, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(shrunk, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "profile-partition")

        stale = copy.deepcopy(self.manifest)
        stale["measurement_policy"]["sample_iterations"] = 63
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(stale, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "manifest-fingerprint")

    def test_positive_fixture_cannot_claim_live_measurement_or_baseline(self) -> None:
        self.assertEqual(self.evidence["evidence_kind"], "synthetic-contract-fixture")
        self.assertEqual(
            self.evidence["operation_id"],
            "certification.performance-resource-local",
        )
        self.assertEqual(
            self.evidence["checks"],
            self.evidence["deterministic_evidence"]["checks"],
        )
        details = self.evidence["deterministic_evidence"]["checks"][0]["details"]
        self.assertFalse(details["live_measurement"])
        self.assertFalse(details["baseline_authority"])
        changed = copy.deepcopy(self.evidence)
        changed["deterministic_evidence"]["checks"][0]["details"][
            "live_measurement"
        ] = True
        changed["checks"] = copy.deepcopy(changed["deterministic_evidence"]["checks"])
        changed["evidence_fingerprint"] = document_fingerprint(
            changed["deterministic_evidence"], "not-present"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_evidence(changed, manifest=self.manifest)
        self.assertEqual(raised.exception.code, "fixture-check")

        mismatched = copy.deepcopy(self.evidence)
        mismatched["operation_id"] = "certification.performance-resource-full"
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_evidence(mismatched, manifest=self.manifest)
        self.assertEqual(raised.exception.code, "profile-result-envelope")

    def test_calibration_instability_names_the_coordinate_and_samples(self) -> None:
        with self.assertRaises(PerformanceResourceError) as raised:
            self._active_contract(unstable_first=True)
        self.assertEqual(raised.exception.code, "unstable-baseline")
        self.assertIn("latency:semantic-parse", str(raised.exception))
        self.assertIn("repetition medians=", str(raised.exception))

    def test_environment_rollover_is_os_only_and_passes_prior_contract(self) -> None:
        history = (
            BASELINE_PATH.parent
            / "history"
            / "947dee8367cd582d6360f13295296b0343316a4ad5698f0e559b71d370336b4d"
        )
        prior_manifest = load_json(history / "manifest.json")
        prior_baseline = load_json(history / "baseline.json")
        candidate_manifest = copy.deepcopy(prior_manifest)
        candidate_baseline = copy.deepcopy(prior_baseline)
        environment = candidate_baseline["environment"]
        environment["os_version"] = (
            "Windows 10 Pro 25H2 | build 26200.9278 | "
            "26100.1.amd64fre.ge_release.240331-1435"
        )
        attestation = environment["host_attestation"]
        attestation["host_os"] = "Windows 10 Pro 25H2 build 26200.9278"
        attestation["host_kernel_or_hypervisor"] = (
            "Windows NT 10.0.26200 native host; firmware guest indicators absent"
        )
        attestation["attestation_fingerprint"] = document_fingerprint(
            attestation, "attestation_fingerprint"
        )
        environment["host_attestation_fingerprint"] = attestation[
            "attestation_fingerprint"
        ]
        candidate_baseline["environment_fingerprint"] = environment_fingerprint(
            environment
        )

        report = validate_environment_rollover(
            prior_manifest,
            prior_baseline,
            candidate_manifest,
            candidate_baseline,
            expected_os_build="26200.9278",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["comparison_count"], 54)
        self.assertEqual(report["failed_comparisons"], 0)
        self.assertTrue(report["artifact_fingerprints_preserved"])

        changed_policy = copy.deepcopy(candidate_manifest)
        changed_policy["measurement_policy"]["sample_iterations"] = 63
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_environment_rollover(
                prior_manifest,
                prior_baseline,
                changed_policy,
                candidate_baseline,
                expected_os_build="26200.9278",
            )
        self.assertEqual(raised.exception.code, "rollover-contract-drift")

        changed_hardware = copy.deepcopy(candidate_baseline)
        changed_hardware["environment"]["cpu_model"] = "different CPU"
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_environment_rollover(
                prior_manifest,
                prior_baseline,
                candidate_manifest,
                changed_hardware,
                expected_os_build="26200.9278",
            )
        self.assertEqual(raised.exception.code, "rollover-environment-drift")

        regressed = copy.deepcopy(candidate_baseline)
        prior_row = prior_baseline["measurements"][0]
        regressed["measurements"][0]["statistics"]["median"] = (
            prior_row["budget"]["absolute_ceiling"] + 1
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_environment_rollover(
                prior_manifest,
                prior_baseline,
                candidate_manifest,
                regressed,
                expected_os_build="26200.9278",
            )
        self.assertEqual(raised.exception.code, "rollover-regression")

    def test_environment_rollover_reset_preserves_nonperformance_contract(self) -> None:
        planned = planned_environment_rollover_manifest(self.manifest)
        validate_manifest(planned, fixtures=self.fixtures, inventory=self.inventory)
        prior_operations = {row["id"]: row for row in self.manifest["operations"]}
        planned_operations = {row["id"]: row for row in planned["operations"]}
        for operation_id in PERFORMANCE_OPERATION_IDS:
            self.assertEqual(planned_operations[operation_id]["state"], "planned")
            self.assertIsNone(
                planned_operations[operation_id]["budget"]["absolute_ceiling"]
            )
        for operation_id in RESOURCE_OPERATION_IDS:
            self.assertEqual(
                planned_operations[operation_id], prior_operations[operation_id]
            )
        self.assertNotEqual(
            planned["manifest_fingerprint"], self.manifest["manifest_fingerprint"]
        )

    @staticmethod
    def _environment() -> dict[str, Any]:
        selected_topology = {
            "logical_cpu": 20,
            "online": True,
            "package_id": "0",
            "die_id": "0",
            "core_id": "10",
            "core_type": "unknown",
            "thread_siblings": "20",
        }
        reservation_evidence = {
            "selected_cpu_topology": selected_topology,
            "host_topology": [selected_topology],
            "online_cpus": [20],
            "cgroup_path": "/strling-performance",
            "cgroup_cpuset_effective": "20",
            "cgroup_cpu_max": "max 100000",
            "isolated_cpus": [20],
            "nohz_full_cpus": [20],
            "isolcpus": [20],
            "rcu_nocbs": [20],
            "irq_affinity": [0],
            "governor": "performance",
            "energy_performance_preference": "performance",
            "thermal_throttle_counts": {"core_throttle_count": 0},
            "unrelated_schedulable_tasks": [],
            "clocksource": "tsc",
        }
        host_attestation: dict[str, Any] = {
            "schema_version": "1.0.0",
            "attestation_kind": "strling-performance-host-reservation",
            "environment_kind": "dedicated-bare-metal",
            "host_id_sha256": "1" * 64,
            "host_os": "synthetic-host",
            "host_kernel_or_hypervisor": "synthetic-linux",
            "host_processor": {
                "vendor_id": "SyntheticVendor",
                "family": "1",
                "model": "2",
                "stepping": "3",
                "microcode": "0x1",
                "model_name": "synthetic-cpu",
                "logical_cpu_count": 32,
                "topology_sha256": "2" * 64,
            },
            "reservation": {
                "mechanism": "bare-metal-cpuset-isolation",
                "reservation_id": "synthetic-reservation",
                "host_logical_processors": [20],
                "host_physical_core_identity": "package-0/core-10",
                "cpu_quota": "unlimited",
                "exclusive": True,
                "housekeeping_excluded": True,
                "unrelated_workloads_excluded": True,
                "evidence_sha256": document_fingerprint(
                    reservation_evidence, "not-present"
                ),
            },
            "reservation_evidence": reservation_evidence,
            "conditioning": {
                "policy_id": "synthetic-conditioning",
                "executable_path": "/usr/local/libexec/strling-condition",
                "executable_sha256": "4" * 64,
            },
            "attestation_fingerprint": "0" * 64,
        }
        host_attestation["attestation_fingerprint"] = document_fingerprint(
            host_attestation, "attestation_fingerprint"
        )
        return {
            "os": "linux",
            "os_version": "synthetic-contract-fixture",
            "architecture": "x86_64",
            "cpu_model": "synthetic-cpu",
            "logical_cpu_count": 8,
            "memory_bytes": 17179869184,
            "python_version": "3.12.0",
            "runtime_abi": "glibc 2.39",
            "rustc_version": "rustc 1.75.0",
            "cargo_version": "cargo 1.75.0",
            "toolchain_sha256": {
                "python": "5" * 64,
                "rustc": "6" * 64,
                "cargo": "7" * 64,
            },
            "target_triple": "x86_64-unknown-linux-gnu",
            "build_profile": "release",
            "feature_set": [],
            "cpu_affinity_policy": "single-fixed-logical-cpu",
            "selected_logical_cpu": 20,
            "effective_cpu_affinity": [20],
            "effective_cpuset": "20",
            "execution_resource": {
                "cgroup_version": 2,
                "cgroup_path": "/strling-performance",
                "cgroup_cpuset_effective": "20",
                "cgroup_cpu_max": "max 100000",
                "clocksource": "tsc",
                "processor_topology": selected_topology,
            },
            "host_attestation": host_attestation,
            "host_attestation_fingerprint": host_attestation["attestation_fingerprint"],
        }

    @staticmethod
    def _artifact_fingerprints() -> dict[str, Any]:
        return {
            "runner": {
                "path": "runner/target/release/strling-performance-runner",
                "sha256": "8" * 64,
                "bytes": 100,
            },
            "kernel": {
                "path": "core/target/release/strling-kernel",
                "sha256": "9" * 64,
                "bytes": 200,
            },
            "interop": {
                "path": "bindings/interop/target/release/libstrling_interop.so",
                "sha256": "a" * 64,
                "bytes": 300,
            },
        }

    @staticmethod
    def _conditioning_snapshot(environment: dict[str, Any]) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "status": "passed",
            "policy_id": environment["host_attestation"]["conditioning"]["policy_id"],
            "host_attestation_fingerprint": environment["host_attestation_fingerprint"],
            "conditioner_sha256": environment["host_attestation"]["conditioning"][
                "executable_sha256"
            ],
            "selected_logical_cpu": 20,
            "effective_cpu_affinity": [20],
            "effective_cpuset": "20",
            "cgroup_cpu_max": "max 100000",
            "clocksource": "tsc",
            "thermal_state": "nominal",
            "power_state": "governed",
            "unrelated_workloads_excluded": True,
            "snapshot_fingerprint": "0" * 64,
        }
        snapshot["snapshot_fingerprint"] = document_fingerprint(
            snapshot, "snapshot_fingerprint"
        )
        return snapshot

    def _active_contract(
        self, *, unstable_first: bool = False
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        environment = self._environment()
        operations = {row["id"]: row for row in self.manifest["operations"]}
        repetitions: dict[tuple[str, str | None], list[list[int]]] = {}
        batch_iterations: dict[tuple[str, str | None], int] = {}
        batch_duration_repetitions: dict[
            tuple[str, str | None], list[list[int]] | None
        ] = {}
        for key_index, key in enumerate(performance_measurement_keys(self.manifest)):
            operation = operations[key[0]]
            base = 100_000 + (key_index * 10_000)
            repetition_rows = []
            for repetition in range(5):
                repetition_offset = repetition * 20
                if unstable_first and key_index == 0:
                    repetition_offset = repetition * 10_000
                if operation["measurement_kind"] == "latency":
                    repetition_rows.append(
                        [
                            base + repetition_offset + ((index % 5) - 2) * 10
                            for index in range(64)
                        ]
                    )
                else:
                    repetition_rows.append([base + repetition_offset])
            repetitions[key] = repetition_rows
            if operation["measurement_kind"] == "latency":
                batch_iterations[key] = 16
                batch_duration_repetitions[key] = [
                    [value * 16 for value in repetition]
                    for repetition in repetition_rows
                ]
            else:
                batch_iterations[key] = 1
                batch_duration_repetitions[key] = None
        return create_active_contract(
            self.manifest,
            self.fixtures,
            environment=environment,
            artifact_fingerprints=self._artifact_fingerprints(),
            conditioning_repetitions=[
                self._conditioning_snapshot(environment) for _ in range(5)
            ],
            source_commit="1" * 40,
            repetitions=repetitions,
            batch_iterations=batch_iterations,
            batch_duration_repetitions=batch_duration_repetitions,
            rationale=(
                "Synthetic complete calibration corpus for controlled contract tests."
            ),
        )


if __name__ == "__main__":
    unittest.main()
