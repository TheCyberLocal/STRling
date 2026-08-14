import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LSP_ROOT = ROOT / "tooling" / "lsp-server"


def test_client_runtime_plan_matches_packaged_contract(tmp_path: Path) -> None:
    node = "node"
    esbuild_package = json.loads(
        (LSP_ROOT / "node_modules" / "esbuild" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    esbuild = LSP_ROOT / "node_modules" / "esbuild" / esbuild_package["bin"]["esbuild"]
    compiled = tmp_path / "runtime.cjs"
    bundle = subprocess.run(
        [
            node,
            str(esbuild),
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
    esbuild_package = json.loads(
        (LSP_ROOT / "node_modules" / "esbuild" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    esbuild = LSP_ROOT / "node_modules" / "esbuild" / esbuild_package["bin"]["esbuild"]
    compiled = tmp_path / "extension.cjs"
    bundle = subprocess.run(
        [
            node,
            str(esbuild),
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
