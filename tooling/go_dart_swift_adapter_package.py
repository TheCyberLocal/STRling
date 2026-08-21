"""Certify clean consumers and release graphs for Go, Dart, and Swift adapters."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OPERATION_ID = "certification.go-dart-swift-adapter-package"
CHECK_ID = f"{OPERATION_ID}.clean-consumers-and-release-graphs"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}
CONSUMER_DIRECTORIES = {
    "go": "go-consumer",
    "dart": "dart-consumer",
    "swift": "swift-consumer",
}


class GoDartSwiftAdapterPackageError(RuntimeError):
    """The clean-consumer or release-graph proof failed."""


@dataclass(frozen=True)
class PackageReport:
    clean_consumers: tuple[str, ...]
    tool_versions: Mapping[str, str]
    release_graphs: Mapping[str, Any]


def _version_tuple(text: str, pattern: str, label: str) -> tuple[int, ...]:
    match = re.search(pattern, text)
    if match is None:
        raise GoDartSwiftAdapterPackageError(
            f"cannot parse governed {label} version from {text!r}"
        )
    return tuple(int(part) for part in match.group(1).split("."))


def _assert_tool_versions(versions: Mapping[str, str]) -> None:
    go = _version_tuple(versions["go"], r"\bgo(\d+\.\d+(?:\.\d+)?)\b", "Go")
    dart = _version_tuple(
        versions["dart"], r"Dart SDK version:\s*(\d+\.\d+(?:\.\d+)?)", "Dart"
    )
    swift = _version_tuple(
        versions["swift"], r"Swift version\s+(\d+\.\d+(?:\.\d+)?)", "Swift"
    )
    if go[:2] != (1, 22):
        raise GoDartSwiftAdapterPackageError(
            f"Go {'.'.join(map(str, go))} is outside >=1.22,<1.23"
        )
    if dart[0] != 3:
        raise GoDartSwiftAdapterPackageError(
            f"Dart {'.'.join(map(str, dart))} is outside >=3.0,<4.0"
        )
    if swift < (5, 9) or swift >= (7, 0):
        raise GoDartSwiftAdapterPackageError(
            f"Swift {'.'.join(map(str, swift))} is outside >=5.9,<7.0"
        )


def _tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise FileNotFoundError(name)
    return resolved


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int = 900,
) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-8000:]
        raise GoDartSwiftAdapterPackageError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def _go_consumer(root: Path, go: str, environment: Mapping[str, str]) -> None:
    module = (ROOT / "bindings/go").as_posix()
    _write(
        root / "go.mod",
        "\n".join(
            (
                "module example.test/strling-consumer",
                "",
                "go 1.22",
                "",
                "require github.com/strling-lang/strling/bindings/go v0.0.0",
                f"replace github.com/strling-lang/strling/bindings/go => {module}",
                "",
            )
        ),
    )
    _write(
        root / "consumer_test.go",
        """package consumer

import (
    "testing"
    strling "github.com/strling-lang/strling/bindings/go"
)

func TestPublicFacade(t *testing.T) {
    if strling.Email("root")["operation"] != "stdlib_helper" {
        t.Fatal("unexpected public facade")
    }
    if strling.SourceCompileRequest("literal \\"hello\\"", nil)["contract_version"] != "1.0.0" {
        t.Fatal("unexpected request contract")
    }
}
""",
    )
    no_cgo = dict(environment)
    no_cgo["CGO_ENABLED"] = "0"
    _run([go, "test", "./..."], cwd=root, environment=no_cgo)


def _dart_consumer(root: Path, dart: str, environment: Mapping[str, str]) -> None:
    package = (ROOT / "bindings/dart").as_posix()
    _write(
        root / "pubspec.yaml",
        f"""name: strling_consumer
publish_to: none
environment:
  sdk: ">=3.0.0 <4.0.0"
dependencies:
  strling:
    path: {package}
""",
    )
    _write(
        root / "lib/main.dart",
        """import 'package:strling/strling.dart';

void verifyPublicFacade() {
  final step = email('root');
  if (step['operation'] != 'stdlib_helper') throw StateError('unexpected public facade');
  final request = sourceCompileRequest('literal "hello"');
  if (request['contract_version'] != '1.0.0') throw StateError('unexpected request contract');
}
""",
    )
    _run([dart, "pub", "get", "--offline"], cwd=root, environment=environment)
    _run(
        [dart, "analyze", "--fatal-infos", "--fatal-warnings"],
        cwd=root,
        environment=environment,
    )


def _swift_consumer(root: Path, swift: str, environment: Mapping[str, str]) -> None:
    package = (ROOT / "bindings/swift").as_posix().replace('"', '\\"')
    _write(
        root / "Package.swift",
        f"""// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "STRlingConsumer",
    dependencies: [.package(path: "{package}")],
    targets: [
        .executableTarget(
            name: "STRlingConsumer",
            dependencies: [.product(name: "STRling", package: "swift")]
        ),
    ]
)
""",
    )
    _write(
        root / "Sources/STRlingConsumer/main.swift",
        """import STRling

