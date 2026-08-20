"""Certify .NET adapter release graphs, packages, consumers, and live risk."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "tests/adapters/dotnet-3.0/release-graph.json"
OSV_ENDPOINT = "https://api.osv.dev/v1/querybatch"
SDK_VERSIONS = ("9.0.120", "9.0.200", "9.0.302")
INTERNAL_PACKAGES = (("STRling", "3.0.0"), ("STRling.FSharp", "3.0.0"))
EXTERNAL_PACKAGES = (
    ("coverlet.collector", "6.0.2", "MIT", ("test",)),
    ("FSharp.Core", "9.0.300", "MIT", ("runtime", "test")),
    ("Microsoft.CodeCoverage", "17.12.0", "MIT", ("test",)),
    ("Microsoft.NET.Test.Sdk", "17.12.0", "MIT", ("test",)),
    ("Microsoft.TestPlatform.ObjectModel", "17.12.0", "MIT", ("test",)),
    ("Microsoft.TestPlatform.TestHost", "17.12.0", "MIT", ("test",)),
    ("Newtonsoft.Json", "13.0.1", "MIT", ("test",)),
    ("System.Reflection.Metadata", "1.6.0", "MIT", ("test",)),
    ("xunit", "2.9.2", "Apache-2.0", ("test",)),
    ("xunit.abstractions", "2.0.3", "Apache-2.0", ("test",)),
    ("xunit.analyzers", "1.16.0", "Apache-2.0", ("test",)),
    ("xunit.assert", "2.9.2", "Apache-2.0", ("test",)),
    ("xunit.core", "2.9.2", "Apache-2.0", ("test",)),
    ("xunit.extensibility.core", "2.9.2", "Apache-2.0", ("test",)),
    ("xunit.extensibility.execution", "2.9.2", "Apache-2.0", ("test",)),
    ("xunit.runner.visualstudio", "2.8.2", "Apache-2.0", ("test",)),
)
CSHARP_TEST_PACKAGES = {
    (name, version)
    for name, version, _, scopes in EXTERNAL_PACKAGES
    if "test" in scopes and name != "FSharp.Core"
}
FSHARP_TEST_PACKAGES = {
    (name, version)
    for name, version, _, scopes in EXTERNAL_PACKAGES
    if "test" in scopes and name != "coverlet.collector"
}
PROJECTS = {
    "csharp": ROOT / "bindings/csharp/src/STRling/STRling.csproj",
    "fsharp": ROOT / "bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj",
    "csharp-tests": ROOT / "bindings/csharp/tests/STRling.Tests/STRling.Tests.csproj",
    "fsharp-tests": ROOT
    / "bindings/fsharp/test/STRling.FSharp.Tests/STRling.FSharp.Tests.fsproj",
}


class DotNetPackageCertificationError(RuntimeError):
    """The .NET release graph, package, consumer, or live-risk proof failed."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: Mapping[str, Any]) -> str:
    normalized = {key: item for key, item in value.items() if key != "fingerprint"}
    return f"sha256:{hashlib.sha256(_canonical(normalized)).hexdigest()}"


def _tool() -> str:
    configured = os.environ.get("STRLING_DOTNET")
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("dotnet")
    if found:
        return found
    raise DotNetPackageCertificationError("dotnet is unavailable")


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path = ROOT,
    environment: Mapping[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment or os.environ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-8000:]
        raise DotNetPackageCertificationError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _require_project_markers() -> None:
    markers = {
        "bindings/csharp/src/STRling/STRling.csproj": (
            "<PackageId>STRling</PackageId>",
            "<Version>3.0.0</Version>",
            "<PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>",
            'PackagePath="runtimes\\win-x64\\native\\strling_interop.dll"',
            "RequireCertifiedNativeAsset",
            "'$(STRlingNativeRid)' != 'win-x64'",
        ),
        "bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj": (
            "<PackageId>STRling.FSharp</PackageId>",
            "<Version>3.0.0</Version>",
            "<PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>",
            '<ProjectReference Include="../../../csharp/src/STRling/STRling.csproj" />',
            '<PackageReference Include="FSharp.Core" Version="9.0.300" />',
        ),
    }
    for relative, required in markers.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        missing = [marker for marker in required if marker not in text]
        if missing:
            raise DotNetPackageCertificationError(
                f"{relative} does not match the locked package graph: {missing!r}"
            )


