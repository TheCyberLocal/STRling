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


def portability_planning_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first pure portability-planning architecture violation."""

    source = source_texts.get("core/src/portability_planning.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn plan_portability(" not in source:
        return "canonical portability planning stage boundary cannot be located"

    prerequisites = (
        ("crate::capability_evaluation::{", "factual capability evaluation"),
        ("crate::semantic::{", "normalized semantic IR"),
        ("crate::semantic_analysis::{", "certified foundational semantic facts"),
        ("crate::structural_analysis::", "certified structural facts"),
        ("crate::target::{", "immutable target profiles"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"portability planning must consume {description}"

    forbidden = _first_forbidden(
        source,
        (
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "crate::normalization",
            "crate::safety_analysis",
            "crate::diagnostic",
            "crate::diagnostic_generation",
            "crate::protocol",
            "crate::conformance",
            "crate::capability_pipeline",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
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
            "runtime_probe",
            "engine_options",
            "emitted_pattern",
            "target_artifact",
            "capture_numbering",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return f"portability planning violates pure stage boundary: {forbidden}"
    return None


def portability_diagnostics_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first portability-explanation architecture violation."""

    source = source_texts.get("core/src/portability_diagnostics.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn explain_portability(" not in source:
        return "canonical portability diagnostics stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical diagnostic contracts"),
        ("crate::portability_planning::{", "certified portability plans"),
        ("crate::semantic::{", "normalized Semantic IR and source origins"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"portability diagnostics must consume {description}"

    forbidden = _first_forbidden(
        source,
        (
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "apply_rewrite(",
            "apply_semantic_rewrite(",
            "lower_to_target(",
            "emit_target(",
            "crate::normalization",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::protocol",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
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
            "runtime_probe",
            "engine_options",
            "emitted_pattern",
            "target_artifact",
            "capture_numbering",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return (
            "portability diagnostics violates evidence-only explanation boundary: "
            f"{forbidden}"
        )
    return None


def portability_pipeline_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first target-aware planning-pipeline violation."""

    source = source_texts.get("core/src/capability_pipeline.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn compile_semantic_portability(" not in source:
        return "canonical portability pipeline boundary cannot be located"

    prerequisites = (
        ("crate::compiler_pipeline", "completed target-neutral stages"),
        ("crate::capability_evaluation", "factual capability evaluation"),
        ("crate::portability_planning", "certified portability planning"),
        ("crate::portability_diagnostics", "target-aware portability explanations"),
        ("crate::semantic", "normalized semantic input contract"),
        ("crate::target", "immutable target profile contract"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"portability pipeline must consume {description}"

    neutral = source.find("run_target_neutral_stages(input)")
    capability = source.find("evaluate_capabilities(")
    planning = source.find("plan_portability(")
    explanation = source.find("explain_portability(")
    if (
        neutral < 0
        or capability < 0
        or planning < 0
        or explanation < 0
        or neutral >= capability
        or capability >= planning
        or planning >= explanation
    ):
        return (
            "portability pipeline must run target-neutral diagnostics, factual "
            "capability evaluation, planning, and target-aware explanations in "
            "dependency order"
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
            "target_artifact",
            "pcre2",
            "ecmascript",
            "python_re",
        ),
    )
    if forbidden is not None:
        return f"portability pipeline violates dependency boundary: {forbidden}"
    return None


def kernel_boundary_violation(source_texts: Mapping[str, str]) -> str | None:
    """Return the first public compiler-facade architecture violation."""

    source = source_texts.get("core/src/kernel.rs", "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn compile(" not in source:
        return "canonical public kernel facade cannot be located"

    prerequisites = (
        ("crate::protocol", "canonical request and result contracts"),
        ("crate::compiler_pipeline", "canonical target-neutral orchestration"),
        ("crate::capability_pipeline", "canonical target-aware orchestration"),
        ("crate::regex_frontend", "governed compatibility frontend"),
        ("crate::target", "immutable target-profile contracts"),
        ("crate::validation", "canonical contract validation"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"kernel facade must consume {description}"

    for call, description in (
        (
            "compile_semantic_diagnostics(",
            "canonical target-neutral orchestration",
        ),
        (
            "compile_semantic_portability(",
            "canonical target-aware orchestration",
        ),
        ("regex_frontend::parse(", "governed compatibility frontend"),
    ):
        if call not in source:
            return f"kernel facade must invoke {description}"

    lib = source_texts.get("core/src/lib.rs", "").lower()
    for internal_module in (
        "pub mod compiler_pipeline;",
        "pub mod capability_pipeline;",
    ):
        if internal_module in lib:
            return (
                "crate-private orchestration cannot be exposed beside the "
                f"authoritative kernel facade: {internal_module}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "evaluate_capabilities(",
            "plan_portability(",
            "crate::conformance",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::parser",
            "bindings::",
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
            "static mut",
            "thread_local!",
            "once_cell::",
            "lazy_static!",
            "std::sync::mutex",
            "std::sync::rwlock",
            "std::sync::atomic",
            "std::sync::oncelock",
            "std::sync::lazylock",
            "runtime_probe",
            "engine_probe",
            "package_manager",
            "parse_regex",
            "scan_regex",
        ),
    )
    if forbidden is not None:
        return f"kernel facade violates embeddable boundary: {forbidden}"
    return None


def pcre2_target_lowering_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first structured PCRE2 target-lowering violation."""

    path = "core/src/target_lowering.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn lower_pcre2(" not in source:
        return "canonical PCRE2 target-lowering stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured diagnostics"),
        ("crate::portability_planning::{", "certified portability plans"),
        ("crate::semantic::{", "normalized Semantic IR"),
        ("crate::source::{", "canonical identity and provenance contracts"),
        ("crate::target::{", "exact immutable target profiles"),
        ("crate::validation::{", "canonical validation and fingerprints"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"PCRE2 target lowering must consume {description}"

    correspondence = (
        "portability.validate()",
        "canonical_sha256(input)",
        "target.reference()",
        'target.engine.id.as_str() != "pcre2"',
    )
    for marker in correspondence:
        if marker not in source:
            return (
                "PCRE2 target lowering must validate exact planner/program/profile "
                f"correspondence: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::ecmascript_lowering",
            "crate::ecmascript_serialization",
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "pcre2_compile",
            "pcre2_match",
            "regex::",
            "emittedpattern {",
            "generatedspan {",
            "targetartifact {",
        ),
    )
    if forbidden is not None:
        return f"PCRE2 target lowering violates pure pre-serialization boundary: {forbidden}"

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "lower_pcre2(" in text.lower():
            return (
                "PCRE2 target lowering has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
    return None


def ecmascript_target_lowering_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first structured ECMAScript target-lowering violation."""

    path = "core/src/ecmascript_lowering.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn lower_ecmascript(" not in source:
        return "canonical ECMAScript target-lowering stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured diagnostics"),
        ("crate::portability_planning::{", "certified portability plans"),
        ("crate::semantic::{", "normalized Semantic IR"),
        ("crate::source::{", "canonical identity and provenance contracts"),
        ("crate::target::{", "exact immutable target profiles"),
        ("crate::validation::{", "canonical validation and fingerprints"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"ECMAScript target lowering must consume {description}"

    correspondence = (
        "portability.validate()",
        "canonical_sha256(input)",
        "target.reference()",
        'target.engine.id.as_str() != "ecmascript"',
    )
    for marker in correspondence:
        if marker not in source:
            return (
                "ECMAScript target lowering must validate exact planner/program/profile "
                f"correspondence: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::target_lowering",
            "crate::ecmascript_serialization",
            "crate::python_re_serialization",
            "crate::target_serialization",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "bindings::",
            "frontend::",
            "emitters::",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "pcre2operation",
            "pcre2loweringplan",
            "serialize_pcre2(",
            "new regexp(",
            "regexp(",
            "node::process",
            "regex::",
            "emittedpattern {",
            "generatedspan {",
            "targetartifact {",
        ),
    )
    if forbidden is not None:
        return (
            "ECMAScript target lowering violates independent pure "
            f"pre-serialization boundary: {forbidden}"
        )

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "lower_ecmascript(" in text.lower():
            return (
                "ECMAScript target lowering has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
    return None


def python_re_target_lowering_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first structured Python re target-lowering violation."""

    path = "core/src/python_re_lowering.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn lower_python_re(" not in source:
        return "canonical Python re target-lowering stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured diagnostics"),
        ("crate::portability_planning::{", "certified portability plans"),
        ("crate::semantic::{", "normalized Semantic IR"),
        ("crate::source::{", "canonical identity and provenance contracts"),
        ("crate::target::{", "exact immutable target profiles"),
        ("crate::validation::{", "canonical validation and fingerprints"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"Python re target lowering must consume {description}"

    correspondence = (
        "portability.validate()",
        "canonical_sha256(input)",
        "target.reference()",
        'target.engine.id.as_str() != "python_re"',
        "target.runtime.as_ref()",
        'runtime.id.as_str() != "cpython"',
    )
    for marker in correspondence:
        if marker not in source:
            return (
                "Python re target lowering must validate exact planner/program/profile/runtime "
                f"correspondence: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::normalization",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::target_lowering",
            "crate::ecmascript_lowering",
            "crate::ecmascript_serialization",
            "crate::target_serialization",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "crate::python_reference",
            "crate::legacy_reference",
            "bindings::",
            "bindings::python",
            "frontend::",
            "emitters::",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "serde_json::to_string",
            "serde::serialize",
            "format_pattern(",
            "escape_literal(",
            "pcre2operation",
            "pcre2loweringplan",
            "lower_pcre2(",
            "serialize_pcre2(",
            "ecmascriptoperation",
            "ecmascriptloweringplan",
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "serialize_python_re(",
            "re.compile(",
            "strling.core",
            "python::",
            "regex::",
            "emittedpattern {",
            "generatedspan {",
            "targetartifact {",
        ),
    )
    if forbidden is not None:
        return (
            "Python re target lowering violates independent pure "
            f"pre-serialization boundary: {forbidden}"
        )

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "lower_python_re(" in text.lower():
            return (
                "Python re target lowering has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
    return None


def python_re_target_serialization_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first deterministic Python re serialization violation."""

    path = "core/src/python_re_serialization.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn serialize_python_re(" not in source:
        return "canonical Python re target-serialization stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured emission diagnostics"),
        ("crate::python_re_lowering::{", "validated Python re lowering plans"),
        ("crate::source::{", "canonical generated and source coordinates"),
        ("crate::target::{", "canonical TargetArtifact contracts"),
        ("crate::validation::validate", "canonical contract validation"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"Python re target serialization must consume {description}"

    for marker in ("plan.validate()", "artifact.validate()"):
        if marker not in source:
            return (
                "Python re target serialization must validate its exact input and output "
                f"contracts: {marker}"
            )

    for marker in (
        "55e7f0bc93e2192d5f09f6c4ef65b6bff0dc831571059d80edf9b8b661f80a6c",
        "2ba10d0f9ba00c0f5685fc20a40ae436937952074558d8bba89ffe6bb244dfca",
        "python.pattern_kind",
        "plan.case_matching",
    ):
        if marker not in source:
            return (
                "Python re target serialization must preserve exact profile, pattern-kind, "
                f"and flag intent: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "lower_python_re(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::normalization",
            "crate::portability_planning",
            "crate::semantic",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::target_lowering",
            "crate::target_serialization",
            "crate::ecmascript_lowering",
            "crate::ecmascript_serialization",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "bindings::",
            "frontend::",
            "emitters::",
            "crate::target::targetprofile",
            "crate::target::optionselection",
            "engine.version",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "re.compile(",
            "runtime_probe",
            "engine_probe",
            "regex::",
            "pcre2",
            "ecmascriptoperation",
            "ecmascriptloweringplan",
            "serialize_ecmascript(",
            'flags.push("a"',
            'flags.push("l"',
            'flags.push("m"',
            'flags.push("s"',
            'flags.push("u"',
            'flags.push("x"',
        ),
    )
    if forbidden is not None:
        return (
            "Python re target serialization violates mechanical artifact boundary: "
            f"{forbidden}"
        )

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "serialize_python_re(" in text.lower():
            return (
                "Python re target serialization has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
    return None


def ecmascript_target_serialization_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first deterministic ECMAScript serialization violation."""

    path = "core/src/ecmascript_serialization.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn serialize_ecmascript(" not in source:
        return (
            "canonical ECMAScript target-serialization stage boundary cannot be located"
        )

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured emission diagnostics"),
        ("crate::ecmascript_lowering::{", "validated ECMAScript lowering plans"),
        ("crate::source::{", "canonical generated and source coordinates"),
        ("crate::target::{", "canonical TargetArtifact contracts"),
        ("crate::validation::validate", "canonical contract validation"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"ECMAScript target serialization must consume {description}"

    for marker in ("plan.validate()", "artifact.validate()"):
        if marker not in source:
            return (
                "ECMAScript target serialization must validate its exact input and output "
                f"contracts: {marker}"
            )

    for marker in (
        "5117ff6e6c30da54eb31a4621dce5f4807ab0e95f183848e70a01731a4bb4c9f",
        "ecmascript.unicode_mode",
        "plan.case_matching",
    ):
        if marker not in source:
            return (
                "ECMAScript target serialization must preserve exact profile and flag "
                f"intent: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "lower_ecmascript(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::normalization",
            "crate::portability_planning",
            "crate::semantic",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::target_lowering",
            "crate::target_serialization",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "bindings::",
            "frontend::",
            "emitters::",
            "crate::target::targetprofile",
            "crate::target::optionselection",
            "engine.version",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "new regexp(",
            "regexp(",
            "node::process",
            "runtime_probe",
            "engine_probe",
            "regex::",
            "pcre2",
            'flags.push("d"',
            'flags.push("g"',
            'flags.push("m"',
            'flags.push("s"',
            'flags.push("v"',
            'flags.push("y"',
        ),
    )
    if forbidden is not None:
        return (
            "ECMAScript target serialization violates mechanical artifact boundary: "
            f"{forbidden}"
        )

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "serialize_ecmascript(" in text.lower():
            return (
                "ECMAScript target serialization has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
    return None


def python_re_runtime_certification_boundary_violation(
    orchestrator_text: str,
    harness_text: str,
) -> str | None:
    """Return the first exact-CPython certification isolation violation."""

    orchestrator = orchestrator_text.lower()
    harness = harness_text.lower()
    orchestrator_prerequisites = (
        'python_env = "strling_cpython_311_binary"',
        'expected_version = "3.11.15"',
        'expected_implementation = "cpython"',
        'expected_platform = "linux"',
        'expected_machine = "x86_64"',
        "272179ddd9a2e41a0fc8e42e33dfbdca0b3711aa5abf372d3f2d51543d09b625",
        "1fbfa9ca2d8b4a1180be898c8de67732deee8aff7bb838012acb63764be83232",
        "55e7f0bc93e2192d5f09f6c4ef65b6bff0dc831571059d80edf9b8b661f80a6c",
        "2ba10d0f9ba00c0f5685fc20a40ae436937952074558d8bba89ffe6bb244dfca",
        '[str(binary), "-i", "-s", "-b", str(harness)]',
        "identity_reader(binary)",
        "def exact_runtime(",
        '"lang": "c.utf-8"',
        '"lc_all": "c.utf-8"',
        '"tz": "utc"',
        "timeout=30",
    )
    for marker in orchestrator_prerequisites:
        if marker not in orchestrator:
            return (
                "Python re runtime certification must preserve exact binary, profile, "
                f"runtime, harness, and bounded-process authority: {marker}"
            )

    forbidden_orchestrator = _first_forbidden(
        orchestrator,
        (
            "shell=true",
            "os.system(",
            "os.popen(",
            "subprocess.popen(",
            "requests.",
            "urllib.",
            "http.client",
            "socket.",
            "curl ",
            "wget ",
            "pythonpath",
        ),
    )
    if forbidden_orchestrator is not None:
        return (
            "Python re runtime certification violates fixed offline orchestrator "
            f"authority: {forbidden_orchestrator}"
        )

    harness_prerequisites = (
        'protocol_version = "1.0.0"',
        "maximum_input_bytes",
        "maximum_cases",
        "maximum_subjects_per_case",
        "maximum_source_bytes",
        "maximum_subject_units",
        "maximum_matches",
        "sys.stdin.buffer",
        "re.compile(",
        "compiled.finditer(",
        "platform.python_version()",
        "platform.python_implementation()",
        "sys.implementation.cache_tag",
        'sysconfig.get_config_var("soabi")',
    )
    for marker in harness_prerequisites:
        if marker not in harness:
            return (
                "Python re runtime harness must remain bounded, observable, and "
                f"protocol-complete: {marker}"
            )

    forbidden_harness = _first_forbidden(
        harness,
        (
            "import os",
            "import pathlib",
            "import random",
            "import socket",
            "import subprocess",
            "import threading",
            "import time",
            "import urllib",
            "from pathlib",
            "from subprocess",
            "open(",
            "path(",
            "requests.",
            "socket.",
            "sys.argv",
            "sys.path",
            "os.environ",
            "os.getcwd",
            "os.chdir",
        ),
    )
    if forbidden_harness is not None:
        return (
            "Python re runtime harness violates standard-library deterministic authority: "
            f"{forbidden_harness}"
        )
    return None


def ecmascript_runtime_certification_boundary_violation(
    orchestrator_text: str,
    harness_text: str,
) -> str | None:
    """Return the first exact-runtime certification isolation violation."""

    orchestrator = orchestrator_text.lower()
    harness = harness_text.lower()
    orchestrator_prerequisites = (
        'node_env = "strling_node_22_binary"',
        'expected_node = "v22.23.2"',
        'expected_v8 = "12.4.254.21-node.56"',
        'expected_platform = "linux"',
        'expected_architecture = "x64"',
        "d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307",
        "3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327",
        "5117ff6e6c30da54eb31a4621dce5f4807ab0e95f183848e70a01731a4bb4c9f",
        '[str(binary), "--no-warnings", str(harness)]',
        "identity_reader(binary)",
        "def exact_runtime(",
        '"lang": "c.utf-8"',
        '"lc_all": "c.utf-8"',
        '"tz": "utc"',
        "timeout=30",
    )
    for marker in orchestrator_prerequisites:
        if marker not in orchestrator:
            return (
                "ECMAScript runtime certification must preserve exact binary, "
                f"runtime, harness, and bounded-process authority: {marker}"
            )

    forbidden_orchestrator = _first_forbidden(
        orchestrator,
        (
            "shell=true",
            "os.system(",
            "os.popen(",
            "subprocess.popen(",
            "requests.",
            "urllib.",
            "http.client",
            "socket.",
            "fetch(",
            "curl ",
            "wget ",
            "node_options",
        ),
    )
    if forbidden_orchestrator is not None:
        return (
            "ECMAScript runtime certification violates fixed offline orchestrator "
            f"authority: {forbidden_orchestrator}"
        )

    harness_prerequisites = (
        'const protocol_version = "1.0.0"',
        "const maximum_input_bytes",
        "const maximum_cases",
        "const maximum_subjects_per_case",
        "const maximum_source_bytes",
        "const maximum_subject_code_units",
        "const maximum_matches",
        "process.stdin",
        "process.stdout.write",
        "new regexp(",
        'addflag(flags, "d")',
        'addflag(flags, "g")',
        "function advancestringindex(",
        "process.version",
        "process.versions.v8",
        "process.platform",
        "process.arch",
    )
    for marker in harness_prerequisites:
        if marker not in harness:
            return (
                "ECMAScript runtime harness must remain bounded, observable, and "
                f"protocol-complete: {marker}"
            )

    forbidden_harness = _first_forbidden(
        harness,
        (
            "import ",
            "require(",
            'from "',
            "from '",
            "fetch(",
            "xmlhttprequest",
            "websocket",
            "child_process",
            "worker_threads",
            "math.random",
            "date.now",
            "settimeout(",
            "setinterval(",
            "process.env",
            "process.argv",
            "process.cwd",
            "process.chdir",
        ),
    )
    if forbidden_harness is not None:
        return (
            "ECMAScript runtime harness violates module-free deterministic authority: "
            f"{forbidden_harness}"
        )
    return None


def pcre2_target_serialization_boundary_violation(
    source_texts: Mapping[str, str],
) -> str | None:
    """Return the first deterministic PCRE2 serialization violation."""

    path = "core/src/target_serialization.rs"
    source = source_texts.get(path, "").lower()
    source = source.split("\n#[cfg(test)]", maxsplit=1)[0]
    if "pub fn serialize_pcre2(" not in source:
        return "canonical PCRE2 target-serialization stage boundary cannot be located"

    prerequisites = (
        ("crate::diagnostic::{", "canonical structured emission diagnostics"),
        ("crate::source::{", "canonical generated and source coordinates"),
        ("crate::target::{", "canonical TargetArtifact contracts"),
        ("crate::target_lowering::{", "validated structured PCRE2 lowering plans"),
        ("crate::validation::validate", "canonical contract validation"),
    )
    for marker, description in prerequisites:
        if marker not in source:
            return f"PCRE2 target serialization must consume {description}"

    for marker in ("plan.validate()", "artifact.validate()"):
        if marker not in source:
            return (
                "PCRE2 target serialization must validate its exact input and output "
                f"contracts: {marker}"
            )

    forbidden = _first_forbidden(
        source,
        (
            "lower_pcre2(",
            "lower_ecmascript(",
            "serialize_ecmascript(",
            "evaluate_capabilities(",
            "extract_requirements(",
            "plan_portability(",
            "certified_rewrite_registry(",
            "crate::capability_evaluation",
            "crate::ecmascript_lowering",
            "crate::ecmascript_serialization",
            "crate::normalization",
            "crate::portability_planning",
            "crate::semantic",
            "crate::semantic_analysis",
            "crate::structural_analysis",
            "crate::safety_analysis",
            "crate::diagnostic_generation",
            "crate::compiler_pipeline",
            "crate::capability_pipeline",
            "crate::kernel",
            "crate::protocol",
            "crate::conformance",
            "crate::regex_frontend",
            "crate::emitter",
            "crate::emitters",
            "crate::bindings",
            "crate::frontend",
            "crate::lsp",
            "crate::editor",
            "bindings::",
            "frontend::",
            "emitters::",
            "crate::target::targetprofile",
            "crate::target::optionselection",
            "engine.version",
            "std::env::",
            "std::fs::",
            "std::net::",
            "std::path::",
            "std::process::",
            "std::thread::",
            "std::time::",
            "systemtime",
            "thread_rng",
            "rand::",
            "pcre2_compile",
            "pcre2_match",
            "runtime_probe",
            "engine_probe",
            "regex::",
            "(*utf)",
            "(*ucp)",
            "pcre2_code_unit_width",
        ),
    )
    if forbidden is not None:
        return (
            "PCRE2 target serialization violates mechanical artifact boundary: "
            f"{forbidden}"
        )

    for candidate, text in source_texts.items():
        if candidate in {path, "core/src/lib.rs"}:
            continue
        if "serialize_pcre2(" in text.lower():
            return (
                "PCRE2 target serialization has an ungoverned direct caller before "
                f"canonical orchestration exists: {candidate}"
            )
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
            (
                "crate::capability_evaluation",
                "crate::portability_planning",
                "crate::capability_pipeline",
                "crate::target_lowering",
                "crate::ecmascript_serialization",
                "crate::python_re_serialization",
                "crate::target_serialization",
            ),
        )
        if forbidden is not None:
            return (
                "target-neutral stage has a reverse target dependency: "
                f"{path}: {forbidden}"
            )
    return None
