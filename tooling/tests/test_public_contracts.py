from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess

from tooling.public_contracts import (
    ContractError,
    compare_schema_value,
    declaration_units,
    extract_c_header,
    load_registry,
    parse_go_doc,
    process_surface,
)


ROOT = Path(__file__).resolve().parents[2]


def c_surface() -> dict[str, object]:
    return {
        "id": "test-c-api",
        "component": "c",
        "source_locations": ["include/api.h"],
        "snapshot_path": "snapshots/c.json",
        "comparison": "declaration-set",
        "enforcement": "enforced",
        "extraction": {"mechanism": "c-header-declarations"},
    }


class PublicContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "include").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_header(self, text: str) -> None:
        (self.root / "include/api.h").write_text(text, encoding="utf-8")

    def test_positive_regeneration_is_exact_and_check_is_non_mutating(self) -> None:
        self.write_header("int strling_parse(const char* text);\n")
        surface = c_surface()
        write_result = process_surface(surface, root=self.root, check=False)
        self.assertEqual(write_result.status, "passed")
        snapshot_path = self.root / "snapshots/c.json"
        first = snapshot_path.read_bytes()

        check_result = process_surface(surface, root=self.root, check=True)
        self.assertEqual(check_result.status, "passed")
        self.assertEqual(snapshot_path.read_bytes(), first)

        process_surface(surface, root=self.root, check=False)
        self.assertEqual(snapshot_path.read_bytes(), first)

    def test_added_public_symbol_without_snapshot_update_fails(self) -> None:
        self.write_header("int strling_parse(const char* text);\n")
        surface = c_surface()
        process_surface(surface, root=self.root, check=False)
        self.write_header(
            "int strling_parse(const char* text);\n"
            "int strling_compile(const char* text);\n"
        )
        result = process_surface(surface, root=self.root, check=True)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.classification, "additive")
        self.assertIn("snapshot is stale", result.findings)

    def test_removed_public_symbol_fails_as_breaking(self) -> None:
        self.write_header(
            "int strling_parse(const char* text);\n"
            "int strling_compile(const char* text);\n"
        )
        surface = c_surface()
        process_surface(surface, root=self.root, check=False)
        self.write_header("int strling_parse(const char* text);\n")
        result = process_surface(surface, root=self.root, check=True)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.classification, "breaking")
        self.assertTrue(
            any(finding.startswith("removed ") for finding in result.findings)
        )

    def test_changed_signature_fails_as_breaking(self) -> None:
        self.write_header("int strling_parse(const char* text);\n")
        surface = c_surface()
        process_surface(surface, root=self.root, check=False)
        self.write_header("int strling_parse(const char* text, int flags);\n")
        result = process_surface(surface, root=self.root, check=True)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.classification, "breaking")

    def test_missing_snapshot_fails(self) -> None:
        self.write_header("int strling_parse(const char* text);\n")
        result = process_surface(c_surface(), root=self.root, check=True)
        self.assertEqual(result.status, "failed")
        self.assertIn("cannot read", result.findings[0])

    def test_extraction_failure_propagates(self) -> None:
        surface = {
            **c_surface(),
            "id": "test-go-api",
            "source_locations": ["bindings/go/*.go"],
            "extraction": {"mechanism": "go-doc-declarations"},
        }
        (self.root / "bindings/go").mkdir(parents=True)

        def failing_runner(*_args: object, **_kwargs: object) -> CompletedProcess[str]:
            return CompletedProcess(["go"], 9, "", "controlled extraction failure")

        result = process_surface(
            surface, root=self.root, check=False, runner=failing_runner
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("controlled extraction failure", result.findings[0])

    def test_malformed_registry_fails_closed(self) -> None:
        path = self.root / "registry.json"
        path.write_text('{"registry_version": 1, "surfaces": []}', encoding="utf-8")
        with self.assertRaises(ContractError):
            load_registry(
                path,
                ROOT / "governance/schemas/public-surface-registry.schema.json",
            )

    def test_duplicate_surface_identifier_fails(self) -> None:
        registry = json.loads(
            (ROOT / "governance/public-surfaces.json").read_text(encoding="utf-8")
        )
        registry["surfaces"].append(dict(registry["surfaces"][0]))
        path = self.root / "registry.json"
        path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "identifiers must be unique"):
            load_registry(
                path,
                ROOT / "governance/schemas/public-surface-registry.schema.json",
            )

    def test_private_c_implementation_is_not_part_of_header_api(self) -> None:
        self.write_header("int strling_parse(const char* text);\n")
        (self.root / "private.c").write_text(
            "static int compiler_helper(void) { return 1; }\n", encoding="utf-8"
        )
        snapshot = extract_c_header(c_surface(), self.root)
        symbols = snapshot["symbols"]
        self.assertIsInstance(symbols, dict)
        self.assertFalse(any("compiler_helper" in key for key in symbols))

    def test_go_doc_normalization_excludes_documentation_prose(self) -> None:
        symbols = parse_go_doc(
            """package core

FUNCTIONS

func Parse(text string) error
    Parse compiles a pattern.

TYPES

type Flags struct {
    IgnoreCase bool
}
    Flags controls parsing.
""",
            "./core",
        )
        self.assertEqual(
            set(symbols.values()),
            {
                "func Parse(text string) error",
                "type Flags struct { IgnoreCase bool }",
            },
        )

    def test_typescript_declarations_exclude_private_members(self) -> None:
        symbols = declaration_units(
            "declare class Compiler { private cache; compile(text: string): string; }",
            "index.d.ts",
        )
        self.assertFalse(any("private cache" in value for value in symbols.values()))
        self.assertTrue(
            any("compile(text: string)" in value for value in symbols.values())
        )

    def test_schema_optional_property_addition_is_additive(self) -> None:
        old = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        new = {
            **old,
            "properties": {
                **old["properties"],
                "hint": {"type": "string"},
            },
        }
        comparison = compare_schema_value(old, new)
        self.assertEqual(comparison.classification, "additive")

    def test_schema_required_property_addition_is_breaking(self) -> None:
        old = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        new = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "code": {"type": "string"},
            },
            "required": ["name", "code"],
        }
        comparison = compare_schema_value(old, new)
        self.assertEqual(comparison.classification, "breaking")

    def test_schema_constraint_tightening_is_breaking(self) -> None:
        comparison = compare_schema_value(
            {"type": "string", "minLength": 1},
            {"type": "string", "minLength": 2},
        )
        self.assertEqual(comparison.classification, "breaking")

    def test_schema_description_only_change_is_compatible(self) -> None:
        comparison = compare_schema_value(
            {"type": "string", "description": "old"},
            {"type": "string", "description": "new"},
        )
        self.assertEqual(comparison.classification, "compatible")


if __name__ == "__main__":
    unittest.main()