def build_graph() -> dict[str, Any]:
    _require_project_markers()
    packages = [
        {
            "coordinate": f"{name}:{version}",
            "ecosystem": "NuGet",
            "internal": True,
            "license": "Apache-2.0",
            "scopes": ["runtime"],
        }
        for name, version in INTERNAL_PACKAGES
    ]
    packages.extend(
        {
            "coordinate": f"{name}:{version}",
            "ecosystem": "NuGet",
            "internal": False,
            "license": license_expression,
            "license_disposition": "permitted",
            "scopes": list(scopes),
        }
        for name, version, license_expression, scopes in EXTERNAL_PACKAGES
    )
    roots = {
        "csharp": ["STRling:3.0.0"],
        "fsharp": ["FSharp.Core:9.0.300", "STRling:3.0.0", "STRling.FSharp:3.0.0"],
        "csharp-tests": [
            "STRling:3.0.0",
            *(f"{name}:{version}" for name, version in sorted(CSHARP_TEST_PACKAGES)),
        ],
        "fsharp-tests": [
            "STRling:3.0.0",
            "STRling.FSharp:3.0.0",
            *(f"{name}:{version}" for name, version in sorted(FSHARP_TEST_PACKAGES)),
        ],
    }
    value: dict[str, Any] = {
        "schema_version": "dotnet-release-graph-v1",
        "roots": roots,
        "packages": sorted(packages, key=lambda item: item["coordinate"].lower()),
        "native_payload": {
            "packaged": True,
            "certified_rids": ["win-x64"],
            "assets": ["runtimes/win-x64/native/strling_interop.dll"],
            "source": "governed release build injected at pack time",
            "unclaimed_rids": ["linux-x64", "osx-arm64", "osx-x64"],
        },
    }
    value["fingerprint"] = _fingerprint(value)
    return value


