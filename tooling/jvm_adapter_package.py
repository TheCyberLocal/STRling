"""Certify JVM adapter release graphs, licenses, advisory state, and consumers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "tests/adapters/3.0/release-graph.json"
OSV_ENDPOINT = "https://api.osv.dev/v1/querybatch"
EXTERNAL_PACKAGES = (
    ("com.fasterxml.jackson.core:jackson-annotations", "2.18.9", "Apache-2.0"),
    ("com.fasterxml.jackson.core:jackson-core", "2.18.9", "Apache-2.0"),
    ("com.fasterxml.jackson.core:jackson-databind", "2.18.9", "Apache-2.0"),
    ("net.java.dev.jna:jna", "5.19.1", "LGPL-2.1-or-later OR Apache-2.0"),
    ("org.jetbrains:annotations", "13.0", "Apache-2.0"),
    ("org.jetbrains.kotlin:kotlin-stdlib", "2.0.20", "Apache-2.0"),
)
INTERNAL_PACKAGES = (
    ("com.strling:strling", "3.0.0"),
    ("com.strling:strling-jvm", "3.0.0"),
    ("com.strling:strling-kotlin", "3.0.0"),
)
ROOT_GRAPHS = {
    "java": (
        "com.strling:strling:3.0.0",
        "com.strling:strling-jvm:3.0.0",
        "net.java.dev.jna:jna:5.19.1",
        "com.fasterxml.jackson.core:jackson-databind:2.18.9",
        "com.fasterxml.jackson.core:jackson-annotations:2.18.9",
        "com.fasterxml.jackson.core:jackson-core:2.18.9",
    ),
    "jvm": (
        "com.strling:strling-jvm:3.0.0",
        "net.java.dev.jna:jna:5.19.1",
        "com.fasterxml.jackson.core:jackson-databind:2.18.9",
        "com.fasterxml.jackson.core:jackson-annotations:2.18.9",
        "com.fasterxml.jackson.core:jackson-core:2.18.9",
    ),
    "kotlin": (
        "com.strling:strling-kotlin:3.0.0",
        "org.jetbrains.kotlin:kotlin-stdlib:2.0.20",
        "org.jetbrains:annotations:13.0",
        "com.strling:strling-jvm:3.0.0",
        "net.java.dev.jna:jna:5.19.1",
        "com.fasterxml.jackson.core:jackson-databind:2.18.9",
        "com.fasterxml.jackson.core:jackson-annotations:2.18.9",
        "com.fasterxml.jackson.core:jackson-core:2.18.9",
    ),
}


class JvmPackageCertificationError(RuntimeError):
    """The JVM release graph or clean-consumer proof failed."""


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


def _require_manifest_markers() -> None:
    files = {
        "bindings/jvm/pom.xml": (
            "<artifactId>strling-jvm</artifactId>",
            "<artifactId>jna</artifactId>",
            "<jna.version>5.19.1</jna.version>",
            "<artifactId>jackson-databind</artifactId>",
            "<jackson.version>2.18.9</jackson.version>",
        ),
        "bindings/java/pom.xml": (
            "<artifactId>strling</artifactId>",
            "<artifactId>strling-jvm</artifactId>",
            "<version>3.0.0</version>",
        ),
        "bindings/kotlin/build.gradle.kts": (
            'api("com.strling:strling-jvm:3.0.0")',
            'kotlin("jvm") version "2.0.20"',
        ),
    }
    for relative, markers in files.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise JvmPackageCertificationError(
                f"{relative} does not match the locked release graph: {missing!r}"
            )
    java = (ROOT / "bindings/java/pom.xml").read_text(encoding="utf-8")
    kotlin = (ROOT / "bindings/kotlin/build.gradle.kts").read_text(encoding="utf-8")
    if "net.java.dev.jna" in java or "net.java.dev.jna" in kotlin:
        raise JvmPackageCertificationError("a host package bypasses strling-jvm")


def build_graph() -> dict[str, Any]:
    _require_manifest_markers()
    packages = [
        {
            "coordinate": f"{name}:{version}",
            "ecosystem": "Maven",
            "internal": True,
            "license": "Apache-2.0",
        }
        for name, version in INTERNAL_PACKAGES
    ]
    packages.extend(
        {
            "coordinate": f"{name}:{version}",
            "ecosystem": "Maven",
            "internal": False,
            "license": license_expression,
            "license_disposition": (
                "Apache-2.0 branch selected"
                if name == "net.java.dev.jna:jna"
                else "permitted"
            ),
        }
        for name, version, license_expression in EXTERNAL_PACKAGES
    )
    value: dict[str, Any] = {
        "schema_version": "jvm-release-graph-v1",
        "roots": {key: list(value) for key, value in sorted(ROOT_GRAPHS.items())},
        "packages": sorted(packages, key=lambda item: item["coordinate"]),
        "native_payload": {
            "packaged": False,
            "load_mode": "caller-supplied absolute path",
            "reason": "P17-T04 certifies only the locally executed Windows x86_64 native row; no unexecuted classifier is advertised.",
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
        "root_counts": {key: len(value) for key, value in ROOT_GRAPHS.items()},
    }


def _osv_query(packages: Sequence[tuple[str, str, str]]) -> list[Mapping[str, Any]]:
    request_body = {
        "queries": [
            {
                "package": {"ecosystem": "Maven", "name": name},
                "version": version,
            }
            for name, version, _ in packages
        ]
    }
    request = urllib.request.Request(
        OSV_ENDPOINT,
        data=_canonical(request_body),
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
        raise JvmPackageCertificationError(
            f"OSV advisory retrieval failed: {error}"
        ) from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or len(results) != len(packages):
        raise JvmPackageCertificationError("OSV advisory response is incomplete")
    if any(not isinstance(item, dict) for item in results):
        raise JvmPackageCertificationError("OSV advisory result is malformed")
    return results


def certify_risk() -> dict[str, Any]:
    graph = synchronize(write=False)
    if graph["status"] != "passed":
        raise JvmPackageCertificationError("release graph does not reproduce")
    results = _osv_query(EXTERNAL_PACKAGES)
    affected = []
    for package, result in zip(EXTERNAL_PACKAGES, results, strict=True):
        vulnerabilities = result.get("vulns", [])
        if not isinstance(vulnerabilities, list):
            raise JvmPackageCertificationError(
                "OSV vulnerability inventory is malformed"
            )
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict) or not isinstance(
                vulnerability.get("id"), str
            ):
                raise JvmPackageCertificationError(
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
        "packages_queried": len(EXTERNAL_PACKAGES),
        "affected": affected,
        "license_dispositions": {
            "permitted": len(EXTERNAL_PACKAGES),
            "jna": "Apache-2.0 branch selected from LGPL-2.1-or-later OR Apache-2.0",
        },
        "graph_fingerprint": graph["graph_fingerprint"],
    }


def _tool(name: str, candidates: Sequence[str]) -> str:
    configured = os.environ.get(name)
    if configured and Path(configured).is_file():
        return configured
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise JvmPackageCertificationError(f"{name} is unavailable")


def _run(arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-5000:]
        raise JvmPackageCertificationError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _safe_reset(directory: Path) -> None:
    resolved = directory.resolve()
    target = (ROOT / "target").resolve()
    if resolved.parent != target or not resolved.name.startswith("jvm-adapter-package"):
        raise JvmPackageCertificationError(
            f"unsafe certification directory: {resolved}"
        )
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _jar_has_forbidden_payload(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    forbidden_suffixes = (".dll", ".so", ".dylib")
    forbidden_markers = ("/core/Parser", "/core/Compiler", "/emitters/")
    return any(name.endswith(forbidden_suffixes) for name in names) or any(
        marker in name for marker in forbidden_markers for name in names
    )


def certify_packages(native_library: Path) -> dict[str, Any]:
    graph = synchronize(write=False)
    if graph["status"] != "passed":
        raise JvmPackageCertificationError("release graph does not reproduce")
    native = native_library.resolve()
    if not native.is_file():
        raise JvmPackageCertificationError(f"native library is unavailable: {native}")
    maven = _tool("STRLING_MAVEN", ("mvn", "mvn.cmd"))
    gradle = _tool("STRLING_GRADLE", ("gradle", "gradle.bat"))
    java = _tool("STRLING_JAVA", ("java", "java.exe"))
    javac = _tool("STRLING_JAVAC", ("javac", "javac.exe"))
    repository_text = os.environ.get("STRLING_MAVEN_REPOSITORY")
    if not repository_text or not Path(repository_text).is_dir():
        raise JvmPackageCertificationError("STRLING_MAVEN_REPOSITORY is unavailable")
    repository = Path(repository_text).resolve()
    work = ROOT / "target/jvm-adapter-package-certification"
    _safe_reset(work)
    local_install = work / "repository"
    local_install.mkdir()
    environment = os.environ.copy()
    environment["STRLING_NATIVE_LIBRARY"] = str(native)
    environment["STRLING_LOCAL_MAVEN_REPOSITORY"] = str(local_install)
    _run([maven, "-o", "-B", "-q", "install"], ROOT / "bindings/jvm", environment)
    _run([maven, "-o", "-B", "-q", "install"], ROOT / "bindings/java", environment)
    _run(
        [
            gradle,
            "--offline",
            "--no-daemon",
            "clean",
            "test",
            "publishMavenPublicationToLocalInstallRepository",
        ],
        ROOT / "bindings/kotlin",
        environment,
    )

    coordinates = [
        ("com/strling/strling/3.0.0/strling-3.0.0.jar", repository),
        ("com/strling/strling-jvm/3.0.0/strling-jvm-3.0.0.jar", repository),
        (
            "com/strling/strling-kotlin/3.0.0/strling-kotlin-3.0.0.jar",
            local_install,
        ),
    ]
    product_jars = [root / relative for relative, root in coordinates]
    if any(not path.is_file() for path in product_jars):
        raise JvmPackageCertificationError(
            "one or more product jars were not installed"
        )
    if any(_jar_has_forbidden_payload(path) for path in product_jars):
        raise JvmPackageCertificationError(
            "a product jar contains native or semantic-copy payload"
        )

    external_jars = []
    for name, version, _ in EXTERNAL_PACKAGES:
        if name in {"org.jetbrains.kotlin:kotlin-stdlib", "org.jetbrains:annotations"}:
            continue
        group, artifact = name.split(":", 1)
        external_jars.append(
            repository
            / Path(*group.split("."))
            / artifact
            / version
            / f"{artifact}-{version}.jar"
        )
    if any(not path.is_file() for path in external_jars):
        raise JvmPackageCertificationError("the Java consumer graph is incomplete")
    classpath = os.pathsep.join(
        str(path) for path in [*product_jars[:2], *external_jars]
    )
    java_root = work / "java-consumer"
    java_root.mkdir()
    source = java_root / "Consumer.java"
    source.write_text(
        """import com.strling.Compiler;
