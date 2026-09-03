from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.governance import (
    Change,
    Exemption,
    GovernanceError,
    evaluate_architecture,
    load_json,
    load_yaml,
    parse_name_status,
    path_matches,
    validate_declarations,
    validate_instance,
    validate_scope,
)


ROOT = Path(__file__).resolve().parents[2]


def task_fixture() -> dict[str, object]:
    task = load_yaml(ROOT / "governance/templates/task-record.yaml")
    assert isinstance(task, dict)
    task["scope"]["allowed_paths"] = ["governance/**"]
    task["scope"]["forbidden_paths"] = []
    task["scope"]["expected_files"] = []
    task["scope"]["permitted_generated_changes"] = []
    task["scope"]["expected_generated_outputs"] = []
    return task


def set_level(task: dict[str, object], name: str, level: str) -> None:
    task["change_classification"][name] = {
        "level": level,
        "evidence": [] if level == "none" else ["test evidence"],
    }


class PathMatchingTests(unittest.TestCase):
    def test_globs_are_case_sensitive_and_directory_aware(self) -> None:
        self.assertTrue(path_matches("docs/report.md", "docs/**"))
        self.assertTrue(path_matches("report.md", "**/*.md"))
        self.assertTrue(
            path_matches("bindings/r/v1.rockspec", "bindings/r/v[0-9].rockspec")
        )
        self.assertFalse(path_matches("Docs/report.md", "docs/**"))
        self.assertFalse(path_matches("docs/nested/report.md", "docs/*.md"))

    def test_unsafe_paths_are_rejected(self) -> None:
        for path in ("/absolute", "docs/../spec", "docs\\file"):
            with self.subTest(path=path), self.assertRaises(GovernanceError):
                path_matches(path, "docs/**")

    def test_rename_and_deletion_statuses_preserve_all_paths(self) -> None:
        changes = parse_name_status(
            b"R100\0old/name.py\0new/name.py\0D\0removed/file.py\0"
        )
        self.assertEqual(("old/name.py", "new/name.py"), changes[0].paths)
        self.assertEqual(("removed/file.py",), changes[1].paths)

    def test_git_for_windows_path_separators_are_normalized_at_ingestion(self) -> None:
        changes = parse_name_status(
            b"M\0tooling\\architecture_fitness.py\0R100\0old\\name.py\0new\\name.py\0"
        )
        self.assertEqual(("tooling/architecture_fitness.py",), changes[0].paths)
        self.assertEqual(("old/name.py", "new/name.py"), changes[1].paths)


