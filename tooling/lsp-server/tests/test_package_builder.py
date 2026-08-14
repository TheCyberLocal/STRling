import importlib.util
import json
import warnings
import zipfile
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[3]
LSP_ROOT = ROOT / "tooling" / "lsp-server"
SPEC = importlib.util.spec_from_file_location(
    "strling_package_extension", LSP_ROOT / "package_extension.py"
)
assert SPEC is not None and SPEC.loader is not None
package_extension = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_extension)


def _contract() -> dict:
    return package_extension.load_contract()


def _target(contract: dict, identifier: str = "win32-x64") -> dict:
    return next(target for target in contract["targets"] if target["id"] == identifier)


def _fake_payload(root: Path, contract: dict, target: dict) -> Path:
    root.mkdir()
    required = package_extension._expanded_paths(contract, target)
    for relative in sorted(required - {"strling-package-manifest.json"}):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture:{relative}\n".encode())
    package_extension._write_manifest(root, contract, target)
    return root


def test_host_target_resolution_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = _contract()
    monkeypatch.setattr(package_extension, "_host_identity", lambda: ("win32", "x64"))
    monkeypatch.setattr(
        package_extension, "_rust_host", lambda: "x86_64-pc-windows-msvc"
    )
    assert package_extension.resolve_target(contract, "auto")["id"] == "win32-x64"
    with pytest.raises(package_extension.PackageError, match="does not match host"):
        package_extension.resolve_target(contract, "linux-x64")
    with pytest.raises(
        package_extension.PackageError, match="no declared package target"
    ):
        package_extension.resolve_target(contract, "plan9-x64")


def test_generated_manifest_validates_closed_schema_and_payload(tmp_path: Path) -> None:
    contract = _contract()
    target = _target(contract)
    payload = _fake_payload(tmp_path / "payload", contract, target)
    manifest = package_extension.validate_payload(payload, contract, target)
    schema = json.loads(
        (LSP_ROOT / "package_manifest.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(manifest)
    assert manifest["target"] == "win32-x64"
    assert len(manifest["entries"]) == 20


def test_payload_refuses_missing_unexpected_and_legacy_files(tmp_path: Path) -> None:
    contract = _contract()
    target = _target(contract)
    payload = _fake_payload(tmp_path / "payload", contract, target)
    (payload / "server" / "canonical_core.py").unlink()
    with pytest.raises(package_extension.PackageError, match="missing="):
        package_extension.validate_payload(payload, contract, target)

    payload = _fake_payload(tmp_path / "payload-two", contract, target)
    legacy = payload / "server" / "libs" / "STRling" / "parser.py"
    legacy.parent.mkdir()
    legacy.write_text("legacy", encoding="utf-8")
    with pytest.raises(package_extension.PackageError, match="unexpected="):
        package_extension.validate_payload(payload, contract, target)


def test_payload_refuses_content_and_manifest_mutation(tmp_path: Path) -> None:
    contract = _contract()
    target = _target(contract)
    payload = _fake_payload(tmp_path / "payload", contract, target)
    (payload / "server" / "bin" / "strling-kernel.exe").write_bytes(b"changed")
    with pytest.raises(package_extension.PackageError, match="entry hashes"):
        package_extension.validate_payload(payload, contract, target)

    payload = _fake_payload(tmp_path / "payload-two", contract, target)
    manifest_path = payload / "strling-package-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["target"] = "linux-x64"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(package_extension.PackageError, match="target is incorrect"):
        package_extension.validate_payload(payload, contract, target)


def test_nondefault_existing_output_is_never_deleted(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "owned-by-caller"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(package_extension.PackageError, match="already exists"):
        package_extension._safe_output(output)
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_certification_artifact_outputs_are_new_and_typed(tmp_path: Path) -> None:
    vsix = package_extension._new_artifact_path(
        tmp_path / "artifacts" / "package.vsix", suffix=".vsix"
    )
    assert vsix.parent.is_dir()
    vsix.write_bytes(b"owned")
    with pytest.raises(package_extension.PackageError, match="already exists"):
        package_extension._new_artifact_path(vsix, suffix=".vsix")
    with pytest.raises(package_extension.PackageError, match="must end"):
        package_extension._new_artifact_path(
            tmp_path / "artifacts" / "evidence.txt", suffix=".json"
        )


def test_vsix_entry_manifest_refuses_traversal_and_duplicates(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.vsix"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../escape", b"bad")
    with pytest.raises(package_extension.PackageError, match="unsafe or duplicate"):
        package_extension._zip_entries(traversal)

    duplicate = tmp_path / "duplicate.vsix"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("extension/package.json", b"one")
            archive.writestr("extension/package.json", b"two")
    with pytest.raises(package_extension.PackageError, match="unsafe or duplicate"):
        package_extension._zip_entries(duplicate)


def test_isolated_install_upgrade_uninstall_never_touches_user_state(
    tmp_path: Path,
) -> None:
    contract = _contract()
    target = _target(contract)
    payload = _fake_payload(tmp_path / "payload", contract, target)
    vsix = tmp_path / "fixture.vsix"
    with zipfile.ZipFile(vsix, "w") as archive:
        for path in sorted(payload.rglob("*")):
            if path.is_file():
                archive.write(path, "extension/" + path.relative_to(payload).as_posix())
    lifecycle = package_extension._lifecycle_smoke(
        vsix, contract, target, tmp_path / "lifecycle-root"
    )
    assert lifecycle == {"install": True, "upgrade": True, "uninstall": True}
    assert not any((tmp_path / "lifecycle-root" / "extensions").iterdir())
