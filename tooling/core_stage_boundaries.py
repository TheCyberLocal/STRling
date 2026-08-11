"""Focused architecture fitness rules for late target-neutral kernel stages."""

from __future__ import annotations

from collections.abc import Mapping


def _first_forbidden(source: str, markers: tuple[str, ...]) -> str | None:
    return next((marker for marker in markers if marker in source), None)


def diagnostic_generation_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first diagnostic-stage architecture violation, if any."""

    source = source_texts.get("core/src/diagnostic_generation.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn generate_diagnostics(" not in source:
        return "canonical diagnostic generation stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic", "certified diagnostic contracts"),
        ("crate::semantic_analysis", "certified foundational semantic facts"),
        ("crate::structural_analysis", "certified structural analysis facts"),
        ("crate::safety_analysis", "certified semantic safety evidence"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"diagnostic generation must consume {description}"

    forbidden = _first_forbidden(
        source,
        (
            "crate::normalization",
            "crate::capability_evaluation",
            "crate::capability_pipeline",
            "crate::target",
            "crate::protocol",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::planner",
            "crate::portability",
            "crate::parser",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env",
            "std::time",
            "std::process",
            "std::thread",
            "systemtime",
            "thread_rng",
            "rand::",
            "target_profile",
            "engine_options",
            "emitted_pattern",
            "portability_plan",
            "portability_decision",
            "raw_source",
            "source_text",
            "regex_source",
            "parse_regex",
            "scan_regex",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return (
            "diagnostic generation violates target-neutral communication boundary: "
            f"{forbidden}"
        )
    return None


def compiler_pipeline_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first target-neutral pipeline architecture violation, if any."""

    source = source_texts.get("core/src/compiler_pipeline.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn compile_semantic_diagnostics(" not in source:
        return "canonical target-neutral compiler pipeline boundary cannot be located"

    prerequisites = (
        ("crate::normalization", "canonical normalization"),
        ("crate::semantic_analysis", "foundational semantic analysis"),
        ("crate::structural_analysis", "structural analysis"),
        ("crate::safety_analysis", "semantic safety analysis"),
        ("crate::diagnostic_generation", "diagnostic generation"),
        ("crate::protocol", "CompileResult protocol projection"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"target-neutral compiler pipeline must invoke {description}"

    forbidden = _first_forbidden(
        source,
        (
            "crate::target",
            "crate::capability_evaluation",
            "crate::capability_pipeline",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::planner",
            "crate::portability",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env",
            "std::time",
            "std::process",
            "std::thread",
            "systemtime",
            "thread_rng",
            "rand::",
            "target_profile",
            "engine_options",
            "emitted_pattern",
            "portability_plan",
            "portability_decision",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return (
            "target-neutral compiler pipeline violates dependency boundary: "
            f"{forbidden}"
        )
    return None


def capability_evaluation_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first factual capability-stage architecture violation."""

    source = source_texts.get("core/src/capability_evaluation.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    for boundary in (
        "pub fn extract_requirements(",
        "pub fn evaluate_capabilities(",
    ):
        if boundary not in source:
            return "canonical capability evaluation stage boundary cannot be located"

    prerequisites = (
        ("use crate::semantic::{", "normalized semantic IR"),
        (
            "use crate::semantic_analysis::{",
            "certified foundational semantic facts",
        ),
        ("use crate::structural_analysis::{", "certified structural facts"),
        ("use crate::target::{", "immutable target profiles"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"capability evaluation must consume {description}"

    forbidden = _first_forbidden(
        source,
        (
            "crate::normalization",
            "crate::safety_analysis",
            "crate::diagnostic",
            "crate::diagnostic_generation",
            "crate::protocol",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::planner",
            "crate::portability",
            "crate::parser",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env",
            "std::fs",
            "std::net",
            "std::path",
            "std::process",
            "std::thread",
            "std::time",
            "systemtime",
            "thread_rng",
            "rand::",
            "raw_source",
            "source_text",
            "regex_source",
            "parse_regex",
            "scan_regex",
            "engine_options",
            "emitted_pattern",
            "portability_plan",
            "portability_decision",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return f"capability evaluation violates pure stage boundary: {forbidden}"
    return None


def capability_pipeline_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first target-aware pipeline architecture violation."""

    source = source_texts.get("core/src/capability_pipeline.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn compile_semantic_capabilities(" not in source:
        return "canonical capability pipeline boundary cannot be located"

    prerequisites = (
        ("crate::compiler_pipeline", "completed target-neutral stages"),
        ("crate::capability_evaluation", "factual capability evaluation"),
        ("crate::semantic", "normalized semantic input contract"),
        ("crate::target", "immutable target profile contract"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"capability pipeline must consume {description}"

    neutral = source.find("run_target_neutral_stages(input)")
    capability = source.find("evaluate_capabilities(")
    if neutral < 0 or capability < 0 or neutral >= capability:
        return (
            "capability pipeline must run target-neutral diagnostics before "
            "capability evaluation"
        )

    forbidden = _first_forbidden(
        source,
        (
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::protocol",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::planner",
            "crate::portability",
            "crate::parser",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env",
            "std::fs",
            "std::net",
            "std::path",
            "std::process",
            "std::thread",
            "std::time",
            "systemtime",
            "thread_rng",
            "rand::",
            "engine_options",
            "emitted_pattern",
            "portability_plan",
            "portability_decision",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return f"capability pipeline violates dependency boundary: {forbidden}"
    return None


def target_neutral_reverse_dependency_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Prevent target-neutral stages from reaching capability code."""

    target_neutral_paths = (
        "core/src/semantic/mod.rs",
        "core/src/normalization.rs",
        "core/src/semantic_analysis.rs",
        "core/src/semantic_analysis/",
        "core/src/structural_analysis.rs",
        "core/src/structural_analysis/",
        "core/src/safety_analysis.rs",
        "core/src/safety_analysis/",
        "core/src/diagnostic_generation.rs",
    )
    for path, text in source_texts.items():
        if not any(
            path == candidate or path.startswith(candidate)
            for candidate in target_neutral_paths
        ):
            continue
        source = text.lower()
        forbidden = _first_forbidden(
            source,
            ("crate::capability_evaluation", "crate::capability_pipeline"),
        )
        if forbidden is not None:
            return (
                "target-neutral stage has a reverse target dependency: "
                f"{path}: {forbidden}"
            )
    return None
