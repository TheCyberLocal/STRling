from __future__ import annotations

import copy
import json
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


class RegexFrontendArchitectureTests(unittest.TestCase):
    def test_runner_corpora_match_the_specification_correspondence_set(self) -> None:
        correspondence = json.loads(
            (
                ROOT
                / "spec/frontends/legacy-regex/1.0/correspondence/canonical-parser-cases.json"
            ).read_text(encoding="utf-8")
        )
        expected = {
            (case["id"], case["source"], case["expected_status"])
            for case in correspondence["cases"]
        }
        self.assertEqual(len(expected), 5)

        for relative in (
            "tooling/legacy_reference/python_corpus.json",
            "tooling/legacy_reference/corpus.json",
        ):
            corpus = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            actual = {
                (
                    case["id"],
                    case["request"]["input"]["source"],
                    (
                        "rejected"
                        if case["behavior_family"] == "malformed-input"
                        else "accepted"
                    ),
                )
                for case in corpus["cases"]
                if case["request"]["operation"] == "parser.parse"
            }
            self.assertEqual(actual, expected, relative)

    def test_contract_mapping_registers_the_frontend_on_both_boundaries(self) -> None:
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
            "regex_frontend",
            schemas["spec/contracts/1.0/semantic-ir.schema.json"]["rust_modules"][0],
        )

    def test_mapping_cannot_drop_the_frontend(self) -> None:
        mapping = load_mapping(ROOT / "core" / "contract-mapping.json")
        changed = copy.deepcopy(mapping)
        for entry in changed["schemas"]:
            if entry["schema"] == "spec/contracts/1.0/source.schema.json":
                entry["rust_modules"] = ["source"]
        with self.assertRaisesRegex(CoreContractError, "regex compatibility frontend"):
            validate_mapping_document(changed, ROOT)

    def test_parse_semantic_diagnostic_and_provenance_boundaries_are_required(
        self,
    ) -> None:
        for current, replacement in (
            ("pub fn parse(", "fn parse("),
            ("let program = SemanticProgram", "let program = MissingSemanticProgram"),
            ("InvalidSemanticOutput", "UncheckedSemanticOutput"),
            ("crate::diagnostic", "crate::missing_contract"),
            ("CompilerPhase::FrontendParse", "CompilerPhase::Normalization"),
            ("SeverityBasis::Normative", "SeverityBasis::Inferred"),
            ("SourceOrigin", "MissingOrigin"),
            ("SourceSpan", "MissingSpan"),
        ):
            sources = source_texts()
            sources["core/src/regex_frontend.rs"] = sources[
                "core/src/regex_frontend.rs"
            ].replace(current, replacement)
            with (
                self.subTest(boundary=current),
                self.assertRaisesRegex(CoreContractError, "regex"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_target_host_binding_and_environment_dependencies_fail(self) -> None:
        for forbidden in (
            "use crate::target;",
            "use crate::protocol;",
            "use crate::kernel;",
            "use crate::diagnostic_generation;",
            "std::env::var",
            "std::time::SystemTime",
            "std::process::Command",
            "bindings::python",
            "target_profile",
            "engine_options",
            "emitted_pattern",
        ):
            sources = source_texts()
            sources["core/src/regex_frontend.rs"] += f"\n// {forbidden}\n"
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaises(CoreContractError),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
