#!/usr/bin/env python3
"""Validate canonical STRling contracts and their cross-object invariants."""

from __future__ import annotations

import json
import hashlib
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "contracts" / "1.0"
PROFILE_ROOT = ROOT / "spec" / "targets" / "profiles"

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
        option_ids = [item["option_id"] for item in profile["options"]]
        if option_ids != sorted(set(option_ids)):
            raise ContractValidationError(
                "target profile options must have unique sorted option IDs"
            )
        option_id_set = set(option_ids)
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

        evidence_ids = [item["evidence_id"] for item in profile["evidence"]]
        if evidence_ids != sorted(set(evidence_ids)):
            raise ContractValidationError(
                "profile evidence must have unique sorted evidence IDs"
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
    suite = ContractSuite()
    positive_count = suite.validate_positive_examples()
    negative_count = suite.validate_negative_examples()
    print(
        "CANONICAL_CONTRACTS status=passed "
        f"schemas={len(suite.schemas)} positive={positive_count} negative={negative_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
