from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tooling import dotnet_adapter_package as package


class DotNetAdapterPackageTests(unittest.TestCase):
    def test_release_graph_is_exact_and_certifies_one_native_rid(self) -> None:
        graph = package.build_graph()

        self.assertEqual("dotnet-release-graph-v1", graph["schema_version"])
        self.assertEqual(18, len(graph["packages"]))
        self.assertEqual(graph["fingerprint"], package._fingerprint(graph))
        self.assertEqual(["win-x64"], graph["native_payload"]["certified_rids"])
        self.assertEqual(
            ["runtimes/win-x64/native/strling_interop.dll"],
            graph["native_payload"]["assets"],
        )
        fsharp = next(
            item
            for item in graph["packages"]
            if item["coordinate"] == "FSharp.Core:9.0.300"
        )
        self.assertEqual(["runtime", "test"], fsharp["scopes"])
        self.assertEqual("MIT", fsharp["license"])

    def test_live_risk_requires_complete_clean_advisory_results(self) -> None:
        clean = [{} for _ in package.EXTERNAL_PACKAGES]
        resolved = {name: set() for name in package.PROJECTS}
        with (
            patch.object(package, "verify_resolved_graph", return_value=resolved),
            patch.object(package, "_osv_query", return_value=clean),
        ):
            result = package.certify_risk()
        self.assertEqual("passed", result["status"])
        self.assertEqual(len(package.EXTERNAL_PACKAGES), result["packages_queried"])

        affected = copy.deepcopy(clean)
        affected[0] = {"vulns": [{"id": "OSV-TEST-1"}]}
        with (
            patch.object(package, "verify_resolved_graph", return_value=resolved),
            patch.object(package, "_osv_query", return_value=affected),
        ):
            result = package.certify_risk()
        self.assertEqual("failed", result["status"])
        self.assertEqual("OSV-TEST-1", result["affected"][0]["advisory"])


if __name__ == "__main__":
    unittest.main()
