from __future__ import annotations

import copy
import unittest

from tooling import dynamic_language_adapter_package as package


class DynamicLanguageAdapterPackageTests(unittest.TestCase):
    def test_release_graph_is_exact_and_has_no_native_or_semantic_payload(self) -> None:
        graph = package.build_graph()

        self.assertEqual("dynamic-language-release-graphs-v1", graph["schema_version"])
        self.assertEqual(set(package.BINDINGS), set(graph["bindings"]))
        self.assertEqual(graph["fingerprint"], package._fingerprint(graph))
        self.assertEqual([], graph["policy"]["native_payloads_packaged"])
        self.assertEqual([], graph["policy"]["semantic_runtime_packages"])
        for binding in graph["bindings"].values():
            self.assertFalse(binding["native_payload_packaged"])

    def test_fingerprint_rejects_runtime_graph_mutation(self) -> None:
        graph = package.build_graph()
        changed = copy.deepcopy(graph)
        changed["bindings"]["ruby"]["runtime_dependencies"].append("compiler-copy:1")

        self.assertNotEqual(graph["fingerprint"], package._fingerprint(changed))


if __name__ == "__main__":
    unittest.main()
