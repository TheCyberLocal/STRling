from __future__ import annotations

import unittest
from pathlib import Path

from tooling.core_contract_validation import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    CoreContractError,
    validate_source_boundaries,
)


ROOT = Path(__file__).resolve().parents[2]


def source_texts() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "core" / "src").glob("**/*.rs"))
    }


def insert_before_tests(source: str, addition: str) -> str:
    marker = source.find("\n#[cfg(test)]")
    if marker < 0:
        return f"{source}\n{addition}\n"
    return source[:marker] + f"\n{addition}\n" + source[marker:]


class CompilerBoundaryArchitectureTests(unittest.TestCase):
    def test_public_boundary_and_canonical_prerequisites_are_required(self) -> None:
        sources = source_texts()
        path = "core/src/kernel.rs"
        sources[path] = sources[path].replace("pub fn compile(", "fn compile(", 1)
        with self.assertRaisesRegex(CoreContractError, "public kernel facade"):
            validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

        for prerequisite in (
            "crate::protocol",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::regex_frontend",
            "crate::target",
            "crate::validation",
        ):
            sources = source_texts()
            sources[path] = sources[path].replace(
                prerequisite, "crate::missing_prerequisite", 1
            )
            with (
                self.subTest(prerequisite=prerequisite),
                self.assertRaisesRegex(CoreContractError, "kernel facade"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_both_canonical_orchestration_paths_are_required(self) -> None:
        for call in (
            "compile_semantic_diagnostics(",
            "compile_semantic_portability(",
            "regex_frontend::parse(",
        ):
            sources = source_texts()
            path = "core/src/kernel.rs"
            sources[path] = sources[path].replace(call, "missing_pipeline_call(", 1)
            with (
                self.subTest(call=call),
                self.assertRaisesRegex(CoreContractError, "kernel facade"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_internal_orchestration_cannot_become_an_alternate_public_api(self) -> None:
        for module in ("compiler_pipeline", "capability_pipeline"):
            sources = source_texts()
            path = "core/src/lib.rs"
            sources[path] = sources[path].replace(
                f"mod {module};", f"pub mod {module};", 1
            )
            with (
                self.subTest(module=module),
                self.assertRaisesRegex(
                    CoreContractError, "crate-private orchestration"
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_facade_cannot_reimplement_certified_stages(self) -> None:
        for forbidden in (
            "use crate::normalization;",
            "use crate::semantic_analysis;",
            "use crate::structural_analysis;",
            "use crate::safety_analysis;",
            "use crate::diagnostic_generation;",
            "evaluate_capabilities(",
            "plan_portability(",
        ):
            sources = source_texts()
            path = "core/src/kernel.rs"
            sources[path] = insert_before_tests(sources[path], f"// {forbidden}")
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(CoreContractError, "embeddable boundary"),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)

    def test_host_frontend_emitter_and_binding_dependencies_fail(self) -> None:
        for forbidden in (
            "std::env::var",
            "std::fs::read_to_string",
            "std::net::TcpStream",
            "std::time::SystemTime",
            "std::process::Command",
            "static mut KERNEL_CACHE",
            "thread_local!",
            "once_cell::sync::Lazy",
            "lazy_static!",
            "std::sync::Mutex",
            "std::sync::RwLock",
            "std::sync::atomic::AtomicUsize",
            "std::sync::OnceLock",
            "std::sync::LazyLock",
            "use crate::emitters;",
            "use crate::bindings;",
            "use crate::frontend;",
            "use crate::lsp;",
            "runtime_probe",
            "engine_probe",
            "package_manager",
            "parse_regex",
        ):
            sources = source_texts()
            path = "core/src/kernel.rs"
            sources[path] = insert_before_tests(sources[path], f"// {forbidden}")
            with (
                self.subTest(forbidden=forbidden),
                self.assertRaisesRegex(
                    CoreContractError,
                    "embeddable boundary|deterministic dependency",
                ),
            ):
                validate_source_boundaries(sources, ALLOWED_RUNTIME_DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
