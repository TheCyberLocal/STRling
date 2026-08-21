import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LSP_ROOT = ROOT / "tooling" / "lsp-server"


def _esbuild_command(node: str) -> list[str]:
    package = json.loads(
        (LSP_ROOT / "node_modules" / "esbuild" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    entry = LSP_ROOT / "node_modules" / "esbuild" / package["bin"]["esbuild"]
    header = entry.read_bytes()[:4]
    return (
        [str(entry)]
        if header == b"\x7fELF" or header[:2] == b"MZ"
        else [node, str(entry)]
    )


def test_client_runtime_plan_matches_packaged_contract(tmp_path: Path) -> None:
    node = "node"
    compiled = tmp_path / "runtime.cjs"
    bundle = subprocess.run(
        [
            *_esbuild_command(node),
            str(LSP_ROOT / "client" / "runtime.ts"),
            "--bundle",
            "--platform=node",
            "--format=cjs",
            f"--outfile={compiled}",
            "--log-level=warning",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bundle.returncode == 0, bundle.stderr
    smoke = subprocess.run(
        [
            node,
            str(LSP_ROOT / "tests" / "client_runtime_smoke.mjs"),
            str(compiled),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stderr
    assert json.loads(smoke.stdout)["selectors"] == 21


def test_extension_activation_uses_exact_packaged_runtime(tmp_path: Path) -> None:
    node = "node"
    compiled = tmp_path / "extension.cjs"
    bundle = subprocess.run(
        [
            *_esbuild_command(node),
            str(LSP_ROOT / "client" / "extension.ts"),
            "--bundle",
            "--platform=node",
            "--format=cjs",
            "--external:vscode",
            "--external:vscode-languageclient/node",
            f"--outfile={compiled}",
            "--log-level=warning",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bundle.returncode == 0, bundle.stderr
    smoke = subprocess.run(
        [
            node,
            str(LSP_ROOT / "tests" / "extension_activation_smoke.cjs"),
            str(compiled),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stderr
    assert json.loads(smoke.stdout) == {"clients": 1, "errors": 1, "selectors": 21}
