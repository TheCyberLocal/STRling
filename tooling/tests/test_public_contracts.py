from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

from tooling.public_contracts import (
    ContractError,
    _dotnet_projects,
    _javap_declarations,
    _kotlin_brace_delta,
    _kotlin_signature_head,
    _rust_facade_symbols,
    compare_schema_value,
    cpp_declaration_units,
    declaration_units,
    extract_c_header,
    extract_cli,
    extract_cpp_headers,
    extract_dart_analyzer_api,
    extract_lua,
    extract_perl,
    extract_php,
    extract_ruby,
    extract_rust_facade,
    extract_rust_source_boundary,
    extract_swift_symbolgraph,
    extract_typescript,
    load_registry,
    normalize_swift_symbol_graph,
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


def rust_facade_surface() -> dict[str, object]:
    return {
        "id": "test-rust-facade-api",
        "component": "rust",
        "source_locations": ["bindings/rust/Cargo.toml", "bindings/rust/src/lib.rs"],
        "snapshot_path": "snapshots/rust-facade.json",
        "comparison": "symbol-signatures",
        "enforcement": "enforced",
        "extraction": {"mechanism": "rust-public-api"},
    }


def dynamic_surface(
    component: str, mechanism: str, locations: list[str]
) -> dict[str, object]:
    return {
        "id": f"test-{component}-api",
        "component": component,
        "source_locations": locations,
        "snapshot_path": f"snapshots/{component}.json",
        "comparison": "symbol-signatures",
        "enforcement": "enforced",
        "extraction": {"mechanism": mechanism},
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
            'function Show-Help {\n    Write-Host "  ' + powershell_row + '"\n}\n',
            encoding="utf-8",
        )

    def test_perl_declared_api_extracts_packages_exports_and_arities(self) -> None:
        path = self.root / "bindings/perl/lib/STRling.pm"
        path.parent.mkdir(parents=True)
        path.write_text(
            """package STRling;
our @EXPORT_OK = qw(load_native compile);
# STRling-public-arity: load_native=1
sub load_native { return 1; }
# STRling-public-arity: compile=2..3
sub compile { return 1; }
sub _private { return 1; }
1;
""",
            encoding="utf-8",
        )
        result = extract_perl(
            dynamic_surface("perl", "perl-declared-api", ["bindings/perl/lib/**/*.pm"]),
            self.root,
        )
        self.assertEqual("arity=2..3", result["symbols"]["sub:STRling::compile"])
        self.assertEqual("EXPORT_OK", result["symbols"]["export:STRling::load_native"])
        self.assertNotIn("sub:STRling::_private", result["symbols"])

    def test_perl_declared_api_rejects_missing_arity(self) -> None:
        path = self.root / "bindings/perl/lib/STRling.pm"
        path.parent.mkdir(parents=True)
        path.write_text(
            "package STRling;\nour @EXPORT_OK = qw(load_native);\nsub load_native { 1 }\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ContractError, "lack declared arity"):
            extract_perl(
                dynamic_surface(
                    "perl", "perl-declared-api", ["bindings/perl/lib/**/*.pm"]
                ),
                self.root,
            )

    def test_lua_bounded_facade_extracts_projected_module_and_client(self) -> None:
        source = self.root / "bindings/lua/src"
        source.mkdir(parents=True)
        (source / "adapter.lua").write_text(
            """local strling = { VERSION = "3.0.0" }
local client_methods = {}
function client_methods:compile(request, target) return request end
function strling.load_native(path) return path end
local stdlib = require("strling.stdlib_generated")
for name, value in pairs(stdlib) do strling[name] = value end
return strling
""",
            encoding="utf-8",
        )
        (source / "stdlib_generated.lua").write_text(
            """local surface = { REGISTRY_VERSION = "1.0.0" }
function surface.email(step_id) return step_id end
return surface
""",
            encoding="utf-8",
        )
        result = extract_lua(
            dynamic_surface(
                "lua", "lua-bounded-facade-api", ["bindings/lua/src/*.lua"]
            ),
            self.root,
        )
        self.assertEqual("(self,request,target)", result["symbols"]["client:compile"])
        self.assertEqual("(step_id)", result["symbols"]["module:email"])
        self.assertIn("constant:VERSION", result["symbols"])

    def test_external_dynamic_extractors_are_nonexecuting_script_drivers(self) -> None:
        ruby = self.root / "bindings/ruby/lib/strling.rb"
        php = self.root / "bindings/php/src/STRling.php"
        (self.root / "tooling").mkdir()
        ruby.parent.mkdir(parents=True)
        php.parent.mkdir(parents=True)
        (self.root / "tooling/ruby_public_api.rb").write_text(
            "# extractor\n", encoding="utf-8"
        )
        (self.root / "tooling/php_public_api.php").write_text(
            "<?php\n", encoding="utf-8"
        )
        ruby.write_text("module Strling; end\n", encoding="utf-8")
        php.write_text("<?php final class STRling {}\n", encoding="utf-8")

        def runner(command, **_kwargs):
            symbol = (
                "module:Strling"
                if "ruby_public_api.rb" in command[1]
                else "type:STRling"
            )
            return CompletedProcess(command, 0, json.dumps({symbol: "public"}), "")

        with mock.patch(
            "tooling.public_contracts._required_tool", return_value="parser"
        ):
            ruby_result = extract_ruby(
                dynamic_surface(
                    "ruby", "ruby-ripper-api", ["bindings/ruby/lib/**/*.rb"]
                ),
                self.root,
                runner,
            )
            php_result = extract_php(
                dynamic_surface("php", "php-token-api", ["bindings/php/src/**/*.php"]),
                self.root,
                runner,
            )
        self.assertIn("module:Strling", ruby_result["symbols"])
        self.assertIn("type:STRling", php_result["symbols"])

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

    def test_cpp_declarations_preserve_move_overloads_and_access(self) -> None:
        symbols = cpp_declaration_units(
            "namespace sample { class value { public: value(value&&) noexcept; "
            "void run(int); void run(const char*); private: int state_; }; }",
            "sample.hpp",
        )
        declarations = set(symbols.values())
        self.assertIn("class value", declarations)
        self.assertIn("value(value&&) noexcept", declarations)
        self.assertIn("void run(int)", declarations)
        self.assertIn("void run(const char*)", declarations)
        self.assertNotIn("int state_", declarations)

    def test_cpp_installed_header_closure_rejects_omission(self) -> None:
        header = self.root / "bindings/cpp/include/strling"
        header.mkdir(parents=True)
        (header / "strling.hpp").write_text(
            '#include "strling/native.hpp"\n', encoding="utf-8"
        )
        surface = {
            "id": "test-cpp-api",
            "component": "cpp",
            "source_locations": ["bindings/cpp/include/strling/strling.hpp"],
            "snapshot_path": "snapshots/cpp.json",
            "comparison": "declaration-set",
            "enforcement": "enforced",
            "extraction": {"mechanism": "cpp-header-declarations"},
        }
        with self.assertRaisesRegex(ContractError, "closure omits included header"):
            extract_cpp_headers(surface, self.root)

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
        self.assertNotIn(b"\r\n", first)

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

    def test_c_installed_header_closure_is_combined(self) -> None:
        self.write_header("int strling_execute(const char* text);\n")
        (self.root / "include/simply.h").write_text(
            "typedef struct sl_value sl_value;\n"
            "sl_value* sl_literal(const char* text);\n",
            encoding="utf-8",
        )
        surface = c_surface()
        surface["source_locations"] = ["include/api.h", "include/simply.h"]
        snapshot = extract_c_header(surface, self.root)

        self.assertEqual(
            set(snapshot["symbols"]),
            {
                "int strling_execute(const char* text);",
                "typedef struct sl_value sl_value;",
                "sl_value* sl_literal(const char* text);",
            },
        )

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

    def test_dart_analyzer_output_must_be_a_symbol_map(self) -> None:
        binding = self.root / "bindings/dart/lib"
        binding.mkdir(parents=True)
        (binding / "strling.dart").write_text("library strling;\n", encoding="utf-8")
        package_config = self.root / "bindings/dart/.dart_tool/package_config.json"
        package_config.parent.mkdir()
        package_config.write_text("{}\n", encoding="utf-8")
        tooling = self.root / "tooling"
        tooling.mkdir()
        (tooling / "dart_public_api.dart").write_text(
            "void main() {}\n", encoding="utf-8"
        )
        surface = {
            "id": "test-dart-api",
            "component": "dart",
            "source_locations": ["bindings/dart/lib/**/*.dart"],
            "snapshot_path": "snapshots/dart.json",
            "comparison": "symbol-signatures",
            "enforcement": "enforced",
            "extraction": {"mechanism": "dart-analyzer-api"},
        }

        calls: list[list[str]] = []

        def runner(arguments: list[str], **_kwargs: object) -> CompletedProcess[str]:
            calls.append(arguments)
            return CompletedProcess(
                ["dart"],
                0,
                json.dumps(
                    {
                        "export::NativeClient::class::NativeClient": (
                            "class NativeClient"
                        )
                    }
                ),
                "",
            )

        with mock.patch("tooling.public_contracts._required_tool", return_value="dart"):
            result = extract_dart_analyzer_api(surface, self.root, runner)
        self.assertEqual(result["format"], "dart-analyzer-signatures")
        self.assertEqual(calls[0][1], f"--packages={package_config}")

    def test_swift_extractor_builds_only_the_product_module(self) -> None:
        binding = self.root / "bindings/swift"
        include = binding / "Sources/CSTRlingNative/include"
        include.mkdir(parents=True)
        swift = self.root / "toolchain/bin/swift"
        swift.parent.mkdir(parents=True)
        swift.write_text("", encoding="utf-8")
        symbolgraph = swift.with_name("swift-symbolgraph-extract")
        symbolgraph.write_text("", encoding="utf-8")
        surface = {
            "id": "test-swift-api",
            "component": "swift",
            "source_locations": ["bindings/swift/Sources/STRling/**/*.swift"],
            "snapshot_path": "snapshots/swift.json",
            "comparison": "symbol-signatures",
            "enforcement": "enforced",
            "extraction": {"mechanism": "swift-symbolgraph"},
        }
        calls: list[list[str]] = []

        def runner(arguments: list[str], **_kwargs: object) -> CompletedProcess[str]:
            calls.append(arguments)
            if "-print-target-info" in arguments:
                return CompletedProcess(
                    arguments,
                    0,
                    json.dumps(
                        {"target": {"unversionedTriple": "x86_64-unknown-linux-gnu"}}
                    ),
                    "",
                )
            if "-output-dir" in arguments:
                output = Path(arguments[arguments.index("-output-dir") + 1])
                output.mkdir(parents=True, exist_ok=True)
                (output / "STRling.symbols.json").write_text(
                    json.dumps(
                        {
                            "module": {"name": "STRling"},
                            "symbols": [
                                {
                                    "identifier": {"precise": "s:7STRling6ClientV"},
                                    "kind": {"identifier": "swift.struct"},
                                    "names": {"title": "Client"},
                                    "declarationFragments": [
                                        {"spelling": "public struct Client"}
                                    ],
                                    "pathComponents": ["Client"],
                                    "accessLevel": "public",
                                    "availability": [],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
            return CompletedProcess(arguments, 0, "", "")

        with mock.patch(
            "tooling.public_contracts._required_tool", return_value=str(swift)
        ):
            result = extract_swift_symbolgraph(surface, self.root, runner)
        self.assertEqual(result["format"], "swift-symbolgraph-signatures")
        self.assertIn("build", calls[1])
        self.assertIn("--target", calls[1])
        self.assertNotIn("dump-symbol-graph", calls[1])
        self.assertIn("-module-name", calls[2])
        self.assertIn("-minimum-access-level", calls[2])

    def test_swift_symbol_graph_normalization_drops_tool_metadata(self) -> None:
        symbols = normalize_swift_symbol_graph(
            {
                "metadata": {"generator": "unstable-tool-version"},
                "module": {
                    "name": "STRling",
                    "platform": {"architecture": "x86_64"},
                },
                "symbols": [
                    {
                        "identifier": {
                            "precise": "s:7STRling5emailys10DictionaryVySSypGSSF"
                        },
                        "kind": {
                            "identifier": "swift.func",
                            "displayName": "Function",
                        },
                        "names": {"title": "email(_:)"},
                        "pathComponents": ["email(_:)"],
                        "declarationFragments": [
                            {"kind": "keyword", "spelling": "public func "},
                            {"kind": "identifier", "spelling": "email"},
                            {"kind": "text", "spelling": "(_ stepID: String)"},
                        ],
                        "accessLevel": "public",
                        "availability": [],
                        "location": {"uri": "file:///unstable/path"},
                    }
                ],
            }
        )
        self.assertEqual(len(symbols), 1)
        value = next(iter(symbols.values()))
        self.assertIsInstance(value, dict)
        self.assertNotIn("metadata", value)
        self.assertNotIn("location", value)

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

    def test_javap_normalization_pairs_signatures_and_descriptors(self) -> None:
        symbols = _javap_declarations(
            """Compiled from \"Client.java\"
public final class dev.strling.Client {
  public dev.strling.Client(java.lang.String);
    descriptor: (Ljava/lang/String;)V
  protected java.lang.String invoke(byte[]);
    descriptor: ([B)Ljava/lang/String;
}
""",
            "dev.strling.Client",
        )
        self.assertEqual(
            set(symbols.values()),
            {
                "public final class dev.strling.Client",
                "public dev.strling.Client(java.lang.String); | descriptor: (Ljava/lang/String;)V",
                "protected java.lang.String invoke(byte[]); | descriptor: ([B)Ljava/lang/String;",
            },
        )

    def test_kotlin_signature_normalization_preserves_defaults_and_nullability(
        self,
    ) -> None:
        signature = _kotlin_signature_head(
            "public fun compile(source: String, target: String? = null): Result = body"
        )
        self.assertEqual(
            signature,
            "public fun compile(source: String, target: String? = null): Result",
        )

    def test_kotlin_brace_count_ignores_strings(self) -> None:
        self.assertEqual(_kotlin_brace_delta('fun value() = "${notABrace}"'), 0)

    def test_dotnet_project_denominator_is_language_specific(self) -> None:
        self.assertEqual(
            ("bindings/csharp/src/STRling/STRling.csproj",),
            _dotnet_projects("csharp"),
        )
        self.assertEqual(
            ("bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj",),
            _dotnet_projects("fsharp"),
        )

    def test_dotnet_project_denominator_rejects_unknown_component(self) -> None:
        with self.assertRaisesRegex(ContractError, "does not support component"):
            _dotnet_projects("visual-basic")

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

    def test_rust_facade_source_extraction_captures_existing_public_closure(
        self,
    ) -> None:
        snapshot = extract_rust_facade(rust_facade_surface(), ROOT)
        symbols = snapshot["symbols"]
        self.assertEqual("strling", symbols["crate:name"])
        self.assertEqual("path:../../core", symbols["dependency:strling-kernel"])
        self.assertIn("module:stdlib", symbols)
        self.assertIn("function:check", symbols)
        self.assertIn("function:version", symbols)
        self.assertIn("constant:VERSION", symbols)

    def test_rust_facade_extractor_records_added_public_types(self) -> None:
        manifest = """
[package]
name = "strling"
edition = "2021"
rust-version = "1.70"
[dependencies]
strling-kernel = { path = "../../core" }
"""
        modules = "\n".join(
            f"pub mod {name} {{ pub use strling_kernel::{name}::*; }}"
            for name in (
                "contract",
                "diagnostics",
                "semantic",
                "simply",
                "source",
                "stdlib",
                "target",
            )
        )
        lib = (
            modules
            + "\npub use contract::CompileRequest;\n"
            + 'pub const VERSION: &str = "4";\n'
            + "pub const fn version() -> &'static str { VERSION }\n"
            + "pub fn check() -> bool { true }\n"
            + "pub struct Added { pub value: bool }\n"
            + "fn private_helper() {}\n"
        )
        symbols = _rust_facade_symbols(manifest, lib)
        self.assertIn("struct:Added", symbols)
        self.assertFalse(any("private_helper" in key for key in symbols))

    def test_rust_facade_extractor_rejects_missing_required_module(self) -> None:
        manifest = """
[package]
name = "strling"
edition = "2021"
rust-version = "1.70"
[dependencies]
strling-kernel = { path = "../../core" }
"""
        lib = """
pub mod contract { pub use strling_kernel::protocol::*; }
pub const VERSION: &str = "4";
pub const fn version() -> &'static str { VERSION }
pub fn check() -> bool { true }
"""
        with self.assertRaisesRegex(ContractError, "missing required public items"):
            _rust_facade_symbols(manifest, lib)

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