import com.strling.jvm.NativeClient;
import java.nio.file.Paths;
public final class Consumer {
  public static void main(String[] args) {
    try (NativeClient client = NativeClient.load(Paths.get(args[0]).toAbsolutePath())) {
      Object result = new Compiler(client).parse("literal \\\"consumer\\\"");
      if (!(result instanceof java.util.Map)) throw new IllegalStateException("not canonical data");
      System.out.println("JAVA_CONSUMER_PASS");
    }
  }
}
""",
        encoding="utf-8",
        newline="\n",
    )
    _run(
        [javac, "--release", "11", "-cp", classpath, str(source)],
        java_root,
        environment,
    )
    java_output = _run(
        [
            java,
            "-cp",
            os.pathsep.join((str(java_root), classpath)),
            "Consumer",
            str(native),
        ],
        java_root,
        environment,
    )
    if "JAVA_CONSUMER_PASS" not in java_output:
        raise JvmPackageCertificationError("Java clean consumer did not complete")

    kotlin_root = work / "kotlin-consumer"
    (kotlin_root / "src/main/kotlin").mkdir(parents=True)
    (kotlin_root / "settings.gradle.kts").write_text(
        'rootProject.name = "strling-kotlin-consumer"\n', encoding="utf-8", newline="\n"
    )
    local_uri = local_install.as_posix()
    base_uri = repository.as_posix()
    (kotlin_root / "build.gradle.kts").write_text(
        f'''plugins {{ kotlin("jvm") version "2.0.20"; application }}
repositories {{ maven {{ url = uri("{local_uri}") }}; maven {{ url = uri("{base_uri}") }}; mavenCentral() }}
dependencies {{ implementation("com.strling:strling-kotlin:3.0.0") }}
application {{ mainClass.set("ConsumerKt") }}
''',
        encoding="utf-8",
        newline="\n",
    )
    (kotlin_root / "src/main/kotlin/Consumer.kt").write_text(
        """import com.strling.jvm.NativeClient
