import json
from pathlib import Path

import pytest

from STRling.simply.preview import (
    CliSimplyPreviewTransport,
    SimplyPreviewBuilder,
    SimplyPreviewError,
    SimplyPreviewTransportError,
    serialize_simply_builder_request,
)

REPOSITORY = Path(__file__).resolve().parents[4]
ROOT_CLI = REPOSITORY / "strling"
POSITIVE = json.loads(
    (REPOSITORY / "spec/frontends/simply/1.0/fixtures/positive.json").read_text(
        encoding="utf-8"
    )
)
CONVERGENCE = json.loads(
    (REPOSITORY / "tests/convergence/frontend-convergence.json").read_text(
        encoding="utf-8"
    )
)
PROJECTION = {
    "requested_outputs": ["semantic", "analysis"],
    "compiler_options": {
        "partial_semantics": "forbid",
        "diagnostic_policy": {"minimum_severity": "warning"},
    },
}


def rebuild_fixture(request: dict[str, object]) -> dict[str, object]:
    builder = SimplyPreviewBuilder(
        request["identity_namespace"],
        request["specification_version"],
        request["semantic_options"],
    )
    values = {}
    for step in request["steps"]:
        step_id = step["step_id"]
        operation = step["operation"]
        arguments = step["arguments"]
        if operation == "empty":
            value = builder.empty(step_id)
        elif operation == "literal":
            value = builder.literal(step_id, arguments["text"])
        elif operation == "wildcard":
            value = builder.wildcard(step_id, arguments.get("line_terminators"))
        elif operation == "character_set":
            value = builder.character_set(
                step_id, arguments["members"], arguments["negated"]
            )
        elif operation == "sequence":
            value = builder.sequence(
                step_id, [values[item] for item in arguments["values"]]
            )
        elif operation == "alternation":
            value = builder.alternation(
                step_id, [values[item] for item in arguments["values"]]
            )
        elif operation == "group":
            value = builder.group(step_id, values[arguments["value"]])
        elif operation == "capture":
            value = builder.capture(
                step_id,
                arguments["capture_key"],
                values[arguments["value"]],
                arguments.get("name"),
            )
        elif operation == "backreference":
            value = builder.backreference(step_id, arguments["capture_key"])
        elif operation == "position":
            value = builder.position(step_id, arguments["position"])
        elif operation == "lookaround":
            value = builder.lookaround(
                step_id,
                arguments["direction"],
                arguments["polarity"],
                values[arguments["value"]],
            )
        elif operation == "atomic":
            value = builder.atomic(step_id, values[arguments["value"]])
        elif operation == "repeat":
            value = builder.repeat(
                step_id,
                values[arguments["value"]],
                arguments["min"],
                arguments["max"],
                arguments["mode"],
            )
        elif operation == "import_node":
            value = builder.import_node(
                step_id, arguments["node"], arguments.get("sources")
            )
        elif operation == "import_program":
            value = builder.import_program(step_id, arguments["program"])
        else:
            raise AssertionError(f"unknown fixture operation {operation}")
        values[step_id] = value
    return builder.build_request(values[request["root_step_id"]], request["compile"])


