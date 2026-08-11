from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import cast

from tooling.certification import (
    aggregate_profile_exit,
    aggregate_profile_status,
    build_certification_artifact,
    profile_definition_fingerprint,
    render_certification_summary,
    validate_certification_artifact,
    write_certification_artifact,
)
from tooling.tests.test_quality import (
    Execution,
    OperationResult,
    QualityRunner,
    Toolchain,
    policy,
    target_config,
)


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_STATE = {"commit": "2" * 40, "dirty": False}


def configured_policy() -> dict[str, object]:
    alpha = target_config(
        {
            "lint": "configured",
            "typecheck": "configured",
            "build": "configured",
            "test": "configured",
        },
        {
            "lint": ["fixture-lint"],
            "typecheck": ["fixture-typecheck"],
            "build": ["fixture-build"],
            "test": ["fixture-test"],
        },
    )
    beta = target_config(
        {
            "lint": "configured",
            "typecheck": "configured",
            "build": "configured",
            "test": "configured",
        },
        {
            "lint": ["fixture-lint"],
            "typecheck": ["fixture-typecheck"],
            "build": ["fixture-build"],
            "test": ["fixture-test"],
        },
    )
    return policy(alpha=alpha, beta=beta)


def artifact(
    profile: dict[str, object],
    results: list[OperationResult],
    generated_at: str = "2026-08-11T12:00:00Z",
) -> dict[str, object]:
    statuses = [result.status for result in results]
    return build_certification_artifact(
        root=ROOT,
        profile_id="local",
        profile_definition=profile,
        requested_component=None,
        results=[result.as_dict() for result in results],
        aggregate_status=aggregate_profile_status(statuses),
        exit_code=aggregate_profile_exit(statuses),
        resolved_repository_state=REPOSITORY_STATE,
        generated_at=generated_at,
    )


