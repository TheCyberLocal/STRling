#!/usr/bin/env python3
"""Validate canonical STRling contracts and their cross-object invariants."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

if __package__:
    from tooling.explanation_contract import ExplanationContractSuite
    from tooling.legacy_regex_contract import LegacyRegexContractSuite
    from tooling.no_match_explanation_contract import NoMatchExplanationContractSuite
    from tooling.semantic_conversion_contract import SemanticConversionContractSuite
    from tooling.semantic_strling_contract import SemanticStrlingContractSuite
    from tooling.stdlib_guarantee_contracts import StandardLibraryGuaranteeSuite
    from tooling.stdlib_registry import StandardLibraryRegistrySuite
else:
    from explanation_contract import ExplanationContractSuite
    from legacy_regex_contract import LegacyRegexContractSuite
    from no_match_explanation_contract import NoMatchExplanationContractSuite
    from semantic_conversion_contract import SemanticConversionContractSuite
    from semantic_strling_contract import SemanticStrlingContractSuite
    from stdlib_guarantee_contracts import StandardLibraryGuaranteeSuite
    from stdlib_registry import StandardLibraryRegistrySuite

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "contracts" / "1.0"
PROFILE_ROOT = ROOT / "spec" / "targets" / "profiles"
CONFORMANCE_ROOT = ROOT / "spec" / "conformance"

FAMILY_SCHEMAS = (
    ("source", "source.schema.json"),
    ("semantic-ir", "semantic-ir.schema.json"),
    ("diagnostic", "diagnostic.schema.json"),
    ("analysis", "analysis.schema.json"),
    ("compile-request", "compile-request.schema.json"),
    ("compile-result", "compile-result.schema.json"),
    ("portability", "portability.schema.json"),
    ("target-profile", "target-profile.schema.json"),
    ("target-artifact", "target-artifact.schema.json"),
    ("conformance-case", "conformance-case.schema.json"),
    ("conformance-manifest", "conformance-manifest.schema.json"),
)

PHASE_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "protocol",
            "frontend_parse",
            "semantic_lowering",
            "normalization",
            "semantic_analysis",
            "portability",
            "target_lowering",
            "emission",
        )
    )
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2, "hint": 3}


class ContractValidationError(ValueError):
    """A schema or cross-contract invariant was violated."""


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from *path*."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ContractValidationError(f"{path}: root value must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    """Return the deterministic JSON encoding governed by the contract suite."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _parse_unicode_scalar(value: str) -> int | None:
    """Parse canonical U+XXXX notation, excluding surrogate code points."""
    if not re.fullmatch(r"U\+[0-9A-F]{4,6}", value):
        return None
    scalar = int(value[2:], 16)
    if scalar > 0x10FFFF or 0xD800 <= scalar <= 0xDFFF:
        return None
    if value != f"U+{scalar:04X}":
        return None
    return scalar


