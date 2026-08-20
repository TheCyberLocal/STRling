from __future__ import annotations

import copy
import unittest

from tooling.typescript_python_adapter_runtime import (
    AdapterRuntimeError,
    EXPECTED_ACTION_COUNT,
    assert_parity,
    build_actions,
)


class TypeScriptPythonAdapterRuntimeTests(unittest.TestCase):
    def test_live_action_denominator_is_closed(self) -> None:
        actions = build_actions()
        self.assertEqual(len(actions), EXPECTED_ACTION_COUNT)
        self.assertEqual(
            len({action["id"] for action in actions}), EXPECTED_ACTION_COUNT
        )
        self.assertEqual(
            sum(action["kind"] == "simply.compile" for action in actions), 32
        )
        self.assertEqual(sum(action["kind"] == "compile" for action in actions), 7)

    def test_parity_rejects_one_host_mutation(self) -> None:
        actions = [{"id": "case"}]
        python_results = [{"id": "case", "state": "value", "value": {"x": 1}}]
        node_results = copy.deepcopy(python_results)
        node_results[0]["value"]["x"] = 2
        with self.assertRaisesRegex(AdapterRuntimeError, "Python/native"):
            assert_parity(actions, python_results, node_results)


if __name__ == "__main__":
    unittest.main()