import java.nio.file.Paths
import strling.Compiler
fun main(args: Array<String>) {
    NativeClient.load(Paths.get(args[0]).toAbsolutePath()).use { client ->
        check(Compiler(client).parse("literal \\\"consumer\\\"") is Map<*, *>)
        println("KOTLIN_CONSUMER_PASS")
    }
}
""",
        encoding="utf-8",
        newline="\n",
    )
    kotlin_output = _run(
        [gradle, "--offline", "--no-daemon", "run", "--args", str(native)],
        kotlin_root,
        environment,
    )
    if "KOTLIN_CONSUMER_PASS" not in kotlin_output:
        raise JvmPackageCertificationError("Kotlin clean consumer did not complete")
    return {
        "status": "passed",
        "graph_fingerprint": graph["graph_fingerprint"],
        "product_jars": len(product_jars),
        "native_payloads": 0,
        "semantic_copy_payloads": 0,
        "clean_consumers": 2,
        "native_library": str(native),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write-graph", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--risk", action="store_true")
    mode.add_argument("--certify", action="store_true")
    parser.add_argument("--native-library", type=Path)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        if arguments.write_graph:
            result = synchronize(write=True)
        elif arguments.risk:
            result = certify_risk()
        elif arguments.certify:
            native = arguments.native_library or Path(
                os.environ.get("STRLING_NATIVE_LIBRARY", "")
            )
            result = certify_packages(native)
        else:
            result = synchronize(write=False)
    except (JvmPackageCertificationError, OSError, ValueError) as error:
        result = {"status": "failed", "error": str(error)}
    print(json.dumps(result, sort_keys=True) if arguments.json else result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
