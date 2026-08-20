from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tooling import jvm_adapter_package as package


class JvmAdapterPackageTests(unittest.TestCase):
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
