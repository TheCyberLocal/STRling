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
        with self.assertRaisesRegex(CoreContractError, "normalization stage"):
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


if __name__ == "__main__":
    unittest.main()