class ScopeValidationTests(unittest.TestCase):
    def test_allowed_change_passes(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("M", None, "governance/policy.json")]
        )
        self.assertEqual("passed", result.status)

    def test_forbidden_path_fails_even_when_allowed(self) -> None:
        task = task_fixture()
        task["scope"]["forbidden_paths"] = ["governance/private/**"]
        result = validate_scope(
            task, [Change("M", None, "governance/private/policy.json")]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("forbidden", result.findings[0])

    def test_undeclared_path_fails(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("M", None, "tooling/new_check.py")]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("outside every allowed path", result.findings[0])

    def test_both_sides_of_rename_are_validated(self) -> None:
        result = validate_scope(
            task_fixture(),
            [Change("R100", "tooling/old.py", "governance/new.py")],
        )
        self.assertEqual("failed", result.status)
        self.assertIn("tooling/old.py", result.findings[0])

    def test_deleted_path_is_validated(self) -> None:
        result = validate_scope(
            task_fixture(), [Change("D", "tooling/removed.py", None)]
        )
        self.assertEqual("failed", result.status)
        self.assertIn("tooling/removed.py", result.findings[0])

    def test_exact_bounded_exemption_can_cover_one_scope_rule(self) -> None:
        exemption = Exemption(
            "WVR-TEST-001",
            "scope-undeclared-path",
            ("tooling/one.py",),
        )
        result = validate_scope(
            task_fixture(),
            [Change("M", None, "tooling/one.py")],
            [exemption],
        )
        self.assertEqual("passed", result.status)


class DeclarationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.control = load_json(ROOT / "governance/change-control.json")
        cls.registry = load_json(ROOT / "governance/generated-artifacts.json")
        cls.generated_patterns = ["tests/spec/**", "docs/generated/**"]
        assert isinstance(cls.control, dict)
        assert isinstance(cls.registry, dict)

    def test_generated_output_requires_declaration_and_permission(self) -> None:
        task = task_fixture()
        task["scope"]["allowed_paths"] = ["tests/certification/profile-source/**"]
        result = validate_declarations(
            task,
            [
                Change(
                    "M",
                    None,
                    "tests/certification/profile-source/1.0/definitions.json",
                )
            ],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any(
                "generated_output_change is undeclared" in item
                for item in result.findings
            )
        )
        self.assertTrue(any("is not permitted" in item for item in result.findings))

        set_level(task, "generated_output_change", "compatible")
        task["scope"]["permitted_generated_changes"] = ["profile-source-definitions"]
        task["scope"]["expected_generated_outputs"] = ["profile-source-definitions"]
        result = validate_declarations(
            task,
            [
                Change(
                    "M",
                    None,
                    "tests/certification/profile-source/1.0/definitions.json",
                )
            ],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("passed", result.status)

    def test_inconsistent_semantic_declaration_fails(self) -> None:
        task = task_fixture()
        task["scope"]["allowed_paths"] = ["spec/**"]
        result = validate_declarations(
            task,
            [Change("M", None, "spec/grammar/dsl.ebnf")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("semantic_change is undeclared" in item for item in result.findings)
        )

    def test_unregistered_generated_output_fails(self) -> None:
        task = task_fixture()
        result = validate_declarations(
            task,
            [Change("M", None, "docs/generated/unknown.txt")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertTrue(
            any("unregistered generated output" in item for item in result.findings)
        )

    def test_documentation_only_does_not_require_semantic_change(self) -> None:
        task = task_fixture()
        task["change_classification"]["documentation_only"] = True
        task["change_classification"]["internal_implementation"] = False
        result = validate_declarations(
            task,
            [Change("M", None, "docs/guide.md")],
            self.control,
            self.registry,
            self.generated_patterns,
        )
        self.assertEqual("passed", result.status)


class ArchitectureValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "tooling").mkdir()
        self.task = task_fixture()
        self.control = {
            "active_task": "docs/migration/records/task.yaml",
        }
        self.registry = {"registry_version": 1, "artifacts": []}

    def evaluate(self, rule: dict[str, object], changes=()):
        return evaluate_architecture(
            {"registry_version": 1, "rules": [rule]},
            root=self.root,
            task=self.task,
            changes=list(changes),
            control=self.control,
            artifact_registry=self.registry,
        )[0]

    def write_profile_workflows(
        self,
        *,
        ci_invocation: str = './strling profile "$PROFILE" --artifact "$ARTIFACT_PATH"',
        cd_invocation: str = './strling profile release --artifact "$ARTIFACT_PATH"',
        product_invocation: str = 'python3 tooling/product_certification.py --profile-artifact "$ARTIFACT_PATH" --artifact "$PRODUCT_ARTIFACT_PATH" --report "$PRODUCT_REPORT_PATH"',
        upload_action: str = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        schedule_profile: str = "full",
        upload_non_authoritative: bool = True,
    ) -> None:
        workflows = self.root / ".github/workflows"
        workflows.mkdir(parents=True)
        continue_line = (
            "        continue-on-error: true\n" if upload_non_authoritative else ""
        )
        (workflows / "ci.yml").write_text(
            "name: CI\n"
            "# selectable profiles: local pull-request full release\n"
            "jobs:\n"
            "  quality-hardgates:\n"
            "    steps:\n"
            "      - run: |\n"
            '          workflow_dispatch) profile="$REQUESTED_PROFILE" ;;\n'
            '          pull_request) profile="pull-request" ;;\n'
            f'          schedule) profile="{schedule_profile}" ;;\n'
            '          profile="release"\n'
            '          profile="pull-request"\n'
            f"          {ci_invocation}\n"
            "      - if: >-\n"
            "          always() &&\n"
            "          steps.certification_profile.outputs.profile == 'full'\n"
            "          steps.certification_profile.outputs.profile == 'release'\n"
            "          steps.certification_profile.outputs.product_artifact_path\n"
            "          steps.certification_profile.outputs.product_report_path\n"
            f"          {product_invocation}\n"
            "      - if: ${{ always() }}\n"
            f"{continue_line}"
            f"        uses: {upload_action}\n"
            "        with:\n"
            "          steps.certification_profile.outputs.product_artifact_path\n"
            "          steps.certification_profile.outputs.product_report_path\n"
            "          if-no-files-found: warn\n",
            encoding="utf-8",
        )
        (workflows / "cd.yml").write_text(
            "name: CD\n"
            "jobs:\n"
            "  release-certification:\n"
            "    steps:\n"
            "      - run: |\n"
            f"          {cd_invocation}\n"
            "      - if: ${{ always() }}\n"
            "        run: |\n"
            "          artifacts/product-certification-release.json\n"
            "          artifacts/product-certification-release.md\n"
            f"          {product_invocation}\n"
            "      - if: ${{ always() }}\n"
            f"{continue_line}"
            f"        uses: {upload_action}\n"
            "        with:\n"
            "          artifacts/product-certification-release.json\n"
            "          artifacts/product-certification-release.md\n"
            "          if-no-files-found: warn\n"
            "  verify-release:\n"
            "    needs: release-certification\n",
            encoding="utf-8",
        )

    @staticmethod
    def ci_profile_rule() -> dict[str, object]:
        return {
            "id": "canonical-ci-profile-routing",
            "status": "enforced",
            "kind": "ci-profile-routing",
            "configuration": {
                "sources": [
                    ".github/workflows/ci.yml",
                    ".github/workflows/cd.yml",
                ]
            },
        }

    def test_canonical_ci_profile_routing_passes(self) -> None:
        self.write_profile_workflows()
        self.assertEqual("passed", self.evaluate(self.ci_profile_rule()).status)

    def test_ci_profile_routing_rejects_direct_quality_implementation(self) -> None:
        self.write_profile_workflows(
            ci_invocation='python3 tooling/quality.py profile "$PROFILE" --artifact "$ARTIFACT_PATH"'
        )
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(any("directly" in finding for finding in result.findings))

    def test_ci_profile_routing_rejects_compatibility_alias_substitution(self) -> None:
        self.write_profile_workflows(ci_invocation="./strling check")
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("compatibility aliases" in finding for finding in result.findings)
        )

    def test_ci_profile_routing_rejects_missing_product_derivation(self) -> None:
        self.write_profile_workflows(product_invocation="echo product-omitted")
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any(
                "structured product derivation" in finding
                for finding in result.findings
            )
        )

    def test_ci_profile_routing_rejects_success_only_product_derivation(self) -> None:
        self.write_profile_workflows()
        for relative in (".github/workflows/ci.yml", ".github/workflows/cd.yml"):
            path = self.root / relative
            path.write_text(
                path.read_text(encoding="utf-8").replace("always()", "success()", 1),
                encoding="utf-8",
            )
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any(
                "preserve nonpassing profile evidence" in finding
                for finding in result.findings
            )
        )

    def test_ci_profile_routing_rejects_mutable_artifact_action(self) -> None:
        self.write_profile_workflows(upload_action="actions/upload-artifact@v7")
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("immutable action" in finding for finding in result.findings)
        )

    def test_ci_profile_routing_rejects_wrong_event_mapping(self) -> None:
        self.write_profile_workflows(schedule_profile="pull-request")
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("routing fragment" in finding for finding in result.findings)
        )

    def test_ci_profile_routing_rejects_authoritative_artifact_upload(self) -> None:
        self.write_profile_workflows(upload_non_authoritative=False)
        result = self.evaluate(self.ci_profile_rule())
        self.assertEqual("failed", result.status)
        self.assertTrue(
            any("non-authoritative" in finding for finding in result.findings)
        )

    def test_rust_crate_boundary_rejects_binding_path_dependency(self) -> None:
        (self.root / "core/src").mkdir(parents=True)
        (self.root / "bindings/rust").mkdir(parents=True)
        (self.root / "core/Cargo.toml").write_text(
            '[dependencies]\nlegacy = { path = "../bindings/rust" }\n',
            encoding="utf-8",
        )
        (self.root / "core/src/lib.rs").write_text("", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "kernel-boundary",
                "status": "enforced",
                "kind": "rust-crate-boundary",
                "configuration": {
                    "manifest": "core/Cargo.toml",
                    "sources": ["core/src/**/*.rs"],
                    "forbidden_repository_roots": ["bindings", "tooling"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("bindings/rust", result.findings[0])

    def test_rust_crate_boundary_rejects_tooling_source_inclusion(self) -> None:
        (self.root / "core/src").mkdir(parents=True)
        (self.root / "tooling").mkdir(exist_ok=True)
        (self.root / "tooling/model.rs").write_text("", encoding="utf-8")
        (self.root / "core/Cargo.toml").write_text(
            '[dependencies]\nserde = "1"\n', encoding="utf-8"
        )
        (self.root / "core/src/lib.rs").write_text(
            '#[path = "../../tooling/model.rs"]\nmod model;\n',
            encoding="utf-8",
        )
        result = self.evaluate(
            {
                "id": "kernel-boundary",
                "status": "enforced",
                "kind": "rust-crate-boundary",
                "configuration": {
                    "manifest": "core/Cargo.toml",
                    "sources": ["core/src/**/*.rs"],
                    "forbidden_repository_roots": ["bindings", "tooling"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("tooling/model.rs", result.findings[0])

    def test_native_adapter_boundary_requires_canonical_route(self) -> None:
        (self.root / "bindings/c/src").mkdir(parents=True)
        (self.root / "bindings/c/src/strling.c").write_text(
            "void execute(void) {}\n", encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "c-native-boundary",
                "status": "enforced",
                "kind": "native-adapter-boundary",
                "configuration": {
                    "sources": ["bindings/c/src/**/*.c"],
                    "forbidden_paths": ["bindings/c/src/core/**"],
                    "forbidden_markers": ["pcre2_compile"],
                    "required_markers": [
                        {
                            "path": "bindings/c/src/strling.c",
                            "markers": ["strling_interop_execute_v1"],
                        }
                    ],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("required canonical adapter marker", result.findings[0])

    def test_native_adapter_boundary_rejects_semantic_copy(self) -> None:
        (self.root / "bindings/c/src/core").mkdir(parents=True)
        (self.root / "bindings/c/src/strling.c").write_text(
            "strling_interop_execute_v1();\n", encoding="utf-8"
        )
        (self.root / "bindings/c/src/core/parser.c").write_text(
            "pcre2_compile();\n", encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "c-native-boundary",
                "status": "enforced",
                "kind": "native-adapter-boundary",
                "configuration": {
                    "sources": ["bindings/c/src/**/*.c"],
                    "forbidden_paths": ["bindings/c/src/core/**"],
                    "forbidden_markers": ["pcre2_compile"],
                    "required_markers": [
                        {
                            "path": "bindings/c/src/strling.c",
                            "markers": ["strling_interop_execute_v1"],
                        }
                    ],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertTrue(any("retired semantic" in item for item in result.findings))

    def test_forbidden_dependency_violation_fails(self) -> None:
        (self.root / "tooling/governance.py").write_text(
            "import bindings.python.compiler\n", encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "governance-boundary",
                "status": "enforced",
                "kind": "forbidden-dependency",
                "configuration": {
                    "sources": ["tooling/governance.py"],
                    "forbidden_dependencies": ["bindings"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("bindings.python.compiler", result.findings[0])

    def test_valid_dependency_passes(self) -> None:
        (self.root / "tooling/governance.py").write_text(
            "import json\n", encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "governance-boundary",
                "status": "enforced",
                "kind": "forbidden-dependency",
                "configuration": {
                    "sources": ["tooling/governance.py"],
                    "forbidden_dependencies": ["bindings"],
                },
            }
        )
        self.assertEqual("passed", result.status)
        self.assertEqual([], result.findings)

    def test_valid_transition_is_reported_without_failing(self) -> None:
        result = self.evaluate(
            {
                "id": "binding-transition",
                "status": "transitional",
                "kind": "tracked-transition",
                "configuration": {"tracked_paths": ["bindings/**"]},
                "rationale": "Legacy bindings remain.",
                "retirement_condition": "Migrate them.",
            }
        )
        self.assertEqual("transitional", result.status)
        self.assertEqual([], result.findings)

    def test_transitional_forbidden_import_is_reported_without_failing(self) -> None:
        source = self.root / "tooling/lsp.py"
        source.write_text("import STRling.core.parser\n", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "lsp-transition",
                "status": "transitional",
                "kind": "forbidden-import",
                "configuration": {
                    "sources": ["tooling/lsp.py"],
                    "forbidden_modules": ["STRling"],
                },
                "rationale": "The canonical service is not available.",
                "retirement_condition": "Route through the canonical service.",
            }
        )
        self.assertEqual("transitional", result.status)
        self.assertTrue(any("STRling.core.parser" in item for item in result.findings))

    def test_future_rule_does_not_block_current_architecture(self) -> None:
        source = self.root / "tooling/lsp.py"
        source.write_text("import STRling.core.parser\n", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "future-canonical-dependency",
                "status": "future",
                "kind": "forbidden-import",
                "configuration": {
                    "sources": ["tooling/lsp.py"],
                    "forbidden_modules": ["STRling"],
                },
                "rationale": "The canonical service is not available.",
                "activation_condition": "Activate after migration.",
            }
        )
        self.assertEqual("future", result.status)
        self.assertEqual([], result.findings)

    def test_new_top_level_directory_requires_architecture_declaration(self) -> None:
        rule = {
            "id": "top-level",
            "status": "enforced",
            "kind": "new-top-level-directory",
            "configuration": {
                "allowed_top_level_directories": ["tooling"],
                "requires_declaration": "architecture_change",
            },
        }
        change = Change("A", None, "newcore/compiler.py")
        self.assertEqual("failed", self.evaluate(rule, [change]).status)
        set_level(self.task, "architecture_change", "additive")
        self.assertEqual("passed", self.evaluate(rule, [change]).status)

    def test_new_semantic_implementation_island_requires_declaration(self) -> None:
        source = self.root / "tooling/compiler.py"
        source.write_text(
            "class Compiler:\n    def compile(self):\n        return None\n",
            encoding="utf-8",
        )
        rule = {
            "id": "semantic-island",
            "status": "enforced",
            "kind": "semantic-island-placement",
            "configuration": {
                "guarded_roots": ["tooling"],
                "semantic_names": ["parser", "compiler", "emitter"],
                "requires_declaration": "architecture_change",
                "registered_paths": ["tooling/compiler.py"],
            },
        }
        change = Change("A", None, "tooling/compiler.py")
        self.assertEqual("failed", self.evaluate(rule, [change]).status)
        set_level(self.task, "architecture_change", "additive")
        self.assertEqual("passed", self.evaluate(rule, [change]).status)

    def test_new_semantic_implementation_island_must_be_registered(self) -> None:
        source = self.root / "tooling/compiler.py"
        source.write_text("class Compiler:\n    pass\n", encoding="utf-8")
        rule = {
            "id": "semantic-island",
            "status": "enforced",
            "kind": "semantic-island-placement",
            "configuration": {
                "guarded_roots": ["tooling"],
                "semantic_names": ["compiler"],
                "requires_declaration": "architecture_change",
                "registered_paths": [],
            },
        }
        set_level(self.task, "architecture_change", "additive")
        result = self.evaluate(rule, [Change("A", None, "tooling/compiler.py")])
        self.assertEqual("failed", result.status)
        self.assertIn("unregistered semantic implementation", result.findings[0])

    def test_test_file_is_not_misclassified_as_semantic_island(self) -> None:
        (self.root / "tooling/tests").mkdir()
        source = self.root / "tooling/tests/test_parser.py"
        source.write_text("def test_parser():\n    pass\n", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "semantic-island",
                "status": "enforced",
                "kind": "semantic-island-placement",
                "configuration": {
                    "guarded_roots": ["tooling"],
                    "semantic_names": ["parser"],
                    "requires_declaration": "architecture_change",
                    "registered_paths": [],
                },
            },
            [Change("A", None, "tooling/tests/test_parser.py")],
        )
        self.assertEqual("passed", result.status)

    def test_binding_local_parser_declaration_is_rejected(self) -> None:
        source = self.root / "bindings/new/bridge.py"
        source.parent.mkdir(parents=True)
        source.write_text("class DslParser:\n    pass\n", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "binding-semantics",
                "status": "enforced",
                "kind": "binding-semantic-path-boundary",
                "configuration": {
                    "sources": ["bindings/**"],
                    "semantic_names": ["parser", "capability_evaluator"],
                    "permitted_paths": ["bindings/current/Compiler.py"],
                    "permitted_declarations": [],
                    "excluded_path_parts": ["tests"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("DslParser", result.findings[0])

    def test_adapter_semantic_logic_requires_exact_classification(self) -> None:
        source = self.root / "bindings/new/bridge.py"
        source.parent.mkdir(parents=True)
        source.write_text("class CapabilitiesEvaluator:\n    pass\n", encoding="utf-8")
        rule = {
            "id": "binding-semantics",
            "status": "enforced",
            "kind": "binding-semantic-path-boundary",
            "configuration": {
                "sources": ["bindings/**"],
                "semantic_names": ["capability"],
                "permitted_paths": ["bindings/current/Compiler.py"],
                "permitted_declarations": [],
                "excluded_path_parts": ["tests"],
            },
        }
        self.assertEqual("failed", self.evaluate(rule).status)
        rule["configuration"]["permitted_declarations"] = [
            {"path": "bindings/new/bridge.py", "names": ["CapabilitiesEvaluator"]}
        ]
        self.assertEqual("passed", self.evaluate(rule).status)

    def test_retained_history_cannot_be_promoted_into_core_authority(self) -> None:
        history = self.root / "tests/spec"
        history.mkdir(parents=True)
        (history / "legacy.json").write_text("{}", encoding="utf-8")
        core = self.root / "core"
        core.mkdir()
        (core / "authority.json").write_text(
            '{"semantic_source": "tests/spec/legacy.json"}', encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "history",
                "status": "enforced",
                "kind": "non-normative-history-boundary",
                "configuration": {
                    "history_roots": ["tests/spec/**"],
                    "allowed_files": ["tests/spec/*.json"],
                    "consumer_sources": ["core/**"],
                    "forbidden_reference_markers": ["tests/spec/"],
                    "forbidden_extensions": [".py"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("imports retained historical data", result.findings[0])

    def test_retired_transitional_dependency_is_rejected(self) -> None:
        (self.root / "package.json").write_text(
            '{"devDependencies": {"typescript": "1.0.0"}}', encoding="utf-8"
        )
        (self.root / "package-lock.json").write_text(
            '{"packages": {"node_modules/typescript": {}}}', encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "retired-dependency",
                "status": "enforced",
                "kind": "retired-dependency-boundary",
                "configuration": {
                    "dependency_manifests": [
                        {
                            "path": "package.json",
                            "forbidden_dependencies": ["typescript"],
                            "lockfiles": ["package-lock.json"],
                        }
                    ]
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("retired transitional dependency", result.findings[0])

    def test_retired_architecture_path_is_rejected(self) -> None:
        source = self.root / "tooling/audit_omega.py"
        source.write_text("pass\n", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "retired-path",
                "status": "enforced",
                "kind": "retired-path-boundary",
                "configuration": {"forbidden_paths": ["tooling/audit_omega.py"]},
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("retired architecture path", result.findings[0])

    def test_schema_reference_inside_allowed_root_passes(self) -> None:
        schema_root = self.root / "spec/schema"
        schema_root.mkdir(parents=True)
        (schema_root / "base.json").write_text("{}", encoding="utf-8")
        (schema_root / "child.json").write_text(
            '{"$ref": "./base.json"}', encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "schema-boundary",
                "status": "enforced",
                "kind": "schema-reference-boundary",
                "configuration": {
                    "sources": ["spec/schema/*.json"],
                    "allowed_reference_roots": ["spec/schema"],
                },
            }
        )
        self.assertEqual("passed", result.status)

    def test_schema_reference_outside_allowed_root_fails(self) -> None:
        schema_root = self.root / "spec/schema"
        generated_root = self.root / "generated"
        schema_root.mkdir(parents=True)
        generated_root.mkdir()
        (generated_root / "output.json").write_text("{}", encoding="utf-8")
        (schema_root / "child.json").write_text(
            '{"$ref": "../../generated/output.json"}', encoding="utf-8"
        )
        result = self.evaluate(
            {
                "id": "schema-boundary",
                "status": "enforced",
                "kind": "schema-reference-boundary",
                "configuration": {
                    "sources": ["spec/schema/*.json"],
                    "allowed_reference_roots": ["spec/schema"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("outside allowed roots", result.findings[0])

    def test_malformed_schema_source_fails_closed(self) -> None:
        schema_root = self.root / "spec/schema"
        schema_root.mkdir(parents=True)
        (schema_root / "bad.json").write_text("{", encoding="utf-8")
        result = self.evaluate(
            {
                "id": "schema-boundary",
                "status": "enforced",
                "kind": "schema-reference-boundary",
                "configuration": {
                    "sources": ["spec/schema/*.json"],
                    "allowed_reference_roots": ["spec/schema"],
                },
            }
        )
        self.assertEqual("failed", result.status)
        self.assertIn("malformed JSON schema", result.findings[0])

    def test_implementation_fixture_authority_is_bounded(self) -> None:
        rule = {
            "id": "fixture-authority",
            "status": "enforced",
            "kind": "artifact-authority-boundary",
            "configuration": {
                "artifact_ids": ["fixtures"],
                "allowed_authorities": ["transitional-compatibility-evidence"],
            },
        }
        self.registry["artifacts"] = [
            {
                "id": "fixtures",
                "authority": "transitional-compatibility-evidence",
            }
        ]
        self.assertEqual("passed", self.evaluate(rule).status)
        self.registry["artifacts"][0]["authority"] = "certification-evidence"
        self.assertEqual("failed", self.evaluate(rule).status)

    def test_malformed_task_record_is_rejected(self) -> None:
        schema = load_json(ROOT / "governance/schemas/task-record.schema.json")
        invalid = task_fixture()
        del invalid["change_classification"]["semantic_change"]
        with self.assertRaises(GovernanceError):
            validate_instance(invalid, schema, "task record")


if __name__ == "__main__":
    unittest.main()
