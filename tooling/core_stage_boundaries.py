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