let step = Essential.email("root")
precondition(step["operation"] as? String == "stdlib_helper")
precondition(sourceCompileRequest("literal \\"hello\\"")["contract_version"] as? String == "1.0.0")
""",
    )
    _run(
        [swift, "build", "-c", "release", "-Xswiftc", "-warnings-as-errors"],
        cwd=root,
        environment=environment,
    )


def _go_release_graph(go: str, environment: Mapping[str, str]) -> list[str]:
    output = _run(
        [
            go,
            "list",
            "-deps",
            "-f",
            "{{if not .Standard}}{{.ImportPath}}{{end}}",
            "./...",
        ],
        cwd=ROOT / "bindings/go",
        environment=environment,
    )
    graph = sorted({line.strip() for line in output.splitlines() if line.strip()})
    expected = ["github.com/strling-lang/strling/bindings/go"]
    if graph != expected:
        raise GoDartSwiftAdapterPackageError(
            f"Go release graph contains unexpected non-standard packages: {graph!r}"
        )
    return graph


def _dart_release_graph(dart: str, environment: Mapping[str, str]) -> Any:
    output = _run(
        [dart, "pub", "deps", "--json"],
        cwd=ROOT / "bindings/dart",
        environment=environment,
    )
    try:
        graph = json.loads(output)
    except json.JSONDecodeError as error:
        raise GoDartSwiftAdapterPackageError(
            f"Dart release graph is not JSON: {error}"
        ) from error
    packages = graph.get("packages")
    if not isinstance(packages, list):
        raise GoDartSwiftAdapterPackageError("Dart release graph has no package list")
    root = next((item for item in packages if item.get("kind") == "root"), None)
    if root is None or root.get("name") != "strling":
        raise GoDartSwiftAdapterPackageError("Dart release graph root identity changed")
    runtime_dependencies = {
        str(item.get("name")) for item in packages if item.get("kind") == "direct"
    }
    if runtime_dependencies != {"ffi", "path"}:
        raise GoDartSwiftAdapterPackageError(
            f"Dart runtime dependencies changed: {sorted(runtime_dependencies)!r}"
        )
    return {
        "root": "strling",
        "packages": sorted(
            (
                {
                    key: item[key]
                    for key in ("name", "version", "kind", "source", "dependencies")
                    if key in item
                }
                for item in packages
            ),
            key=lambda item: (str(item.get("kind")), str(item.get("name"))),
        ),
    }


def _swift_release_graph(swift: str, environment: Mapping[str, str]) -> Any:
    output = _run(
        [swift, "package", "show-dependencies", "--format", "json"],
        cwd=ROOT / "bindings/swift",
        environment=environment,
    )
    try:
        graph = json.loads(output)
    except json.JSONDecodeError as error:
        raise GoDartSwiftAdapterPackageError(
            f"Swift release graph is not JSON: {error}"
        ) from error
    if graph.get("name") != "STRling" or graph.get("dependencies") not in ([], None):
        raise GoDartSwiftAdapterPackageError(
            "Swift release graph has an unexpected identity or external dependency"
        )
    return {"name": "STRling", "dependencies": []}


def execute() -> PackageReport:
    tools = {name: _tool(name) for name in ("go", "dart", "swift")}
    environment = os.environ.copy()
    environment["NO_COLOR"] = "1"
    environment["CI"] = "true"
    versions = {
        "go": _run([tools["go"], "version"], cwd=ROOT, environment=environment).strip(),
        "dart": _run(
            [tools["dart"], "--version"], cwd=ROOT, environment=environment
        ).strip(),
        "swift": _run(
            [tools["swift"], "--version"], cwd=ROOT, environment=environment
        ).strip(),
    }
    _assert_tool_versions(versions)
    _run(
        [tools["dart"], "pub", "get", "--offline", "--enforce-lockfile"],
        cwd=ROOT / "bindings/dart",
        environment=environment,
    )
    release_graphs = {
        "go": _go_release_graph(tools["go"], environment),
        "dart": _dart_release_graph(tools["dart"], environment),
        "swift": _swift_release_graph(tools["swift"], environment),
    }
    target = ROOT / "target"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gds-package-", dir=target) as directory:
        consumer_root = Path(directory)
        _go_consumer(
            consumer_root / CONSUMER_DIRECTORIES["go"], tools["go"], environment
        )
        _dart_consumer(
            consumer_root / CONSUMER_DIRECTORIES["dart"],
            tools["dart"],
            environment,
        )
        _swift_consumer(
            consumer_root / CONSUMER_DIRECTORIES["swift"],
            tools["swift"],
            environment,
        )
    return PackageReport(
        clean_consumers=("go", "dart", "swift"),
        tool_versions=versions,
        release_graphs=release_graphs,
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    started = time.monotonic()
    try:
        report = execute()
    except FileNotFoundError as error:
        payload = _result("unavailable", started, {"missing": str(error)})
    except (
        GoDartSwiftAdapterPackageError,
        OSError,
        subprocess.SubprocessError,
    ) as error:
        payload = _result("failed", started, {"error": str(error)})
    else:
        payload = _result("passed", started, asdict(report))
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return EXIT_CODES[str(payload["status"])]


if __name__ == "__main__":
    raise SystemExit(main())
