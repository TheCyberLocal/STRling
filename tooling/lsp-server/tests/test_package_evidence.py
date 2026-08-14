import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    ROOT
    / "tooling"
    / "lsp-server"
    / "tests"
    / "fixtures"
    / "package-certification"
    / "manifest.json"
)
GROUPS = (
    "targets",
    "selectors",
    "features",
    "failures",
    "lifecycle",
    "identity",
    "mutations",
    "reproducibility",
)


def _load() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _fingerprint(value: dict) -> str:
    material = copy.deepcopy(value)
    material.pop("manifest_fingerprint")
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def test_package_evidence_has_exact_closed_denominator() -> None:
    manifest = _load()
    assert manifest["counts"] == {
        "targets": 4,
        "selectors": 21,
        "features": 10,
        "failures": 12,
        "lifecycle": 3,
        "identity": 6,
        "mutations": 12,
        "reproducibility": 4,
        "total": 72,
    }
    cases = [case for group in GROUPS for case in manifest[group]]
    assert len(cases) == manifest["counts"]["total"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert manifest["manifest_fingerprint"] == _fingerprint(manifest)


def test_package_evidence_dimensions_are_exact() -> None:
    manifest = _load()
    assert {case["target"] for case in manifest["targets"]} == {
        "darwin-arm64",
        "darwin-x64",
        "linux-x64",
        "win32-x64",
    }
    assert {case["language"] for case in manifest["selectors"]} == {
        "strling",
        "c",
        "cpp",
        "csharp",
        "dart",
        "fsharp",
        "go",
        "java",
        "javascript",
        "javascriptreact",
        "kotlin",
        "lua",
        "perl",
        "php",
        "python",
        "r",
        "ruby",
        "rust",
        "swift",
        "typescript",
        "typescriptreact",
    }
    assert {case["id"] for case in manifest["features"]} == {
        "feature.diagnostics",
        "feature.hover",
        "feature.completion",
        "feature.definition",
        "feature.references",
        "feature.document-symbols",
        "feature.semantic-tokens",
        "feature.code-actions",
        "feature.formatting",
        "feature.embedded-islands",
    }


def test_failures_lifecycle_identity_and_reproducibility_are_closed() -> None:
    manifest = _load()
    assert {case["id"] for case in manifest["failures"]} == {
        "failure.python-missing",
        "failure.kernel-missing",
        "failure.editor-missing",
        "failure.resource-missing",
        "failure.resource-hash-mismatch",
        "failure.target-mismatch",
        "failure.undeclared-target",
        "failure.malformed-manifest",
        "failure.manifest-hash-mismatch",
        "failure.server-timeout",
        "failure.stale-document",
        "failure.invalid-package-path",
    }
    assert {case["id"] for case in manifest["lifecycle"]} == {
        "lifecycle.install",
        "lifecycle.upgrade",
        "lifecycle.uninstall",
    }
    assert {case["id"] for case in manifest["identity"]} == {
        "identity.regex-diagnostics",
        "identity.semantic-diagnostics",
        "identity.semantic-hover",
        "identity.semantic-completion",
        "identity.capture-navigation-tokens",
        "identity.actions-formatting",
    }
    assert {case["id"] for case in manifest["reproducibility"]} == {
        "repro.clean-snapshot-pair",
        "repro.payload-pair",
        "repro.vsix-pair",
        "repro.offline-runtime",
    }


def test_mutations_cover_authority_contents_metadata_paths_and_network() -> None:
    mutations = {case["id"] for case in _load()["mutations"]}
    assert mutations == {
        "mutation.remove-canonical-bridge",
        "mutation.replace-kernel-binary",
        "mutation.add-legacy-binding",
        "mutation.add-bytecode",
        "mutation.change-governed-resource",
        "mutation.change-selector",
        "mutation.change-activation-event",
        "mutation.change-extension-version",
        "mutation.wrong-executable-suffix",
        "mutation.path-traversal",
        "mutation.duplicate-manifest-entry",
        "mutation.network-runtime-dependency",
    }


def test_removing_one_case_breaks_fingerprint_and_count() -> None:
    manifest = _load()
    mutated = copy.deepcopy(manifest)
    mutated["mutations"].pop()
    assert _fingerprint(mutated) != manifest["manifest_fingerprint"]
    assert sum(len(mutated[group]) for group in GROUPS) != mutated["counts"]["total"]
