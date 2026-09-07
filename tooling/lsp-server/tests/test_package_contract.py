import hashlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
LSP_ROOT = ROOT / "tooling" / "lsp-server"
CONTRACT_PATH = LSP_ROOT / "package_contract.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(value: dict, field: str) -> str:
    material = dict(value)
    material.pop(field)
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def test_package_contract_is_closed_and_fingerprinted() -> None:
    contract = _load(CONTRACT_PATH)
    schema = _load(LSP_ROOT / "package_contract.schema.json")
    jsonschema.Draft202012Validator(schema).validate(contract)
    assert contract["contract_fingerprint"] == _fingerprint(
        contract, "contract_fingerprint"
    )


def test_package_targets_are_exact_native_runner_pairs() -> None:
    contract = _load(CONTRACT_PATH)
    targets = {target["id"]: target for target in contract["targets"]}
    assert list(targets) == [
        "darwin-arm64",
        "darwin-x64",
        "linux-x64",
        "win32-x64",
    ]
    assert {
        (target["node_platform"], target["node_arch"], target["ci_runner"])
        for target in targets.values()
    } == {
        ("darwin", "arm64", "macos-latest"),
        ("darwin", "x64", "macos-15-intel"),
        ("linux", "x64", "ubuntu-latest"),
        ("win32", "x64", "windows-latest"),
    }


def test_extension_routes_match_governed_island_registry() -> None:
    contract = _load(CONTRACT_PATH)
    registry = _load(ROOT / "spec" / "tooling" / "island_boundaries.json")
    assert contract["extension"]["island_route_ids"] == [
        host["language_id"] for host in registry["hosts"]
    ]
    selectors = contract["extension"]["document_selectors"]
    assert len(selectors) == 21
    assert contract["extension"]["activation_events"] == [
        f"onLanguage:{language}" for language in selectors
    ]


def test_payload_contains_only_authored_adapters_and_canonical_processes() -> None:
    contract = _load(CONTRACT_PATH)
    destinations = {entry["destination"] for entry in contract["payload"]["copies"]}
    assert {
        "server/canonical_core.py",
        "server/canonical_intelligence.py",
        "server/island_extractor.py",
        "server/server.py",
    } <= destinations
    assert contract["payload"]["runtime_binaries"] == [
        "server/bin/strling-kernel{executable_suffix}",
        "server/bin/strling-editor-core{executable_suffix}",
    ]
    assert not any(
        source.startswith("bindings/")
        for source in (entry["source"] for entry in contract["payload"]["copies"])
    )
    assert "server/libs/STRling/**" in contract["payload"]["forbidden_path_patterns"]


def test_runtime_is_offline_and_has_no_external_python_packages() -> None:
    runtime = _load(CONTRACT_PATH)["runtime"]
    assert runtime["python_minimum"] == "3.11"
    assert runtime["network_after_dependency_install"] == "forbidden"
    assert runtime["external_python_packages"] == []
    assert set(runtime["environment"]) == {
        "PYTHONPATH",
        "STRLING_KERNEL",
        "STRLING_EDITOR_CORE",
        "STRLING_SIMPLY_PROTOCOL_PATH",
        "STRLING_STDLIB_REGISTRY_PATH",
        "STRLING_ISLAND_BOUNDARIES_PATH",
    }


def test_package_metadata_has_one_owned_language_surface() -> None:
    contract = _load(CONTRACT_PATH)
    package = _load(LSP_ROOT / "package.json")
    assert contract["extension"]["package_name"] == package["name"]
    assert contract["extension"]["publisher"] == package["publisher"]
    assert contract["extension"]["license"] == package["license"]
    assert contract["extension"]["owned_language"] == {
        "id": "strling",
        "extensions": [".strling", ".strl"],
    }
    assert package["activationEvents"] == contract["extension"]["activation_events"]
    assert package["contributes"]["languages"] == [
        {
            "id": "strling",
            "aliases": ["STRling", "strling"],
            "extensions": [".strling", ".strl"],
            "configuration": "./language-configuration.json",
        }
    ]
    assert package["contributes"]["grammars"] == [
        {
            "language": "strling",
            "scopeName": "source.strling.semantic",
            "path": "./syntaxes/semantic-strling.tmLanguage.json",
        }
    ]
    settings = package["contributes"]["configuration"]["properties"]
    assert [setting["name"] for setting in contract["extension"]["settings"]] == list(
        settings
    )


def test_semantic_language_has_static_highlighting_before_lsp_startup() -> None:
    grammar = _load(LSP_ROOT / "syntaxes" / "semantic-strling.tmLanguage.json")
    assert grammar["name"] == "Semantic STRling"
    assert grammar["scopeName"] == "source.strling.semantic"
    assert grammar["patterns"] == [
        {"include": "#comments"},
        {"include": "#strings"},
        {"include": "#numbers"},
        {"include": "#keywords"},
        {"include": "#identifiers"},
    ]
    assert set(grammar["repository"]) == {
        "comments",
        "strings",
        "numbers",
        "keywords",
        "identifiers",
    }


def test_node_lock_root_matches_extension_identity() -> None:
    package = _load(LSP_ROOT / "package.json")
    lock = _load(LSP_ROOT / "package-lock.json")
    assert lock["name"] == package["name"]
    assert lock["version"] == package["version"]
    assert lock["packages"][""]["name"] == package["name"]
    assert lock["packages"][""]["version"] == package["version"]
    assert lock["packages"][""]["license"] == package["license"]