class ProfileCertificationProperties(unittest.TestCase):
    def test_deterministic_execution_matches_canonical_membership_and_order(
        self,
    ) -> None:
        toolchain = Toolchain(configured_policy(), ROOT)
        runner = QualityRunner(toolchain, lambda *_args: Execution(0))
        for profile_id in ("local", "pull-request", "full", "release"):
            with self.subTest(profile=profile_id):
                definition = toolchain.profile(profile_id)
                members = cast(list[dict[str, object]], definition["operations"])
                expected = [
                    (str(member["operation"]), str(target))
                    for member in members
                    for target in cast(list[str], member["targets"])
                ]
                first = runner.run_profile(profile_id, None)
                second = runner.run_profile(profile_id, None)
                self.assertEqual(
                    expected,
                    [(result.operation, result.component) for result in first],
                )
                self.assertEqual(
                    [result.as_dict() for result in first],
                    [result.as_dict() for result in second],
                )

    def test_membership_exists_only_in_canonical_profile_definitions(self) -> None:
        data = configured_policy()
        policy_data = cast(dict[str, object], data["policy"])
        registry = cast(dict[str, object], policy_data["operation_registry"])
        registry["unselected_gate"] = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-unselected"],
            "network": "offline",
        }
        calls: list[str] = []
        toolchain = Toolchain(data, ROOT)
        results = QualityRunner(
            toolchain,
            lambda *_args: Execution(0),
            hardgate_executor=lambda operation, _command: (
                calls.append(operation) or Execution(0)
            ),
        ).run_profile("local", None)
        self.assertNotIn("unselected_gate", [result.operation for result in results])
        self.assertEqual([], calls)
        self.assertTrue(
            all(
                "profiles" not in cast(dict[str, object], definition)
                for definition in registry.values()
            )
        )

    def test_component_selection_cannot_bypass_repository_gate(self) -> None:
        data = configured_policy()
        policy_data = cast(dict[str, object], data["policy"])
        registry = cast(dict[str, object], policy_data["operation_registry"])
        registry["mandatory_gate"] = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-mandatory"],
            "network": "offline",
        }
        profiles = cast(dict[str, object], policy_data["profiles"])
        for profile in profiles.values():
            members = cast(list[object], cast(dict[str, object], profile)["operations"])
            members.insert(0, {"operation": "mandatory_gate"})
        calls: list[str] = []
        results = QualityRunner(
            Toolchain(data, ROOT),
            lambda *_args: Execution(0),
            hardgate_executor=lambda operation, _command: (
                calls.append(operation) or Execution(0)
            ),
        ).run_profile("local", "beta")
        self.assertEqual("mandatory_gate", results[0].operation)
        self.assertEqual("alpha", results[0].component)
        self.assertEqual(["mandatory_gate"], calls)
        self.assertEqual(["beta", "beta"], [result.component for result in results[1:]])

    def test_blocking_states_cannot_produce_a_false_pass(self) -> None:
        blockers = (
            "failed",
            "incomplete",
            "unavailable",
            "not_yet_configured",
            "not_yet_enforceable",
        )
        for blocker in blockers:
            with self.subTest(status=blocker):
                statuses = ("passed", blocker, "waived")
                self.assertNotEqual("passed", aggregate_profile_status(statuses))
                self.assertEqual(1, aggregate_profile_exit(statuses))

    def test_waived_evidence_remains_distinct_from_passed(self) -> None:
        profile = cast(
            dict[str, object],
            Toolchain(configured_policy(), ROOT).profile("local"),
        )
        waived_result = {
            "checks": [
                {
                    "check_id": "security.fixture",
                    "status": "waived",
                    "findings": [
                        {
                            "code": "FIXTURE-WAIVED",
                            "waiver_id": "WVR-TEST-001",
                        }
                    ],
                }
            ]
        }
        results = [
            OperationResult("lint", "alpha", "passed", ["fixture-lint"], 0, None),
            OperationResult(
                "security_fixture",
                "repository",
                "waived",
                ["fixture-security"],
                0,
                None,
                structured_result=waived_result,
            ),
        ]
        evidence = artifact(profile, results)
        aggregate = evidence["deterministic_evidence"]["aggregate"]
        self.assertEqual("waived", aggregate["status"])
        self.assertEqual(1, aggregate["counts"]["passed"])
        self.assertEqual(1, aggregate["counts"]["waived"])
        summary = render_certification_summary(evidence)
        self.assertIn("WVR-TEST-001", summary)
        self.assertIn("FIXTURE-WAIVED", summary)

    def test_artifact_and_summary_use_the_exact_exit_result_set(self) -> None:
        profile = cast(
            dict[str, object],
            Toolchain(configured_policy(), ROOT).profile("local"),
        )
        results = [
            OperationResult("lint", "alpha", "passed", ["fixture-lint"], 0, None),
            OperationResult(
                "test",
                "beta",
                "unavailable",
                None,
                None,
                "fixture runtime unavailable",
            ),
        ]
        evidence = artifact(profile, results)
        deterministic = evidence["deterministic_evidence"]
        operations = deterministic["operations"]
        self.assertEqual(
            [result.as_dict()["status"] for result in results],
            [operation["status"] for operation in operations],
        )
        self.assertEqual("unavailable", deterministic["aggregate"]["status"])
        self.assertEqual(1, deterministic["aggregate"]["exit_code"])
        summary = render_certification_summary(evidence)
        self.assertIn("Aggregate: UNAVAILABLE", summary)
        self.assertIn("test@beta - fixture runtime unavailable", summary)

    def test_certification_is_input_immutable(self) -> None:
        before = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        toolchain = Toolchain(configured_policy(), ROOT)
        results = QualityRunner(toolchain, lambda *_args: Execution(0)).run_profile(
            "local", None
        )
        profile = cast(dict[str, object], toolchain.profile("local"))
        evidence = artifact(profile, results)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "certification.json"
            write_certification_artifact(path, evidence)
            validate_certification_artifact(ROOT, evidence)
        after = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(before, after)

    def test_profile_ratchet_requires_no_executor_or_artifact_redefinition(
        self,
    ) -> None:
        data = configured_policy()
        policy_data = cast(dict[str, object], data["policy"])
        profiles = cast(dict[str, object], policy_data["profiles"])
        original_local = cast(dict[str, object], profiles["local"])
        original_fingerprint = profile_definition_fingerprint(original_local)
        registry = cast(dict[str, object], policy_data["operation_registry"])
        registry["ratchet_gate"] = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-ratchet"],
            "network": "offline",
        }
        for profile in profiles.values():
            definition = cast(dict[str, object], profile)
            definition["definition_version"] = "1.1.0"
            members = cast(list[object], definition["operations"])
            members.insert(0, {"operation": "ratchet_gate"})

        toolchain = Toolchain(data, ROOT)
        calls: list[str] = []
        results = QualityRunner(
            toolchain,
            lambda *_args: Execution(0),
            hardgate_executor=lambda operation, _command: (
                calls.append(operation) or Execution(0)
            ),
        ).run_profile("local", None)
        self.assertEqual(["ratchet_gate"], calls)
        self.assertEqual("ratchet_gate", results[0].operation)
        profile = cast(dict[str, object], toolchain.profile("local"))
        evidence = artifact(profile, results)
        self.assertNotEqual(
            original_fingerprint, profile_definition_fingerprint(profile)
        )
        self.assertEqual(
            "ratchet_gate",
            evidence["deterministic_evidence"]["operations"][0]["operation_id"],
        )


if __name__ == "__main__":
    unittest.main()
