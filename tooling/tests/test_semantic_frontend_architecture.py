from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tooling.core_contract_validation import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    CoreContractError,
    load_mapping,
    validate_mapping_document,
    validate_source_boundaries,
)


ROOT = Path(__file__).resolve().parents[2]


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


class SemanticFrontendArchitectureTests(unittest.TestCase):
    def test_contract_mapping_registers_both_frontends_on_both_boundaries(
        self,
    ) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        schemas = {entry["schema"]: entry for entry in mapping["schemas"]}
        self.assertEqual(
            [
                "source",
                "regex_frontend",
                "semantic_frontend",
                "semantic_conversion",
                "explanation",
            ],
            schemas["spec/contracts/1.0/source.schema.json"]["rust_modules"],
        )
        self.assertEqual(
            ["regex_frontend", "semantic_frontend", "normalization"],
            schemas["spec/contracts/1.0/semantic-ir.schema.json"]["rust_modules"][:3],
        )

    def test_mapping_cannot_drop_the_semantic_frontend(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        for entry in changed["schemas"]:
            if entry["schema"] == "spec/contracts/1.0/source.schema.json":
                entry["rust_modules"] = ["source", "regex_frontend"]
        with self.assertRaisesRegex(CoreContractError, "semantic frontend"):
            validate_mapping_document(changed, ROOT)

    def test_parse_format_normalization_diagnostic_and_provenance_are_required(
        self,
    ) -> None:
        for current, replacement in (
            ("pub fn parse(", "fn parse("),
            ("pub fn format(", "fn format("),
            ("let candidate = SemanticProgram", "let candidate = MissingProgram"),
            ("InvalidSemanticOutput", "UncheckedSemanticOutput"),
            ("crate::normalization", "crate::missing_contract"),
            ("CompilerPhase::SemanticLowering", "CompilerPhase::Normalization"),
            ("SeverityBasis::Normative", "SeverityBasis::Inferred"),
            ("SourceOrigin", "MissingOrigin"),
            ("SourceSpan", "MissingSpan"),
        ):
            sources = source_texts()
            sources["core/src/semantic_frontend.rs"] = sources[
                "core/src/semantic_frontend.rs"
            ].replace(current, replacement)
            with (
                self.subTest(boundary=current),
                self.assertRaisesRegex(CoreContractError, "semantic frontend"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_host_io_binding_and_environment_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::target;",
            "use crate::protocol;",
            "use crate::kernel;",
            "use crate::diagnostic_generation;",
            "use crate::capability_evaluation;",
            "use crate::portability_planning;",
            "std::env::var",
            "std::time::SystemTime",
            "std::process::Command",
            "std::fs::read",
            "std::net::TcpStream",
            "std::path::Path",
            'include_str!("language.json")',
            'include_bytes!("fixtures.json")',
            "bindings::python",
            "target_profile",
            "TargetArtifact",
            "engine_options",
            "emitted_pattern",
        ):
            sources = source_texts()
            sources["core/src/semantic_frontend.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaises(CoreContractError),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