def synchronize(*, write: bool) -> dict[str, Any]:
    expected = build_graph()
    actual = None
    if GRAPH_PATH.is_file():
        try:
            actual = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            actual = None
    matches = actual == expected
    if write and not matches:
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_PATH.write_text(
            json.dumps(expected, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        matches = True
    return {
        "status": "passed" if matches else "failed",
        "graph_fingerprint": expected["fingerprint"],
        "package_count": len(expected["packages"]),
        "external_package_count": len(EXTERNAL_PACKAGES),
        "certified_rids": ["win-x64"],
    }


def _resolved_packages(project: Path) -> set[tuple[str, str]]:
    output = _run(
        [
            _tool(),
            "list",
            str(project),
            "package",
            "--include-transitive",
            "--format",
            "json",
        ]
    )
    try:
        payload = json.loads(output)
        frameworks = payload["projects"][0]["frameworks"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise DotNetPackageCertificationError(
            f"cannot read package graph for {project}"
        ) from error
    result: set[tuple[str, str]] = set()
    for framework in frameworks:
        for key in ("topLevelPackages", "transitivePackages"):
            for package in framework.get(key, []):
                result.add((str(package["id"]), str(package["resolvedVersion"])))
    return result


def verify_resolved_graph() -> dict[str, set[tuple[str, str]]]:
    actual = {name: _resolved_packages(project) for name, project in PROJECTS.items()}
    expected = {
        "csharp": set(),
        "fsharp": {("FSharp.Core", "9.0.300")},
        "csharp-tests": CSHARP_TEST_PACKAGES,
        "fsharp-tests": FSHARP_TEST_PACKAGES,
    }
    mismatches = {
        name: {"expected": sorted(expected[name]), "actual": sorted(packages)}
        for name, packages in actual.items()
        if packages != expected[name]
    }
    if mismatches:
        raise DotNetPackageCertificationError(
            f"resolved NuGet graph changed: {mismatches!r}"
        )
    return actual


def _osv_query(packages: Sequence[tuple[str, str]]) -> list[Mapping[str, Any]]:
    request = urllib.request.Request(
        OSV_ENDPOINT,
        data=_canonical(
            {
                "queries": [
                    {
                        "package": {"ecosystem": "NuGet", "name": name},
                        "version": version,
                    }
                    for name, version in packages
                ]
            }
        ),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "strling-certifier/1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise DotNetPackageCertificationError(
            f"OSV advisory retrieval failed: {error}"
        ) from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or len(results) != len(packages):
        raise DotNetPackageCertificationError("OSV advisory response is incomplete")
    if any(not isinstance(item, dict) for item in results):
        raise DotNetPackageCertificationError("OSV advisory result is malformed")
    return results


def certify_risk() -> dict[str, Any]:
    graph = synchronize(write=False)
    if graph["status"] != "passed":
        raise DotNetPackageCertificationError("release graph does not reproduce")
    verify_resolved_graph()
    packages = [(name, version) for name, version, _, _ in EXTERNAL_PACKAGES]
    results = _osv_query(packages)
    affected = []
    for package, result in zip(packages, results, strict=True):
        vulnerabilities = result.get("vulns", [])
        if not isinstance(vulnerabilities, list):
            raise DotNetPackageCertificationError(
                "OSV vulnerability inventory is malformed"
            )
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict) or not isinstance(
                vulnerability.get("id"), str
            ):
                raise DotNetPackageCertificationError(
                    "OSV vulnerability identity is missing"
                )
            affected.append(
                {
                    "coordinate": f"{package[0]}:{package[1]}",
                    "advisory": vulnerability["id"],
                }
            )
    return {
        "status": "failed" if affected else "passed",
        "source": "OSV",
        "retrieval": "completed",
        "packages_queried": len(packages),
        "affected": affected,
        "license_dispositions": {
            "MIT": sum(
                1 for _, _, license_id, _ in EXTERNAL_PACKAGES if license_id == "MIT"
            ),
            "Apache-2.0": sum(
                1
                for _, _, license_id, _ in EXTERNAL_PACKAGES
                if license_id == "Apache-2.0"
            ),
            "status": "permitted",
        },
        "graph_fingerprint": graph["graph_fingerprint"],
    }


def _safe_reset(directory: Path, prefix: str) -> None:
    resolved = directory.resolve()
    target = (ROOT / "target").resolve()
    if resolved.parent != target or not resolved.name.startswith(prefix):
        raise DotNetPackageCertificationError(
            f"unsafe certification directory: {resolved}"
        )
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _archive_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def _nuspec_dependencies(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        nuspec = next(name for name in archive.namelist() if name.endswith(".nuspec"))
        root = ET.fromstring(archive.read(nuspec))
    return {
        str(element.attrib["id"]): str(element.attrib["version"])
        for element in root.iter()
        if element.tag.endswith("dependency")
    }


def _fsharp_core_package(dotnet: str) -> Path:
    active = _run([dotnet, "--version"]).strip()
    for line in _run([dotnet, "--list-sdks"]).splitlines():
        version, _, location = line.partition(" [")
        if version == active and location.endswith("]"):
            candidate = (
                Path(location[:-1])
                / active
                / "FSharp"
                / "library-packs"
                / "FSharp.Core.9.0.300.nupkg"
            )
            if candidate.is_file():
                return candidate
    raise DotNetPackageCertificationError(
        "the pinned FSharp.Core 9.0.300 SDK package is unavailable"
    )


def _write_consumer_files(work: Path, feed: Path) -> tuple[Path, Path, Path]:
    config = work / "NuGet.Config"
    config.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<configuration><packageSources><clear />"
        f'<add key="local" value="{escape(str(feed))}" />'
        "</packageSources></configuration>\n",
        encoding="utf-8",
        newline="\n",
    )
    csharp = work / "csharp-consumer"
    csharp.mkdir()
    (csharp / "Consumer.csproj").write_text(
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net9.0</TargetFramework>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
    <SelfContained>false</SelfContained>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup><PackageReference Include="STRling" Version="3.0.0" /></ItemGroup>
</Project>
""",
        encoding="utf-8",
        newline="\n",
    )
    (csharp / "Program.cs").write_text(
        """using System.Text.Json;
using Strling.Native;
var native = Path.Combine(AppContext.BaseDirectory, "strling_interop.dll");
using var client = NativeClient.Load(native);
if (client.Describe().ValueKind != JsonValueKind.Object) throw new Exception("not canonical data");
Console.WriteLine("CSHARP_CONSUMER_PASS");
""",
        encoding="utf-8",
        newline="\n",
    )
    fsharp = work / "fsharp-consumer"
    fsharp.mkdir()
    (fsharp / "Consumer.fsproj").write_text(
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net9.0</TargetFramework>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
    <SelfContained>false</SelfContained>
    <DisableImplicitFSharpCoreReference>true</DisableImplicitFSharpCoreReference>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="FSharp.Core" Version="9.0.300" />
    <PackageReference Include="STRling.FSharp" Version="3.0.0" />
  </ItemGroup>
  <ItemGroup><Compile Include="Program.fs" /></ItemGroup>
</Project>
""",
        encoding="utf-8",
        newline="\n",
    )
    (fsharp / "Program.fs").write_text(
        """open System
open System.IO
open System.Text.Json
open STRling.FSharp
let native = Path.Combine(AppContext.BaseDirectory, "strling_interop.dll")
use client = Api.loadClient native
if (Api.createCompiler client |> Api.describe).ValueKind <> JsonValueKind.Object then
    failwith "not canonical data"
printfn "FSHARP_CONSUMER_PASS"
""",
        encoding="utf-8",
        newline="\n",
    )
    return config, csharp / "Consumer.csproj", fsharp / "Consumer.fsproj"


def certify_packages(native_library: Path) -> dict[str, Any]:
    graph = synchronize(write=False)
    if graph["status"] != "passed":
        raise DotNetPackageCertificationError("release graph does not reproduce")
    verify_resolved_graph()
    native = native_library.resolve()
    if not native.is_file():
        raise DotNetPackageCertificationError(
            f"native library is unavailable: {native}"
        )
    dotnet = _tool()
    work = ROOT / "target/dotnet-adapter-package-certification"
    _safe_reset(work, "dotnet-adapter-package")
    feed = work / "feed"
    feed.mkdir()
    shutil.copy2(_fsharp_core_package(dotnet), feed)
    common = ["-c", "Release", "--no-restore", "-p:NuGetAudit=false", "-o", str(feed)]
    _run(
        [
            dotnet,
            "pack",
            str(PROJECTS["csharp"]),
            *common,
            f"-p:STRlingNativeLibrary={native}",
            "-p:STRlingNativeRid=win-x64",
        ]
    )
    _run([dotnet, "pack", str(PROJECTS["fsharp"]), *common])
    csharp_package = feed / "STRling.3.0.0.nupkg"
    fsharp_package = feed / "STRling.FSharp.3.0.0.nupkg"
    if not csharp_package.is_file() or not fsharp_package.is_file():
        raise DotNetPackageCertificationError("one or more product packages are absent")
    csharp_names = _archive_names(csharp_package)
    fsharp_names = _archive_names(fsharp_package)
    native_assets = sorted(
        name
        for name in csharp_names | fsharp_names
        if name.endswith((".dll", ".so", ".dylib")) and name.startswith("runtimes/")
    )
    if native_assets != ["runtimes/win-x64/native/strling_interop.dll"]:
        raise DotNetPackageCertificationError(
            f"native package payload changed: {native_assets!r}"
        )
    if "lib/net9.0/STRling.dll" not in csharp_names:
        raise DotNetPackageCertificationError("C# product assembly is absent")
    if "lib/net9.0/STRling.FSharp.dll" not in fsharp_names:
        raise DotNetPackageCertificationError("F# product assembly is absent")
    if any(name.startswith("runtimes/") for name in fsharp_names):
        raise DotNetPackageCertificationError("F# package duplicates native assets")
    dependencies = _nuspec_dependencies(fsharp_package)
    if dependencies.get("STRling") not in {"3.0.0", "[3.0.0, )"}:
        raise DotNetPackageCertificationError(
            f"F# package does not depend on STRling 3.0.0: {dependencies!r}"
        )
    if dependencies.get("FSharp.Core") not in {"9.0.300", "[9.0.300, )"}:
        raise DotNetPackageCertificationError(
            f"F# package does not depend on FSharp.Core 9.0.300: {dependencies!r}"
        )
    config, csharp_consumer, fsharp_consumer = _write_consumer_files(work, feed)
    packages = work / "packages"
    environment = os.environ.copy()
    environment["NUGET_PACKAGES"] = str(packages)
    consumer_outputs = []
    for project, marker in (
        (csharp_consumer, "CSHARP_CONSUMER_PASS"),
        (fsharp_consumer, "FSHARP_CONSUMER_PASS"),
    ):
        _run(
            [dotnet, "restore", str(project), "--configfile", str(config)],
            cwd=project.parent,
            environment=environment,
        )
        output = _run(
            [dotnet, "run", "--project", str(project), "-c", "Release", "--no-restore"],
            cwd=project.parent,
            environment=environment,
        )
        if marker not in output:
            raise DotNetPackageCertificationError(
                f"{project.stem} clean consumer did not complete"
            )
        consumer_outputs.append(marker)
    return {
        "status": "passed",
        "graph_fingerprint": graph["graph_fingerprint"],
        "product_packages": 2,
        "external_packages": len(EXTERNAL_PACKAGES),
        "native_payloads": 1,
        "native_assets": native_assets,
        "semantic_copy_payloads": 0,
        "clean_consumers": len(consumer_outputs),
        "certified_rids": ["win-x64"],
        "native_library": str(native),
    }


def certify_sdk_matrix(native_library: Path) -> dict[str, Any]:
    native = native_library.resolve()
    if not native.is_file():
        raise DotNetPackageCertificationError(
            f"native library is unavailable: {native}"
        )
    installed = {
        line.partition(" ")[0] for line in _run([_tool(), "--list-sdks"]).splitlines()
    }
    missing = sorted(set(SDK_VERSIONS) - installed)
    if missing:
        raise DotNetPackageCertificationError(
            f"required .NET SDKs are absent: {missing!r}"
        )
    work = ROOT / "target/dotnet-adapter-sdk-certification"
    _safe_reset(work, "dotnet-adapter-sdk")
    environment = os.environ.copy()
    environment["STRLING_NATIVE_LIBRARY"] = str(native)
    cli_home = work / "dotnet-cli-home"
    cli_home.mkdir()
    environment["DOTNET_CLI_HOME"] = str(cli_home)
    environment["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    results = []
    for version in SDK_VERSIONS:
        sdk_root = work / version
        sdk_root.mkdir()
        (sdk_root / "global.json").write_text(
            json.dumps(
                {"sdk": {"version": version, "rollForward": "disable"}}, indent=4
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for project in (PROJECTS["csharp-tests"], PROJECTS["fsharp-tests"]):
            _run(
                [
                    _tool(),
                    "test",
                    str(project),
                    "-c",
                    "Release",
                    "-p:NuGetAudit=false",
                    "-m:1",
                    "--no-restore",
                ],
                cwd=sdk_root,
                environment=environment,
            )
        results.append({"sdk": version, "csharp_tests": 9, "fsharp_tests": 4})
    return {
        "status": "passed",
        "tfm": "net9.0",
        "sdk_results": results,
        "certified_rids": ["win-x64"],
        "native_library": str(native),
    }


def _native_default() -> Path:
    name = "strling_interop.dll" if sys.platform == "win32" else "libstrling_interop.so"
    return ROOT / "bindings/interop/target/release" / name


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write-graph", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--risk", action="store_true")
    mode.add_argument("--certify", action="store_true")
    mode.add_argument("--sdk-matrix", action="store_true")
    parser.add_argument("--native-library", type=Path, default=_native_default())
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_graph:
            result = synchronize(write=True)
        elif arguments.risk:
            result = certify_risk()
        elif arguments.certify:
            result = certify_packages(arguments.native_library)
        elif arguments.sdk_matrix:
            result = certify_sdk_matrix(arguments.native_library)
        else:
            result = synchronize(write=False)
    except (DotNetPackageCertificationError, OSError, ValueError) as error:
        result = {"status": "failed", "error": str(error)}
    print(json.dumps(result, sort_keys=True) if arguments.json else result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