def convergence_request(case: dict[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "1.0.0",
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "identity_namespace": case["identity_namespace"],
        "semantic_options": case["semantic_options"],
        "steps": case["steps"],
        "root_step_id": case["root_step_id"],
        "compile": {
            "target_profile": CONVERGENCE["target_profiles"][0]["reference"],
            "requested_outputs": CONVERGENCE["comparison_outputs"],
            "compiler_options": CONVERGENCE["compiler_options"],
        },
    }


def test_authored_basic_case_is_exact_and_compiles_through_rust() -> None:
    builder = SimplyPreviewBuilder("basic")
    literal = builder.literal("literal", "a.b")
    empty_text = builder.literal("empty-text", "")
    empty = builder.empty("empty")
    grouped = builder.group("grouped", literal)
    root = builder.sequence("root", [grouped, empty_text, empty])
    request = builder.build_request(root, PROJECTION)
    expected = POSITIVE["cases"][0]

    assert request == expected["request"]
    assert json.loads(serialize_simply_builder_request(request)) == expected["request"]

    response = builder.compile(
        root,
        PROJECTION,
        CliSimplyPreviewTransport([str(ROOT_CLI), "simply"]),
    )
    assert response["compile_request"] == expected["expected"]["compile_request"]
    assert response["compile_result"]["outcome"] == "succeeded"


def test_all_nine_authored_cross_language_requests_are_exact() -> None:
    for fixture in POSITIVE["cases"]:
        assert rebuild_fixture(fixture["request"]) == fixture["request"]


def test_all_convergence_requests_are_exact_and_compile_through_rust() -> None:
    transport = CliSimplyPreviewTransport(
        [str(ROOT_CLI), "simply"],
        str(REPOSITORY / CONVERGENCE["target_profiles"][0]["path"]),
    )
    for case in CONVERGENCE["cases"]:
        request = convergence_request(case)
        assert rebuild_fixture(request) == request, case["id"]
        response = transport.execute(request)
        assert response["status"] == "success", case["id"]
        assert response["compile_request"]["input"]["kind"] == "semantic", case["id"]
        assert response["compile_result"]["semantic_result"]["status"] == "complete", case["id"]


def test_exact_target_profile_is_transport_only() -> None:
    fixture = POSITIVE["cases"][-1]
    request = rebuild_fixture(fixture["request"])
    response = CliSimplyPreviewTransport(
        [str(ROOT_CLI), "simply"],
        str(REPOSITORY / "spec/targets/profiles/pcre2-10.43.json"),
    ).execute(request)
    assert response["status"] == "success"
    assert response["compile_request"] == fixture["expected"]["compile_request"]
    assert response["compile_result"]["outcome"] == "failed"
    assert "artifact" not in response["compile_result"]
    diagnostics = response["compile_result"]["diagnostics"]
    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "STRL-PROTOCOL-0005"
    assert diagnostics[0]["phase"] == "target_lowering"


def test_complete_closed_operation_inventory_is_recorded_without_aliasing() -> None:
    builder = SimplyPreviewBuilder("inventory")
    members = [{"kind": "literal", "value": "x"}]
    empty = builder.empty("empty")
    literal = builder.literal("literal", "x")
    wildcard = builder.wildcard("wildcard", "include")
    character_set = builder.character_set("set", members)
    members[0]["value"] = "y"
    sequence = builder.sequence("sequence", [empty, literal])
    alternation = builder.alternation("alternation", [wildcard, character_set])
    grouped = builder.group("group", sequence)
    capture = builder.capture("capture", "logical", grouped, "name")
    reference = builder.backreference("reference", "logical")
    position = builder.position("position", "input_start")
    lookaround = builder.lookaround("lookaround", "ahead", "positive", alternation)
    atomic = builder.atomic("atomic", lookaround)
    repeated = builder.repeat("repeat", atomic, 1, None, "lazy")
    imported_node = builder.import_node(
        "import-node",
        {"node_id": "node:imported", "kind": "literal", "text": "n"},
    )
    imported_program = builder.import_program(
        "import-program",
        {
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": {
                "node_id": "node:program",
                "kind": "literal",
                "text": "p",
            },
        },
    )
    root = builder.sequence(
        "root",
        [
            capture,
            reference,
            position,
            repeated,
            imported_node,
            imported_program,
        ],
    )
    request = builder.build_request(root, PROJECTION)

    assert [step["operation"] for step in request["steps"]] == [
        "empty",
        "literal",
        "wildcard",
        "character_set",
        "sequence",
        "alternation",
        "group",
        "capture",
        "backreference",
        "position",
        "lookaround",
        "atomic",
        "repeat",
        "import_node",
        "import_program",
        "sequence",
    ]
    assert request["steps"][3]["arguments"]["members"][0]["value"] == "x"


def test_canonical_construction_failure_keeps_code_and_path() -> None:
    builder = SimplyPreviewBuilder("duplicate")
    builder.literal("same", "a")
    root = builder.literal("same", "b")

    with pytest.raises(SimplyPreviewError) as caught:
        builder.compile(
            root,
            {
                "requested_outputs": ["semantic"],
                "compiler_options": PROJECTION["compiler_options"],
            },
            CliSimplyPreviewTransport([str(ROOT_CLI), "simply"]),
        )
    assert caught.value.errors == (
        {"code": "STRL-SIMPLY-0003", "path": "$.steps[1].step_id"},
    )


def test_foreign_handles_and_implicit_transport_are_rejected() -> None:
    first = SimplyPreviewBuilder("first")
    second = SimplyPreviewBuilder("second")
    foreign = first.literal("foreign", "x")
    with pytest.raises(SimplyPreviewTransportError):
        second.group("bad", foreign)
    with pytest.raises(SimplyPreviewTransportError):
        CliSimplyPreviewTransport([])
