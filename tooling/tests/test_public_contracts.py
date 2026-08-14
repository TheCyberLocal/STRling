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
    extract_cli,
    extract_rust_source_boundary,
    extract_typescript,
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


def rust_kernel_surface() -> dict[str, object]:
    return {
        "id": "test-kernel-api",
        "component": "core",
        "source_locations": [
            "core/src/lib.rs",
            "core/src/kernel.rs",
            "core/src/simply.rs",
            "core/src/explanation.rs",
            "core/src/no_match_explanation.rs",
            "core/src/semantic_conversion.rs",
        ],
        "snapshot_path": "snapshots/kernel.json",
        "comparison": "symbol-signatures",
        "enforcement": "enforced",
        "extraction": {"mechanism": "rust-source-boundary"},
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

    def write_cli_wrappers(self, posix_row: str, powershell_row: str) -> None:
        (self.root / "strling").write_text(
            'print_help() {\n    echo "  ' + posix_row + '"\n}\n',
            encoding="utf-8",
        )
        (self.root / "strling.ps1").write_text(
            'function Show-Help {\n    Write-Host "  '
            + powershell_row
            + '"\n}\n',
            encoding="utf-8",
        )

    @staticmethod
    def cli_surface() -> dict[str, object]:
        return {
            "id": "test-root-cli",
            "component": "repository",
            "source_locations": ["strling", "strling.ps1"],
            "snapshot_path": "snapshots/cli.json",
            "comparison": "cli-command-set",
            "enforcement": "enforced",
            "extraction": {"mechanism": "cli-help-parser"},
        }

    def test_cli_extraction_requires_posix_powershell_parity(self) -> None:
        self.write_cli_wrappers("help Show help", "help Show help")
        result = extract_cli(self.cli_surface(), self.root)
        self.assertEqual(result["symbols"], {"help": "help Show help"})

        self.write_cli_wrappers("help Show help", "help Different help")
        with self.assertRaisesRegex(ContractError, "help command rows diverge"):
            extract_cli(self.cli_surface(), self.root)

    def write_kernel(self, profile_type: str = "Option<&TargetProfile>") -> None:
        source = self.root / "core/src"
        source.mkdir(parents=True, exist_ok=True)
        (source / "lib.rs").write_text(
            "pub mod kernel;\n"
            "pub mod simply;\n"
            "pub mod explanation;\n"
            "pub mod no_match_explanation;\n"
            "pub mod semantic_conversion;\n"
            "pub use kernel::{compile, KernelCompileError, KernelStage};\n"
            "pub use simply::{SimplyBuilder, SimplyValue};\n",
            encoding="utf-8",
        )
        (source / "explanation.rs").write_text(
            "pub fn explain_semantics() {}\npub fn explain_target() {}\n",
            encoding="utf-8",
        )
        (source / "no_match_explanation.rs").write_text(
            'pub const NO_MATCH_EXPLANATION_MODEL_VERSION: &str = "1.0.0";\n'
            "pub enum NoMatchOutcome { Matched, NoMatch }\n"
            "pub struct NoMatchExplanationDocument { pub outcome: NoMatchOutcome, }\n"
            "pub fn explain_no_match() {}\n",
            encoding="utf-8",
        )
        (source / "semantic_conversion.rs").write_text(
            'pub const SEMANTIC_CONVERSION_VERSION: &str = "1.0.0";\n'
            'pub const SEMANTIC_ALPHA_EQUIVALENCE_METHOD: &str = "alpha@1.0.0";\n'
            "pub enum SemanticConversionDestination { SemanticStrling, SimplyBuilder }\n"
            "pub enum SemanticConversionStatus { Exact, Partial, Unsupported }\n"
            "pub struct SemanticConversionResult { pub status: SemanticConversionStatus, }\n"
            "pub struct SemanticConversionErrors { pub errors: Vec<String>, }\n"
            "pub fn convert_semantic_program() {}\n",
            encoding="utf-8",
        )
        (source / "simply.rs").write_text(
            'pub const SIMPLY_PROTOCOL_VERSION: &str = "1.0.0";\n'
            "pub struct SimplyOptions {\n"
            "    pub case_matching: CaseMatching,\n"
            "}\n"
            "pub enum SimplyCharacterSetMember { Literal { value: char } }\n"
            "pub struct SimplyCompileProjection { pub requested_outputs: Vec<RequestedOutput>, }\n"
            "pub enum SimplyErrorCode { InvalidArgument }\n"
            "pub struct SimplyError { pub code: SimplyErrorCode, pub path: String, }\n"
            "pub struct SimplyErrors { pub errors: Vec<SimplyError>, }\n"
            "pub struct SimplyValue { private: String }\n"
            "pub struct SimplyBuilder { private: String }\n"
            'impl SimplyErrorCode { pub const fn as_str(self) -> &\'static str { "test" } }\n'
            "impl SimplyValue { pub fn step_id(&self) -> &str { &self.private } }\n"
            "impl SimplyBuilder {\n"
            "    pub fn new() -> Self { unimplemented!() }\n"
            "    pub fn empty(&mut self) {}\n"
            "    pub fn literal(&mut self) {}\n"
            "    pub fn wildcard(&mut self) {}\n"
            "    pub fn character_set(&mut self) {}\n"
            "    pub fn sequence(&mut self) {}\n"
            "    pub fn alternation(&mut self) {}\n"
            "    pub fn group(&mut self) {}\n"
            "    pub fn capture(&mut self) {}\n"
            "    pub fn backreference(&mut self) {}\n"
            "    pub fn position(&mut self) {}\n"
            "    pub fn lookaround(&mut self) {}\n"
            "    pub fn atomic(&mut self) {}\n"
            "    pub fn repeat(&mut self) {}\n"
            "    pub fn import_node(&mut self) {}\n"
            "    pub fn import_program(&mut self) {}\n"
            "    pub fn finish_program(self) {}\n"
            "    pub fn finish_request(self) {}\n"
            "}\n"
            "fn private_simply_helper() {}\n",
            encoding="utf-8",
        )
        (source / "kernel.rs").write_text(
            'pub const KERNEL_COMPILER_ID: &str = \\"test\\";\n'
            "pub enum KernelStage { ContractValidation }\n"
            "pub enum KernelCompileError { InvalidRequest }\n"
            "pub fn compile(\n"
            "    request: &CompileRequest,\n"
            f"    target_profile: {profile_type},\n"
            ") -> Result<CompileResult, KernelCompileError> { unimplemented!() }\n"
            "fn private_helper() {}\n",
            encoding="utf-8",
        )

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

    def test_typescript_extraction_uses_node_compiler_entrypoint(self) -> None:
        compiler = self.root / "bindings/typescript/node_modules/typescript/bin/tsc"
        compiler.parent.mkdir(parents=True)
        compiler.write_text("", encoding="utf-8")
        commands: list[list[str]] = []

        def runner(arguments: list[str], **_kwargs: object) -> CompletedProcess[str]:
            commands.append(arguments)
            output = Path(arguments[arguments.index("--outDir") + 1])
            output.mkdir(parents=True, exist_ok=True)
            (output / "index.d.ts").write_text(
                "export declare function compile(text: string): string;\n",
                encoding="utf-8",
            )
            return CompletedProcess(arguments, 0, "", "")

        snapshot = extract_typescript(
            {"id": "test-typescript-api"}, self.root, runner=runner
        )

        self.assertEqual(["node", str(compiler)], commands[0][:2])
        self.assertTrue(snapshot["symbols"])

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

    def test_rust_kernel_source_boundary_is_exact_and_excludes_private_code(
        self,
    ) -> None:
        self.write_kernel()
        snapshot = extract_rust_source_boundary(rust_kernel_surface(), self.root)
        symbols = snapshot["symbols"]
        self.assertIsInstance(symbols, dict)
        self.assertEqual(
            {
                "const:KERNEL_COMPILER_ID",
                "enum:KernelCompileError",
                "enum:KernelStage",
                "fn:compile",
                "fn:convert_semantic_program",
                "fn:explain_semantics",
                "fn:explain_target",
                "fn:explain_no_match",
                "module:explanation",
                "module:kernel",
                "module:no_match_explanation",
                "module:semantic_conversion",
                "module:simply",
                "reexport:kernel",
                "reexport:simply",
                "const:SIMPLY_PROTOCOL_VERSION",
                "enum:SimplyCharacterSetMember",
                "enum:SimplyErrorCode",
                "enum:SemanticConversionDestination",
                "enum:SemanticConversionStatus",
                "struct:SimplyBuilder",
                "struct:SimplyCompileProjection",
                "struct:SimplyError",
                "struct:SimplyErrors",
                "struct:SimplyOptions",
                "struct:SimplyValue",
                "struct:SemanticConversionErrors",
                "struct:SemanticConversionResult",
                "struct:NoMatchExplanationDocument",
                "enum:NoMatchOutcome",
                "const:NO_MATCH_EXPLANATION_MODEL_VERSION",
                "const:SEMANTIC_ALPHA_EQUIVALENCE_METHOD",
                "const:SEMANTIC_CONVERSION_VERSION",
                "method:SimplyBuilder::alternation",
                "method:SimplyBuilder::atomic",
                "method:SimplyBuilder::backreference",
                "method:SimplyBuilder::capture",
                "method:SimplyBuilder::character_set",
                "method:SimplyBuilder::empty",
                "method:SimplyBuilder::finish_program",
                "method:SimplyBuilder::finish_request",
                "method:SimplyBuilder::group",
                "method:SimplyBuilder::import_node",
                "method:SimplyBuilder::import_program",
                "method:SimplyBuilder::literal",
                "method:SimplyBuilder::lookaround",
                "method:SimplyBuilder::new",
                "method:SimplyBuilder::position",
                "method:SimplyBuilder::repeat",
                "method:SimplyBuilder::sequence",
                "method:SimplyBuilder::wildcard",
                "method:SimplyErrorCode::as_str",
                "method:SimplyValue::step_id",
            },
            set(symbols),
        )
        self.assertFalse(any("private_helper" in key for key in symbols))
        self.assertFalse(any("private_simply_helper" in key for key in symbols))
        self.assertNotIn("private", symbols["struct:SimplyBuilder"])

    def test_rust_simply_method_signature_drift_fails_as_breaking(self) -> None:
        self.write_kernel()
        surface = rust_kernel_surface()
        self.assertEqual(
            "passed", process_surface(surface, root=self.root, check=False).status
        )
        path = self.root / "core/src/simply.rs"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "pub fn literal(&mut self) {}", "pub fn literal(&self) {}"
            ),
            encoding="utf-8",
        )
        result = process_surface(surface, root=self.root, check=True)
        self.assertEqual("failed", result.status)
        self.assertEqual("breaking", result.classification)
        self.assertIn("changed method:SimplyBuilder::literal", result.findings)

    def test_rust_kernel_signature_drift_fails_as_breaking(self) -> None:
        self.write_kernel()
        surface = rust_kernel_surface()
        self.assertEqual(
            "passed", process_surface(surface, root=self.root, check=False).status
        )
        self.write_kernel("&TargetProfile")
        result = process_surface(surface, root=self.root, check=True)
        self.assertEqual("failed", result.status)
        self.assertEqual("breaking", result.classification)
        self.assertIn("changed fn:compile", result.findings)


if __name__ == "__main__":
    unittest.main()
