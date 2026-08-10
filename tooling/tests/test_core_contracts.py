from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tooling.core_contract_validation import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    CoreContractError,
    load_mapping,
    validate_fixture_coverage,
    validate_mapping_document,
    validate_repository,
    validate_source_boundaries,
)


ROOT = Path(__file__).resolve().parents[2]


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class CoreSchemaMappingTests(unittest.TestCase):
    def test_current_mapping_and_fixture_corpus_pass(self) -> None:
        self.assertEqual((11, 62), validate_repository(ROOT))
        self.assertEqual(62, validate_fixture_coverage(ROOT))

    def test_changed_schema_without_mapping_update_fails(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        schema = mapping["schemas"][0]["schema"]
        changed = (ROOT / schema).read_bytes() + b"\n"
        with self.assertRaisesRegex(CoreContractError, "fingerprint is stale"):
            validate_mapping_document(
                mapping,
                ROOT,
                content_overrides={schema: changed},
            )

    def test_missing_or_unknown_mapping_fields_fail(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        missing = copy.deepcopy(mapping)
        missing["schemas"].pop()
        with self.assertRaisesRegex(CoreContractError, "every canonical family"):
            validate_mapping_document(missing, ROOT)

        unknown = copy.deepcopy(mapping)
        unknown["generated_by"] = "rust"
        with self.assertRaisesRegex(CoreContractError, "unknown or missing"):
            validate_mapping_document(unknown, ROOT)

    def test_semantic_mapping_requires_normalization_stage(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        semantic = next(
            entry
            for entry in changed["schemas"]
            if entry["schema"] == "spec/contracts/1.0/semantic-ir.schema.json"
        )
        semantic["rust_modules"] = ["semantic"]
        with self.assertRaisesRegex(CoreContractError, "dependency order"):
            validate_mapping_document(changed, ROOT)

    def test_analysis_mapping_requires_executable_stage(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        analysis = next(
            entry
            for entry in changed["schemas"]
            if entry["schema"] == "spec/contracts/1.0/analysis.schema.json"
        )
        analysis["rust_modules"] = ["protocol::analysis"]
        with self.assertRaisesRegex(CoreContractError, "semantic safety analysis"):
            validate_mapping_document(changed, ROOT)


class CoreArchitectureBoundaryTests(unittest.TestCase):
    def test_unapproved_runtime_dependency_fails(self) -> None:
        with self.assertRaisesRegex(CoreContractError, "runtime dependencies"):
            validate_source_boundaries(
                source_texts(),
                ALLOWED_RUNTIME_DEPENDENCIES | {"reqwest"},
            )

    def test_filesystem_network_and_binding_dependencies_fail(self) -> None:
        for forbidden in ("std::fs::read", "std::net::TcpStream", "bindings::python"):
            sources = source_texts()
            sources["core/src/source/mod.rs"] += forbidden
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaises(CoreContractError),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_syntax_and_derived_analysis_in_semantic_ir_fail(self) -> None:
        for forbidden in ("pcre2", "target_profile", "nullable"):
            sources = source_texts()
            semantic = sources["core/src/semantic/mod.rs"]
            marker = semantic.find("pub enum Node")
            self.assertGreaterEqual(marker, 0)
            insertion = (
                marker + len("pub enum Node") if forbidden == "nullable" else marker
            )
            sources["core/src/semantic/mod.rs"] = (
                semantic[:insertion] + f"// {forbidden}\n" + semantic[insertion:]
            )
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaises(CoreContractError),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_normalization_target_environment_and_analysis_dependencies_fail(
        self,
    ) -> None:
        for forbidden in (
            "use crate::target;",
            "use crate::protocol;",
            "use crate::semantic_analysis;",
            "std::env::var",
            "std::time::SystemTime",
            "target_profile",
            "nullable",
        ):
            sources = source_texts()
            sources["core/src/normalization.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "normalization"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_semantic_analysis_boundary_is_required(self) -> None:
        sources = source_texts()
        sources["core/src/semantic_analysis.rs"] = sources[
            "core/src/semantic_analysis.rs"
        ].replace("pub fn analyze(", "fn analyze(")
        with self.assertRaisesRegex(CoreContractError, "analysis stage boundary"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_semantic_analysis_forbidden_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::normalization;",
            "use crate::target;",
            "use crate::protocol;",
            "use crate::diagnostic;",
            "use crate::emitter;",
            "use crate::frontend;",
            "use crate::lsp;",
            "use crate::editor;",
            "std::env::var",
            "std::time::SystemTime",
            "thread_rng",
            "target_profile",
            "portability_plan",
        ):
            sources = source_texts()
            sources["core/src/semantic_analysis.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "semantic analysis"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/semantic_analysis.rs"] += "\n// bindings::python\n"
        with self.assertRaises(CoreContractError):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_structural_analysis_boundary_and_foundational_dependency_are_required(
        self,
    ) -> None:
        sources = source_texts()
        sources["core/src/structural_analysis.rs"] = sources[
            "core/src/structural_analysis.rs"
        ].replace("pub fn analyze_structure(", "fn analyze_structure(")
        with self.assertRaisesRegex(
            CoreContractError, "structural analysis stage boundary"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/structural_analysis.rs"] = sources[
            "core/src/structural_analysis.rs"
        ].replace("crate::semantic_analysis", "crate::foundational_analysis")
        with self.assertRaisesRegex(CoreContractError, "foundational semantic facts"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_structural_analysis_forbidden_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::normalization;",
            "use crate::target::profile;",
            "use crate::planner;",
            "use crate::bindings;",
            "use crate::portability;",
            "use crate::safety;",
            "use crate::emitter;",
            "use crate::frontend;",
            "use crate::lsp;",
            "std::env::var",
            "std::time::SystemTime",
            "std::process::id",
            "thread_rng",
            "target_profile",
            "portability_plan",
            "risk_severity",
            "redos",
        ):
            sources = source_texts()
            sources["core/src/structural_analysis.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "structural analysis"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_safety_analysis_boundary_and_prerequisites_are_required(self) -> None:
        sources = source_texts()
        sources["core/src/safety_analysis.rs"] = sources[
            "core/src/safety_analysis.rs"
        ].replace("pub fn analyze_safety(", "fn analyze_safety(")
        with self.assertRaisesRegex(
            CoreContractError, "semantic safety analysis stage boundary"
        ):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/safety_analysis.rs"] = sources[
            "core/src/safety_analysis.rs"
        ].replace("crate::semantic_analysis", "crate::missing_foundational_analysis")
        with self.assertRaisesRegex(CoreContractError, "foundational semantic facts"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        sources = source_texts()
        sources["core/src/safety_analysis.rs"] = sources[
            "core/src/safety_analysis.rs"
        ].replace("crate::structural_analysis", "crate::missing_structural_analysis")
        with self.assertRaisesRegex(CoreContractError, "structural analysis facts"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_safety_analysis_forbidden_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::normalization;",
            "use crate::target::profile;",
            "use crate::planner;",
            "use crate::bindings;",
            "use crate::portability;",
            "use crate::emitter;",
            "use crate::diagnostic;",
            "use crate::protocol;",
            "use crate::parser;",
            "use crate::frontend;",
            "use crate::lsp;",
            "use crate::editor;",
            "std::env::var",
            "std::time::SystemTime",
            "std::process::id",
            "std::thread::current",
            "thread_rng",
            "target_profile",
            "portability_plan",
            "risk_severity",
            "raw_source",
            "source_text",
            "regex_source",
            "parse_regex",
            "scan_regex",
            "redos",
            "pcre2",
        ):
            sources = source_texts()
            sources["core/src/safety_analysis.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "semantic safety analysis"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
