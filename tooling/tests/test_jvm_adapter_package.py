from __future__ import annotations

import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tooling import jvm_adapter_package as package


class JvmAdapterPackageTests(unittest.TestCase):
    def test_repository_gradle_wrapper_precedes_host_tool(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = (
                root
                / "bindings/kotlin"
                / ("gradlew.bat" if package.os.name == "nt" else "gradlew")
            )
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text("governed wrapper", encoding="utf-8")
            with (
                patch.object(package, "ROOT", root),
                patch.object(package, "_tool", side_effect=AssertionError),
            ):
                self.assertEqual(str(wrapper), package._gradle_tool())

    def test_host_gradle_is_fallback_when_wrapper_is_absent(self) -> None:
        with TemporaryDirectory() as directory:
            with (
                patch.object(package, "ROOT", Path(directory)),
                patch.object(package, "_tool", return_value="host-gradle") as tool,
            ):
                self.assertEqual("host-gradle", package._gradle_tool())
                tool.assert_called_once_with("STRLING_GRADLE", ("gradle", "gradle.bat"))

    def test_release_graph_is_exact_and_selects_apache_jna_branch(self) -> None:
        graph = package.build_graph()

        self.assertEqual("jvm-release-graph-v1", graph["schema_version"])
        self.assertEqual(9, len(graph["packages"]))
        self.assertEqual(graph["fingerprint"], package._fingerprint(graph))
        jna = next(
            item
            for item in graph["packages"]
            if item["coordinate"] == "net.java.dev.jna:jna:5.19.1"
        )
        self.assertEqual("Apache-2.0 branch selected", jna["license_disposition"])
        self.assertFalse(graph["native_payload"]["packaged"])

    def test_live_risk_requires_complete_advisory_results(self) -> None:
        clean = [{} for _ in package.EXTERNAL_PACKAGES]
        with patch.object(package, "_osv_query", return_value=clean):
            result = package.certify_risk()
        self.assertEqual("passed", result["status"])
        self.assertEqual(len(package.EXTERNAL_PACKAGES), result["packages_queried"])

        affected = copy.deepcopy(clean)
        affected[0] = {"vulns": [{"id": "OSV-TEST-1"}]}
        with patch.object(package, "_osv_query", return_value=affected):
            result = package.certify_risk()
        self.assertEqual("failed", result["status"])
        self.assertEqual("OSV-TEST-1", result["affected"][0]["advisory"])


if __name__ == "__main__":
    unittest.main()
