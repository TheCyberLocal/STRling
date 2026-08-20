from __future__ import annotations

import unittest

from tooling.jvm_adapter_runtime import _fingerprint


class JvmAdapterRuntimeTests(unittest.TestCase):
    def test_fingerprint_is_order_stable(self) -> None:
        self.assertEqual(_fingerprint({"b": 2, "a": 1}), _fingerprint({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