class ContractSuite:
    """Loaded schemas plus semantic validation not expressible in JSON Schema."""

    def __init__(self, contract_root: Path = CONTRACT_ROOT) -> None:
        self.contract_root = contract_root
        self.schemas = {
            path.name: load_json(path)
            for path in sorted(contract_root.glob("*.schema.json"))
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        schema_store = {schema["$id"]: schema for schema in self.schemas.values()}
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=schema_store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }

        self.profile_documents = {
            path: load_json(path) for path in sorted(PROFILE_ROOT.glob("*.json"))
        }
        self.profile_fingerprints: dict[tuple[str, str], str] = {}
        for path, profile in self.profile_documents.items():
            key = (profile["profile_id"], profile["profile_version"])
            if key in self.profile_fingerprints:
                raise ContractValidationError(
                    f"{path}: duplicate target profile identity/revision {key}"
                )
            self.profile_fingerprints[key] = hashlib.sha256(
                canonical_json(profile)
            ).hexdigest()

    def validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        """Validate *value* against one schema and its cross-contract rules."""
        validator = self.validators[schema_name]
        errors = sorted(
            validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise ContractValidationError(
                f"{schema_name} {_json_path(error.path)}: {error.message}"
            )
        if schema_name == "source.schema.json":
            self._validate_source(value)
        elif schema_name == "semantic-ir.schema.json":
            self._validate_semantic(value)
        elif schema_name == "diagnostic.schema.json":
            self._validate_diagnostic(value)
        elif schema_name == "analysis.schema.json":
            self._validate_analysis(value)
        elif schema_name == "compile-request.schema.json":
            self._validate_compile_request(value)
        elif schema_name == "compile-result.schema.json":
            self._validate_compile_result(value)
        elif schema_name == "portability.schema.json":
            self._validate_portability(value)
        elif schema_name == "target-profile.schema.json":
            self._validate_target_profile(value)
        elif schema_name == "target-artifact.schema.json":
            self._validate_target_artifact(value)
        elif schema_name == "conformance-case.schema.json":
            self._validate_conformance_case(value)
        elif schema_name == "conformance-manifest.schema.json":
            self._validate_conformance_manifest(value)

    def validate_suite_structure(self) -> int:
        """Certify suite-wide ownership, boundary, version, and link invariants."""
        schema_ids = [schema["$id"] for schema in self.schemas.values()]
        if len(schema_ids) != len(set(schema_ids)):
            raise ContractValidationError("canonical schema IDs must be unique")
        for name, schema in self.schemas.items():
            expected_id = f"https://strling.dev/contracts/1.0/{name}"
            if schema["$id"] != expected_id:
                raise ContractValidationError(
                    f"{name}: schema ID must be {expected_id}"
                )
            if schema.get("additionalProperties") is not False:
                raise ContractValidationError(
                    f"{name}: canonical root objects must reject unknown fields"
                )

        source_contract_version = self.schemas["source.schema.json"]["$defs"][
            "ContractVersion"
        ]
        if source_contract_version != {
            "type": "string",
            "const": "1.0.0",
        }:
            raise ContractValidationError(
                "source schema must own the suite contract version"
            )
        contract_version_reference = "source.schema.json#/$defs/ContractVersion"
        for name, schema in self.schemas.items():
            if name == "source.schema.json":
                continue
            if contract_version_reference not in json.dumps(schema, sort_keys=True):
                raise ContractValidationError(
                    f"{name}: contract_version must reuse the source definition"
                )

        semantic_text = json.dumps(
            self.schemas["semantic-ir.schema.json"], sort_keys=True
        ).lower()
        for forbidden in (
            "pcre2",
            "ecmascript",
            "python_re",
            "target_profile",
            "engine_options",
            "emitted_pattern",
        ):
            if forbidden in semantic_text:
                raise ContractValidationError(
                    f"Semantic IR contains target-specific marker {forbidden}"
                )
        target_text = json.dumps(
            {
                "profile": self.schemas["target-profile.schema.json"],
                "artifact": self.schemas["target-artifact.schema.json"],
            },
            sort_keys=True,
        ).lower()
        for forbidden in ("frontendidentity", "dialect_version", "parse_ast"):
            if forbidden in target_text:
                raise ContractValidationError(
                    f"target contracts contain frontend marker {forbidden}"
                )

        documents = {
            ROOT / "spec" / "README.md",
            ROOT / "docs" / "spec_links.md",
            ROOT / "spec" / "conformance" / "README.md",
            *sorted((ROOT / "spec" / "contracts").glob("*.md")),
            *sorted(CONTRACT_ROOT.glob("*.md")),
        }
        link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        for document in sorted(documents):
            text = document.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative_target = target.split("#", 1)[0]
                if not relative_target:
                    continue
                resolved = (document.parent / relative_target).resolve()
                if not resolved.exists():
                    raise ContractValidationError(
                        f"{document.relative_to(ROOT)}: unresolved link {target}"
                    )
        return len(documents)

    def validate_positive_examples(self) -> int:
        """Validate every authored positive source and Semantic IR example."""
        count = 0
        for family, schema_name in FAMILY_SCHEMAS:
            for path in sorted(
                (self.contract_root / "examples" / family).glob("*.json")
            ):
                self.validate(schema_name, load_json(path))
                count += 1
        for profile in self.profile_documents.values():
            self.validate("target-profile.schema.json", profile)
            count += 1
        for path in sorted((CONFORMANCE_ROOT / "cases").glob("*.json")):
            self.validate("conformance-case.schema.json", load_json(path))
            count += 1
        self.validate(
            "conformance-manifest.schema.json",
            load_json(CONFORMANCE_ROOT / "manifest.json"),
        )
        count += 1
        return count

    def validate_negative_examples(self) -> int:
        """Prove every controlled malformed example is rejected."""
        count = 0
        for family, schema_name in FAMILY_SCHEMAS:
            for path in sorted(
                (self.contract_root / "invalid" / family).glob("*.json")
            ):
                try:
                    self.validate(schema_name, load_json(path))
                except ContractValidationError:
                    count += 1
                    continue
                raise ContractValidationError(
                    f"controlled invalid example unexpectedly passed: {path}"
                )
        return count

    def _validate_source(self, source: Mapping[str, Any]) -> None:
        content = source["content"]
        if content["kind"] == "inline":
            self._utf8_boundaries(content["text"])
        provenance = source["provenance"]
        for parent in provenance.get("parent_sources", []):
            span = parent.get("span")
            if span is not None:
                if span["source_id"] != parent["source_id"]:
                    raise ContractValidationError(
                        "parent provenance span must identify its parent source"
                    )
                self._validate_span(span, None)

    def _validate_semantic(self, program: Mapping[str, Any]) -> None:
        sources: dict[str, Mapping[str, Any]] = {}
        for source in program.get("sources", []):
            self._validate_source(source)
            source_id = source["source_id"]
            if source_id in sources:
                raise ContractValidationError(f"duplicate source_id {source_id}")
            if source["specification_version"] != program["specification_version"]:
                raise ContractValidationError(
                    f"source {source_id} uses a different specification version"
                )
            sources[source_id] = source

        nodes = list(iter_nodes(program["root"]))
        node_ids: set[str] = set()
        captures: set[str] = set()
        capture_names: set[str] = set()
        references: list[str] = []

        for node in nodes:
            node_id = node["node_id"]
            if node_id in node_ids:
                raise ContractValidationError(f"duplicate node_id {node_id}")
            node_ids.add(node_id)

            origin = node.get("origin")
            if origin is not None:
                self._validate_origin(origin, sources)

            kind = node["kind"]
            if kind == "sequence":
                items = node["items"]
                if any(item["kind"] == "sequence" for item in items):
                    raise ContractValidationError("canonical sequence cannot be nested")
                if any(
                    left["kind"] == right["kind"] == "literal"
                    for left, right in zip(items, items[1:])
                ):
                    raise ContractValidationError(
                        "adjacent canonical literals must be coalesced"
                    )
            elif kind == "alternation" and any(
                branch["kind"] == "alternation" for branch in node["branches"]
            ):
                raise ContractValidationError("canonical alternation cannot be nested")
            elif kind == "repeat":
                maximum = node["max"]
                if maximum is not None and maximum < node["min"]:
                    raise ContractValidationError(
                        "finite repetition maximum cannot be less than minimum"
                    )
            elif kind == "character_set":
                self._validate_character_set(node["members"])
            elif kind == "capture":
                capture_id = node["capture_id"]
                if capture_id in captures:
                    raise ContractValidationError(f"duplicate capture_id {capture_id}")
                captures.add(capture_id)
                name = node.get("name")
                if name is not None:
                    if name in capture_names:
                        raise ContractValidationError(f"duplicate capture name {name}")
                    capture_names.add(name)
            elif kind == "backreference":
                references.append(node["capture_id"])

        for capture_id in references:
            if capture_id not in captures:
                raise ContractValidationError(
                    f"backreference resolves to missing capture_id {capture_id}"
                )

    def _validate_diagnostic(self, diagnostic: Mapping[str, Any]) -> None:
        location = diagnostic.get("primary_location")
        if location is not None:
            self._validate_span(location, None)
        for related in diagnostic.get("related_locations", []):
            self._validate_span(related["location"], None)
        for fix in diagnostic.get("fixes", []):
            edits = fix["edits"]
            edit_keys = [
                (edit["span"]["source_id"], edit["span"]["start"], edit["span"]["end"])
                for edit in edits
            ]
            if edit_keys != sorted(edit_keys):
                raise ContractValidationError("fix edits must be canonically sorted")
            previous: tuple[str, int] | None = None
            for edit in edits:
                span = edit["span"]
                self._validate_span(span, None)
                if previous is not None and previous[0] == span["source_id"]:
                    if span["start"] < previous[1]:
                        raise ContractValidationError("fix edits must not overlap")
                previous = (span["source_id"], span["end"])

    def _validate_analysis(self, analysis: Mapping[str, Any]) -> None:
        facts = analysis["node_facts"]
        fact_ids = [fact["node_id"] for fact in facts]
        if fact_ids != sorted(set(fact_ids)):
            raise ContractValidationError(
                "analysis node_facts must have unique sorted node IDs"
            )
        for fact in facts:
            bounds = fact.get("length_bounds")
            if bounds is not None:
                maximum = bounds["max"]
                if maximum is not None and maximum < bounds["min"]:
                    raise ContractValidationError(
                        "analysis length maximum cannot be less than minimum"
                    )

        requirements = analysis["feature_requirements"]
        requirement_ids = [item["requirement_id"] for item in requirements]
        if requirement_ids != sorted(set(requirement_ids)):
            raise ContractValidationError(
                "feature requirements must have unique sorted IDs"
            )
        for requirement in requirements:
            node_ids = requirement["node_ids"]
            if node_ids != sorted(set(node_ids)):
                raise ContractValidationError(
                    "feature requirement node_ids must be unique and sorted"
                )

    def _validate_portability(self, portability: Mapping[str, Any]) -> None:
        self._validate_profile_reference(portability["target_profile"])
        decisions = portability["decisions"]
        requirement_ids = [item["requirement_id"] for item in decisions]
        if requirement_ids != sorted(set(requirement_ids)):
            raise ContractValidationError(
                "portability decisions must have unique sorted requirement IDs"
            )
        for decision in decisions:
            node_ids = decision["node_ids"]
            if node_ids != sorted(set(node_ids)):
                raise ContractValidationError(
                    "portability decision node_ids must be unique and sorted"
                )
        rank = {"native": 0, "equivalent_rewrite": 1, "unsupported": 2}
        expected = max(
            (decision["status"] for decision in decisions),
            key=rank.__getitem__,
            default="native",
        )
        if portability["status"] != expected:
            raise ContractValidationError(
                "overall portability status must equal the least-supported decision"
            )

    def _validate_target_profile(self, profile: Mapping[str, Any]) -> None:
        specification_versions = profile["compatible_specification_versions"]
        if specification_versions != sorted(specification_versions):
            raise ContractValidationError(
                "compatible specification versions must be canonically sorted"
            )

        capabilities = profile["capabilities"]
        capability_ids = [item["capability_id"] for item in capabilities]
        if capability_ids != sorted(set(capability_ids)):
            raise ContractValidationError(
                "target capabilities must have unique sorted capability IDs"
            )
        semantic_sets = profile["semantic_sets"]
        set_ids = [item["set_id"] for item in semantic_sets]
        if set_ids != sorted(set(set_ids)):
            raise ContractValidationError(
                "semantic sets must have unique sorted set IDs"
            )

        semantic_algorithms = profile["semantic_algorithms"]
        algorithm_ids = [item["algorithm_id"] for item in semantic_algorithms]
        if algorithm_ids != sorted(set(algorithm_ids)):
            raise ContractValidationError(
                "semantic algorithms must have unique sorted algorithm IDs"
            )

        target_limits = profile["target_limits"]
        limit_ids = [item["limit_id"] for item in target_limits]
        if limit_ids != sorted(set(limit_ids)):
            raise ContractValidationError(
                "target limits must have unique sorted limit IDs"
            )

        option_ids = [item["option_id"] for item in profile["options"]]
        if option_ids != sorted(set(option_ids)):
            raise ContractValidationError(
                "target profile options must have unique sorted option IDs"
            )
        evidence_ids = [item["evidence_id"] for item in profile["evidence"]]
        if evidence_ids != sorted(set(evidence_ids)):
            raise ContractValidationError(
                "profile evidence must have unique sorted evidence IDs"
            )
        evidence_id_set = set(evidence_ids)

        def validate_fact_evidence(fact: Mapping[str, Any]) -> None:
            references = fact["evidence"]
            if references != sorted(set(references)):
                raise ContractValidationError(
                    "semantic fact evidence must be nonempty, unique, and sorted"
                )
            missing = set(references) - evidence_id_set
            if missing:
                raise ContractValidationError(
                    "semantic fact evidence does not resolve: "
                    + ", ".join(sorted(missing))
                )

        for semantic_set in semantic_sets:
            definition = semantic_set["definition"]
            kind = definition["kind"]
            unicode_version = semantic_set.get("unicode_version")
            if kind == "character_set":
                scalars = definition["scalars"]
                ranges = definition["ranges"]
                categories = definition["unicode_general_categories"]
                if not scalars and not ranges and not categories:
                    raise ContractValidationError(
                        "character-set definitions require at least one member"
                    )
                parsed_scalars = [_parse_unicode_scalar(item) for item in scalars]
                if any(item is None for item in parsed_scalars):
                    raise ContractValidationError(
                        "character-set scalars require canonical Unicode scalar notation"
                    )
                if parsed_scalars != sorted(set(parsed_scalars)):
                    raise ContractValidationError(
                        "character-set scalars must be unique and sorted by scalar value"
                    )
                parsed_ranges: list[tuple[int, int]] = []
                for item in ranges:
                    start = _parse_unicode_scalar(item["start"])
                    end = _parse_unicode_scalar(item["end"])
                    if start is None or end is None:
                        raise ContractValidationError(
                            "character-set ranges require canonical Unicode scalars"
                        )
                    if start >= end:
                        raise ContractValidationError(
                            "character-set ranges must contain increasing scalars"
                        )
                    parsed_ranges.append((start, end))
                if parsed_ranges != sorted(set(parsed_ranges)):
                    raise ContractValidationError(
                        "character-set ranges must be unique and sorted"
                    )
                if any(
                    left_end + 1 >= right_start
                    for (_, left_end), (right_start, _) in zip(
                        parsed_ranges, parsed_ranges[1:]
                    )
                ):
                    raise ContractValidationError(
                        "character-set ranges must be disjoint and non-adjacent"
                    )
                if any(
                    start <= scalar <= end
                    for scalar in parsed_scalars
                    for start, end in parsed_ranges
                ):
                    raise ContractValidationError(
                        "character-set scalars must not duplicate range members"
                    )
                if categories != sorted(set(categories)):
                    raise ContractValidationError(
                        "Unicode general categories must be unique and sorted"
                    )
                for aggregate in ("C", "L", "M", "N", "P", "S", "Z"):
                    if aggregate in categories and any(
                        item.startswith(aggregate) and len(item) == 2
                        for item in categories
                    ):
                        raise ContractValidationError(
                            "aggregate Unicode categories cannot be combined with subcategories"
                        )
                if definition["universe"] == "byte":
                    if any(item > 0xFF for item in parsed_scalars) or any(
                        end > 0xFF for _, end in parsed_ranges
                    ):
                        raise ContractValidationError(
                            "byte character sets cannot contain values above U+00FF"
                        )
                    if categories or unicode_version is not None:
                        raise ContractValidationError(
                            "byte character sets cannot depend on Unicode data"
                        )
                elif categories and unicode_version is None:
                    raise ContractValidationError(
                        "category-derived character sets require a Unicode version"
                    )
            else:
                canonical_member_order = {
                    member: index
                    for index, member in enumerate(
                        ("LF", "VT", "FF", "CR", "CRLF", "NEL", "LS", "PS")
                    )
                }
                members = definition["members"]
                if not members:
                    raise ContractValidationError(
                        "line-terminator sets require at least one member"
                    )
                if members != sorted(
                    set(members), key=canonical_member_order.__getitem__
                ):
                    raise ContractValidationError(
                        "line terminators must be unique and use canonical semantic order"
                    )
                if unicode_version is not None:
                    raise ContractValidationError(
                        "line-terminator sets cannot declare a Unicode version"
                    )
                has_crlf = "CRLF" in members
                if has_crlf and not {"CR", "LF"}.issubset(members):
                    raise ContractValidationError(
                        "CRLF line semantics require CR and LF members"
                    )
                if not has_crlf and definition["sequence_policy"] != (
                    "independent_code_points"
                ):
                    raise ContractValidationError(
                        "atomic-longest sequence policy requires a CRLF member"
                    )
            set_id = semantic_set["set_id"]
            if set_id == "line_terminators" and kind != "line_terminator_set":
                raise ContractValidationError(
                    "line_terminators must use a line-terminator-set definition"
                )
            if set_id in {"word_characters", "wildcard_exclusions"} and kind != (
                "character_set"
            ):
                raise ContractValidationError(
                    f"{set_id} must use a character-set definition"
                )
            validate_fact_evidence(semantic_set)

        for algorithm in semantic_algorithms:
            definition = algorithm["definition"]
            kind = definition["kind"]
            if algorithm["algorithm_id"] != kind:
                raise ContractValidationError(
                    "semantic algorithm ID must match its closed definition kind"
                )
            unicode_version = algorithm.get("unicode_version")
            if kind == "case_folding":
                mode = definition["mode"]
                unicode_sensitive = mode != "ascii"
                if unicode_sensitive != (unicode_version is not None):
                    raise ContractValidationError(
                        "Unicode-sensitive case folding requires exactly one Unicode version"
                    )
                has_variant = "variant" in definition
                if (mode == "engine_specific") != has_variant:
                    raise ContractValidationError(
                        "only engine-specific case folding requires a variant identity"
                    )
                classes = definition["additional_equivalence_classes"]
                if mode == "ascii" and classes:
                    raise ContractValidationError(
                        "ASCII case folding cannot declare Unicode equivalence classes"
                    )
                parsed_classes: list[tuple[int, ...]] = []
                seen_scalars: set[int] = set()
                for equivalence_class in classes:
                    parsed = tuple(
                        scalar
                        for item in equivalence_class
                        if (scalar := _parse_unicode_scalar(item)) is not None
                    )
                    if len(parsed) != len(equivalence_class):
                        raise ContractValidationError(
                            "case-folding equivalence classes require canonical Unicode scalars"
                        )
                    if list(parsed) != sorted(set(parsed)):
                        raise ContractValidationError(
                            "case-folding equivalence-class scalars must be unique and sorted"
                        )
                    if seen_scalars.intersection(parsed):
                        raise ContractValidationError(
                            "a scalar may occur in only one additional equivalence class"
                        )
                    seen_scalars.update(parsed)
                    parsed_classes.append(parsed)
                if parsed_classes != sorted(set(parsed_classes)):
                    raise ContractValidationError(
                        "case-folding equivalence classes must be unique and sorted"
                    )
            elif unicode_version is not None:
                raise ContractValidationError(
                    "non-folding semantic algorithms cannot declare a Unicode version"
                )
            validate_fact_evidence(algorithm)

        for target_limit in target_limits:
            scope = target_limit["scope"]
            bound_kind = target_limit["bound"]["kind"]
            prediction = target_limit["prediction"]
            valid_limit = (
                (
                    scope == "syntactic_quantifier"
                    and bound_kind == "numeric"
                    and prediction == "exact"
                )
                or (
                    scope == "compiled_pattern"
                    and bound_kind in {"numeric", "unknown"}
                    and prediction == "artifact_and_configuration_dependent"
                )
                or (
                    scope == "resource_dependent"
                    and bound_kind == "resource_dependent"
                    and prediction == "resource_dependent"
                )
            )
            if not valid_limit:
                raise ContractValidationError(
                    "target limit scope, bound, and prediction are inconsistent"
                )
            if (
                target_limit["limit_id"] == "compiled_pattern_size"
                and scope != "compiled_pattern"
            ):
                raise ContractValidationError(
                    "compiled_pattern_size must describe a compiled-pattern limit"
                )
            if (
                target_limit["limit_id"] == "syntactic_quantifier_bound"
                and scope != "syntactic_quantifier"
            ):
                raise ContractValidationError(
                    "syntactic_quantifier_bound must describe a syntactic limit"
                )
            validate_fact_evidence(target_limit)

        option_id_set = set(option_ids)
        semantic_fact_ids = {
            "semantic_set": set(set_ids),
            "semantic_algorithm": set(algorithm_ids),
            "target_limit": set(limit_ids),
        }

        def capability_supports_word(capability: Mapping[str, Any]) -> bool:
            constraint = next(
                (
                    item
                    for item in capability["constraints"]
                    if item["constraint_id"] == "class"
                ),
                None,
            )
            if constraint is None:
                return True
            value = constraint["value"]
            if isinstance(value, list):
                return "word" in value
            return value == "word"

        for capability in capabilities:
            constraints = capability["constraints"]
            constraint_ids = [item["constraint_id"] for item in constraints]
            if constraint_ids != sorted(set(constraint_ids)):
                raise ContractValidationError(
                    "capability constraints must have unique sorted constraint IDs"
                )
            for constraint in constraints:
                if constraint["operator"] == "requires_option":
                    value = constraint["value"]
                    if not isinstance(value, str) or value not in option_id_set:
                        raise ContractValidationError(
                            "requires_option must name an option declared by the profile"
                        )
            references = capability["semantic_fact_refs"]
            reference_keys = [
                (item["kind"], item["role"], item["fact_id"]) for item in references
            ]
            if reference_keys != sorted(set(reference_keys)):
                raise ContractValidationError(
                    "capability semantic fact references must be unique and sorted"
                )
            reference_roles = [(item["kind"], item["role"]) for item in references]
            if len(reference_roles) != len(set(reference_roles)):
                raise ContractValidationError(
                    "capability semantic fact roles must be unique within each kind"
                )
            for reference in references:
                if reference["fact_id"] not in semantic_fact_ids[reference["kind"]]:
                    raise ContractValidationError(
                        "capability semantic fact reference does not resolve"
                    )

            if capability["availability"] == "unavailable":
                continue
            capability_id = capability["capability_id"]
            required: list[tuple[str, str, str]] = []
            if capability_id in {
                "anchors.end_before_final_line_terminator",
                "anchors.line_end",
                "anchors.line_start",
            }:
                required.append(
                    ("semantic_set", "line_terminators", "line_terminators")
                )
            elif capability_id == "boundaries.word":
                required.append(("semantic_set", "word_characters", "word_characters"))
            elif capability_id == "character_classes.unicode" and (
                capability_supports_word(capability)
            ):
                required.append(("semantic_set", "word_characters", "word_characters"))
            elif capability_id == "matching.case_insensitive":
                required.append(("semantic_algorithm", "case_folding", "case_folding"))
            elif capability_id == "references.backreference":
                required.extend(
                    (
                        (
                            "semantic_algorithm",
                            "backreference_unset",
                            "backreference_unset",
                        ),
                        (
                            "semantic_algorithm",
                            "capture_reset_on_iteration",
                            "capture_reset_on_iteration",
                        ),
                    )
                )
            elif capability_id == "character_semantics.unicode_scalar":
                required.append(
                    ("semantic_algorithm", "matching_unit", "matching_unit")
                )
            elif capability_id == "character_classes.wildcard":
                required.extend(
                    (
                        (
                            "semantic_algorithm",
                            "matching_unit",
                            "matching_unit",
                        ),
                        (
                            "semantic_set",
                            "wildcard_exclusions",
                            "wildcard_exclusions",
                        ),
                    )
                )
            for reference in required:
                if reference not in reference_keys:
                    raise ContractValidationError(
                        f"usable capability {capability_id} lacks required semantic fact"
                    )
            if capability_id == "repetition.bounded":
                referenced_limits = {
                    item["fact_id"]
                    for item in references
                    if item["kind"] == "target_limit"
                }
                supported_limits = {
                    item["limit_id"]
                    for item in target_limits
                    if item["scope"] in {"syntactic_quantifier", "compiled_pattern"}
                }
                if not referenced_limits.intersection(supported_limits):
                    raise ContractValidationError(
                        "usable repetition.bounded requires a syntactic or compiled target-limit fact"
                    )

    def _validate_profile_reference(
        self, reference: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        key = (reference["profile_id"], reference["profile_version"])
        expected = self.profile_fingerprints.get(key)
        if expected is None:
            raise ContractValidationError(
                f"target profile reference does not resolve: {key}"
            )
        if reference["sha256"] != expected:
            raise ContractValidationError(
                "target profile reference fingerprint does not match canonical JSON"
            )
        return next(
            profile
            for profile in self.profile_documents.values()
            if (profile["profile_id"], profile["profile_version"]) == key
        )

    def _validate_target_artifact(self, artifact: Mapping[str, Any]) -> None:
        profile = self._validate_profile_reference(artifact["target_profile"])
        options = artifact["engine_options"]
        option_keys = [(item["option_id"], item["stage"]) for item in options]
        if option_keys != sorted(set(option_keys)):
            raise ContractValidationError(
                "artifact engine options must be unique and canonically sorted"
            )
        profile_options = {item["option_id"]: item for item in profile["options"]}
        for option in options:
            declared = profile_options.get(option["option_id"])
            if declared is None:
                raise ContractValidationError(
                    f"artifact option is not declared by profile: {option['option_id']}"
                )
            if (option["stage"], option["value"]) != (
                declared["stage"],
                declared["value"],
            ):
                raise ContractValidationError(
                    f"artifact option disagrees with profile: {option['option_id']}"
                )
        required_options = {
            item["option_id"]
            for item in profile["options"]
            if item["selection"] == "required"
        }
        missing_options = required_options - {item["option_id"] for item in options}
        if missing_options:
            raise ContractValidationError(
                "artifact omits required profile options: "
                + ", ".join(sorted(missing_options))
            )

        requirements = artifact["requirements"]
        requirement_ids = [item["requirement_id"] for item in requirements]
        if requirement_ids != sorted(set(requirement_ids)):
            raise ContractValidationError(
                "artifact requirements must have unique sorted requirement IDs"
            )
        rank = {"native": 0, "equivalent_rewrite": 1}
        expected_status = max(
            (item["status"] for item in requirements),
            key=rank.__getitem__,
            default="native",
        )
        if artifact["portability_status"] != expected_status:
            raise ContractValidationError(
                "artifact status must equal its least-supported requirement"
            )

        generated_boundaries = self._utf8_boundaries(artifact["pattern"]["text"])
        source_map = artifact["source_map"]
        generated_keys = [
            (item["generated_span"]["start"], item["generated_span"]["end"])
            for item in source_map
        ]
        if generated_keys != sorted(set(generated_keys)):
            raise ContractValidationError(
                "source-map entries must have unique sorted generated spans"
            )
        for entry in source_map:
            generated_span = entry["generated_span"]
            if (
                generated_span["start"] > generated_span["end"]
                or generated_span["start"] not in generated_boundaries
                or generated_span["end"] not in generated_boundaries
            ):
                raise ContractValidationError(
                    "generated spans must use valid UTF-8 pattern boundaries"
                )
            node_ids = entry["node_ids"]
            if node_ids != sorted(set(node_ids)):
                raise ContractValidationError(
                    "source-map node IDs must be unique and sorted"
                )
            source_spans = entry["source_spans"]
            source_keys = [
                (item["source_id"], item["start"], item["end"]) for item in source_spans
            ]
            if source_keys != sorted(set(source_keys)):
                raise ContractValidationError(
                    "source-map source spans must be unique and sorted"
                )
            for span in source_spans:
                self._validate_span(span, None)

        diagnostics = artifact["emission_diagnostics"]
        if any(item["severity"] == "error" for item in diagnostics):
            raise ContractValidationError(
                "an emitted artifact cannot contain an error diagnostic"
            )
        if any(
            item["phase"] not in {"target_lowering", "emission"} for item in diagnostics
        ):
            raise ContractValidationError(
                "artifact diagnostics must belong to target lowering or emission"
            )
        keys = [_diagnostic_key(item) for item in diagnostics]
        if keys != sorted(keys):
            raise ContractValidationError(
                "artifact diagnostics must use canonical result order"
            )

    def _validate_conformance_case(self, case: Mapping[str, Any]) -> None:
        specification_version = case["specification_version"]
        input_value = case["input"]
        sources: dict[str, Mapping[str, Any]] = {}
        input_program: Mapping[str, Any] | None = None
        if input_value["kind"] == "source":
            source = input_value["document"]
            self._validate_source(source)
            sources[source["source_id"]] = source
            input_specification = source["specification_version"]
        else:
            input_program = input_value["program"]
            self._validate_semantic(input_program)
            input_specification = input_program["specification_version"]
            sources = {
                source["source_id"]: source
                for source in input_program.get("sources", [])
            }
        if input_specification != specification_version:
            raise ContractValidationError(
                "conformance input and case specification versions must match"
            )

        intent_path = (ROOT / case["authorship"]["intent_source"]).resolve()
        specification_root = (ROOT / "spec").resolve()
        if (
            not intent_path.is_relative_to(specification_root)
            or not intent_path.is_file()
        ):
            raise ContractValidationError(
                "conformance intent_source must resolve to specification material"
            )

        expectations = case["expectations"]
        semantic = expectations.get("semantic")
        expected_program: Mapping[str, Any] | None = None
        if semantic is not None:
            expected_program = semantic.get("exact_program")
            if expected_program is not None:
                self._validate_semantic(expected_program)
                if expected_program["specification_version"] != specification_version:
                    raise ContractValidationError(
                        "exact semantic expectation must use the case specification"
                    )
                if input_program is not None and expected_program != input_program:
                    raise ContractValidationError(
                        "normalized semantic input must be preserved by an exact expectation"
                    )
            fact_program = expected_program or input_program
            facts = semantic.get("facts")
            if facts is not None and fact_program is not None:
                nodes = list(iter_nodes(fact_program["root"]))
                if (
                    "root_kind" in facts
                    and facts["root_kind"] != fact_program["root"]["kind"]
                ):
                    raise ContractValidationError(
                        "semantic root_kind fact contradicts the expected program"
                    )
                if "node_count" in facts and facts["node_count"] != len(nodes):
                    raise ContractValidationError(
                        "semantic node_count fact contradicts the expected program"
                    )
                captures = sorted(
                    node["capture_id"] for node in nodes if node["kind"] == "capture"
                )
                if "capture_ids" in facts and facts["capture_ids"] != captures:
                    raise ContractValidationError(
                        "semantic capture_ids fact contradicts the expected program"
                    )

        diagnostics = expectations.get("diagnostics")
        has_expected_error = False
        if diagnostics is not None:
            items = diagnostics["items"]
            keys = [_diagnostic_expectation_key(item) for item in items]
            if keys != sorted(set(keys)):
                raise ContractValidationError(
                    "diagnostic expectations must be unique and canonically sorted"
                )
            has_expected_error = any(item["severity"] == "error" for item in items)
            for item in items:
                location = item.get("primary_location")
                if location is not None:
                    source = sources.get(location["source_id"])
                    if source is None:
                        raise ContractValidationError(
                            "diagnostic expectation refers to an undeclared source"
                        )
                    self._validate_span(location, source)

        matches = expectations.get("matches")
        targets = expectations.get("targets")
        if has_expected_error and (matches is not None or targets is not None):
            raise ContractValidationError(
                "error-diagnostic cases cannot declare match or target expectations"
            )

        semantic_program = expected_program or input_program
        declared_capture_ids: set[str] = set()
        if semantic_program is not None:
            declared_capture_ids = {
                node["capture_id"]
                for node in iter_nodes(semantic_program["root"])
                if node["kind"] == "capture"
            }
        if matches is not None:
            positive = matches["positive"]
            negative = matches["negative"]
            positive_ids = [item["match_id"] for item in positive]
            negative_ids = [item["match_id"] for item in negative]
            if positive_ids != sorted(set(positive_ids)):
                raise ContractValidationError(
                    "positive match IDs must be unique and sorted"
                )
            if negative_ids != sorted(set(negative_ids)):
                raise ContractValidationError(
                    "negative match IDs must be unique and sorted"
                )
            if set(positive_ids).intersection(negative_ids):
                raise ContractValidationError(
                    "match IDs must be unique across positive and negative cases"
                )
            for match in positive:
                capture_ids = [item["capture_id"] for item in match["captures"]]
                if capture_ids != sorted(set(capture_ids)):
                    raise ContractValidationError(
                        "capture expectations must have unique sorted logical IDs"
                    )
                missing = set(capture_ids) - declared_capture_ids
                if missing:
                    raise ContractValidationError(
                        "capture expectations refer to undeclared logical IDs: "
                        + ", ".join(sorted(missing))
                    )
                subject_bytes = match["subject"].encode("utf-8")
                subject_boundaries = self._utf8_boundaries(match["subject"])
                for capture in match["captures"]:
                    if not capture["matched"]:
                        continue
                    span = capture["subject_span"]
                    start = span["start"]
                    end = span["end"]
                    if (
                        start > end
                        or start not in subject_boundaries
                        or end not in subject_boundaries
                        or subject_bytes[start:end].decode("utf-8") != capture["text"]
                    ):
                        raise ContractValidationError(
                            "capture text must equal its UTF-8 subject span"
                        )

        if targets is not None:
            target_keys = [
                (
                    item["target_profile"]["profile_id"],
                    item["target_profile"]["profile_version"],
                    item["target_profile"]["sha256"],
                )
                for item in targets
            ]
            if target_keys != sorted(set(target_keys)):
                raise ContractValidationError(
                    "target expectations must be unique and canonically sorted"
                )
            for item in targets:
                profile = self._validate_profile_reference(item["target_profile"])
                if (
                    specification_version
                    not in profile["compatible_specification_versions"]
                ):
                    raise ContractValidationError(
                        "target profile is not declared compatible with case specification"
                    )
                reason_codes = item.get("reason_codes", [])
                if reason_codes != sorted(reason_codes):
                    raise ContractValidationError(
                        "target reason codes must be canonically sorted"
                    )

        evidence = case.get("compatibility_evidence", [])
        evidence_keys = [(item["kind"], item["reference"]) for item in evidence]
        if evidence_keys != sorted(set(evidence_keys)):
            raise ContractValidationError(
                "compatibility evidence must be unique and canonically sorted"
            )
        for item in evidence:
            reference = item["reference"]
            if reference.startswith(("tests/", "spec/", "docs/")):
                if not (ROOT / reference).is_file():
                    raise ContractValidationError(
                        f"compatibility evidence does not resolve: {reference}"
                    )
        tags = case.get("tags", [])
        if tags != sorted(tags):
            raise ContractValidationError("conformance tags must be sorted")

    def _validate_conformance_manifest(self, manifest: Mapping[str, Any]) -> None:
        entries = manifest["cases"]
        case_ids = [entry["case_id"] for entry in entries]
        paths = [entry["path"] for entry in entries]
        if case_ids != sorted(set(case_ids)):
            raise ContractValidationError(
                "manifest case entries must have unique sorted case IDs"
            )
        if len(paths) != len(set(paths)):
            raise ContractValidationError("manifest case paths must be unique")

        listed_paths: set[Path] = set()
        cases_root = (CONFORMANCE_ROOT / "cases").resolve()
        for entry in entries:
            path = (ROOT / entry["path"]).resolve()
            if not path.is_relative_to(cases_root) or not path.is_file():
                raise ContractValidationError(
                    f"manifest case path does not resolve under spec/conformance: {path}"
                )
            listed_paths.add(path)
            case = load_json(path)
            self.validate("conformance-case.schema.json", case)
            if case["case_id"] != entry["case_id"]:
                raise ContractValidationError(
                    "manifest case ID does not match case document"
                )
            if case["specification_version"] != manifest["specification_version"]:
                raise ContractValidationError(
                    "manifest and case specification versions must match"
                )
            fingerprint = hashlib.sha256(canonical_json(case)).hexdigest()
            if fingerprint != entry["sha256"]:
                raise ContractValidationError(
                    "manifest case fingerprint does not match canonical JSON"
                )

        actual_paths = {
            path.resolve() for path in (CONFORMANCE_ROOT / "cases").glob("*.json")
        }
        if listed_paths != actual_paths:
            raise ContractValidationError(
                "manifest must list every and only specification-owned case file"
            )

        if manifest["authority_status"] == "delegated_normative":
            delegation = manifest["delegation"]
            normative_source = (ROOT / delegation["normative_source"]).resolve()
            versions_root = (ROOT / "spec" / "versions").resolve()
            if (
                not normative_source.is_relative_to(versions_root)
                or not normative_source.is_file()
                or delegation["ratified_specification"]
                != manifest["specification_version"]
            ):
                raise ContractValidationError(
                    "normative manifest delegation must resolve to its ratified specification"
                )

    def _validate_compile_request(self, request: Mapping[str, Any]) -> None:
        input_value = request["input"]
        if input_value["kind"] == "source":
            source = input_value["document"]
            self._validate_source(source)
            input_specification = source["specification_version"]
        else:
            program = input_value["program"]
            self._validate_semantic(program)
            input_specification = program["specification_version"]
        if input_specification != request["specification_version"]:
            raise ContractValidationError(
                "compile input and request specification versions must match"
            )
        output_order = {
            "semantic": 0,
            "analysis": 1,
            "portability": 2,
            "target_artifact": 3,
        }
        outputs = request["requested_outputs"]
        if outputs != sorted(outputs, key=output_order.__getitem__):
            raise ContractValidationError("requested_outputs must use canonical order")
        if "target_profile" in request:
            self._validate_profile_reference(request["target_profile"])

    def _validate_compile_result(self, result: Mapping[str, Any]) -> None:
        diagnostics = result["diagnostics"]
        for diagnostic in diagnostics:
            self._validate_diagnostic(diagnostic)
        occurrences = [diagnostic["occurrence"] for diagnostic in diagnostics]
        if len(occurrences) != len(set(occurrences)):
            raise ContractValidationError("diagnostic occurrence values must be unique")
        keys = [_diagnostic_key(diagnostic) for diagnostic in diagnostics]
        if keys != sorted(keys):
            raise ContractValidationError("diagnostics must use canonical result order")

        has_error = any(item["severity"] == "error" for item in diagnostics)
        if result["outcome"] == "succeeded" and has_error:
            raise ContractValidationError("successful result cannot contain errors")
        if result["outcome"] == "failed" and not has_error:
            raise ContractValidationError("failed result must contain an error")

        specification_version = result["specification_version"]
        semantic_result = result.get("semantic_result")
        if semantic_result is not None:
            program = semantic_result["program"]
            self._validate_semantic(program)
            if program["specification_version"] != specification_version:
                raise ContractValidationError(
                    "semantic result specification version must match result"
                )
            if semantic_result["status"] == "partial":
                prohibited = {"analysis", "portability", "artifact"}.intersection(
                    result
                )
                if prohibited:
                    raise ContractValidationError(
                        "partial semantics cannot feed analysis, planning, or emission"
                    )

        analysis = result.get("analysis")
        if analysis is not None:
            self._validate_analysis(analysis)
            if analysis["specification_version"] != specification_version:
                raise ContractValidationError(
                    "analysis specification version must match result"
                )
        portability = result.get("portability")
        if portability is not None:
            self._validate_portability(portability)
            if portability["specification_version"] != specification_version:
                raise ContractValidationError(
                    "portability specification version must match result"
                )
        artifact = result.get("artifact")
        if artifact is not None:
            self._validate_target_artifact(artifact)
            if has_error:
                raise ContractValidationError(
                    "an error result cannot contain an artifact"
                )
            if artifact["specification_version"] != specification_version:
                raise ContractValidationError(
                    "artifact specification version must match result"
                )
            if portability is not None:
                if portability["status"] == "unsupported":
                    raise ContractValidationError(
                        "unsupported portability cannot produce an artifact"
                    )
                if artifact["target_profile"] != portability["target_profile"]:
                    raise ContractValidationError(
                        "artifact and portability profiles must match"
                    )
                if artifact["portability_status"] != portability["status"]:
                    raise ContractValidationError(
                        "artifact and portability statuses must match"
                    )
            result_diagnostics = {canonical_json(item) for item in diagnostics}
            if any(
                canonical_json(item) not in result_diagnostics
                for item in artifact["emission_diagnostics"]
            ):
                raise ContractValidationError(
                    "artifact emission diagnostics must also appear in result diagnostics"
                )

    def validate_exchange(
        self,
        request: Mapping[str, Any],
        result: Mapping[str, Any],
        supported_frontends: frozenset[str] = frozenset(
            {"semantic_strling", "regex_frontend"}
        ),
    ) -> None:
        """Validate request/result behavior that requires both protocol objects."""
        self.validate("compile-request.schema.json", request)
        self.validate("compile-result.schema.json", result)
        if request["specification_version"] != result["specification_version"]:
            raise ContractValidationError(
                "request and result specification versions must match"
            )

        outputs = set(request["requested_outputs"])
        if result["outcome"] == "succeeded":
            required_sections = {
                "semantic": "semantic_result",
                "analysis": "analysis",
                "portability": "portability",
                "target_artifact": "artifact",
            }
            for output in outputs:
                if required_sections[output] not in result:
                    raise ContractValidationError(
                        f"successful result omitted requested output {output}"
                    )
        semantic_result = result.get("semantic_result")
        if semantic_result is not None and semantic_result["status"] == "partial":
            if (
                request["compiler_options"]["partial_semantics"]
                != "allow_for_diagnostics"
            ):
                raise ContractValidationError(
                    "partial semantics were not enabled by the request"
                )

        input_value = request["input"]
        if input_value["kind"] == "source":
            frontend = input_value["document"]["frontend"]["id"]
            if frontend not in supported_frontends:
                if result["outcome"] != "failed" or not any(
                    diagnostic["code"] == "STRL-PROTOCOL-0002"
                    for diagnostic in result["diagnostics"]
                ):
                    raise ContractValidationError(
                        "unsupported frontend must produce a structured protocol failure"
                    )

        sources: dict[str, Mapping[str, Any]] = {}

        def add_sources(program_sources: list[Mapping[str, Any]]) -> None:
            for source in program_sources:
                source_id = source["source_id"]
                if source_id in sources and sources[source_id] != source:
                    raise ContractValidationError(
                        f"conflicting source declarations for {source_id}"
                    )
                sources[source_id] = source

        if input_value["kind"] == "source":
            document = input_value["document"]
            sources[document["source_id"]] = document
        else:
            add_sources(input_value["program"].get("sources", []))
        if semantic_result is not None:
            add_sources(semantic_result["program"].get("sources", []))

        def validate_attributed_span(span: Mapping[str, Any]) -> None:
            source_id = span["source_id"]
            if source_id not in sources:
                raise ContractValidationError(
                    f"diagnostic refers to undeclared source_id {source_id}"
                )
            self._validate_span(span, sources[source_id])

        for diagnostic in result["diagnostics"]:
            location = diagnostic.get("primary_location")
            if location is not None:
                validate_attributed_span(location)
            for related in diagnostic.get("related_locations", []):
                validate_attributed_span(related["location"])
            for fix in diagnostic.get("fixes", []):
                for edit in fix["edits"]:
                    validate_attributed_span(edit["span"])

        program: Mapping[str, Any] | None = None
        if semantic_result is not None:
            program = semantic_result["program"]
        elif input_value["kind"] == "semantic":
            program = input_value["program"]
        if program is not None:
            node_ids = {node["node_id"] for node in iter_nodes(program["root"])}
            analysis = result.get("analysis")
            if analysis is not None:
                referenced_node_ids = {
                    fact["node_id"] for fact in analysis["node_facts"]
                }
                referenced_node_ids.update(
                    node_id
                    for requirement in analysis["feature_requirements"]
                    for node_id in requirement["node_ids"]
                )
                missing = referenced_node_ids - node_ids
                if missing:
                    raise ContractValidationError(
                        "analysis refers to undeclared semantic node IDs: "
                        + ", ".join(sorted(missing))
                    )
            portability = result.get("portability")
            if portability is not None:
                referenced_node_ids = {
                    node_id
                    for decision in portability["decisions"]
                    for node_id in decision["node_ids"]
                }
                missing = referenced_node_ids - node_ids
                if missing:
                    raise ContractValidationError(
                        "portability refers to undeclared semantic node IDs: "
                        + ", ".join(sorted(missing))
                    )
            artifact = result.get("artifact")
            if artifact is not None:
                referenced_node_ids = {
                    node_id
                    for entry in artifact["source_map"]
                    for node_id in entry["node_ids"]
                }
                missing = referenced_node_ids - node_ids
                if missing:
                    raise ContractValidationError(
                        "artifact source map refers to undeclared semantic node IDs: "
                        + ", ".join(sorted(missing))
                    )
                for entry in artifact["source_map"]:
                    for span in entry["source_spans"]:
                        validate_attributed_span(span)

        portability = result.get("portability")
        if (
            portability is not None
            and request.get("target_profile") != portability["target_profile"]
        ):
            raise ContractValidationError(
                "portability profile must equal the requested target profile"
            )
        artifact = result.get("artifact")
        if (
            artifact is not None
            and request.get("target_profile") != artifact["target_profile"]
        ):
            raise ContractValidationError(
                "artifact profile must equal the requested target profile"
            )

    def _validate_origin(
        self,
        origin: Mapping[str, Any],
        sources: Mapping[str, Mapping[str, Any]],
    ) -> None:
        spans = origin.get("source_spans", [])
        span_keys = [(span["source_id"], span["start"], span["end"]) for span in spans]
        if span_keys != sorted(set(span_keys)):
            raise ContractValidationError(
                "origin source_spans must be unique and canonically sorted"
            )
        for span in spans:
            source_id = span["source_id"]
            if source_id not in sources:
                raise ContractValidationError(
                    f"origin refers to undeclared source_id {source_id}"
                )
            self._validate_span(span, sources[source_id])

        derived = origin.get("derived_from_node_ids", [])
        if derived != sorted(set(derived)):
            raise ContractValidationError(
                "derived_from_node_ids must be unique and canonically sorted"
            )

    def _validate_span(
        self,
        span: Mapping[str, Any],
        source: Mapping[str, Any] | None,
    ) -> None:
        start = span["start"]
        end = span["end"]
        if start > end:
            raise ContractValidationError("source span start must not exceed end")
        if source is None or source["content"]["kind"] != "inline":
            return
        boundaries = self._utf8_boundaries(source["content"]["text"])
        if start not in boundaries or end not in boundaries:
            raise ContractValidationError(
                "source span endpoints must be UTF-8 code-point boundaries"
            )

    @staticmethod
    def _utf8_boundaries(text: str) -> set[int]:
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ContractValidationError(
                "source text must contain valid Unicode"
            ) from error
        boundaries = {0}
        offset = 0
        for character in text:
            offset += len(character.encode("utf-8"))
            boundaries.add(offset)
        if offset != len(encoded):
            raise ContractValidationError("UTF-8 boundary calculation was inconsistent")
        return boundaries

    @staticmethod
    def _validate_character_set(members: list[Mapping[str, Any]]) -> None:
        keys = [_character_member_key(member) for member in members]
        if keys != sorted(set(keys)):
            raise ContractValidationError(
                "character-set members must be unique and canonically sorted"
            )
        for member in members:
            if member["kind"] == "range" and ord(member["start"]) > ord(member["end"]):
                raise ContractValidationError(
                    "character-set range start cannot exceed its end"
                )


def _diagnostic_expectation_key(
    diagnostic: Mapping[str, Any],
) -> tuple[Any, ...]:
    location = diagnostic.get("primary_location")
    if location is None:
        location_key: tuple[Any, ...] = (1, "", 0, 0)
    else:
        location_key = (
            0,
            location["source_id"],
            location["start"],
            location["end"],
        )
    return (
        *location_key,
        PHASE_ORDER[diagnostic["phase"]],
        SEVERITY_ORDER[diagnostic["severity"]],
        diagnostic["category"],
        diagnostic["code"],
    )


def _diagnostic_key(diagnostic: Mapping[str, Any]) -> tuple[Any, ...]:
    location = diagnostic.get("primary_location")
    if location is None:
        location_key: tuple[Any, ...] = (1, "", 0, 0)
    else:
        location_key = (
            0,
            location["source_id"],
            location["start"],
            location["end"],
        )
    return (
        *location_key,
        PHASE_ORDER[diagnostic["phase"]],
        SEVERITY_ORDER[diagnostic["severity"]],
        diagnostic["code"],
        diagnostic["occurrence"],
    )


def _character_member_key(member: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = member["kind"]
    if kind == "literal":
        return (0, member["value"])
    if kind == "range":
        return (1, member["start"], member["end"])
    if kind == "builtin":
        return (2, member["name"], member["domain"], member["negated"])
    return (
        3,
        member["property"],
        member.get("value", ""),
        member["negated"],
    )


def iter_nodes(root: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Yield Semantic IR nodes in deterministic preorder."""
    yield root
    kind = root["kind"]
    if kind == "sequence":
        for child in root["items"]:
            yield from iter_nodes(child)
    elif kind == "alternation":
        for child in root["branches"]:
            yield from iter_nodes(child)
    elif kind in {"repeat", "capture", "lookaround", "atomic"}:
        yield from iter_nodes(root["body"])


def main() -> int:
    repository_path = str(ROOT)
    if repository_path not in sys.path:
        sys.path.insert(0, repository_path)
    from tooling.shared_cross_engine_corpus import validate_corpus
    from tooling.simply_adapter_contract import certify as certify_simply_adapters
    from tooling.simply_contract import Simply11ContractSuite, SimplyContractSuite

    suite = ContractSuite()
    explanation_suite = ExplanationContractSuite()
    no_match_explanation_suite = NoMatchExplanationContractSuite()
    semantic_conversion_suite = SemanticConversionContractSuite()
    stdlib_suite = StandardLibraryGuaranteeSuite()
    stdlib_registry_suite = StandardLibraryRegistrySuite()
    legacy_regex_suite = LegacyRegexContractSuite()
    semantic_strling_suite = SemanticStrlingContractSuite()
    simply_suite = SimplyContractSuite()
    simply_1_1_suite = Simply11ContractSuite()
    explanation = explanation_suite.certify()
    no_match_explanation = no_match_explanation_suite.certify()
    semantic_conversion = semantic_conversion_suite.certify()
    document_count = suite.validate_suite_structure()
    positive_count = suite.validate_positive_examples()
    negative_count = suite.validate_negative_examples()
    stdlib_schema_count = stdlib_suite.validate_suite_structure()
    stdlib_positive_count = stdlib_suite.validate_positive_examples()
    stdlib_negative_count = stdlib_suite.validate_negative_examples()
    stdlib_registry = stdlib_registry_suite.certify()
    legacy_regex = legacy_regex_suite.certify()
    semantic_strling = semantic_strling_suite.certify()
    simply = simply_suite.certify()
    simply_1_1 = simply_1_1_suite.certify()
    simply_adapters = certify_simply_adapters()
    shared_corpus = validate_corpus()
    print(
        "CANONICAL_CONTRACTS status=passed "
        f"schemas={len(suite.schemas)} positive={positive_count} "
        f"negative={negative_count} documents={document_count} "
        f"explanation_schemas={explanation['schemas']} "
        f"explanation_positive={explanation['positive']} "
        f"explanation_negative={explanation['negative']} "
        f"explanation_fingerprint={explanation['fingerprint']} "
        f"no_match_schemas={no_match_explanation['schemas']} "
        f"no_match_positive={no_match_explanation['positive']} "
        f"no_match_negative={no_match_explanation['negative']} "
        f"no_match_reasons={no_match_explanation['reasons']} "
        f"no_match_programs={no_match_explanation['programs']} "
        f"no_match_cases={no_match_explanation['cases']} "
        f"no_match_fingerprint={no_match_explanation['fingerprint']} "
        f"semantic_conversion_schemas={semantic_conversion['schemas']} "
        f"semantic_conversion_positive={semantic_conversion['positive']} "
        f"semantic_conversion_negative={semantic_conversion['negative']} "
        f"semantic_conversion_exact={semantic_conversion['exact']} "
        f"semantic_conversion_partial={semantic_conversion['partial']} "
        f"semantic_conversion_unsupported={semantic_conversion['unsupported']} "
        f"semantic_conversion_node_kinds={semantic_conversion['node_kinds']} "
        f"semantic_conversion_member_kinds={semantic_conversion['member_kinds']} "
        f"semantic_conversion_fingerprint={semantic_conversion['fingerprint']} "
        f"stdlib_schemas={stdlib_schema_count} stdlib_positive={stdlib_positive_count} "
        f"stdlib_negative={stdlib_negative_count} "
        f"stdlib_registry_schemas={stdlib_registry['schema_count']} "
        f"stdlib_registry_helpers={stdlib_registry['helper_count']} "
        f"stdlib_registry_variants={stdlib_registry['variant_count']} "
        f"stdlib_registry_bindings={stdlib_registry['binding_count']} "
        f"stdlib_registry_cases={stdlib_registry['case_count']} "
        f"stdlib_registry_negative={stdlib_registry['negative_count']} "
        f"stdlib_registry_semantic_forms={stdlib_registry['semantic_form_count']} "
        f"simply_1_1_operations={simply_1_1['operations']} "
        f"simply_1_1_positive={simply_1_1['positive']} "
        f"simply_1_1_negative={simply_1_1['negative']} "
        f"stdlib_registry_stress_cases={stdlib_registry['semantic_stress_count']} "
        f"stdlib_registry_semantic_validators={stdlib_registry['semantic_validator_count']} "
        f"stdlib_registry_runtime_applications={stdlib_registry['runtime_application_count']} "
        f"stdlib_registry_runtime_execute={stdlib_registry['runtime_execute_count']} "
        f"stdlib_registry_runtime_not_applicable={stdlib_registry['runtime_not_applicable_count']} "
        f"stdlib_registry_edge_cases={stdlib_registry['edge_case_count']} "
        f"stdlib_registry_fingerprint={stdlib_registry['fingerprint']} "
        f"legacy_regex_schemas={legacy_regex['schemas']} "
        f"legacy_regex_features={legacy_regex['features']} "
        f"legacy_regex_positive={legacy_regex['positive']} "
        f"legacy_regex_negative={legacy_regex['negative']} "
        f"legacy_regex_fingerprint={legacy_regex['fingerprint']} "
        f"semantic_strling_schemas={semantic_strling['schemas']} "
        f"semantic_strling_productions={semantic_strling['productions']} "
        f"semantic_strling_mappings={semantic_strling['mappings']} "
        f"semantic_strling_diagnostics={semantic_strling['diagnostics']} "
        f"semantic_strling_positive={semantic_strling['positive']} "
        f"semantic_strling_negative={semantic_strling['negative']} "
        f"semantic_strling_fingerprint={semantic_strling['fingerprint']} "
        f"simply_schemas={simply['schemas']} "
        f"simply_operations={simply['operations']} "
        f"simply_errors={simply['errors']} "
        f"simply_compatibility={simply['compatibility']} "
        f"simply_positive={simply['positive']} "
        f"simply_negative={simply['negative']} "
        f"simply_fingerprint={simply['fingerprint']} "
        f"simply_adapter_operations={simply_adapters['operation_count']} "
        f"simply_adapter_errors={simply_adapters['error_count']} "
        f"simply_adapter_typescript_legacy={simply_adapters['typescript_legacy_operation_count']} "
        f"simply_adapter_python_legacy={simply_adapters['python_legacy_operation_count']} "
        f"simply_adapter_fingerprint={simply_adapters['source_fingerprint']} "
        f"shared_cases={shared_corpus['case_count']} "
        f"shared_fingerprint={shared_corpus['corpus_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
