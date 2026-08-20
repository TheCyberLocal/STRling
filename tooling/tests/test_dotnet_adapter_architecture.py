from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from tooling.architecture_fitness import (
    candidate_paths,
    dotnet_adapter_boundary_findings,
)
from tooling.governance import matches_any


class DotNetAdapterArchitectureTests(unittest.TestCase):
    def test_candidate_paths_ignores_deleted_tracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "bindings/csharp/src/STRling/Canonical/Compiler.cs"
            live.parent.mkdir(parents=True)
            live.write_text("class Compiler {}", encoding="utf-8")
            git_output = (
                b"bindings/csharp/src/STRling/Canonical/Compiler.cs\0"
                b"bindings/csharp/src/STRling/Core/Parser.cs\0"
            )

            with patch(
                "tooling.architecture_fitness.subprocess.run",
                return_value=CompletedProcess([], 0, git_output, b""),
            ):
                paths = candidate_paths(root)

        self.assertEqual(["bindings/csharp/src/STRling/Canonical/Compiler.cs"], paths)

    def test_rejects_semantic_copy_and_fsharp_native_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            facade = root / "bindings/fsharp/src/STRling.FSharp/Api.fs"
            facade.parent.mkdir(parents=True)
            facade.write_text("let handle = NativeLibrary.Load path", encoding="utf-8")
            retired = root / "bindings/csharp/src/STRling/Core/Parser.cs"
            retired.parent.mkdir(parents=True)
            retired.write_text("class Parser {}", encoding="utf-8")
            manifest = root / "bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("missing", encoding="utf-8")

            findings = dotnet_adapter_boundary_findings(
                root,
                {
                    "sources": ["bindings/fsharp/src/STRling.FSharp/**/*.fs"],
                    "fsharp_sources": ["bindings/fsharp/src/STRling.FSharp/**/*.fs"],
                    "forbidden_paths": ["bindings/csharp/src/STRling/Core/Parser.cs"],
                    "forbidden_markers": [],
                    "fsharp_forbidden_markers": ["NativeLibrary"],
                    "required_markers": [
                        {
                            "path": manifest.relative_to(root).as_posix(),
                            "markers": ["ProjectReference"],
                        }
                    ],
                },
                matches_any,
            )

        self.assertEqual(3, len(findings))


if __name__ == "__main__":
    unittest.main()
