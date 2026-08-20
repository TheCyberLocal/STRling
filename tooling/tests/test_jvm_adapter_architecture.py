from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.architecture_fitness import jvm_adapter_boundary_findings
from tooling.governance import matches_any


class JvmAdapterArchitectureTests(unittest.TestCase):
    def test_rejects_semantic_copy_and_alternate_native_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            facade = root / "bindings/java/src/main/java/com/strling/Facade.java"
            facade.parent.mkdir(parents=True)
            facade.write_text("class Facade { com.sun.jna.Pointer value; }", encoding="utf-8")
            retired = root / "bindings/java/src/main/java/com/strling/core/Parser.java"
            retired.parent.mkdir(parents=True)
            retired.write_text("class Parser {}", encoding="utf-8")
            manifest = root / "bindings/java/pom.xml"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("missing", encoding="utf-8")

            findings = jvm_adapter_boundary_findings(
                root,
                {
                    "sources": ["bindings/java/src/main/java/**/*.java"],
                    "forbidden_paths": ["bindings/java/src/main/java/com/strling/core/**"],
                    "forbidden_markers": ["com.sun.jna"],
                    "required_markers": [
                        {"path": "bindings/java/pom.xml", "markers": ["strling-jvm"]}
                    ],
                },
                matches_any,
            )

        self.assertEqual(3, len(findings))


if __name__ == "__main__":
    unittest.main()
